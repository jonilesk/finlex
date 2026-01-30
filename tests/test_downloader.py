"""Tests for document downloader."""

import pytest
from pathlib import Path

from finlex_downloader.downloader import extract_media_links, DownloadOptions


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
