"""Tests for document downloader."""

import pytest
import responses
from pathlib import Path

from finlex_downloader.downloader import (
    extract_media_links,
    download_document,
    DownloadOptions,
    check_in_force,
)
from finlex_downloader.client import FinlexClient


class TestExtractMediaLinks:
    """Tests for extract_media_links function."""

    def test_extract_img_src(self):
        """Extract media links from img elements."""
        xml = b'''<?xml version="1.0"?>
        <akomaNtoso xmlns="http://docs.oasis-open.org/legaldocml/ns/akn/3.0">
            <act>
                <body>
                    <img src="media/image1.gif"/>
                    <img src="media/image2.png"/>
                </body>
            </act>
        </akomaNtoso>'''
        
        links = extract_media_links(xml)
        assert "media/image1.gif" in links
        assert "media/image2.png" in links

    def test_extract_attachment_href(self):
        """Extract media links from attachment elements."""
        xml = b'''<?xml version="1.0"?>
        <akomaNtoso xmlns="http://docs.oasis-open.org/legaldocml/ns/akn/3.0">
            <act>
                <attachments>
                    <attachment href="media/attachment1.pdf"/>
                </attachments>
            </act>
        </akomaNtoso>'''
        
        links = extract_media_links(xml)
        assert "media/attachment1.pdf" in links

    def test_extract_ref_href(self):
        """Extract media links from ref elements."""
        xml = b'''<?xml version="1.0"?>
        <akomaNtoso xmlns="http://docs.oasis-open.org/legaldocml/ns/akn/3.0">
            <act>
                <body>
                    <ref href="media/doc.pdf">Link</ref>
                </body>
            </act>
        </akomaNtoso>'''
        
        links = extract_media_links(xml)
        assert "media/doc.pdf" in links

    def test_ignore_non_media_links(self):
        """Ignore links that don't start with media/."""
        xml = b'''<?xml version="1.0"?>
        <akomaNtoso xmlns="http://docs.oasis-open.org/legaldocml/ns/akn/3.0">
            <act>
                <body>
                    <img src="media/valid.gif"/>
                    <img src="http://example.com/image.gif"/>
                    <ref href="/some/other/path">Link</ref>
                </body>
            </act>
        </akomaNtoso>'''
        
        links = extract_media_links(xml)
        assert links == ["media/valid.gif"]

    def test_deduplicate_links(self):
        """Duplicate links should be removed."""
        xml = b'''<?xml version="1.0"?>
        <akomaNtoso xmlns="http://docs.oasis-open.org/legaldocml/ns/akn/3.0">
            <act>
                <body>
                    <img src="media/same.gif"/>
                    <img src="media/same.gif"/>
                </body>
            </act>
        </akomaNtoso>'''
        
        links = extract_media_links(xml)
        assert links == ["media/same.gif"]

    def test_empty_xml(self):
        """Handle XML with no media links."""
        xml = b'''<?xml version="1.0"?>
        <akomaNtoso xmlns="http://docs.oasis-open.org/legaldocml/ns/akn/3.0">
            <act><body></body></act>
        </akomaNtoso>'''
        
        links = extract_media_links(xml)
        assert links == []

    def test_invalid_xml(self):
        """Handle invalid XML gracefully."""
        links = extract_media_links(b"not xml at all")
        assert links == []


class TestDownloadOptions:
    """Tests for DownloadOptions dataclass."""

    def test_default_options(self):
        """Default options have correct values."""
        opts = DownloadOptions(output_dir=Path("/tmp"))
        assert opts.output_dir == Path("/tmp")
        assert opts.fetch_pdf is False
        assert opts.fetch_zip is False
        assert opts.fetch_media is False
        assert opts.force is False
        assert opts.dry_run is False
        assert opts.in_force_only is False


class TestCheckInForce:
    """Tests for check_in_force function."""

    def test_in_force_true(self):
        """Statute with isInForce value=true."""
        xml = b'''<?xml version="1.0"?>
        <akomaNtoso xmlns="http://docs.oasis-open.org/legaldocml/ns/akn/3.0"
                    xmlns:finlex="http://data.finlex.fi/schema/finlex">
            <act>
                <meta>
                    <proprietary>
                        <finlex:isInForce value="true"/>
                    </proprietary>
                </meta>
            </act>
        </akomaNtoso>'''
        assert check_in_force(xml) is True

    def test_in_force_false(self):
        """Statute with isInForce value=false."""
        xml = b'''<?xml version="1.0"?>
        <akomaNtoso xmlns="http://docs.oasis-open.org/legaldocml/ns/akn/3.0"
                    xmlns:finlex="http://data.finlex.fi/schema/finlex">
            <act>
                <meta>
                    <proprietary>
                        <finlex:isInForce value="false"/>
                    </proprietary>
                </meta>
            </act>
        </akomaNtoso>'''
        assert check_in_force(xml) is False

    def test_no_in_force_element(self):
        """XML without isInForce element returns None."""
        xml = b'''<?xml version="1.0"?>
        <akomaNtoso xmlns="http://docs.oasis-open.org/legaldocml/ns/akn/3.0"
                    xmlns:finlex="http://data.finlex.fi/schema/finlex">
            <act>
                <meta>
                    <proprietary>
                        <finlex:documentYear>1999</finlex:documentYear>
                    </proprietary>
                </meta>
            </act>
        </akomaNtoso>'''
        assert check_in_force(xml) is None

    def test_invalid_xml(self):
        """Invalid XML returns None."""
        assert check_in_force(b"not xml") is None

    def test_empty_xml(self):
        """Empty bytes returns None."""
        assert check_in_force(b"") is None

    def test_nested_in_real_structure(self):
        """isInForce found in realistic nested AKN structure."""
        xml = '''<?xml version="1.0"?>
        <akomaNtoso xmlns="http://docs.oasis-open.org/legaldocml/ns/akn/3.0"
                    xmlns:finlex="http://data.finlex.fi/schema/finlex">
            <act contains="multipleVersions" name="main">
                <meta>
                    <identification source="#organization_fi.finlex">
                        <FRBRWork>
                            <FRBRnumber value="731"/>
                        </FRBRWork>
                    </identification>
                    <proprietary source="#organization_fi.finlex">
                        <finlex:documentYear>1999</finlex:documentYear>
                        <finlex:typeStatute refersTo="#act"/>
                        <finlex:isInForce value="true"/>
                        <finlex:inForce>
                            <finlex:dateEntryIntoForce date="2000-03-01"/>
                        </finlex:inForce>
                    </proprietary>
                </meta>
                <preface>
                    <p><docTitle>Suomen perustuslaki</docTitle></p>
                </preface>
            </act>
        </akomaNtoso>'''.encode("utf-8")
        assert check_in_force(xml) is True


def _make_xml(in_force_value: str) -> bytes:
    """Helper to create minimal AKN XML with isInForce."""
    return f'''<?xml version="1.0"?>
    <akomaNtoso xmlns="http://docs.oasis-open.org/legaldocml/ns/akn/3.0"
                xmlns:finlex="http://data.finlex.fi/schema/finlex">
        <act><meta><proprietary>
            <finlex:isInForce value="{in_force_value}"/>
        </proprietary></meta><body/></act>
    </akomaNtoso>'''.encode("utf-8")


_AKN_URI = "https://opendata.finlex.fi/finlex/avoindata/v1/akn/fi/act/statute-consolidated/1999/731/fin@20180817"
_API_URL = "https://opendata.finlex.fi/finlex/avoindata/v1/akn/fi/act/statute-consolidated/1999/731/fin@20180817"


class TestDownloadDocumentInForceOnly:
    """Tests for download_document with in_force_only option."""

    @responses.activate
    def test_skips_repealed_statute(self, tmp_path):
        """Repealed statute is not saved when in_force_only is True."""
        responses.add(responses.GET, _API_URL, body=_make_xml("false"), status=200)

        client = FinlexClient(sleep_seconds=0)
        opts = DownloadOptions(output_dir=tmp_path, in_force_only=True)
        result = download_document(client, _AKN_URI, opts)

        assert result.status == "skipped-repealed"
        assert not (tmp_path / "act" / "statute-consolidated" / "1999" / "731" / "fin@20180817" / "main.xml").exists()

    @responses.activate
    def test_saves_in_force_statute(self, tmp_path):
        """In-force statute is saved when in_force_only is True."""
        responses.add(responses.GET, _API_URL, body=_make_xml("true"), status=200)

        client = FinlexClient(sleep_seconds=0)
        opts = DownloadOptions(output_dir=tmp_path, in_force_only=True)
        result = download_document(client, _AKN_URI, opts)

        assert result.status == "success"
        xml_path = tmp_path / "act" / "statute-consolidated" / "1999" / "731" / "fin@20180817" / "main.xml"
        assert xml_path.exists()

    @responses.activate
    def test_saves_without_in_force_flag(self, tmp_path):
        """Repealed statute is saved when in_force_only is False (default)."""
        responses.add(responses.GET, _API_URL, body=_make_xml("false"), status=200)

        client = FinlexClient(sleep_seconds=0)
        opts = DownloadOptions(output_dir=tmp_path, in_force_only=False)
        result = download_document(client, _AKN_URI, opts)

        assert result.status == "success"
        xml_path = tmp_path / "act" / "statute-consolidated" / "1999" / "731" / "fin@20180817" / "main.xml"
        assert xml_path.exists()

    @responses.activate
    def test_saves_when_no_in_force_element(self, tmp_path):
        """Statute without isInForce element is saved (not skipped) even with in_force_only."""
        xml = b'''<?xml version="1.0"?>
        <akomaNtoso xmlns="http://docs.oasis-open.org/legaldocml/ns/akn/3.0"
                    xmlns:finlex="http://data.finlex.fi/schema/finlex">
            <act><meta><proprietary>
                <finlex:documentYear>1999</finlex:documentYear>
            </proprietary></meta><body/></act>
        </akomaNtoso>'''
        responses.add(responses.GET, _API_URL, body=xml, status=200)

        client = FinlexClient(sleep_seconds=0)
        opts = DownloadOptions(output_dir=tmp_path, in_force_only=True)
        result = download_document(client, _AKN_URI, opts)

        assert result.status == "success"
