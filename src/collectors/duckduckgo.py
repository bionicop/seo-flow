"""
DuckDuckGo search collector.

Provides fallback search capability without API key.
Uses the duckduckgo-search library.
"""

import time
from urllib.parse import urlparse

from config.logging import get_logger
from src.collectors.base import BaseCollector, CollectorResponse, SERPResult
from src.utils.decorators import log_execution_time, retry
from src.utils.exceptions import CollectorError

logger = get_logger(__name__)


class DuckDuckGoCollector(BaseCollector):
    """
    Collector using DuckDuckGo search.

    No API key required - uses the duckduckgo-search library.
    Serves as backup when Serper is unavailable.

    Example:
        >>> collector = DuckDuckGoCollector()
        >>> response = collector.collect("seo automation", num_results=10)
        >>> print(response.success)
        True
    """

    source_name: str = "duckduckgo"

    def __init__(self):
        """Initialize DuckDuckGo collector."""
        self._ddg_available = self._check_library()

    def _check_library(self) -> bool:
        """Check if ddgs library is available."""
        try:
            from ddgs import DDGS

            return True
        except ImportError:
            logger.warning("ddgs library not installed")
            return False

    def health_check(self) -> bool:
        """Check if library is available."""
        return self._ddg_available

    @log_execution_time
    @retry(max_attempts=3, delay_seconds=5, exceptions=(CollectorError,))
    def collect(
        self,
        query: str,
        num_results: int = 10,
        country: str = "us",
        language: str = "en",
    ) -> CollectorResponse:
        """
        Fetch search results from DuckDuckGo.

        Args:
            query: Search query or keyword.
            num_results: Number of results to fetch.
            country: Country code (mapped to region).
            language: Language code for results.

        Returns:
            CollectorResponse with search results.
        """
        start_time = time.perf_counter()

        if not self._ddg_available:
            return CollectorResponse.error_response(
                error="duckduckgo-search library not available",
                source=self.source_name,
                query=query,
            )

        try:
            from ddgs import DDGS

            # Map country code to DuckDuckGo region
            region = f"{language}-{country}".lower()

            # Use new ddgs API pattern (no context manager needed)
            raw_results = DDGS().text(
                query,
                region=region,
                max_results=num_results,
            )

            results = self._parse_results(raw_results)
            duration_ms = int((time.perf_counter() - start_time) * 1000)

            logger.info(
                "Collected %d results for '%s' from DuckDuckGo",
                len(results),
                query,
            )

            return CollectorResponse.success_response(
                data=results,
                source=self.source_name,
                query=query,
                duration_ms=duration_ms,
            )

        except Exception as e:
            logger.exception("DuckDuckGo collection failed")
            return CollectorResponse.error_response(
                error=f"DuckDuckGo error: {str(e)}",
                source=self.source_name,
                query=query,
            )

    def _parse_results(self, raw_results: list[dict]) -> list[SERPResult]:
        """
        Parse DuckDuckGo results into SERPResult objects.

        Args:
            raw_results: Raw results from DDGS.

        Returns:
            List of SERPResult objects.
        """
        results = []

        for idx, item in enumerate(raw_results, start=1):
            try:
                url = item.get("href", item.get("link", ""))
                domain = urlparse(url).netloc if url else ""

                results.append(
                    SERPResult(
                        position=idx,
                        title=item.get("title", ""),
                        url=url,
                        snippet=item.get("body", item.get("snippet", "")),
                        domain=domain,
                    )
                )
            except Exception as e:
                logger.warning("Failed to parse DuckDuckGo result: %s", e)
                continue

        return results
