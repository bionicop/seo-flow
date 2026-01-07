"""
Serper.dev API collector.

Fetches SERP data using the Serper.dev API.
Requires SERPER_API_KEY in environment.
"""

import time
from urllib.parse import urlparse

import requests

from config import get_settings
from config.logging import get_logger
from src.collectors.base import BaseCollector, CollectorResponse, SERPResult
from src.utils.decorators import log_execution_time, retry
from src.utils.exceptions import AuthenticationError, CollectorError, RateLimitError

logger = get_logger(__name__)


class SerperCollector(BaseCollector):
    """
    Collector using Serper.dev API.

    Provides real-time SERP data with keyword rankings.

    Example:
        >>> collector = SerperCollector()
        >>> response = collector.collect("python tutorial", num_results=10)
        >>> print(response.data[0].position)
        1
    """

    source_name: str = "serper"
    BASE_URL: str = "https://google.serper.dev/search"

    def __init__(self, api_key: str | None = None):
        """
        Initialize Serper collector.

        Args:
            api_key: Serper API key. Falls back to env if not provided.
        """
        settings = get_settings()
        self.api_key = api_key or settings.serper_api_key
        self.timeout = settings.request_timeout_seconds
        self.max_retries = settings.max_retries
        self.retry_delay = settings.retry_delay_seconds

    def health_check(self) -> bool:
        """Check if API key is configured."""
        if not self.api_key:
            logger.warning("Serper API key not configured")
            return False
        return True

    @log_execution_time
    @retry(max_attempts=3, delay_seconds=5, exceptions=(RateLimitError, CollectorError))
    def collect(
        self,
        query: str,
        num_results: int = 10,
        country: str = "us",
        language: str = "en",
    ) -> CollectorResponse:
        """
        Fetch SERP data from Serper.dev API.

        Args:
            query: Search query or keyword.
            num_results: Number of results (max 100).
            country: Country code (e.g., 'us', 'uk').
            language: Language code (e.g., 'en', 'es').

        Returns:
            CollectorResponse with SERP results.
        """
        start_time = time.perf_counter()

        if not self.api_key:
            return CollectorResponse.error_response(
                error="Serper API key not configured",
                source=self.source_name,
                query=query,
            )

        headers = {
            "X-API-KEY": self.api_key,
            "Content-Type": "application/json",
        }

        payload = {
            "q": query,
            "num": min(num_results, 100),
            "gl": country.lower(),
            "hl": language.lower(),
        }

        try:
            response = requests.post(
                self.BASE_URL,
                headers=headers,
                json=payload,
                timeout=self.timeout,
            )

            # Handle rate limiting
            if response.status_code == 429:
                retry_after = int(response.headers.get("Retry-After", 60))
                raise RateLimitError(
                    "Serper API rate limit exceeded",
                    retry_after=retry_after,
                )

            # Handle authentication errors
            if response.status_code in (401, 403):
                raise AuthenticationError("Invalid Serper API key")

            # Handle other errors
            if response.status_code != 200:
                raise CollectorError(
                    f"Serper API error: {response.status_code} - {response.text}"
                )

            data = response.json()
            results = self._parse_results(data)
            duration_ms = int((time.perf_counter() - start_time) * 1000)

            logger.info(
                "Collected %d results for '%s' from Serper",
                len(results),
                query,
            )

            return CollectorResponse.success_response(
                data=results,
                source=self.source_name,
                query=query,
                duration_ms=duration_ms,
            )

        except (RateLimitError, AuthenticationError):
            raise
        except requests.Timeout:
            return CollectorResponse.error_response(
                error=f"Request timeout after {self.timeout}s",
                source=self.source_name,
                query=query,
            )
        except requests.RequestException as e:
            return CollectorResponse.error_response(
                error=f"Network error: {str(e)}",
                source=self.source_name,
                query=query,
            )
        except Exception as e:
            logger.exception("Unexpected error in Serper collector")
            return CollectorResponse.error_response(
                error=f"Unexpected error: {str(e)}",
                source=self.source_name,
                query=query,
            )

    def _parse_results(self, data: dict) -> list[SERPResult]:
        """
        Parse Serper API response into SERPResult objects.

        Args:
            data: Raw API response.

        Returns:
            List of SERPResult objects.
        """
        results = []
        organic = data.get("organic", [])

        for item in organic:
            try:
                url = item.get("link", "")
                domain = urlparse(url).netloc if url else ""

                results.append(
                    SERPResult(
                        position=item.get("position", len(results) + 1),
                        title=item.get("title", ""),
                        url=url,
                        snippet=item.get("snippet", ""),
                        domain=domain,
                    )
                )
            except Exception as e:
                logger.warning("Failed to parse result: %s", e)
                continue

        return results
