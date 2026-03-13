"""CLI for converting downloaded Finlex AKN XML to Markdown."""

import argparse
import sys
from pathlib import Path
from typing import Optional

from finlex_downloader.logging_config import setup_logging, logger
from .parser import parse_statute
from .renderer import render_statute
from .indexer import build_index_from_xml


def parse_args(args: Optional[list[str]] = None) -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        prog="finlex-converter",
        description="Convert Finlex AKN XML documents to Markdown",
    )

    parser.add_argument(
        "-i", "--input",
        type=Path,
        default=Path("./finlex-data"),
        help="Input directory with downloaded XML (default: ./finlex-data)",
    )
    parser.add_argument(
        "-o", "--output",
        type=Path,
        default=Path("./finlex-md"),
        help="Output directory for Markdown files (default: ./finlex-md)",
    )
    parser.add_argument(
        "--category",
        choices=["act", "judgment", "doc"],
        help="Only convert a specific category",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose output",
    )

    return parser.parse_args(args)


def find_xml_files(input_dir: Path, category: Optional[str] = None) -> list[Path]:
    """Find all main.xml files in the input directory.

    Args:
        input_dir: Root directory to search.
        category: Optional category filter (act, judgment, doc).

    Returns:
        List of Path objects pointing to main.xml files.
    """
    if category:
        search_dir = input_dir / category
    else:
        search_dir = input_dir

    if not search_dir.exists():
        logger.warning(f"Directory not found: {search_dir}")
        return []

    return sorted(search_dir.rglob("main.xml"))


def convert_file(xml_path: Path, input_dir: Path, output_dir: Path) -> Optional[Path]:
    """Convert a single XML file to Markdown.

    Args:
        xml_path: Path to main.xml file.
        input_dir: Root input directory (for computing relative path).
        output_dir: Root output directory.

    Returns:
        Path to output Markdown file, or None on failure.
    """
    try:
        xml_bytes = xml_path.read_bytes()
    except OSError as e:
        logger.error(f"Failed to read {xml_path}: {e}")
        return None

    statute = parse_statute(xml_bytes)
    if statute is None:
        logger.error(f"Failed to parse {xml_path}")
        return None

    markdown = render_statute(statute)

    # Compute output path: replace main.xml with statute.md, preserve directory structure
    relative = xml_path.parent.relative_to(input_dir)
    out_dir = output_dir / relative
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "statute.md"

    try:
        out_path.write_text(markdown, encoding="utf-8")
    except OSError as e:
        logger.error(f"Failed to write {out_path}: {e}")
        return None

    return out_path


def run_convert(args: argparse.Namespace) -> int:
    """Run the conversion process.

    Returns:
        Exit code (0 for success).
    """
    setup_logging("DEBUG" if args.verbose else "INFO")

    xml_files = find_xml_files(args.input, args.category)

    if not xml_files:
        logger.info("No XML files found to convert")
        return 0

    logger.info(f"Found {len(xml_files)} XML files to convert")

    success = 0
    failed = 0
    for xml_path in xml_files:
        out_path = convert_file(xml_path, args.input, args.output)
        if out_path:
            success += 1
            logger.debug(f"Converted: {out_path}")
        else:
            failed += 1

    logger.info(f"Conversion complete: {success} success, {failed} failed")

    # Build citation index
    index = build_index_from_xml(args.input, args.output)
    index.save(args.output / "index.json")

    return 0 if failed == 0 else 1


def main(args: Optional[list[str]] = None) -> int:
    """Main entry point."""
    parsed = parse_args(args)
    return run_convert(parsed)


if __name__ == "__main__":
    sys.exit(main())
