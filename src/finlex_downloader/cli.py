"""CLI for Finlex downloader."""

import argparse
import sys
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from typing import Optional

from .client import FinlexClient
from .downloader import download_document, DownloadOptions, DownloadResult
from .listing import list_documents, ListConfig, get_year_range, DOCUMENT_TYPES
from .logging_config import setup_logging, logger
from .state import StateManager, ManifestManager, ManifestEntry


def parse_args(args: Optional[list[str]] = None) -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        prog="finlex-downloader",
        description="Download Akoma Ntoso documents from Finlex Open Data API",
    )

    # Output
    parser.add_argument(
        "-o", "--output",
        type=Path,
        default=Path("./finlex-data"),
        help="Output directory (default: ./finlex-data)",
    )

    # Document types
    parser.add_argument(
        "--types",
        nargs="+",
        choices=["act", "judgment", "doc", "authority-regulation"],
        default=["act"],
        help="Document categories to download (default: act)",
    )
    parser.add_argument(
        "--subtypes",
        nargs="+",
        help="Restrict to specific document subtypes (e.g., statute-consolidated). Omit to download all subtypes for the category.",
    )

    # Year settings
    parser.add_argument(
        "--years",
        type=int,
        default=1,
        help="Number of years to download (default: 1)",
    )
    parser.add_argument(
        "--years-act",
        type=int,
        help="Override years for act category",
    )
    parser.add_argument(
        "--years-judgment",
        type=int,
        help="Override years for judgment category",
    )
    parser.add_argument(
        "--years-doc",
        type=int,
        help="Override years for doc category",
    )
    parser.add_argument(
        "--years-authority-regulation",
        type=int,
        help="Override years for authority-regulation",
    )

    # Language
    parser.add_argument(
        "--lang",
        default="fin@",
        help="Language and version marker (default: fin@)",
    )

    # Paging
    parser.add_argument(
        "--limit",
        type=int,
        default=10,
        help="Page size for list requests (default: 10, max: 10)",
    )
    parser.add_argument(
        "--max-pages",
        type=int,
        help="Maximum pages to fetch per document type",
    )

    # API filtering
    parser.add_argument(
        "--type-statute",
        help="Filter by typeStatute param (e.g., 'act')",
    )
    parser.add_argument(
        "--category-statute",
        help="Filter by categoryStatute param (e.g., 'new-statute')",
    )

    # Download options
    parser.add_argument(
        "--sleep",
        type=float,
        default=1.0,
        help="Minimum seconds between requests per worker (default: 1)",
    )
    parser.add_argument(
        "--sleep-max",
        type=float,
        default=3.0,
        help="Maximum seconds between requests per worker (default: 3). "
             "Actual delay is random between --sleep and --sleep-max.",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=5,
        help="Number of parallel download workers (default: 5)",
    )
    parser.add_argument(
        "--pdf",
        action="store_true",
        help="Also download PDF versions",
    )
    parser.add_argument(
        "--zip",
        action="store_true",
        help="Also download ZIP packages",
    )
    parser.add_argument(
        "--media",
        action="store_true",
        help="Also download media files",
    )
    parser.add_argument(
        "--in-force-only",
        action="store_true",
        help="Skip statutes that are not currently in force (checks finlex:isInForce in XML)",
    )

    # Control
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-download existing files",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be downloaded without downloading",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Resume from last checkpoint",
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Reset state and start fresh",
    )

    # Logging
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose output",
    )

    return parser.parse_args(args)


def get_years_for_type(args: argparse.Namespace, category: str) -> int:
    """Get years setting for a specific category."""
    override_map = {
        "act": args.years_act,
        "judgment": args.years_judgment,
        "doc": args.years_doc,
        "authority-regulation": args.years_authority_regulation,
    }
    return override_map.get(category) or args.years


def run_download(args: argparse.Namespace) -> int:
    """Run the download process.
    
    Returns:
        Exit code (0 for success).
    """
    # Setup logging
    setup_logging("DEBUG" if args.verbose else "INFO")

    # Initialize managers
    state_file = args.output / ".state.json"
    manifest_file = args.output / "manifest.json"

    state_manager = StateManager(state_file)
    manifest_manager = ManifestManager(manifest_file)

    # Lock for thread-safe state/manifest updates
    state_lock = threading.Lock()

    # Handle reset
    if args.reset:
        state_manager.reset()
        logger.info("State reset, starting fresh")

    # Load existing state if resuming
    if args.resume:
        state_manager.load()

    # Listing client (sequential, used only for pagination)
    list_client = FinlexClient(
        sleep_seconds=args.sleep,
        sleep_max=args.sleep_max,
    )

    # Download options
    download_opts = DownloadOptions(
        output_dir=args.output,
        fetch_pdf=args.pdf,
        fetch_zip=args.zip,
        fetch_media=args.media,
        force=args.force,
        dry_run=args.dry_run,
        in_force_only=args.in_force_only,
    )

    workers = max(1, args.workers)
    logger.info(f"Output directory: {args.output}")
    logger.info(f"Document types: {args.types}")
    logger.info(f"Language: {args.lang}")
    logger.info(f"Workers: {workers}, sleep: {args.sleep}-{args.sleep_max}s")

    def _process_item(akn_uri: str) -> DownloadResult:
        """Download a single document using a thread-local client."""
        client = _get_thread_client(args)
        return download_document(client, akn_uri, download_opts)

    def _record_result(result: DownloadResult) -> None:
        """Thread-safe recording of download result."""
        manifest_entry = ManifestEntry(
            akn_uri=result.akn_uri,
            status=result.status,
            timestamp=result.timestamp,
            files=result.files,
            error=result.error,
        )
        with state_lock:
            manifest_manager.add(manifest_entry)
            if result.status in ("success", "skipped", "skipped-repealed"):
                state_manager.mark_completed(result.akn_uri)

    try:
        for category in args.types:
            # Handle authority-regulation specially
            if category == "authority-regulation":
                doc_types = ["authority-regulation"]
                actual_category = "doc"
            else:
                doc_types = DOCUMENT_TYPES.get(category, [])
                actual_category = category

            # Filter subtypes if specified
            if args.subtypes:
                doc_types = [dt for dt in doc_types if dt in args.subtypes]
                if not doc_types:
                    logger.info(f"Skipping {category}: no matching subtypes")
                    continue

            years = get_years_for_type(args, category)
            start_year, end_year = get_year_range(years)
            logger.info(f"Processing {category}: years {start_year}-{end_year}")

            for doc_type in doc_types:
                logger.info(f"  Document type: {doc_type}")

                # Check resume point
                resume_page = 1
                if args.resume:
                    resume_page = state_manager.get_resume_page(actual_category, doc_type)
                    if resume_page > 1:
                        logger.info(f"  Resuming from page {resume_page}")

                # Configure listing
                list_config = ListConfig(
                    category=actual_category,
                    document_type=doc_type,
                    lang_and_version=args.lang,
                    start_year=start_year,
                    end_year=end_year,
                    limit=min(args.limit, 10),
                    max_pages=args.max_pages,
                    type_statute=args.type_statute,
                    category_statute=args.category_statute,
                )

                state_manager.start_session(actual_category, doc_type)

                # Collect URIs to download (skipping already completed)
                uris_to_download = []
                page = 0
                for item in list_documents(list_client, list_config):
                    page += 1
                    with state_lock:
                        if state_manager.is_completed(item.akn_uri):
                            logger.debug(f"Already completed: {item.akn_uri}")
                            continue
                    uris_to_download.append(item.akn_uri)

                logger.info(f"  Found {len(uris_to_download)} documents to download")

                if not uris_to_download:
                    continue

                # Download in parallel
                with ThreadPoolExecutor(max_workers=workers) as executor:
                    futures = {
                        executor.submit(_process_item, uri): uri
                        for uri in uris_to_download
                    }
                    completed = 0
                    for future in as_completed(futures):
                        uri = futures[future]
                        try:
                            result = future.result()
                            _record_result(result)
                            completed += 1
                            if completed % 100 == 0:
                                logger.info(f"  Progress: {completed}/{len(uris_to_download)}")
                        except Exception as e:
                            logger.error(f"Worker error for {uri}: {e}")
                            _record_result(DownloadResult(
                                akn_uri=uri,
                                status="error",
                                timestamp=datetime.now().isoformat(),
                                error=str(e),
                            ))

                with state_lock:
                    state_manager.set_page(page)

    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        return 130
    finally:
        list_client.close()
        _cleanup_thread_clients()

    # Summary
    summary = manifest_manager.summary()
    logger.info(
        f"Download complete: {summary['success']} success, "
        f"{summary['skipped']} skipped, "
        f"{summary['skipped_repealed']} skipped (repealed), "
        f"{summary['error']} errors"
    )

    return 0 if summary["error"] == 0 else 1


# Thread-local storage for per-worker HTTP clients
_thread_local = threading.local()
_thread_clients: list[FinlexClient] = []
_thread_clients_lock = threading.Lock()


def _get_thread_client(args: argparse.Namespace) -> FinlexClient:
    """Get or create a FinlexClient for the current thread."""
    client = getattr(_thread_local, "client", None)
    if client is None:
        client = FinlexClient(
            sleep_seconds=args.sleep,
            sleep_max=args.sleep_max,
        )
        _thread_local.client = client
        with _thread_clients_lock:
            _thread_clients.append(client)
    return client


def _cleanup_thread_clients() -> None:
    """Close all thread-local clients."""
    with _thread_clients_lock:
        for client in _thread_clients:
            client.close()
        _thread_clients.clear()


def main(args: Optional[list[str]] = None) -> int:
    """Main entry point."""
    parsed = parse_args(args)
    return run_download(parsed)


if __name__ == "__main__":
    sys.exit(main())
