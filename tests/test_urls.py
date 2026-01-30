"""Tests for URL parsing and path utilities."""

import pytest
from pathlib import Path

from finlex_downloader.urls import (
    DocumentInfo,
    parse_akn_uri,
    build_api_path,
    build_list_path,
)


class TestParseAknUri:
    """Tests for parse_akn_uri function."""

    def test_parse_full_url_act_statute(self):
        """Parse full URL for act/statute."""
        uri = "https://opendata.finlex.fi/finlex/avoindata/v1/akn/fi/act/statute/2024/123/fin@"
        info = parse_akn_uri(uri)

        assert info is not None
        assert info.category == "act"
        assert info.document_type == "statute"
        assert info.year == "2024"
        assert info.number == "123"
        assert info.lang_and_version == "fin@"
        assert info.authority is None

    def test_parse_path_only(self):
        """Parse path without base URL."""
        uri = "/akn/fi/act/statute/2024/123/fin@"
        info = parse_akn_uri(uri)

        assert info is not None
        assert info.category == "act"
        assert info.document_type == "statute"

    def test_parse_judgment(self):
        """Parse judgment document URI."""
        uri = "/akn/fi/judgment/kko/2023/45/fin@"
        info = parse_akn_uri(uri)

        assert info is not None
        assert info.category == "judgment"
        assert info.document_type == "kko"
        assert info.year == "2023"
        assert info.number == "45"

    def test_parse_doc(self):
        """Parse doc document URI."""
        uri = "/akn/fi/doc/government-proposal/2024/99/fin@"
        info = parse_akn_uri(uri)

        assert info is not None
        assert info.category == "doc"
        assert info.document_type == "government-proposal"

    def test_parse_authority_regulation(self):
        """Parse authority-regulation with authority field."""
        uri = "/akn/fi/doc/authority-regulation/metsahallitus/1996/32082/fin@"
        info = parse_akn_uri(uri)

        assert info is not None
        assert info.category == "doc"
        assert info.document_type == "authority-regulation"
        assert info.authority == "metsahallitus"
        assert info.year == "1996"
        assert info.number == "32082"
        assert info.lang_and_version == "fin@"

    def test_parse_url_encoded(self):
        """Parse URL with encoded characters."""
        uri = "https://opendata.finlex.fi/finlex/avoindata/v1/akn/fi/act/statute/2024/123/fin%40"
        info = parse_akn_uri(uri)

        assert info is not None
        assert info.lang_and_version == "fin@"

    def test_parse_invalid_uri(self):
        """Return None for invalid URI."""
        assert parse_akn_uri("/invalid/path") is None
        assert parse_akn_uri("") is None


class TestDocumentInfoFolderPath:
    """Tests for DocumentInfo.folder_path property."""

    def test_standard_document_path(self):
        """Standard document generates correct folder path."""
        info = DocumentInfo(
            category="act",
            document_type="statute",
            year="2024",
            number="123",
            lang_and_version="fin@",
        )
        expected = Path("act/statute/2024/123/fin@")
        assert info.folder_path == expected

    def test_authority_regulation_path(self):
        """Authority-regulation includes authority in path."""
        info = DocumentInfo(
            category="doc",
            document_type="authority-regulation",
            authority="metsahallitus",
            year="1996",
            number="32082",
            lang_and_version="fin@",
        )
        expected = Path("doc/authority-regulation/metsahallitus/1996/32082/fin@")
        assert info.folder_path == expected


class TestBuildApiPath:
    """Tests for build_api_path function."""

    def test_standard_path(self):
        """Build standard API path."""
        info = DocumentInfo(
            category="act",
            document_type="statute",
            year="2024",
            number="123",
            lang_and_version="fin@",
        )
        assert build_api_path(info) == "/akn/fi/act/statute/2024/123/fin@"

    def test_authority_path(self):
        """Build authority-regulation API path."""
        info = DocumentInfo(
            category="doc",
            document_type="authority-regulation",
            authority="metsahallitus",
            year="1996",
            number="32082",
            lang_and_version="fin@",
        )
        assert build_api_path(info) == "/akn/fi/doc/authority-regulation/metsahallitus/1996/32082/fin@"


class TestBuildListPath:
    """Tests for build_list_path function."""

    def test_act_statute_list(self):
        """Build list path for act/statute."""
        assert build_list_path("act", "statute") == "/akn/fi/act/statute/list"

    def test_authority_regulation_list(self):
        """Build list path for authority-regulation."""
        assert build_list_path("doc", "authority-regulation") == "/akn/fi/doc/authority-regulation/list"
