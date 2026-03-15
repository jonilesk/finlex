"""CLI for building Finlex skill folders for AI agents."""

import argparse
import sys
from pathlib import Path
from typing import Optional

from finlex_downloader.logging_config import setup_logging, logger
from .skill_builder import build_skills


def parse_args(args: Optional[list[str]] = None) -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        prog="finlex-skills",
        description="Build AI-agent skill folders from Finlex XML data",
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
        default=Path("./finlex-skills"),
        help="Output directory for skill folders (default: ./finlex-skills)",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose output",
    )

    return parser.parse_args(args)


def main(args: Optional[list[str]] = None) -> int:
    """Main entry point."""
    parsed = parse_args(args)
    setup_logging("DEBUG" if parsed.verbose else "INFO")

    logger.info(f"Input: {parsed.input}")
    logger.info(f"Output: {parsed.output}")

    stats = build_skills(parsed.input, parsed.output)

    if not stats:
        logger.warning("No statutes were converted")
        return 1

    total = sum(s.total for s in stats.values())
    logger.info(f"Built {len(stats)} skill folders with {total} statutes total")
    return 0


if __name__ == "__main__":
    sys.exit(main())
