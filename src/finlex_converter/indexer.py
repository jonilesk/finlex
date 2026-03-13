"""Build a citation index from converted Markdown files."""

import json
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional

from finlex_downloader.logging_config import logger
from .parser import parse_statute


@dataclass
class IndexEntry:
    """A single entry in the citation index."""

    citation: str  # e.g. "731/1999"
    title: str
    path: str  # relative path to statute.md
    subtype: str = ""  # e.g. "statute", "statute-consolidated"
    eli: str = ""
    date_issued: str = ""


@dataclass
class StatuteIndex:
    """Index of all statutes, keyed by citation."""

    entries: dict[str, IndexEntry] = field(default_factory=dict)

    def add(self, entry: IndexEntry) -> None:
        """Add an entry to the index."""
        self.entries[entry.citation] = entry

    def lookup(self, citation: str) -> Optional[IndexEntry]:
        """Look up a citation in the index."""
        return self.entries.get(citation)

    def save(self, path: Path) -> None:
        """Save index to JSON file."""
        data = {k: asdict(v) for k, v in self.entries.items()}
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        logger.info(f"Index saved: {len(self.entries)} entries to {path}")

    @classmethod
    def load(cls, path: Path) -> "StatuteIndex":
        """Load index from JSON file."""
        index = cls()
        if not path.exists():
            return index
        data = json.loads(path.read_text(encoding="utf-8"))
        for citation, entry_data in data.items():
            index.entries[citation] = IndexEntry(**entry_data)
        return index


def build_index_from_xml(input_dir: Path, md_dir: Path) -> StatuteIndex:
    """Build a citation index by parsing XML files and recording Markdown paths.

    Args:
        input_dir: Root directory containing downloaded XML.
        md_dir: Root directory containing converted Markdown.

    Returns:
        Populated StatuteIndex.
    """
    index = StatuteIndex()

    for xml_path in sorted(input_dir.rglob("main.xml")):
        try:
            xml_bytes = xml_path.read_bytes()
        except OSError as e:
            logger.warning(f"Cannot read {xml_path}: {e}")
            continue

        statute = parse_statute(xml_bytes)
        if statute is None:
            continue

        meta = statute.metadata
        citation = meta.doc_number or f"{meta.number}/{meta.year}"
        if not citation or citation == "/":
            continue

        # Compute relative Markdown path
        relative = xml_path.parent.relative_to(input_dir)
        md_path = str(relative / "statute.md")

        entry = IndexEntry(
            citation=citation,
            title=meta.title,
            path=md_path,
            subtype=meta.subtype,
            eli=meta.eli,
            date_issued=meta.date_issued,
        )
        index.add(entry)

    logger.info(f"Built index with {len(index.entries)} entries")
    return index
