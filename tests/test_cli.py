"""Tests for CLI."""

import pytest
from pathlib import Path

from finlex_downloader.cli import parse_args, get_years_for_type


class TestParseArgs:
    """Tests for argument parsing."""

    def test_default_args(self):
        """Default arguments are set correctly."""
        args = parse_args([])
        
        assert args.output == Path("./finlex-data")
        assert args.types == ["act"]
        assert args.years == 1
        assert args.lang == "fin@"
        assert args.limit == 10
        assert args.sleep == 5.0
        assert args.pdf is False
        assert args.zip is False
        assert args.media is False
        assert args.force is False
        assert args.dry_run is False
        assert args.resume is False

    def test_output_dir(self):
        """Output directory is parsed."""
        args = parse_args(["-o", "/tmp/test"])
        assert args.output == Path("/tmp/test")

    def test_multiple_types(self):
        """Multiple document types."""
        args = parse_args(["--types", "act", "judgment"])
        assert args.types == ["act", "judgment"]

    def test_years(self):
        """Years setting."""
        args = parse_args(["--years", "5"])
        assert args.years == 5

    def test_per_type_years(self):
        """Per-type year overrides."""
        args = parse_args([
            "--years", "1",
            "--years-act", "3",
            "--years-judgment", "5",
        ])
        assert args.years == 1
        assert args.years_act == 3
        assert args.years_judgment == 5

    def test_download_options(self):
        """Download option flags."""
        args = parse_args(["--pdf", "--zip", "--media"])
        assert args.pdf is True
        assert args.zip is True
        assert args.media is True

    def test_control_flags(self):
        """Control flags."""
        args = parse_args(["--force", "--dry-run", "--resume"])
        assert args.force is True
        assert args.dry_run is True
        assert args.resume is True

    def test_sleep(self):
        """Sleep setting."""
        args = parse_args(["--sleep", "10"])
        assert args.sleep == 10.0


class TestGetYearsForType:
    """Tests for get_years_for_type function."""

    def test_default_years(self):
        """Use default years when no override."""
        args = parse_args(["--years", "3"])
        assert get_years_for_type(args, "act") == 3
        assert get_years_for_type(args, "judgment") == 3

    def test_override_years(self):
        """Per-type override takes precedence."""
        args = parse_args([
            "--years", "1",
            "--years-act", "5",
        ])
        assert get_years_for_type(args, "act") == 5
        assert get_years_for_type(args, "judgment") == 1

    def test_authority_regulation_override(self):
        """Authority-regulation specific override."""
        args = parse_args([
            "--years", "1",
            "--years-authority-regulation", "10",
        ])
        assert get_years_for_type(args, "authority-regulation") == 10
