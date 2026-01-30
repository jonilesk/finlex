"""CLI for Finlex downloader."""

import argparse
import sys
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

    # Download options
    parser.add_argument(
        "--sleep",
        type=float,
        default=5.0,
        help="Seconds between requests (default: 5)",
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

    # Handle reset
    if args.reset:
        state_manager.reset()
        logger.info("State reset, starting fresh")

    # Load existing state if resuming
    if args.resume:
        state_manager.load()

    # Initialize client
    client = FinlexClient(sleep_seconds=args.sleep)

    # Download options
    download_opts = DownloadOptions(
        output_dir=args.output,
        fetch_pdf=args.pdf,
        fetch_zip=args.zip,
        fetch_media=args.media,
        force=args.force,
        dry_run=args.dry_run,
    )

    logger.info(f"Output directory: {args.output}")
    logger.info(f"Document types: {args.types}")
    logger.info(f"Language: {args.lang}")

    try:
        for category in args.types:
            # Handle authority-regulation specially
            if category == "authority-regulation":
                doc_types = ["authority-regulation"]
                actual_category = "doc"
            else:
                doc_types = DOCUMENT_TYPES.get(category, [])
                actual_category = category

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
                )

                state_manager.start_session(actual_category, doc_type)

                # Process documents
                page = 0
                for item in list_documents(client, list_config):
                    page += 1
                    
                    # Skip if already completed
                    if state_manager.is_completed(item.akn_uri):
                        logger.debug(f"Already completed: {item.akn_uri}")
                        continue

                    # Download document
                    result = download_document(client, item.akn_uri, download_opts)

                    # Record in manifest
                    manifest_entry = ManifestEntry(
                        akn_uri=result.akn_uri,
                        status=result.status,
                        timestamp=result.timestamp,
                        files=result.files,
                        error=result.error,
                    )
                    manifest_manager.add(manifest_entry)

                    # Update state
                    if result.status in ("success", "skipped"):
                        state_manager.mark_completed(item.akn_uri)

                    state_manager.set_page(page)

    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        return 130
    finally:
        client.close()

    # Summary
    summary = manifest_manager.summary()
    logger.info(f"Download complete: {summary['success']} success, {summary['skipped']} skipped, {summary['error']} errors")

    return 0 if summary["error"] == 0 else 1


def main(args: Optional[list[str]] = None) -> int:
    """Main entry point."""
    parsed = parse_args(args)
    return run_download(parsed)


if __name__ == "__main__":
    sys.exit(main())
