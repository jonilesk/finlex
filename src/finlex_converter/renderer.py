"""Render parsed statute dataclasses to Markdown."""

from .parser import Statute, Chapter, Section, Subsection


def render_statute(statute: Statute) -> str:
    """Render a Statute to Markdown string.

    Args:
        statute: Parsed statute dataclass.

    Returns:
        Markdown string.
    """
    lines: list[str] = []
    meta = statute.metadata

    # Title
    title = meta.title or "Untitled"
    citation = meta.doc_number or f"{meta.number}/{meta.year}"
    lines.append(f"# {title}")
    lines.append("")

    # Metadata block
    if citation:
        lines.append(f"**Citation:** {citation}")
    if meta.subtype:
        lines.append(f"**Type:** {meta.subtype}")
    if meta.language:
        lines.append(f"**Language:** {meta.language}")
    if meta.date_issued:
        lines.append(f"**Date issued:** {meta.date_issued}")
    if meta.date_published:
        lines.append(f"**Date published:** {meta.date_published}")
    if meta.eli:
        lines.append(f"**ELI:** {meta.eli}")
    if meta.type_statute:
        lines.append(f"**Statute type:** {meta.type_statute}")
    if meta.category_statute:
        lines.append(f"**Category:** {meta.category_statute}")

    lines.append("")
    lines.append("---")
    lines.append("")

    # Preamble
    if statute.preamble:
        lines.append(statute.preamble)
        lines.append("")
        lines.append("---")
        lines.append("")

    # Body: chapters with sections, or top-level sections
    if statute.chapters:
        for chapter in statute.chapters:
            lines.extend(_render_chapter(chapter))
    elif statute.sections:
        for section in statute.sections:
            lines.extend(_render_section(section, heading_level=2))

    # Entry into force
    if statute.entry_into_force:
        lines.append("---")
        lines.append("")
        lines.append("**Voimaantulo:**")
        lines.append("")
        lines.append(statute.entry_into_force)
        lines.append("")

    # Conclusions
    if statute.conclusions:
        lines.append("---")
        lines.append("")
        lines.append(statute.conclusions)
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def _render_chapter(chapter: Chapter) -> list[str]:
    """Render a chapter as Markdown lines."""
    lines = []
    heading_parts = []
    if chapter.num:
        heading_parts.append(chapter.num)
    if chapter.heading:
        if heading_parts:
            heading_parts.append("—")
        heading_parts.append(chapter.heading)

    lines.append(f"## {' '.join(heading_parts)}")
    lines.append("")

    for section in chapter.sections:
        lines.extend(_render_section(section, heading_level=3))

    return lines


def _render_section(section: Section, heading_level: int = 2) -> list[str]:
    """Render a section as Markdown lines."""
    lines = []
    prefix = "#" * heading_level
    heading_parts = []
    if section.num:
        heading_parts.append(section.num)
    if section.heading:
        heading_parts.append(section.heading)

    if heading_parts:
        lines.append(f"{prefix} {' '.join(heading_parts)}")
    else:
        lines.append(f"{prefix} (unnumbered section)")
    lines.append("")

    if section.subsections:
        for sub in section.subsections:
            lines.extend(_render_subsection(sub))
    elif section.content:
        lines.append(section.content)
        lines.append("")

    return lines


def _render_subsection(sub: Subsection) -> list[str]:
    """Render a subsection as Markdown lines."""
    lines = []
    if sub.content:
        lines.append(sub.content)
        lines.append("")
    return lines
