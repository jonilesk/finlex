"""State management for resumable downloads."""

import json
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Optional

from .logging_config import logger


@dataclass
class DownloadState:
    """State tracking for resumable downloads."""

    # Current progress
    current_category: Optional[str] = None
    current_document_type: Optional[str] = None
    current_page: int = 1
    last_uri: Optional[str] = None
    
    # Completed tracking
    completed_uris: set[str] = field(default_factory=set)
    
    # Timestamps
    started_at: Optional[str] = None
    updated_at: Optional[str] = None

    def to_dict(self) -> dict:
        """Convert to JSON-serializable dict."""
        return {
            "current_category": self.current_category,
            "current_document_type": self.current_document_type,
            "current_page": self.current_page,
            "last_uri": self.last_uri,
            "completed_uris": list(self.completed_uris),
            "started_at": self.started_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "DownloadState":
        """Create from dict."""
        return cls(
            current_category=data.get("current_category"),
            current_document_type=data.get("current_document_type"),
            current_page=data.get("current_page", 1),
            last_uri=data.get("last_uri"),
            completed_uris=set(data.get("completed_uris", [])),
            started_at=data.get("started_at"),
            updated_at=data.get("updated_at"),
        )


class StateManager:
    """Manages download state for resumability."""

    def __init__(self, state_file: Path):
        """Initialize state manager.
        
        Args:
            state_file: Path to state.json file.
        """
        self.state_file = state_file
        self.state = DownloadState()

    def load(self) -> bool:
        """Load state from file.
        
        Returns:
            True if state was loaded, False if no state file exists.
        """
        if not self.state_file.exists():
            logger.info("No existing state file found")
            return False

        try:
            with open(self.state_file) as f:
                data = json.load(f)
            self.state = DownloadState.from_dict(data)
            logger.info(f"Loaded state: page {self.state.current_page}, {len(self.state.completed_uris)} completed")
            return True
        except Exception as e:
            logger.warning(f"Failed to load state file: {e}")
            return False

    def save(self) -> None:
        """Save current state to file."""
        self.state.updated_at = datetime.now().isoformat()
        
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            with open(self.state_file, "w") as f:
                json.dump(self.state.to_dict(), f, indent=2)
            logger.debug(f"Saved state to {self.state_file}")
        except Exception as e:
            logger.error(f"Failed to save state: {e}")

    def start_session(self, category: str, document_type: str) -> None:
        """Start or resume a download session.
        
        Args:
            category: Document category (act, judgment, doc).
            document_type: Document type.
        """
        if self.state.started_at is None:
            self.state.started_at = datetime.now().isoformat()
        
        self.state.current_category = category
        self.state.current_document_type = document_type
        self.save()

    def mark_completed(self, uri: str) -> None:
        """Mark a URI as completed.
        
        Args:
            uri: Document URI that was successfully processed.
        """
        self.state.completed_uris.add(uri)
        self.state.last_uri = uri
        self.save()

    def is_completed(self, uri: str) -> bool:
        """Check if a URI has been completed.
        
        Args:
            uri: Document URI to check.
        
        Returns:
            True if already completed.
        """
        return uri in self.state.completed_uris

    def set_page(self, page: int) -> None:
        """Update current page number.
        
        Args:
            page: Current page being processed.
        """
        self.state.current_page = page
        self.save()

    def get_resume_page(self, category: str, document_type: str) -> int:
        """Get page to resume from.
        
        Args:
            category: Document category.
            document_type: Document type.
        
        Returns:
            Page number to resume from (1 if starting fresh).
        """
        if (self.state.current_category == category and 
            self.state.current_document_type == document_type):
            return self.state.current_page
        return 1

    def reset(self) -> None:
        """Reset state for a fresh start."""
        self.state = DownloadState()
        if self.state_file.exists():
            self.state_file.unlink()
        logger.info("State reset")


@dataclass 
class ManifestEntry:
    """Single entry in the download manifest."""

    akn_uri: str
    status: str  # success, skipped, error
    timestamp: str
    files: list[str] = field(default_factory=list)
    error: Optional[str] = None


class ManifestManager:
    """Manages download manifest for logging results."""

    def __init__(self, manifest_file: Path):
        """Initialize manifest manager.
        
        Args:
            manifest_file: Path to manifest.json file.
        """
        self.manifest_file = manifest_file
        self.entries: list[ManifestEntry] = []
        self._load()

    def _load(self) -> None:
        """Load existing manifest if present."""
        if self.manifest_file.exists():
            try:
                with open(self.manifest_file) as f:
                    data = json.load(f)
                self.entries = [
                    ManifestEntry(**entry) for entry in data.get("entries", [])
                ]
                logger.info(f"Loaded manifest with {len(self.entries)} entries")
            except Exception as e:
                logger.warning(f"Failed to load manifest: {e}")

    def add(self, entry: ManifestEntry) -> None:
        """Add an entry to the manifest.
        
        Args:
            entry: Manifest entry to add.
        """
        self.entries.append(entry)
        self._save()

    def _save(self) -> None:
        """Save manifest to file."""
        self.manifest_file.parent.mkdir(parents=True, exist_ok=True)
        
        data = {
            "updated_at": datetime.now().isoformat(),
            "total_entries": len(self.entries),
            "success_count": sum(1 for e in self.entries if e.status == "success"),
            "skipped_count": sum(1 for e in self.entries if e.status == "skipped"),
            "error_count": sum(1 for e in self.entries if e.status == "error"),
            "entries": [asdict(e) for e in self.entries],
        }
        
        try:
            with open(self.manifest_file, "w") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save manifest: {e}")

    def summary(self) -> dict:
        """Get summary statistics.
        
        Returns:
            Dict with counts by status.
        """
        return {
            "total": len(self.entries),
            "success": sum(1 for e in self.entries if e.status == "success"),
            "skipped": sum(1 for e in self.entries if e.status == "skipped"),
            "error": sum(1 for e in self.entries if e.status == "error"),
        }
