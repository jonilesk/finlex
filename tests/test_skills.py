"""Tests for the topics, skill_builder, and enhanced parser/renderer."""

from pathlib import Path

import pytest

from finlex_converter.topics import (
    classify,
    classify_skill,
    classify_subtopic,
    should_include,
    is_excluded,
    TopicInfo,
)
from finlex_converter.parser import parse_statute, CrossHeading
from finlex_converter.renderer import render_statute
from finlex_converter.skill_builder import _citation_to_filename, build_skills


# --- XML fixture with crossHeadings and ministry metadata ---

ACT_WITH_CROSSHEADINGS_XML = """\
<?xml version="1.0" encoding="UTF-8"?>
<akomaNtoso xmlns="http://docs.oasis-open.org/legaldocml/ns/akn/3.0"
            xmlns:finlex="http://data.finlex.fi/schema/finlex">
  <act contains="originalVersion" name="main">
    <meta>
      <identification source="#organization_fi.finlex">
        <FRBRWork>
          <FRBRthis value="/akn/fi/act/statute-consolidated/2024/672/!main"/>
          <FRBRuri value="/akn/fi/act/statute-consolidated/2024/672"/>
          <FRBRalias name="eli" value="http://data.finlex.fi/eli/sd/2024/672/ajantasa"/>
          <FRBRdate date="2024-11-27" name="dateIssued"/>
          <FRBRdate date="2024-11-29" name="datePublished"/>
          <FRBRsubtype value="statute-consolidated"/>
          <FRBRnumber value="672"/>
        </FRBRWork>
        <FRBRExpression>
          <FRBRlanguage language="fin"/>
        </FRBRExpression>
      </identification>
      <references source="#organization_fi.finlex">
        <TLCOrganization eId="fi.ministry-of-justice"
          href="/akn/ontology/organization/fi.ministry-of-justice"
          showAs="Oikeusministeriö"/>
      </references>
      <proprietary source="#organization_fi.finlex">
        <finlex:documentYear>2024</finlex:documentYear>
        <finlex:administrativeBranch refersTo="#fi.ministry-of-justice"/>
        <finlex:typeStatute refersTo="#act"/>
        <finlex:isInForce value="true"/>
        <finlex:issuedUnderActs>
          <finlex:statuteReference>
            <finlex:ref href="/akn/fi/act/statute-consolidated/1958/496">496/1958</finlex:ref>
          </finlex:statuteReference>
        </finlex:issuedUnderActs>
      </proprietary>
    </meta>
    <preface>
      <p>
        <docNumber>672/2024</docNumber>
        <docTitle>Testisäännöt</docTitle>
      </p>
    </preface>
    <body>
      <hcontainer finlex:outline="Säädöksen teksti" name="statuteProvisionsWrapper">
        <crossHeading eId="crossHeading">Yleisiä määräyksiä</crossHeading>
        <section eId="sec_1">
          <num>1 §</num>
          <subsection eId="sec_1__subsec_1">
            <content>
              <p>Ensimmäinen pykälä.</p>
            </content>
          </subsection>
        </section>
        <crossHeading eId="crossHeading_2">Erityisiä määräyksiä</crossHeading>
        <section eId="sec_2">
          <num>2 §</num>
          <content>
            <p>Toinen pykälä.</p>
          </content>
        </section>
      </hcontainer>
    </body>
  </act>
</akomaNtoso>""".encode("utf-8")


# --- Topic Classification Tests ---

class TestTopicClassification:
    """Tests for topic classification."""

    def test_ministry_to_skill(self):
        """Known ministry maps to skill folder."""
        assert classify_skill("fi.ministry-of-justice", "") == "oikeus"
        assert classify_skill("fi.ministry-of-finance", "") == "talous-ja-verotus"
        assert classify_skill("fi.ministry-of-economic-affairs-and-employment", "") == "tyolainsaadanto"

    def test_ministry_with_hash_prefix(self):
        """Ministry ID with # prefix is handled."""
        assert classify_skill("#fi.ministry-of-justice", "") == "oikeus"

    def test_unknown_ministry_fallback(self):
        """Unknown ministry falls back to title keywords."""
        assert classify_skill("", "Verolaki") == "talous-ja-verotus"
        assert classify_skill("", "Työsopimuslaki") == "sosiaali-ja-terveys"
        assert classify_skill("", "Rikoslaki") == "oikeus"

    def test_no_match_returns_yleinen(self):
        """No match returns 'yleinen'."""
        assert classify_skill("", "Laki eräiden virkojen muuttamisesta") == "yleinen"

    def test_classify_full(self):
        """Full classification returns TopicInfo."""
        info = classify("fi.ministry-of-justice", "Säätiölaki", 100000)
        assert info.skill == "oikeus"
        assert info.subtopic == "yksityisoikeus"
        assert info.skill_title == "Oikeuslainsäädäntö"

    def test_subtopic_tieliikenne(self):
        """Traffic law classified to tieliikenne subtopic."""
        sub = classify_subtopic("liikenne-ja-viestinta", "Tieliikennelaki")
        assert sub == "tieliikenne"

    def test_subtopic_rahoitusmarkkinat(self):
        """Financial law classified to rahoitusmarkkinat."""
        sub = classify_subtopic("talous-ja-verotus", "Sijoitusrahastolaki")
        assert sub == "rahoitusmarkkinat"

    def test_subtopic_empty_when_no_rules(self):
        """No matching subtopic returns empty string."""
        sub = classify_subtopic("sisaasiat", "Rahapelilaki")
        assert sub == ""

    def test_ulkoasiat_size_threshold(self):
        """ulkoasiat uses size to split merkittavat/sopimukset."""
        assert classify_subtopic("ulkoasiat", "Sopimus X", 5000) == "sopimukset"
        assert classify_subtopic("ulkoasiat", "Sopimus X", 15000) == "merkittavat"


class TestShouldInclude:
    """Tests for filtering logic."""

    def test_act_above_threshold(self):
        """Large act is included."""
        assert should_include("act", "Työsopimuslaki", 50000) is True

    def test_act_below_threshold(self):
        """Tiny act is excluded."""
        assert should_include("act", "Jokin laki", 2000) is False

    def test_act_excluded_by_title(self):
        """Budget amendments excluded."""
        assert should_include("act", "Lisäys vuoden 1990 menoarvioon", 5000) is False

    def test_decree_above_threshold(self):
        """Large decree included."""
        assert should_include("decree", "VN asetus X", 25000) is True

    def test_decree_below_threshold(self):
        """Small decree excluded."""
        assert should_include("decree", "VN asetus X", 15000) is False

    def test_decision_always_excluded(self):
        """Decisions are never included."""
        assert should_include("decision", "Päätös X", 100000) is False

    def test_announcement_excluded(self):
        """Announcements excluded."""
        assert should_include("announcement", "Ilmoitus X", 100000) is False


class TestIsExcluded:
    """Tests for title exclusion patterns."""

    def test_budget_amendment(self):
        assert is_excluded("Lisäys vuoden 1985 menoarvioon") is True

    def test_office_creation(self):
        assert is_excluded("Laki eräiden virkojen ja toimien perustamisesta") is True

    def test_normal_law_not_excluded(self):
        assert is_excluded("Työsopimuslaki") is False


# --- Enhanced Parser Tests ---

class TestEnhancedParser:
    """Tests for crossHeading and ministry metadata parsing."""

    def test_crossheadings_parsed(self):
        """CrossHeadings are parsed from XML."""
        statute = parse_statute(ACT_WITH_CROSSHEADINGS_XML)
        assert statute is not None
        assert len(statute.body_elements) == 4  # 2 crossHeadings + 2 sections
        assert isinstance(statute.body_elements[0], CrossHeading)
        assert statute.body_elements[0].text == "Yleisiä määräyksiä"
        assert statute.body_elements[2].text == "Erityisiä määräyksiä"

    def test_ministry_metadata(self):
        """Ministry ID and name are extracted."""
        statute = parse_statute(ACT_WITH_CROSSHEADINGS_XML)
        assert statute.metadata.ministry_id == "fi.ministry-of-justice"
        assert statute.metadata.ministry_name == "Oikeusministeriö"

    def test_issued_under(self):
        """issuedUnderActs references are extracted."""
        statute = parse_statute(ACT_WITH_CROSSHEADINGS_XML)
        assert "496/1958" in statute.metadata.issued_under

    def test_is_in_force(self):
        """isInForce flag is extracted."""
        statute = parse_statute(ACT_WITH_CROSSHEADINGS_XML)
        assert statute.metadata.is_in_force is True


# --- Enhanced Renderer Tests ---

class TestEnhancedRenderer:
    """Tests for YAML frontmatter and crossHeading rendering."""

    def test_crossheadings_rendered(self):
        """CrossHeadings render as H2."""
        statute = parse_statute(ACT_WITH_CROSSHEADINGS_XML)
        md = render_statute(statute)
        assert "## Yleisiä määräyksiä" in md
        assert "## Erityisiä määräyksiä" in md

    def test_crossheading_order_preserved(self):
        """CrossHeadings appear before their sections."""
        statute = parse_statute(ACT_WITH_CROSSHEADINGS_XML)
        md = render_statute(statute)
        pos_heading = md.index("## Yleisiä määräyksiä")
        pos_section = md.index("## 1 §")
        assert pos_heading < pos_section

    def test_frontmatter_rendered(self):
        """YAML frontmatter is rendered when enabled."""
        statute = parse_statute(ACT_WITH_CROSSHEADINGS_XML)
        md = render_statute(statute, skill="oikeus", subtopic="yksityisoikeus", frontmatter=True)
        assert md.startswith("---\n")
        assert 'citation: "672/2024"' in md
        assert 'title: "Testisäännöt"' in md
        assert "type: act" in md
        assert 'ministry: "Oikeusministeriö"' in md
        assert "skill: oikeus" in md
        assert "subtopic: yksityisoikeus" in md
        assert 'issued_under: ["496/1958"]' in md

    def test_frontmatter_off_by_default(self):
        """Legacy mode without frontmatter."""
        statute = parse_statute(ACT_WITH_CROSSHEADINGS_XML)
        md = render_statute(statute)
        assert not md.startswith("---\n")
        assert "**Citation:** 672/2024" in md

    def test_render_still_ends_with_newline(self):
        """Rendered Markdown ends with one newline."""
        statute = parse_statute(ACT_WITH_CROSSHEADINGS_XML)
        md = render_statute(statute, frontmatter=True)
        assert md.endswith("\n")
        assert not md.endswith("\n\n")


# --- Skill Builder Utility Tests ---

class TestCitationToFilename:
    """Tests for filename generation."""

    def test_basic(self):
        assert _citation_to_filename("872/2019") == "872-2019.md"

    def test_with_spaces(self):
        assert _citation_to_filename(" 100 / 2024 ") == "100-2024.md"

    def test_invalid(self):
        assert _citation_to_filename("invalid") == ""
        assert _citation_to_filename("") == ""

    def test_four_digit_number(self):
        assert _citation_to_filename("1397/2016") == "1397-2016.md"


class TestBuildSkillsIntegration:
    """Integration test for build_skills with minimal data."""

    def test_build_from_test_data(self, tmp_path):
        """Build skills from inline XML."""
        # Create input structure — pad content to exceed 3KB size filter
        xml_dir = tmp_path / "input" / "act" / "statute-consolidated" / "2024" / "672" / "fin@"
        xml_dir.mkdir(parents=True)
        # The fixture XML is small, so we need to make it bigger for the size filter
        padded_xml = ACT_WITH_CROSSHEADINGS_XML.decode("utf-8").replace(
            "Ensimmäinen pykälä.",
            "Ensimmäinen pykälä. " + "x" * 3000,
        ).encode("utf-8")
        (xml_dir / "main.xml").write_bytes(padded_xml)

        output = tmp_path / "output"
        stats = build_skills(tmp_path / "input", output)

        assert "oikeus" in stats
        assert stats["oikeus"].total == 1
        assert stats["oikeus"].acts == 1

        # Check output files exist
        assert (output / "README.md").exists()
        assert (output / "index.json").exists()
        assert (output / "oikeus" / "README.md").exists()
        assert (output / "oikeus" / "_index.json").exists()

        # Check markdown content
        md_files = list(output.rglob("672-2024.md"))
        assert len(md_files) == 1
        content = md_files[0].read_text(encoding="utf-8")
        assert "## Yleisiä määräyksiä" in content
        assert 'skill: oikeus' in content
