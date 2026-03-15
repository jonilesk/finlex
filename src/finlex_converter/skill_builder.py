"""Build AI-agent skill folders from downloaded Finlex XML data.

Orchestrates: read XML → classify topic → convert to Markdown → write to skill folders.
"""

import json
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional

from finlex_downloader.logging_config import logger
from .parser import parse_statute, Metadata
from .renderer import render_statute
from .topics import classify, should_include, SKILL_METADATA


@dataclass
class SkillEntry:
    """A single statute entry for indexing."""

    citation: str
    title: str
    path: str  # relative to skills root
    type: str = ""
    ministry: str = ""
    skill: str = ""
    subtopic: str = ""
    eli: str = ""
    date_issued: str = ""
    xml_size: int = 0


@dataclass
class SkillStats:
    """Statistics for a skill folder."""

    total: int = 0
    acts: int = 0
    decrees: int = 0
    entries: list[SkillEntry] = field(default_factory=list)


def build_skills(
    input_dir: Path,
    output_dir: Path,
    category: Optional[str] = "act",
) -> dict[str, SkillStats]:
    """Build skill folders from XML data.

    Args:
        input_dir: Root directory with downloaded XML (e.g., ./finlex-data).
        output_dir: Output directory for skill folders (e.g., ./finlex-skills).
        category: Category filter (default: "act").

    Returns:
        Dict of skill name → stats.
    """
    # Find all XML files
    if category:
        search_dir = input_dir / category
    else:
        search_dir = input_dir

    if not search_dir.exists():
        logger.warning(f"Directory not found: {search_dir}")
        return {}

    xml_files = sorted(search_dir.rglob("main.xml"))
    logger.info(f"Found {len(xml_files)} XML files to process")

    stats: dict[str, SkillStats] = {}
    master_index: dict[str, dict] = {}
    skipped = 0
    converted = 0
    failed = 0

    for xml_path in xml_files:
        try:
            xml_bytes = xml_path.read_bytes()
            xml_size = len(xml_bytes)
        except OSError as e:
            logger.error(f"Cannot read {xml_path}: {e}")
            failed += 1
            continue

        statute = parse_statute(xml_bytes)
        if statute is None:
            failed += 1
            continue

        meta = statute.metadata

        # Filter
        if not should_include(meta.type_statute, meta.title, xml_size):
            skipped += 1
            continue

        # Classify
        topic = classify(meta.ministry_id, meta.title, xml_size)

        # Render with frontmatter
        markdown = render_statute(
            statute,
            skill=topic.skill,
            subtopic=topic.subtopic,
            frontmatter=True,
        )

        # Compute output path
        citation = meta.doc_number or f"{meta.number}/{meta.year}"
        filename = _citation_to_filename(citation)
        if not filename:
            logger.warning(f"Cannot generate filename for {xml_path}")
            failed += 1
            continue

        if topic.subtopic:
            rel_path = Path(topic.skill) / topic.subtopic / filename
        else:
            rel_path = Path(topic.skill) / filename

        out_path = output_dir / rel_path
        out_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            out_path.write_text(markdown, encoding="utf-8")
        except OSError as e:
            logger.error(f"Cannot write {out_path}: {e}")
            failed += 1
            continue

        converted += 1

        # Track stats
        skill_stats = stats.setdefault(topic.skill, SkillStats())
        skill_stats.total += 1
        if meta.type_statute == "act":
            skill_stats.acts += 1
        elif meta.type_statute == "decree":
            skill_stats.decrees += 1

        entry = SkillEntry(
            citation=citation,
            title=meta.title,
            path=str(rel_path),
            type=meta.type_statute,
            ministry=meta.ministry_name,
            skill=topic.skill,
            subtopic=topic.subtopic,
            eli=meta.eli,
            date_issued=meta.date_issued,
            xml_size=xml_size,
        )
        skill_stats.entries.append(entry)
        if citation in master_index:
            logger.warning(f"Duplicate citation {citation}, overwriting previous entry")
        master_index[citation] = asdict(entry)

        if converted % 500 == 0:
            logger.info(f"Progress: {converted} converted, {skipped} skipped")

    logger.info(
        f"Done: {converted} converted, {skipped} skipped, {failed} failed"
    )

    # Write indexes and READMEs
    _write_master_index(output_dir, master_index)
    _write_skill_readmes(output_dir, stats)
    _write_skill_indexes(output_dir, stats)
    _write_master_readme(output_dir, stats)

    return stats


def _citation_to_filename(citation: str) -> str:
    """Convert citation like '872/2019' to filename '872-2019.md'."""
    citation = citation.strip()
    if "/" not in citation:
        return ""
    parts = citation.split("/")
    if len(parts) != 2:
        return ""
    number, year = parts[0].strip(), parts[1].strip()
    if not number or not year:
        return ""
    return f"{number}-{year}.md"


def _write_master_index(output_dir: Path, index: dict):
    """Write master index.json mapping citation → entry."""
    path = output_dir / "index.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(index, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    logger.info(f"Master index: {len(index)} entries → {path}")


def _write_skill_indexes(output_dir: Path, stats: dict[str, SkillStats]):
    """Write per-folder _index.json."""
    for skill, skill_stats in stats.items():
        entries = {e.citation: asdict(e) for e in skill_stats.entries}
        path = output_dir / skill / "_index.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(entries, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )


def _write_skill_readmes(output_dir: Path, stats: dict[str, SkillStats]):
    """Write README.md for each skill folder."""
    for skill, skill_stats in stats.items():
        meta = SKILL_METADATA.get(skill, ("Muu lainsäädäntö", ""))
        title, description = meta

        lines = [f"# {title}", "", description, ""]

        # Collect subtopics
        subtopics: dict[str, list[SkillEntry]] = {}
        flat_entries: list[SkillEntry] = []
        for entry in skill_stats.entries:
            if entry.subtopic:
                subtopics.setdefault(entry.subtopic, []).append(entry)
            else:
                flat_entries.append(entry)

        if subtopics:
            lines.append("## Alateemat")
            lines.append("")
            for sub_name in sorted(subtopics.keys()):
                sub_entries = subtopics[sub_name]
                lines.append(f"### {sub_name}")
                lines.append(f"{len(sub_entries)} säädöstä.")
                lines.append("")

        # Law table
        all_entries = sorted(skill_stats.entries, key=lambda e: -e.xml_size)
        lines.append(f"## Säädökset ({skill_stats.total} kpl)")
        lines.append("")
        lines.append("| Säädös | Nimi | Tyyppi | Koko |")
        lines.append("|--------|------|--------|------|")
        for entry in all_entries:
            size_str = f"{entry.xml_size // 1024}KB"
            typ = "laki" if entry.type == "act" else "asetus"
            lines.append(
                f"| {entry.citation} | {entry.title} | {typ} | {size_str} |"
            )

        lines.append("")

        path = output_dir / skill / "README.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("\n".join(lines), encoding="utf-8")


def _write_master_readme(output_dir: Path, stats: dict[str, SkillStats]):
    """Write top-level README.md."""
    lines = [
        "# Finlex — Suomen lainsäädäntö (AI Skills)",
        "",
        "Suomen ajantasainen lainsäädäntö Markdown-muodossa, "
        "järjestettynä aihealueittain AI-agenttien taitokansioksi.",
        "",
        "## Taitokansiot",
        "",
        "| Kansio | Aihe | Lakeja | Asetuksia | Yhteensä |",
        "|--------|------|--------|-----------|----------|",
    ]

    total_all = 0
    for skill in sorted(stats.keys()):
        s = stats[skill]
        meta = SKILL_METADATA.get(skill, ("", ""))
        lines.append(
            f"| [{skill}/](./{skill}/) | {meta[0]} | {s.acts} | {s.decrees} | {s.total} |"
        )
        total_all += s.total

    lines.append(f"| **Yhteensä** | | | | **{total_all}** |")
    lines.append("")
    lines.append("## Tiedostomuoto")
    lines.append("")
    lines.append("Jokainen säädös on oma Markdown-tiedostonsa YAML-frontmatterilla:")
    lines.append("")
    lines.append("```yaml")
    lines.append("---")
    lines.append('citation: "872/2019"')
    lines.append('title: "Työaikalaki"')
    lines.append("type: act")
    lines.append('ministry: "Työ- ja elinkeinoministeriö"')
    lines.append("skill: tyolainsaadanto")
    lines.append("subtopic: tyovoima-ja-tyosuhteet")
    lines.append("---")
    lines.append("```")
    lines.append("")

    path = output_dir / "README.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")
    logger.info(f"Master README → {path}")
