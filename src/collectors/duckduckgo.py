"""
DuckDuckGo search collector.

Provides fallback search capability without API key.
Uses the duckduckgo-search library with text, news, and image search.
"""

import time
from datetime import datetime
from typing import Any
from urllib.parse import urlparse

from config.logging import get_logger
from src.collectors.base import BaseCollector, CollectorResponse, SERPResult
from src.utils.decorators import log_execution_time, retry
from src.utils.exceptions import CollectorError

logger = get_logger(__name__)


class DDGFullResponse:
    """
    Full response containing all DuckDuckGo data.
    
    Includes text results, news, and metadata.
    """
    
    def __init__(self, query: str):
        self.query = query
        self.fetched_at = datetime.utcnow()
        self.text_results: list[dict] = []
        self.news_results: list[dict] = []
        self.image_results: list[dict] = []
    
    @property
    def top_domains(self) -> list[str]:
        """Extract unique domains from text results."""
        domains = []
        for result in self.text_results[:10]:
            url = result.get("href", "")
            if url:
                domain = urlparse(url).netloc.replace("www.", "")
                if domain and domain not in domains:
                    domains.append(domain)
        return domains
    
    @property
    def total_results(self) -> int:
        """Total results across all types."""
        return len(self.text_results) + len(self.news_results)
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "query": self.query,
            "fetched_at": self.fetched_at.isoformat(),
            "text_count": len(self.text_results),
            "news_count": len(self.news_results),
            "image_count": len(self.image_results),
            "top_domains": self.top_domains,
        }


class DuckDuckGoCollector(BaseCollector):
    """
    Collector using DuckDuckGo search.

    No API key required - uses the duckduckgo-search library.
    Provides text, news, and image search capabilities.
    Serves as backup when Serper is unavailable.

    Example:
        >>> collector = DuckDuckGoCollector()
        >>> response = collector.collect("seo automation", num_results=10)
        >>> print(response.success)
        True
        
        >>> # Full search with news
        >>> full = collector.collect_full("python tutorial")
        >>> print(full.news_results)
    """

    source_name: str = "duckduckgo"
    DEFAULT_TIMEOUT: int = 20  # Seconds

    def __init__(self, timeout: int = 20):
        """
        Initialize DuckDuckGo collector.
        
        Args:
            timeout: Request timeout in seconds.
        """
        self._ddg_available = self._check_library()
        self._timeout = timeout

    def _check_library(self) -> bool:
        """Check if ddgs library is available."""
        try:
            from ddgs import DDGS
            return True
        except ImportError:
            logger.warning("ddgs library not installed")
            return False

    def _get_ddgs(self):
        """Get DDGS instance with configured timeout."""
        from ddgs import DDGS
        return DDGS(timeout=self._timeout)

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
            # Map to DuckDuckGo region format: country-language (e.g., us-en, in-en)
            region = f"{country}-{language}".lower()

            raw_results = self._get_ddgs().text(
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

    @log_execution_time
    def collect_full(
        self,
        query: str,
        num_results: int = 10,
        include_news: bool = True,
        include_images: bool = False,
        country: str = "us",
        language: str = "en",
    ) -> DDGFullResponse:
        """
        Collect full search data including text, news, and images.

        Args:
            query: Search query.
            num_results: Max results per type.
            include_news: Include news results.
            include_images: Include image results.
            country: Country code.
            language: Language code.

        Returns:
            DDGFullResponse with all data.
        """
        if not self._ddg_available:
            raise CollectorError("duckduckgo-search library not available")

        response = DDGFullResponse(query)
        region = f"{country}-{language}".lower()
        ddgs = self._get_ddgs()

        # Text search
        try:
            response.text_results = ddgs.text(
                query,
                region=region,
                max_results=num_results,
            )
        except Exception as e:
            logger.warning("DDG text search failed: %s", e)

        # News search
        if include_news:
            try:
                response.news_results = ddgs.news(
                    query,
                    region=region,
                    max_results=min(num_results, 20),
                )
            except Exception as e:
                logger.warning("DDG news search failed: %s", e)

        # Image search
        if include_images:
            try:
                response.image_results = ddgs.images(
                    query,
                    region=region,
                    max_results=min(num_results, 20),
                )
            except Exception as e:
                logger.warning("DDG image search failed: %s", e)

        logger.info(
            "Full DDG search for '%s': %d text, %d news, %d images",
            query,
            len(response.text_results),
            len(response.news_results),
            len(response.image_results),
        )

        return response

    def search_news(
        self,
        query: str,
        num_results: int = 10,
        timelimit: str | None = None,
    ) -> list[dict]:
        """
        Search DuckDuckGo news.

        Args:
            query: Search query.
            num_results: Max results.
            timelimit: Time filter ('d' day, 'w' week, 'm' month).

        Returns:
            List of news results.
        """
        if not self._ddg_available:
            return []

        try:
            kwargs = {"max_results": num_results}
            if timelimit:
                kwargs["timelimit"] = timelimit

            results = self._get_ddgs().news(query, **kwargs)
            logger.info("Found %d news for '%s'", len(results), query)
            return results
        except Exception as e:
            logger.error("DDG news search failed: %s", e)
            return []

    def find_position(
        self,
        query: str,
        target_domain: str,
        num_results: int = 50,
    ) -> int | None:
        """
        Find ranking position of a domain.

        Args:
            query: Search query.
            target_domain: Domain to find.
            num_results: Max results to search.

        Returns:
            Position (1-based) or None if not found.
        """
        response = self.collect(query, num_results=num_results)

        if not response.success:
            return None

        target_domain = target_domain.lower().replace("www.", "")

        for result in response.data:
            domain = result.domain.lower().replace("www.", "")
            if target_domain in domain:
                logger.info(
                    "Found %s at position %d for '%s'",
                    target_domain,
                    result.position,
                    query,
                )
                return result.position

        logger.info("%s not found in top %d for '%s'", target_domain, num_results, query)
        return None

    def compare_with_serper(
        self,
        query: str,
        serper_results: list[SERPResult],
        num_results: int = 10,
    ) -> dict[str, Any]:
        """
        Compare DuckDuckGo results with Serper.

        Useful for cross-validation of SERP data.

        Args:
            query: Search query.
            serper_results: Results from Serper.
            num_results: Number of DDG results.

        Returns:
            Comparison data with overlap and differences.
        """
        ddg_response = self.collect(query, num_results=num_results)

        if not ddg_response.success:
            return {"error": ddg_response.error}

        # Extract domains
        serper_domains = [r.domain.replace("www.", "") for r in serper_results]
        ddg_domains = [r.domain.replace("www.", "") for r in ddg_response.data]

        # Find overlap
        overlap = set(serper_domains) & set(ddg_domains)

        return {
            "query": query,
            "serper_count": len(serper_results),
            "ddg_count": len(ddg_response.data),
            "overlap_count": len(overlap),
            "overlap_domains": list(overlap),
            "serper_only": list(set(serper_domains) - overlap),
            "ddg_only": list(set(ddg_domains) - overlap),
            "overlap_percentage": len(overlap) / max(len(serper_domains), 1) * 100,
        }

    def batch_collect(
        self,
        queries: list[str],
        num_results: int = 10,
    ) -> dict[str, CollectorResponse]:
        """
        Collect results for multiple queries.

        Args:
            queries: List of search queries.
            num_results: Results per query.

        Returns:
            Dictionary mapping query to response.
        """
        logger.info("Batch collecting %d queries from DDG", len(queries))

        results = {}
        for query in queries:
            try:
                results[query] = self.collect(query, num_results=num_results)
                time.sleep(0.5)  # Rate limiting
            except Exception as e:
                logger.error("Failed to collect '%s': %s", query, e)
                results[query] = CollectorResponse.error_response(
                    error=str(e),
                    source=self.source_name,
                    query=query,
                )

        success_count = sum(1 for r in results.values() if r.success)
        logger.info("Batch complete: %d/%d succeeded", success_count, len(queries))

        return results

    def _parse_results(self, raw_results: list[dict]) -> list[SERPResult]:
        """Parse DuckDuckGo results into SERPResult objects."""
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
