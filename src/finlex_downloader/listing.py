"""Listing functionality for Finlex documents."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Iterator, Optional

from .client import FinlexClient
from .logging_config import logger
from .urls import build_list_path


@dataclass
class ListItem:
    """Single item from a list response."""

    akn_uri: str
    status: str  # NEW or MODIFIED


@dataclass
class ListConfig:
    """Configuration for listing documents."""

    category: str  # act, judgment, doc
    document_type: str  # statute, statute-consolidated, etc.
    lang_and_version: str = "fin@"
    start_year: Optional[int] = None
    end_year: Optional[int] = None
    limit: int = 10
    max_pages: Optional[int] = None  # None = fetch all


# Default document types per category
DOCUMENT_TYPES = {
    "act": [
        "statute",
        "statute-consolidated",
        "statute-translated",
        "statute-aland",
        "statute-sami",
    ],
    "judgment": [
        "kko",
        "kho",
    ],
    "doc": [
        "government-proposal",
        "treaty",
        "treaty-consolidated",
        "authority-regulation",
    ],
}


def list_documents(
    client: FinlexClient,
    config: ListConfig,
) -> Iterator[ListItem]:
    """Fetch document list from API with paging.
    
    Args:
        client: HTTP client instance.
        config: List configuration.
    
    Yields:
        ListItem for each document found.
    """
    path = build_list_path(config.category, config.document_type)
    page = 1

    while True:
        if config.max_pages and page > config.max_pages:
            logger.info(f"Reached max pages ({config.max_pages})")
            break

        params = {
            "format": "json",
            "page": page,
            "limit": config.limit,
            "langAndVersion": config.lang_and_version,
        }

        if config.start_year:
            params["startYear"] = config.start_year
        if config.end_year:
            params["endYear"] = config.end_year

        logger.info(f"Fetching {config.category}/{config.document_type} page {page}")
        response = client.get_json(path, params=params)

        if response.status_code != 200:
            logger.error(f"List request failed: HTTP {response.status_code}")
            break

        try:
            items = response.json()
        except ValueError:
            logger.error("Failed to parse JSON response")
            break

        if not items:
            logger.info("No more items, pagination complete")
            break

        for item in items:
            yield ListItem(
                akn_uri=item.get("akn_uri", ""),
                status=item.get("status", ""),
            )

        # If we got fewer items than limit, we're on the last page
        if len(items) < config.limit:
            logger.info(f"Last page reached ({len(items)} items)")
            break

        page += 1


def get_year_range(years_back: int) -> tuple[int, int]:
    """Calculate year range from current year.
    
    Args:
        years_back: Number of years to go back.
    
    Returns:
        Tuple of (start_year, end_year).
    """
    current_year = datetime.now().year
    return (current_year - years_back + 1, current_year)
