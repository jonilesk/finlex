"""HTTP client for Finlex Open Data API with retry logic."""

import time
from typing import Optional

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from .logging_config import logger


class FinlexClient:
    """HTTP client for Finlex Open Data API.
    
    Features:
    - Automatic User-Agent header
    - Retry with exponential backoff for 429, 5xx, timeouts
    - Configurable sleep between requests
    """

    BASE_URL = "https://opendata.finlex.fi/finlex/avoindata/v1"
    USER_AGENT = "finlex-downloader/0.1.0"

    def __init__(
        self,
        sleep_seconds: float = 5.0,
        max_retries: int = 5,
        backoff_factor: float = 1.0,
        timeout: float = 30.0,
    ):
        """Initialize the client.
        
        Args:
            sleep_seconds: Seconds to wait between requests.
            max_retries: Maximum retry attempts for failed requests.
            backoff_factor: Multiplier for exponential backoff.
            timeout: Request timeout in seconds.
        """
        self.sleep_seconds = sleep_seconds
        self.timeout = timeout
        self._last_request_time: Optional[float] = None

        # Configure retry strategy
        retry_strategy = Retry(
            total=max_retries,
            backoff_factor=backoff_factor,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET"],
            raise_on_status=False,
        )

        # Create session with retry adapter
        self.session = requests.Session()
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)

        # Set default headers
        self.session.headers.update({
            "User-Agent": self.USER_AGENT,
            "Accept-Encoding": "gzip",
        })

    def _wait_if_needed(self) -> None:
        """Wait to respect rate limits."""
        if self._last_request_time is not None:
            elapsed = time.time() - self._last_request_time
            if elapsed < self.sleep_seconds:
                sleep_time = self.sleep_seconds - elapsed
                logger.debug(f"Sleeping {sleep_time:.2f}s before next request")
                time.sleep(sleep_time)

    def get(
        self,
        path: str,
        params: Optional[dict] = None,
        accept: str = "application/xml",
    ) -> requests.Response:
        """Make a GET request to the API.
        
        Args:
            path: API path (will be appended to BASE_URL).
            params: Query parameters.
            accept: Accept header value.
        
        Returns:
            Response object.
        
        Raises:
            requests.RequestException: On network errors after retries.
        """
        self._wait_if_needed()

        url = f"{self.BASE_URL}{path}" if path.startswith("/") else f"{self.BASE_URL}/{path}"
        headers = {"Accept": accept}

        logger.debug(f"GET {url} (Accept: {accept})")

        try:
            response = self.session.get(
                url,
                params=params,
                headers=headers,
                timeout=self.timeout,
            )
            self._last_request_time = time.time()

            if response.status_code == 429:
                logger.warning("Rate limited (429). Retry should have handled this.")
            elif response.status_code >= 400:
                logger.warning(f"HTTP {response.status_code} for {url}")
            else:
                logger.debug(f"HTTP {response.status_code}, {len(response.content)} bytes")

            return response

        except requests.RequestException as e:
            logger.error(f"Request failed: {e}")
            self._last_request_time = time.time()
            raise

    def get_json(self, path: str, params: Optional[dict] = None) -> requests.Response:
        """Make a GET request expecting JSON response."""
        return self.get(path, params=params, accept="application/json")

    def get_xml(self, path: str, params: Optional[dict] = None) -> requests.Response:
        """Make a GET request expecting XML response."""
        return self.get(path, params=params, accept="application/xml")

    def get_pdf(self, path: str, params: Optional[dict] = None) -> requests.Response:
        """Make a GET request for PDF content."""
        return self.get(path, params=params, accept="application/pdf")

    def get_zip(self, path: str, params: Optional[dict] = None) -> requests.Response:
        """Make a GET request for ZIP content."""
        return self.get(path, params=params, accept="application/zip")

    def close(self) -> None:
        """Close the session."""
        self.session.close()

    def __enter__(self) -> "FinlexClient":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()
