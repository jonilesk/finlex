"""Render parsed statute dataclasses to Markdown."""

from typing import Optional

from .parser import Statute, Chapter, Section, Subsection, CrossHeading


def render_statute(
    statute: Statute,
    skill: str = "",
    subtopic: str = "",
    frontmatter: bool = False,
) -> str:
    """Render a Statute to Markdown string.

    Args:
        statute: Parsed statute dataclass.
        skill: Skill folder name (for frontmatter).
        subtopic: Sub-topic folder name (for frontmatter).
        frontmatter: If True, include YAML frontmatter block.

    Returns:
        Markdown string.
    """
    lines: list[str] = []
    meta = statute.metadata

    # YAML frontmatter
    if frontmatter:
        lines.extend(_render_frontmatter(meta, skill, subtopic))

    # Title
    title = meta.title or "Untitled"
    citation = meta.doc_number or f"{meta.number}/{meta.year}"
    lines.append(f"# {title}")
    lines.append("")

    if not frontmatter:
        # Legacy metadata block (when frontmatter is off)
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

    # Body: chapters with sections, or top-level sections with crossHeadings
    if statute.chapters:
        for chapter in statute.chapters:
            lines.extend(_render_chapter(chapter))
    elif statute.body_elements:
        # Use body_elements to preserve crossHeading/section order
        for elem in statute.body_elements:
            if isinstance(elem, CrossHeading):
                lines.extend(_render_cross_heading(elem))
            elif isinstance(elem, Section):
                lines.extend(_render_section(elem, heading_level=2))
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


def _render_frontmatter(meta, skill: str, subtopic: str) -> list[str]:
    """Render YAML frontmatter block."""
    lines = ["---"]
    citation = meta.doc_number or f"{meta.number}/{meta.year}"
    if citation and citation != "/":
        lines.append(f'citation: "{citation}"')
    if meta.title:
        # Escape quotes in title
        safe_title = meta.title.replace('"', '\\"')
        lines.append(f'title: "{safe_title}"')
    if meta.type_statute:
        lines.append(f"type: {meta.type_statute}")
    if meta.ministry_name:
        safe_name = meta.ministry_name.replace('"', '\\"')
        lines.append(f'ministry: "{safe_name}"')
    if meta.ministry_id:
        lines.append(f"ministry_id: {meta.ministry_id}")
    if meta.eli:
        lines.append(f"eli: {meta.eli}")
    if meta.date_issued:
        lines.append(f"date_issued: {meta.date_issued}")
    if meta.date_published:
        lines.append(f"date_published: {meta.date_published}")
    if meta.language:
        lines.append(f"language: {meta.language}")
    if skill:
        lines.append(f"skill: {skill}")
    if subtopic:
        lines.append(f"subtopic: {subtopic}")
    if meta.issued_under:
        refs = ", ".join(f'"{r}"' for r in meta.issued_under)
        lines.append(f"issued_under: [{refs}]")
    lines.append("---")
    lines.append("")
    return lines


def _render_cross_heading(heading: CrossHeading) -> list[str]:
    """Render a cross-heading as an H2 divider."""
    lines = []
    if heading.text:
        lines.append(f"## {heading.text}")
        lines.append("")
    return lines


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
