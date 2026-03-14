"""Tests for CLI."""

import pytest
import responses
from pathlib import Path

from finlex_downloader.cli import parse_args, get_years_for_type
from finlex_downloader.listing import ListConfig, list_documents
from finlex_downloader.client import FinlexClient


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
        assert args.sleep == 1.0
        assert args.sleep_max == 3.0
        assert args.workers == 5
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
        args = parse_args(["--sleep", "2", "--sleep-max", "5"])
        assert args.sleep == 2.0
        assert args.sleep_max == 5.0

    def test_workers(self):
        """Workers setting."""
        args = parse_args(["--workers", "10"])
        assert args.workers == 10


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

    def test_type_statute_param(self):
        """Type statute filter param."""
        args = parse_args(["--type-statute", "act"])
        assert args.type_statute == "act"

    def test_category_statute_param(self):
        """Category statute filter param."""
        args = parse_args(["--category-statute", "new-statute"])
        assert args.category_statute == "new-statute"

    def test_filter_params_default_none(self):
        """Filter params are None by default."""
        args = parse_args([])
        assert args.type_statute is None
        assert args.category_statute is None

    def test_in_force_only_flag(self):
        """--in-force-only flag."""
        args = parse_args(["--in-force-only"])
        assert args.in_force_only is True

    def test_in_force_only_default(self):
        """--in-force-only defaults to False."""
        args = parse_args([])
        assert args.in_force_only is False

    def test_subtypes_single(self):
        """--subtypes with a single value."""
        args = parse_args(["--subtypes", "statute-consolidated"])
        assert args.subtypes == ["statute-consolidated"]

    def test_subtypes_multiple(self):
        """--subtypes with multiple values."""
        args = parse_args(["--subtypes", "statute", "statute-consolidated"])
        assert args.subtypes == ["statute", "statute-consolidated"]

    def test_subtypes_default_none(self):
        """--subtypes defaults to None."""
        args = parse_args([])
        assert args.subtypes is None


class TestListConfigQueryParams:
    """Tests for query param threading to list endpoint."""

    @responses.activate
    def test_type_statute_sent_in_request(self):
        """typeStatute param is sent when configured."""
        responses.add(
            responses.GET,
            "https://opendata.finlex.fi/finlex/avoindata/v1/akn/fi/act/statute/list",
            json=[],
            status=200,
        )
        client = FinlexClient(sleep_seconds=0)
        config = ListConfig(
            category="act",
            document_type="statute",
            type_statute="act",
            category_statute="new-statute",
            max_pages=1,
        )
        list(list_documents(client, config))

        assert "typeStatute=act" in responses.calls[0].request.url
        assert "categoryStatute=new-statute" in responses.calls[0].request.url

    @responses.activate
    def test_filter_params_omitted_when_none(self):
        """typeStatute/categoryStatute omitted when not set."""
        responses.add(
            responses.GET,
            "https://opendata.finlex.fi/finlex/avoindata/v1/akn/fi/act/statute/list",
            json=[],
            status=200,
        )
        client = FinlexClient(sleep_seconds=0)
        config = ListConfig(
            category="act",
            document_type="statute",
            max_pages=1,
        )
        list(list_documents(client, config))

        assert "typeStatute" not in responses.calls[0].request.url
        assert "categoryStatute" not in responses.calls[0].request.url
