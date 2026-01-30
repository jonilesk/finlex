"""URL parsing and path utilities for Finlex documents."""

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional
from urllib.parse import unquote, urlparse


@dataclass
class DocumentInfo:
    """Parsed document information from akn_uri."""

    category: str  # act, judgment, doc
    document_type: str  # statute, statute-consolidated, etc.
    year: str
    number: str
    lang_and_version: str
    authority: Optional[str] = None  # For authority-regulation docs

    @property
    def folder_path(self) -> Path:
        """Generate local folder path for this document."""
        if self.authority:
            return Path(
                self.category,
                self.document_type,
                self.authority,
                self.year,
                self.number,
                self.lang_and_version,
            )
        return Path(
            self.category,
            self.document_type,
            self.year,
            self.number,
            self.lang_and_version,
        )


# Pattern for standard documents: /akn/fi/{category}/{type}/{year}/{number}/{langAndVersion}
STANDARD_PATTERN = re.compile(
    r"/akn/fi/(?P<category>act|judgment|doc)/(?P<type>[^/]+)/(?P<year>\d+)/(?P<number>[^/]+)/(?P<lang>[^/]+)$"
)

# Pattern for authority-regulation: /akn/fi/doc/authority-regulation/{authority}/{year}/{number}/{langAndVersion}
AUTHORITY_PATTERN = re.compile(
    r"/akn/fi/doc/authority-regulation/(?P<authority>[^/]+)/(?P<year>\d+)/(?P<number>[^/]+)/(?P<lang>[^/]+)$"
)


def parse_akn_uri(uri: str) -> Optional[DocumentInfo]:
    """Parse an akn_uri to extract document components.
    
    Args:
        uri: Full URL or path like:
            https://opendata.finlex.fi/finlex/avoindata/v1/akn/fi/act/statute/2024/123/fin@
            /akn/fi/act/statute/2024/123/fin@
    
    Returns:
        DocumentInfo with parsed components, or None if parsing fails.
    """
    # Extract path from full URL if needed
    if uri.startswith("http"):
        parsed = urlparse(uri)
        path = unquote(parsed.path)
        # Remove base path prefix
        if "/finlex/avoindata/v1" in path:
            path = path.split("/finlex/avoindata/v1")[-1]
    else:
        path = unquote(uri)

    # Try authority-regulation pattern first (more specific)
    match = AUTHORITY_PATTERN.match(path)
    if match:
        return DocumentInfo(
            category="doc",
            document_type="authority-regulation",
            authority=match.group("authority"),
            year=match.group("year"),
            number=match.group("number"),
            lang_and_version=match.group("lang"),
        )

    # Try standard pattern
    match = STANDARD_PATTERN.match(path)
    if match:
        return DocumentInfo(
            category=match.group("category"),
            document_type=match.group("type"),
            year=match.group("year"),
            number=match.group("number"),
            lang_and_version=match.group("lang"),
        )

    return None


def build_api_path(info: DocumentInfo) -> str:
    """Build API path from DocumentInfo.
    
    Args:
        info: Parsed document information.
    
    Returns:
        API path string.
    """
    if info.authority:
        return f"/akn/fi/{info.category}/{info.document_type}/{info.authority}/{info.year}/{info.number}/{info.lang_and_version}"
    return f"/akn/fi/{info.category}/{info.document_type}/{info.year}/{info.number}/{info.lang_and_version}"


def build_list_path(category: str, document_type: str) -> str:
    """Build list endpoint path.
    
    Args:
        category: act, judgment, or doc.
        document_type: Specific document type.
    
    Returns:
        List endpoint path.
    """
    if document_type == "authority-regulation":
        return f"/akn/fi/{category}/{document_type}/list"
    return f"/akn/fi/{category}/{document_type}/list"
