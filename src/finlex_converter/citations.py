"""Finnish legal citation parser and path resolver."""

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


# Finnish citation: number/year (e.g., 689/1997, 731/1999)
CITATION_PATTERN = re.compile(r"^(\d+)\s*/\s*(\d{4})$")


@dataclass
class Citation:
    """A parsed Finnish legal citation."""

    number: str
    year: str

    @property
    def display(self) -> str:
        """Human-readable citation string."""
        return f"{self.number}/{self.year}"

    def to_api_path(self, subtype: str = "statute", lang: str = "fin@") -> str:
        """Build API path for this citation.

        Args:
            subtype: Document subtype (statute, statute-consolidated, etc.)
            lang: Language/version marker.

        Returns:
            API path string.
        """
        return f"/akn/fi/act/{subtype}/{self.year}/{self.number}/{lang}"

    def to_folder_path(self, subtype: str = "statute", lang: str = "fin@") -> Path:
        """Build local folder path for this citation.

        Args:
            subtype: Document subtype.
            lang: Language/version marker.

        Returns:
            Relative Path object.
        """
        return Path("act") / subtype / self.year / self.number / lang


def parse_citation(text: str) -> Optional[Citation]:
    """Parse a Finnish legal citation string.

    Supported formats:
        - "689/1997"
        - "731 / 1999"

    Args:
        text: Citation string.

    Returns:
        Citation object, or None if parsing fails.
    """
    text = text.strip()
    match = CITATION_PATTERN.match(text)
    if not match:
        return None
    return Citation(number=match.group(1), year=match.group(2))
