"""Parse Akoma Ntoso XML into structured dataclasses."""

from dataclasses import dataclass, field
from typing import Optional

from lxml import etree

from finlex_downloader.logging_config import logger

AKN_NS = {"akn": "http://docs.oasis-open.org/legaldocml/ns/akn/3.0"}
FINLEX_NS = "http://data.finlex.fi/schema/finlex"


@dataclass
class Subsection:
    """A subsection (momentti) of a section."""

    eid: str = ""
    content: str = ""


@dataclass
class Section:
    """A section (pykälä / §) of a statute."""

    eid: str = ""
    num: str = ""  # e.g. "1 §"
    heading: str = ""
    subsections: list[Subsection] = field(default_factory=list)
    content: str = ""  # direct content when no subsections


@dataclass
class Chapter:
    """A chapter (luku) of a statute."""

    eid: str = ""
    num: str = ""  # e.g. "1 luku"
    heading: str = ""
    sections: list[Section] = field(default_factory=list)


@dataclass
class Metadata:
    """Metadata extracted from AKN identification block."""

    title: str = ""
    doc_number: str = ""  # e.g. "1/2026"
    eli: str = ""
    date_issued: str = ""
    date_published: str = ""
    subtype: str = ""  # e.g. "statute", "statute-consolidated"
    language: str = ""
    year: str = ""
    number: str = ""
    type_statute: str = ""  # e.g. "decree", "act"
    category_statute: str = ""  # e.g. "amending-statute", "new-statute"


@dataclass
class Statute:
    """A complete parsed statute."""

    metadata: Metadata = field(default_factory=Metadata)
    preamble: str = ""
    chapters: list[Chapter] = field(default_factory=list)
    sections: list[Section] = field(default_factory=list)  # top-level when no chapters
    entry_into_force: str = ""
    conclusions: str = ""


def _text_content(element) -> str:
    """Extract all text content from an element, normalizing whitespace."""
    if element is None:
        return ""
    raw = "".join(element.itertext())
    # Collapse runs of whitespace (including newlines from XML indentation) to single spaces
    return " ".join(raw.split()).strip()


def _extract_paragraph_texts(element) -> str:
    """Extract text from <p> elements within a container, joined by newlines."""
    paragraphs = []
    for p in element.findall(".//akn:p", AKN_NS):
        text = _text_content(p)
        if text:
            paragraphs.append(text)
    return "\n\n".join(paragraphs)


def _parse_subsection(elem) -> Subsection:
    """Parse a <subsection> element."""
    return Subsection(
        eid=elem.get("eId", ""),
        content=_extract_paragraph_texts(elem),
    )


def _parse_section(elem) -> Section:
    """Parse a <section> element."""
    num_elem = elem.find("akn:num", AKN_NS)
    heading_elem = elem.find("akn:heading", AKN_NS)

    subsections = []
    for sub in elem.findall("akn:subsection", AKN_NS):
        subsections.append(_parse_subsection(sub))

    # Direct content (no subsections)
    direct_content = ""
    if not subsections:
        content_elem = elem.find("akn:content", AKN_NS)
        if content_elem is not None:
            direct_content = _extract_paragraph_texts(content_elem)

    return Section(
        eid=elem.get("eId", ""),
        num=_text_content(num_elem),
        heading=_text_content(heading_elem),
        subsections=subsections,
        content=direct_content,
    )


def _parse_chapter(elem) -> Chapter:
    """Parse a <chapter> element."""
    num_elem = elem.find("akn:num", AKN_NS)
    heading_elem = elem.find("akn:heading", AKN_NS)

    sections = []
    for sec in elem.findall("akn:section", AKN_NS):
        sections.append(_parse_section(sec))

    return Chapter(
        eid=elem.get("eId", ""),
        num=_text_content(num_elem),
        heading=_text_content(heading_elem),
        sections=sections,
    )


def _parse_metadata(tree: etree._ElementTree) -> Metadata:
    """Extract metadata from AKN identification block."""
    meta = Metadata()

    # Title from preface > docTitle
    titles = tree.xpath("//akn:preface//akn:docTitle/text()", namespaces=AKN_NS)
    if titles:
        meta.title = " ".join(titles[0].split())  # normalize whitespace

    # docNumber from preface
    nums = tree.xpath("//akn:preface//akn:docNumber/text()", namespaces=AKN_NS)
    if nums:
        meta.doc_number = nums[0].strip()

    # ELI from FRBRWork
    eli = tree.xpath(
        "//akn:FRBRWork/akn:FRBRalias[@name='eli']/@value", namespaces=AKN_NS
    )
    if eli:
        meta.eli = eli[0]

    # Dates from FRBRWork
    date_issued = tree.xpath(
        "//akn:FRBRWork/akn:FRBRdate[@name='dateIssued']/@date", namespaces=AKN_NS
    )
    if date_issued:
        meta.date_issued = date_issued[0]

    date_published = tree.xpath(
        "//akn:FRBRWork/akn:FRBRdate[@name='datePublished']/@date", namespaces=AKN_NS
    )
    if date_published:
        meta.date_published = date_published[0]

    # Subtype
    subtypes = tree.xpath(
        "//akn:FRBRWork/akn:FRBRsubtype/@value", namespaces=AKN_NS
    )
    if subtypes:
        meta.subtype = subtypes[0]

    # Number and year
    frbr_numbers = tree.xpath(
        "//akn:FRBRWork/akn:FRBRnumber/@value", namespaces=AKN_NS
    )
    if frbr_numbers:
        meta.number = frbr_numbers[0]

    # Language from FRBRExpression
    langs = tree.xpath(
        "//akn:FRBRExpression/akn:FRBRlanguage/@language", namespaces=AKN_NS
    )
    if langs:
        meta.language = langs[0]

    # Year from proprietary
    years = tree.xpath(
        "//akn:proprietary//*[local-name()='documentYear']/text()",
        namespaces=AKN_NS,
    )
    if years:
        meta.year = years[0]

    # typeStatute and categoryStatute from proprietary
    type_refs = tree.xpath(
        "//akn:proprietary//*[local-name()='typeStatute']/@refersTo",
        namespaces=AKN_NS,
    )
    if type_refs:
        meta.type_statute = type_refs[0].lstrip("#")

    cat_refs = tree.xpath(
        "//akn:proprietary//*[local-name()='categoryStatute']/@refersTo",
        namespaces=AKN_NS,
    )
    if cat_refs:
        meta.category_statute = cat_refs[0].lstrip("#")

    return meta


def _parse_body_sections(body) -> tuple[list[Chapter], list[Section]]:
    """Parse body content, returning chapters and/or top-level sections."""
    chapters = []
    sections = []

    # Look for chapters first
    for ch in body.findall(".//akn:chapter", AKN_NS):
        chapters.append(_parse_chapter(ch))

    if chapters:
        return chapters, []

    # No chapters — look for top-level sections
    for sec in body.findall(".//akn:section", AKN_NS):
        sections.append(_parse_section(sec))

    return [], sections


def _parse_preamble(tree: etree._ElementTree) -> str:
    """Extract preamble text."""
    preamble = tree.find(".//akn:preamble", AKN_NS)
    if preamble is None:
        return ""
    return _text_content(preamble)


def _parse_entry_into_force(tree: etree._ElementTree) -> str:
    """Extract entry into force text."""
    # Look for hcontainer with name=entryIntoForce
    for hc in tree.xpath("//akn:hcontainer[@name='entryIntoForce']", namespaces=AKN_NS):
        return _extract_paragraph_texts(hc)
    # Also try entryIntoForceStart
    for hc in tree.xpath(
        "//akn:hcontainer[@name='entryIntoForceStart']", namespaces=AKN_NS
    ):
        return _extract_paragraph_texts(hc)
    return ""


def _parse_conclusions(tree: etree._ElementTree) -> str:
    """Extract conclusions/signatures text."""
    for hc in tree.xpath("//akn:hcontainer[@name='conclusions']", namespaces=AKN_NS):
        return _extract_paragraph_texts(hc)
    return ""


def parse_statute(xml_bytes: bytes) -> Optional[Statute]:
    """Parse an AKN XML document into a Statute dataclass.

    Args:
        xml_bytes: Raw XML content.

    Returns:
        Statute object, or None if parsing fails.
    """
    try:
        tree = etree.fromstring(xml_bytes)
    except etree.XMLSyntaxError as e:
        logger.error(f"XML parse error: {e}")
        return None

    tree = etree.ElementTree(tree)
    metadata = _parse_metadata(tree)

    body = tree.find(".//akn:body", AKN_NS)
    chapters, sections = [], []
    if body is not None:
        chapters, sections = _parse_body_sections(body)

    preamble = _parse_preamble(tree)
    entry_into_force = _parse_entry_into_force(tree)
    conclusions = _parse_conclusions(tree)

    return Statute(
        metadata=metadata,
        preamble=preamble,
        chapters=chapters,
        sections=sections,
        entry_into_force=entry_into_force,
        conclusions=conclusions,
    )
