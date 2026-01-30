"""Tests for state management."""

import json
import pytest
from pathlib import Path

from finlex_downloader.state import (
    DownloadState,
    StateManager,
    ManifestEntry,
    ManifestManager,
)


class TestDownloadState:
    """Tests for DownloadState dataclass."""

    def test_to_dict(self):
        """Convert state to dict."""
        state = DownloadState(
            current_category="act",
            current_document_type="statute",
            current_page=5,
            completed_uris={"uri1", "uri2"},
        )
        d = state.to_dict()
        
        assert d["current_category"] == "act"
        assert d["current_page"] == 5
        assert set(d["completed_uris"]) == {"uri1", "uri2"}

    def test_from_dict(self):
        """Create state from dict."""
        data = {
            "current_category": "judgment",
            "current_page": 3,
            "completed_uris": ["uri1"],
        }
        state = DownloadState.from_dict(data)
        
        assert state.current_category == "judgment"
        assert state.current_page == 3
        assert "uri1" in state.completed_uris


class TestStateManager:
    """Tests for StateManager."""

    def test_save_and_load(self, tmp_path):
        """State saves and loads correctly."""
        state_file = tmp_path / "state.json"
        
        # Save state
        manager1 = StateManager(state_file)
        manager1.state.current_category = "act"
        manager1.state.current_page = 10
        manager1.state.completed_uris.add("test-uri")
        manager1.save()
        
        # Load in new manager
        manager2 = StateManager(state_file)
        loaded = manager2.load()
        
        assert loaded is True
        assert manager2.state.current_category == "act"
        assert manager2.state.current_page == 10
        assert "test-uri" in manager2.state.completed_uris

    def test_load_nonexistent(self, tmp_path):
        """Load returns False when no state file."""
        manager = StateManager(tmp_path / "nonexistent.json")
        assert manager.load() is False

    def test_mark_completed(self, tmp_path):
        """mark_completed adds URI and saves."""
        state_file = tmp_path / "state.json"
        manager = StateManager(state_file)
        
        manager.mark_completed("uri1")
        manager.mark_completed("uri2")
        
        assert manager.is_completed("uri1")
        assert manager.is_completed("uri2")
        assert not manager.is_completed("uri3")

    def test_get_resume_page(self, tmp_path):
        """get_resume_page returns correct page."""
        state_file = tmp_path / "state.json"
        manager = StateManager(state_file)
        manager.state.current_category = "act"
        manager.state.current_document_type = "statute"
        manager.state.current_page = 5
        
        # Same category/type returns saved page
        assert manager.get_resume_page("act", "statute") == 5
        
        # Different category/type returns 1
        assert manager.get_resume_page("judgment", "kko") == 1

    def test_reset(self, tmp_path):
        """reset clears state and removes file."""
        state_file = tmp_path / "state.json"
        manager = StateManager(state_file)
        manager.state.current_page = 10
        manager.save()
        
        manager.reset()
        
        assert manager.state.current_page == 1
        assert not state_file.exists()


class TestManifestManager:
    """Tests for ManifestManager."""

    def test_add_and_save(self, tmp_path):
        """Manifest entries are saved."""
        manifest_file = tmp_path / "manifest.json"
        manager = ManifestManager(manifest_file)
        
        entry = ManifestEntry(
            akn_uri="test-uri",
            status="success",
            timestamp="2024-01-01T00:00:00",
            files=["file1.xml"],
        )
        manager.add(entry)
        
        # Verify file written
        assert manifest_file.exists()
        with open(manifest_file) as f:
            data = json.load(f)
        assert data["total_entries"] == 1
        assert data["success_count"] == 1

    def test_summary(self, tmp_path):
        """summary returns correct counts."""
        manifest_file = tmp_path / "manifest.json"
        manager = ManifestManager(manifest_file)
        
        manager.add(ManifestEntry(akn_uri="u1", status="success", timestamp="t"))
        manager.add(ManifestEntry(akn_uri="u2", status="success", timestamp="t"))
        manager.add(ManifestEntry(akn_uri="u3", status="skipped", timestamp="t"))
        manager.add(ManifestEntry(akn_uri="u4", status="error", timestamp="t", error="fail"))
        
        summary = manager.summary()
        assert summary["total"] == 4
        assert summary["success"] == 2
        assert summary["skipped"] == 1
        assert summary["error"] == 1
