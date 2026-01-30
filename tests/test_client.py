"""Tests for HTTP client."""

import pytest
import responses
from responses import matchers

from finlex_downloader.client import FinlexClient


class TestFinlexClient:
    """Tests for FinlexClient."""

    @responses.activate
    def test_user_agent_header_always_sent(self):
        """User-Agent header is included in all requests."""
        responses.add(
            responses.GET,
            "https://opendata.finlex.fi/finlex/avoindata/v1/test",
            json={"ok": True},
            status=200,
            match=[
                matchers.header_matcher({"User-Agent": "finlex-downloader/0.1.0"})
            ],
        )

        client = FinlexClient(sleep_seconds=0)
        response = client.get("/test", accept="application/json")

        assert response.status_code == 200
        assert len(responses.calls) == 1

    @responses.activate
    def test_retry_on_429(self):
        """Client retries on HTTP 429."""
        # First call returns 429, second succeeds
        responses.add(
            responses.GET,
            "https://opendata.finlex.fi/finlex/avoindata/v1/test",
            status=429,
        )
        responses.add(
            responses.GET,
            "https://opendata.finlex.fi/finlex/avoindata/v1/test",
            json={"ok": True},
            status=200,
        )

        client = FinlexClient(sleep_seconds=0, backoff_factor=0.1)
        response = client.get("/test", accept="application/json")

        assert response.status_code == 200
        assert len(responses.calls) == 2

    @responses.activate
    def test_retry_on_5xx(self):
        """Client retries on HTTP 5xx errors."""
        responses.add(
            responses.GET,
            "https://opendata.finlex.fi/finlex/avoindata/v1/test",
            status=503,
        )
        responses.add(
            responses.GET,
            "https://opendata.finlex.fi/finlex/avoindata/v1/test",
            json={"ok": True},
            status=200,
        )

        client = FinlexClient(sleep_seconds=0, backoff_factor=0.1)
        response = client.get("/test", accept="application/json")

        assert response.status_code == 200
        assert len(responses.calls) == 2

    @responses.activate
    def test_get_json_sets_accept_header(self):
        """get_json() sets Accept: application/json."""
        responses.add(
            responses.GET,
            "https://opendata.finlex.fi/finlex/avoindata/v1/test",
            json=[{"akn_uri": "test"}],
            status=200,
            match=[
                matchers.header_matcher({"Accept": "application/json"})
            ],
        )

        client = FinlexClient(sleep_seconds=0)
        response = client.get_json("/test")

        assert response.status_code == 200

    @responses.activate
    def test_get_xml_sets_accept_header(self):
        """get_xml() sets Accept: application/xml."""
        responses.add(
            responses.GET,
            "https://opendata.finlex.fi/finlex/avoindata/v1/test",
            body="<xml/>",
            status=200,
            match=[
                matchers.header_matcher({"Accept": "application/xml"})
            ],
        )

        client = FinlexClient(sleep_seconds=0)
        response = client.get_xml("/test")

        assert response.status_code == 200

    @responses.activate
    def test_context_manager(self):
        """Client works as context manager."""
        responses.add(
            responses.GET,
            "https://opendata.finlex.fi/finlex/avoindata/v1/test",
            json={"ok": True},
            status=200,
        )

        with FinlexClient(sleep_seconds=0) as client:
            response = client.get_json("/test")
            assert response.status_code == 200
