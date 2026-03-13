"""Tests for the finlex_converter package."""

from pathlib import Path

import pytest

from finlex_converter.parser import (
    parse_statute,
    Statute,
    Metadata,
    Section,
    Subsection,
    Chapter,
)
from finlex_converter.renderer import render_statute
from finlex_converter.citations import parse_citation, Citation
from finlex_converter.indexer import StatuteIndex, IndexEntry, build_index_from_xml
from finlex_converter.cli import parse_args, find_xml_files, convert_file


# --- Sample XML fixtures ---

MINIMAL_ACT_XML = """\
<?xml version="1.0" encoding="UTF-8"?>
<akomaNtoso xmlns="http://docs.oasis-open.org/legaldocml/ns/akn/3.0">
  <act contains="originalVersion" name="main">
    <meta>
      <identification source="#organization_fi.finlex">
        <FRBRWork>
          <FRBRthis value="/akn/fi/act/statute/2024/100/!main"/>
          <FRBRuri value="/akn/fi/act/statute/2024/100"/>
          <FRBRalias name="eli" value="http://data.finlex.fi/eli/sd/2024/100/alkup"/>
          <FRBRdate date="2024-03-01" name="dateIssued"/>
          <FRBRdate date="2024-03-05" name="datePublished"/>
          <FRBRauthor as="#role_author" href="#organization_fi.parliament"/>
          <FRBRcountry value="fi"/>
          <FRBRsubtype value="statute"/>
          <FRBRnumber value="100"/>
        </FRBRWork>
        <FRBRExpression>
          <FRBRlanguage language="fin"/>
        </FRBRExpression>
      </identification>
    </meta>
    <preface>
      <p>
        <docNumber>100/2024</docNumber>
        <docTitle>Testilaki</docTitle>
      </p>
    </preface>
    <body>
      <section eId="sec_1">
        <num>1 §</num>
        <heading>Soveltamisala</heading>
        <content>
          <p>Lakia sovelletaan testiin.</p>
        </content>
      </section>
    </body>
  </act>
</akomaNtoso>""".encode("utf-8")

ACT_WITH_CHAPTERS_XML = """\
<?xml version="1.0" encoding="UTF-8"?>
<akomaNtoso xmlns="http://docs.oasis-open.org/legaldocml/ns/akn/3.0">
  <act contains="originalVersion" name="main">
    <meta>
      <identification source="#organization_fi.finlex">
        <FRBRWork>
          <FRBRthis value="/akn/fi/act/statute/2024/200/!main"/>
          <FRBRuri value="/akn/fi/act/statute/2024/200"/>
          <FRBRalias name="eli" value="http://data.finlex.fi/eli/sd/2024/200/alkup"/>
          <FRBRdate date="2024-06-01" name="dateIssued"/>
          <FRBRsubtype value="statute"/>
          <FRBRnumber value="200"/>
        </FRBRWork>
        <FRBRExpression>
          <FRBRlanguage language="fin"/>
        </FRBRExpression>
      </identification>
    </meta>
    <preface>
      <p>
        <docNumber>200/2024</docNumber>
        <docTitle>Laki lukujen testauksesta</docTitle>
      </p>
    </preface>
    <body>
      <chapter eId="chap_1">
        <num>1 luku</num>
        <heading>Yleiset säännökset</heading>
        <section eId="sec_1">
          <num>1 §</num>
          <heading>Tarkoitus</heading>
          <subsection eId="sec_1__subsec_1">
            <content>
              <p>Ensimmäinen momentti.</p>
            </content>
          </subsection>
          <subsection eId="sec_1__subsec_2">
            <content>
              <p>Toinen momentti.</p>
            </content>
          </subsection>
        </section>
      </chapter>
      <chapter eId="chap_2">
        <num>2 luku</num>
        <heading>Erityiset säännökset</heading>
        <section eId="sec_2">
          <num>2 §</num>
          <heading>Poikkeukset</heading>
          <content>
            <p>Poikkeus sisältö.</p>
          </content>
        </section>
      </chapter>
    </body>
  </act>
</akomaNtoso>""".encode("utf-8")

ACT_WITH_ENTRY_INTO_FORCE_XML = """\
<?xml version="1.0" encoding="UTF-8"?>
<akomaNtoso xmlns="http://docs.oasis-open.org/legaldocml/ns/akn/3.0"
            xmlns:finlex="http://data.finlex.fi/schema/finlex">
  <act contains="originalVersion" name="main">
    <meta>
      <identification source="#organization_fi.finlex">
        <FRBRWork>
          <FRBRthis value="/akn/fi/act/statute/2024/300/!main"/>
          <FRBRuri value="/akn/fi/act/statute/2024/300"/>
          <FRBRdate date="2024-01-01" name="dateIssued"/>
          <FRBRsubtype value="statute"/>
          <FRBRnumber value="300"/>
        </FRBRWork>
        <FRBRExpression>
          <FRBRlanguage language="fin"/>
        </FRBRExpression>
      </identification>
      <references source="#organization_fi.finlex">
        <TLCConcept eId="act" href="/akn/ontology/concept/statute/type-statute.act" showAs="Laki"/>
        <TLCConcept eId="new-statute" href="/akn/ontology/concept/statute/category-statute.new-statute" showAs="Uusi"/>
      </references>
      <proprietary source="#organization_fi.finlex">
        <finlex:typeStatute refersTo="#act"/>
        <finlex:categoryStatute refersTo="#new-statute"/>
        <finlex:documentYear>2024</finlex:documentYear>
      </proprietary>
    </meta>
    <preface>
      <p>
        <docNumber>300/2024</docNumber>
        <docTitle>Testin voimaantulolaki</docTitle>
      </p>
    </preface>
    <body>
      <hcontainer finlex:outline="Säädöksen teksti" name="statuteProvisionsWrapper">
        <section eId="sec_1">
          <num>1 §</num>
          <content>
            <p>Ainoa pykälä.</p>
          </content>
        </section>
      </hcontainer>
      <hcontainer name="entryIntoForce">
        <content>
          <p>Laki tulee voimaan 1 tammikuuta 2025.</p>
        </content>
      </hcontainer>
    </body>
  </act>
</akomaNtoso>""".encode("utf-8")


# --- Parser Tests ---

class TestParseStatute:
    """Tests for parse_statute."""

    def test_minimal_act(self):
        """Parse a minimal act with one section."""
        statute = parse_statute(MINIMAL_ACT_XML)
        assert statute is not None
        assert statute.metadata.title == "Testilaki"
        assert statute.metadata.doc_number == "100/2024"
        assert statute.metadata.eli == "http://data.finlex.fi/eli/sd/2024/100/alkup"
        assert statute.metadata.date_issued == "2024-03-01"
        assert statute.metadata.date_published == "2024-03-05"
        assert statute.metadata.subtype == "statute"
        assert statute.metadata.number == "100"
        assert statute.metadata.language == "fin"
        assert len(statute.sections) == 1
        assert statute.sections[0].num == "1 §"
        assert statute.sections[0].heading == "Soveltamisala"

    def test_act_with_chapters(self):
        """Parse act with chapters and subsections."""
        statute = parse_statute(ACT_WITH_CHAPTERS_XML)
        assert statute is not None
        assert len(statute.chapters) == 2
        assert statute.chapters[0].num == "1 luku"
        assert statute.chapters[0].heading == "Yleiset säännökset"
        assert len(statute.chapters[0].sections) == 1
        assert len(statute.chapters[0].sections[0].subsections) == 2
        assert statute.chapters[1].num == "2 luku"
        assert len(statute.chapters[1].sections) == 1

    def test_section_with_subsections(self):
        """Subsections are parsed with content."""
        statute = parse_statute(ACT_WITH_CHAPTERS_XML)
        sec = statute.chapters[0].sections[0]
        assert sec.subsections[0].content == "Ensimmäinen momentti."
        assert sec.subsections[1].content == "Toinen momentti."

    def test_section_with_direct_content(self):
        """Sections without subsections have direct content."""
        statute = parse_statute(MINIMAL_ACT_XML)
        assert statute.sections[0].content == "Lakia sovelletaan testiin."

    def test_entry_into_force(self):
        """Entry into force text is extracted."""
        statute = parse_statute(ACT_WITH_ENTRY_INTO_FORCE_XML)
        assert "voimaan" in statute.entry_into_force

    def test_proprietary_metadata(self):
        """typeStatute and categoryStatute from proprietary block."""
        statute = parse_statute(ACT_WITH_ENTRY_INTO_FORCE_XML)
        assert statute.metadata.type_statute == "act"
        assert statute.metadata.category_statute == "new-statute"
        assert statute.metadata.year == "2024"

    def test_invalid_xml_returns_none(self):
        """Invalid XML returns None."""
        result = parse_statute(b"<not valid xml")
        assert result is None

    def test_empty_body(self):
        """Act with no body sections still parses."""
        xml = b"""\
<?xml version="1.0"?>
<akomaNtoso xmlns="http://docs.oasis-open.org/legaldocml/ns/akn/3.0">
  <act name="main">
    <meta><identification source="#x">
      <FRBRWork><FRBRsubtype value="statute"/></FRBRWork>
      <FRBRExpression><FRBRlanguage language="fin"/></FRBRExpression>
    </identification></meta>
    <body></body>
  </act>
</akomaNtoso>"""
        statute = parse_statute(xml)
        assert statute is not None
        assert len(statute.sections) == 0
        assert len(statute.chapters) == 0

    def test_real_xml_file(self):
        """Parse a real test-data XML file."""
        xml_path = Path("test-data/act/statute/2026/1/fin@/main.xml")
        if not xml_path.exists():
            pytest.skip("test-data not available")
        statute = parse_statute(xml_path.read_bytes())
        assert statute is not None
        assert statute.metadata.doc_number == "1/2026"
        assert len(statute.sections) > 0


# --- Renderer Tests ---

class TestRenderStatute:
    """Tests for render_statute."""

    def test_minimal_render(self):
        """Render a minimal statute."""
        statute = parse_statute(MINIMAL_ACT_XML)
        md = render_statute(statute)
        assert md.startswith("# Testilaki\n")
        assert "**Citation:** 100/2024" in md
        assert "**ELI:** http://data.finlex.fi/eli/sd/2024/100/alkup" in md
        assert "## 1 § Soveltamisala" in md
        assert "Lakia sovelletaan testiin." in md

    def test_chapter_headings(self):
        """Chapters render as H2, sections as H3."""
        statute = parse_statute(ACT_WITH_CHAPTERS_XML)
        md = render_statute(statute)
        assert "## 1 luku — Yleiset säännökset" in md
        assert "### 1 § Tarkoitus" in md
        assert "## 2 luku — Erityiset säännökset" in md
        assert "### 2 § Poikkeukset" in md

    def test_subsections_rendered(self):
        """Subsections are rendered as paragraphs."""
        statute = parse_statute(ACT_WITH_CHAPTERS_XML)
        md = render_statute(statute)
        assert "Ensimmäinen momentti." in md
        assert "Toinen momentti." in md

    def test_entry_into_force_rendered(self):
        """Entry into force section is rendered."""
        statute = parse_statute(ACT_WITH_ENTRY_INTO_FORCE_XML)
        md = render_statute(statute)
        assert "**Voimaantulo:**" in md
        assert "voimaan" in md

    def test_metadata_block(self):
        """Metadata block contains expected fields."""
        statute = parse_statute(ACT_WITH_ENTRY_INTO_FORCE_XML)
        md = render_statute(statute)
        assert "**Statute type:** act" in md
        assert "**Category:** new-statute" in md

    def test_render_ends_with_newline(self):
        """Rendered Markdown ends with exactly one newline."""
        statute = parse_statute(MINIMAL_ACT_XML)
        md = render_statute(statute)
        assert md.endswith("\n")
        assert not md.endswith("\n\n")


# --- CLI Tests ---

class TestConverterCli:
    """Tests for converter CLI."""

    def test_default_args(self):
        """Default arguments."""
        args = parse_args([])
        assert args.input == Path("./finlex-data")
        assert args.output == Path("./finlex-md")
        assert args.category is None
        assert args.verbose is False

    def test_custom_args(self):
        """Custom input/output directories."""
        args = parse_args(["-i", "/data/xml", "-o", "/data/md", "--category", "act"])
        assert args.input == Path("/data/xml")
        assert args.output == Path("/data/md")
        assert args.category == "act"

    def test_find_xml_files(self):
        """Find XML files in test-data."""
        files = find_xml_files(Path("test-data"))
        assert len(files) == 3
        assert all(f.name == "main.xml" for f in files)

    def test_find_xml_files_with_category(self):
        """Find XML files filtered by category."""
        files = find_xml_files(Path("test-data"), category="act")
        assert len(files) == 3

    def test_find_xml_files_missing_category(self):
        """Missing category returns empty list."""
        files = find_xml_files(Path("test-data"), category="judgment")
        assert len(files) == 0

    def test_find_xml_files_missing_dir(self):
        """Missing directory returns empty list."""
        files = find_xml_files(Path("/nonexistent"))
        assert len(files) == 0

    def test_convert_file(self, tmp_path):
        """Convert a single XML file to Markdown."""
        xml_dir = tmp_path / "input" / "act" / "statute" / "2024" / "100" / "fin@"
        xml_dir.mkdir(parents=True)
        xml_path = xml_dir / "main.xml"
        xml_path.write_bytes(MINIMAL_ACT_XML)

        out_dir = tmp_path / "output"
        result = convert_file(xml_path, tmp_path / "input", out_dir)

        assert result is not None
        assert result.name == "statute.md"
        content = result.read_text()
        assert "# Testilaki" in content

    def test_convert_file_invalid_xml(self, tmp_path):
        """Invalid XML returns None."""
        xml_dir = tmp_path / "input"
        xml_dir.mkdir()
        xml_path = xml_dir / "main.xml"
        xml_path.write_bytes(b"<invalid xml")

        result = convert_file(xml_path, tmp_path / "input", tmp_path / "output")
        assert result is None


# --- Citation Tests ---

class TestCitationParser:
    """Tests for parse_citation."""

    def test_basic_citation(self):
        """Parse standard number/year format."""
        c = parse_citation("689/1997")
        assert c is not None
        assert c.number == "689"
        assert c.year == "1997"
        assert c.display == "689/1997"

    def test_citation_with_spaces(self):
        """Parse citation with spaces around slash."""
        c = parse_citation("731 / 1999")
        assert c is not None
        assert c.number == "731"
        assert c.year == "1999"

    def test_citation_with_whitespace(self):
        """Leading/trailing whitespace is stripped."""
        c = parse_citation("  39/1889  ")
        assert c is not None
        assert c.display == "39/1889"

    def test_invalid_citation(self):
        """Non-matching strings return None."""
        assert parse_citation("not a citation") is None
        assert parse_citation("") is None
        assert parse_citation("689") is None

    def test_to_api_path(self):
        """Citation maps to API path."""
        c = parse_citation("731/1999")
        assert c.to_api_path() == "/akn/fi/act/statute/1999/731/fin@"
        assert c.to_api_path("statute-consolidated") == "/akn/fi/act/statute-consolidated/1999/731/fin@"

    def test_to_folder_path(self):
        """Citation maps to folder path."""
        c = parse_citation("731/1999")
        assert c.to_folder_path() == Path("act/statute/1999/731/fin@")
        assert c.to_folder_path("statute-consolidated") == Path("act/statute-consolidated/1999/731/fin@")


# --- Index Tests ---

class TestStatuteIndex:
    """Tests for StatuteIndex."""

    def test_add_and_lookup(self):
        """Add and look up an entry."""
        index = StatuteIndex()
        entry = IndexEntry(citation="100/2024", title="Testilaki", path="act/statute/2024/100/fin@/statute.md")
        index.add(entry)

        result = index.lookup("100/2024")
        assert result is not None
        assert result.title == "Testilaki"

    def test_lookup_missing(self):
        """Missing citation returns None."""
        index = StatuteIndex()
        assert index.lookup("999/2024") is None

    def test_save_and_load(self, tmp_path):
        """Index round-trips through JSON."""
        index = StatuteIndex()
        index.add(IndexEntry(
            citation="100/2024", title="Testilaki",
            path="act/statute/2024/100/fin@/statute.md",
            subtype="statute", eli="http://example.com/eli",
            date_issued="2024-03-01",
        ))
        index.add(IndexEntry(
            citation="200/2024", title="Toinen laki",
            path="act/statute/2024/200/fin@/statute.md",
        ))

        json_path = tmp_path / "index.json"
        index.save(json_path)

        loaded = StatuteIndex.load(json_path)
        assert len(loaded.entries) == 2
        assert loaded.lookup("100/2024").title == "Testilaki"
        assert loaded.lookup("200/2024").title == "Toinen laki"

    def test_load_missing_file(self, tmp_path):
        """Loading from nonexistent file returns empty index."""
        index = StatuteIndex.load(tmp_path / "nope.json")
        assert len(index.entries) == 0

    def test_build_index_from_xml(self):
        """Build index from test-data XML files."""
        input_dir = Path("test-data")
        if not input_dir.exists():
            pytest.skip("test-data not available")

        index = build_index_from_xml(input_dir, Path("/tmp/md"))
        assert len(index.entries) == 3
        assert index.lookup("1/2026") is not None
        assert index.lookup("2/2026") is not None
        assert index.lookup("3/2026") is not None
