"""
Serper.dev API collector.

Fetches SERP data including organic results, knowledge graph,
People Also Ask, and related searches.

Requires SERPER_API_KEY in environment.
"""

import time
from datetime import datetime
from threading import Lock
from typing import Any
from urllib.parse import urlparse

import requests

from config import get_settings
from config.logging import get_logger
from src.collectors.base import BaseCollector, CollectorResponse, SERPResult
from src.utils.decorators import log_execution_time, retry
from src.utils.exceptions import AuthenticationError, CollectorError, RateLimitError

logger = get_logger(__name__)


class RateLimiter:
    """
    Thread-safe rate limiter for API requests.
    
    Ensures minimum interval between requests to avoid rate limiting.
    """
    
    def __init__(self, min_interval: float = 0.5):
        """
        Initialize rate limiter.
        
        Args:
            min_interval: Minimum seconds between requests.
        """
        self._min_interval = min_interval
        self._last_request_time = 0.0
        self._lock = Lock()
    
    def wait(self) -> None:
        """Wait if necessary to respect rate limit."""
        with self._lock:
            current_time = time.time()
            elapsed = current_time - self._last_request_time
            
            if elapsed < self._min_interval:
                sleep_time = self._min_interval - elapsed
                logger.debug("Rate limiting: sleeping %.2fs", sleep_time)
                time.sleep(sleep_time)
            
            self._last_request_time = time.time()
    
    def reset(self) -> None:
        """Reset the rate limiter state."""
        with self._lock:
            self._last_request_time = 0.0


# Global rate limiter for Serper API (shared across instances)
_serper_rate_limiter = RateLimiter(min_interval=0.5)


class SerperFullResponse:
    """
    Enhanced response containing all Serper API data.
    
    Includes organic results, knowledge graph, PAA, related searches,
    and computed competition metrics.
    """
    
    def __init__(self, raw_data: dict, query: str):
        self.raw_data = raw_data
        self.query = query
        self.fetched_at = datetime.utcnow()
        
        # Parse all sections
        self.search_parameters = raw_data.get("searchParameters", {})
        self.organic = raw_data.get("organic", [])
        self.knowledge_graph = raw_data.get("knowledgeGraph")
        self.people_also_ask = raw_data.get("peopleAlsoAsk", [])
        self.related_searches = raw_data.get("relatedSearches", [])
        self.credits_used = raw_data.get("credits", 1)
    
    @property
    def top_domains(self) -> list[str]:
        """Extract top 10 domains from organic results."""
        domains = []
        for result in self.organic[:10]:
            url = result.get("link", "")
            if url:
                domain = urlparse(url).netloc
                if domain and domain not in domains:
                    domains.append(domain)
        return domains
    
    @property
    def has_featured_snippet(self) -> bool:
        """Check if a featured snippet exists (position 0)."""
        return any(r.get("position", 1) == 0 for r in self.organic)
    
    @property
    def has_sitelinks(self) -> bool:
        """Check if any result has sitelinks."""
        return any(r.get("sitelinks") for r in self.organic)
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "query": self.query,
            "fetched_at": self.fetched_at.isoformat(),
            "organic_count": len(self.organic),
            "knowledge_graph": self.knowledge_graph,
            "people_also_ask_count": len(self.people_also_ask),
            "related_searches_count": len(self.related_searches),
            "top_domains": self.top_domains,
            "has_featured_snippet": self.has_featured_snippet,
            "has_sitelinks": self.has_sitelinks,
            "credits_used": self.credits_used,
            "raw_data": self.raw_data,
        }


class CompetitionMetrics:
    """
    Computed competition and opportunity metrics.
    
    Analyzes SERP data to determine keyword difficulty
    and opportunity score.
    """
    
    def __init__(self, serp_response: SerperFullResponse):
        self.query = serp_response.query
        self._compute_metrics(serp_response)
    
    def _compute_metrics(self, serp: SerperFullResponse) -> None:
        """Compute competition score based on SERP features."""
        score = 0
        
        # Factor 1: Number of organic results (max 25 points)
        result_count = len(serp.organic)
        if result_count >= 10:
            score += 25
        elif result_count >= 5:
            score += 15
        else:
            score += 5
        
        # Factor 2: Knowledge graph presence (20 points)
        if serp.knowledge_graph:
            score += 20
        
        # Factor 3: Related searches indicate interest (max 15 points)
        related_count = len(serp.related_searches)
        score += min(related_count * 3, 15)
        
        # Factor 4: People Also Ask complexity (max 15 points)
        paa_count = len(serp.people_also_ask)
        score += min(paa_count * 3, 15)
        
        # Factor 5: Sitelinks indicate dominant players (15 points)
        if serp.has_sitelinks:
            score += 15
        
        # Factor 6: Featured snippet (10 points extra difficulty)
        if serp.has_featured_snippet:
            score += 10
        
        # Store computed values
        self.competition_score = min(score, 100)
        self.opportunity_score = 100 - self.competition_score
        
        if self.competition_score >= 70:
            self.difficulty = "High"
        elif self.competition_score >= 40:
            self.difficulty = "Medium"
        else:
            self.difficulty = "Low"
        
        self.organic_count = result_count
        self.has_knowledge_graph = serp.knowledge_graph is not None
        self.related_searches_count = len(serp.related_searches)
        self.paa_count = len(serp.people_also_ask)
        self.top_domains = serp.top_domains
        self.has_featured_snippet = serp.has_featured_snippet
        self.has_sitelinks = serp.has_sitelinks
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "query": self.query,
            "competition_score": self.competition_score,
            "opportunity_score": self.opportunity_score,
            "difficulty": self.difficulty,
            "organic_count": self.organic_count,
            "has_knowledge_graph": self.has_knowledge_graph,
            "related_searches_count": self.related_searches_count,
            "paa_count": self.paa_count,
            "top_domains": self.top_domains,
            "has_featured_snippet": self.has_featured_snippet,
            "has_sitelinks": self.has_sitelinks,
        }


class SerperCollector(BaseCollector):
    """
    Enhanced Serper.dev API collector.

    Provides comprehensive SERP data including:
    - Organic results with position tracking
    - Knowledge graph extraction
    - People Also Ask questions
    - Related searches for keyword expansion
    - Competition metrics calculation
    - Time-filtered searches for trend analysis
    - Batch keyword analysis

    Example:
        >>> collector = SerperCollector()
        >>> response = collector.collect("python tutorial", num_results=10)
        >>> print(response.data[0].position)
        1
        
        >>> # Full analysis with competition metrics
        >>> analysis = collector.analyze_keyword("python async")
        >>> print(analysis["competition"]["difficulty"])
        "Medium"
    """

    source_name: str = "serper"
    BASE_URL: str = "https://google.serper.dev/search"
    
    # Time filter options for trend analysis
    TIME_FILTERS = {
        "hour": "qdr:h",
        "day": "qdr:d",
        "week": "qdr:w",
        "month": "qdr:m",
        "year": "qdr:y",
    }

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

    def _make_request(
        self,
        query: str,
        num_results: int = 10,
        country: str = "in",
        language: str = "en",
        location: str | None = None,
        time_filter: str | None = None,
        autocorrect: bool = True,
    ) -> dict[str, Any]:
        """
        Make a request to Serper API.
        
        Args:
            query: Search query.
            num_results: Number of results (max 100).
            country: Country code (e.g., 'in', 'us', 'uk').
            language: Language code (e.g., 'en', 'es').
            location: Geographic location (e.g., 'Haryana, India').
            time_filter: Time filter key ('hour', 'day', 'week', 'month', 'year').
            autocorrect: Enable Google autocorrect.
        
        Returns:
            Raw API response as dictionary.
        
        Raises:
            RateLimitError: If rate limited.
            AuthenticationError: If API key invalid.
            CollectorError: On other failures.
        """
        headers = {
            "X-API-KEY": self.api_key,
            "Content-Type": "application/json",
        }

        payload = {
            "q": query,
            "num": min(num_results, 100),
            "gl": country.lower(),
            "hl": language.lower(),
            "autocorrect": autocorrect,
        }
        
        # Add optional location
        if location:
            payload["location"] = location
        
        # Add time filter for trend analysis
        if time_filter and time_filter in self.TIME_FILTERS:
            payload["tbs"] = self.TIME_FILTERS[time_filter]

        # Apply rate limiting
        _serper_rate_limiter.wait()

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

        return response.json()

    @log_execution_time
    @retry(max_attempts=3, delay_seconds=5, exceptions=(RateLimitError, CollectorError))
    def collect(
        self,
        query: str,
        num_results: int = 10,
        country: str = "in",
        language: str = "en",
    ) -> CollectorResponse:
        """
        Fetch SERP data from Serper.dev API.

        Args:
            query: Search query or keyword.
            num_results: Number of results (max 100).
            country: Country code (e.g., 'in', 'us', 'uk').
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

        try:
            data = self._make_request(query, num_results, country, language)
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

    @log_execution_time
    def collect_full(
        self,
        query: str,
        num_results: int = 10,
        country: str = "in",
        language: str = "en",
        location: str | None = None,
        time_filter: str | None = None,
    ) -> SerperFullResponse:
        """
        Fetch complete SERP data including all features.
        
        Unlike collect(), this returns all API data including
        knowledge graph, PAA, and related searches.

        Args:
            query: Search query or keyword.
            num_results: Number of results (max 100).
            country: Country code (e.g., 'in', 'us', 'uk').
            language: Language code (e.g., 'en', 'es').
            location: Geographic location (e.g., 'Mumbai, India').
            time_filter: Time filter ('hour', 'day', 'week', 'month', 'year').

        Returns:
            SerperFullResponse with all SERP features.
        
        Example:
            >>> response = collector.collect_full("python async", location="India")
            >>> print(response.related_searches)
            [{"query": "python asyncio"}, ...]
        """
        if not self.api_key:
            raise CollectorError("Serper API key not configured")
        
        data = self._make_request(
            query=query,
            num_results=num_results,
            country=country,
            language=language,
            location=location,
            time_filter=time_filter,
        )
        
        response = SerperFullResponse(data, query)
        
        logger.info(
            "Full SERP collected for '%s': %d organic, %d PAA, %d related",
            query,
            len(response.organic),
            len(response.people_also_ask),
            len(response.related_searches),
        )
        
        return response

    def get_competition_metrics(self, query: str, **kwargs) -> CompetitionMetrics:
        """
        Analyze competition for a keyword.
        
        Fetches SERP data and computes competition score,
        difficulty level, and opportunity score.

        Args:
            query: Keyword to analyze.
            **kwargs: Additional arguments for collect_full().

        Returns:
            CompetitionMetrics with analysis results.
        
        Example:
            >>> metrics = collector.get_competition_metrics("seo tools")
            >>> print(f"Difficulty: {metrics.difficulty}")
            >>> print(f"Opportunity: {metrics.opportunity_score}%")
        """
        serp = self.collect_full(query, num_results=20, **kwargs)
        return CompetitionMetrics(serp)

    def get_related_keywords(
        self,
        query: str,
        include_paa: bool = True,
        **kwargs,
    ) -> list[str]:
        """
        Extract related keywords from SERP.
        
        Combines related searches and People Also Ask questions
        for keyword expansion.

        Args:
            query: Seed keyword.
            include_paa: Include PAA questions as keywords.
            **kwargs: Additional arguments for collect_full().

        Returns:
            List of related keywords.
        
        Example:
            >>> keywords = collector.get_related_keywords("python tutorial")
            >>> print(keywords[:5])
            ['python for beginners', 'learn python', ...]
        """
        serp = self.collect_full(query, num_results=10, **kwargs)
        
        keywords = []
        
        # Add related searches
        for item in serp.related_searches:
            kw = item.get("query", "").strip()
            if kw and kw not in keywords:
                keywords.append(kw)
        
        # Add PAA questions if requested
        if include_paa:
            for item in serp.people_also_ask:
                question = item.get("question", "").strip()
                if question and question not in keywords:
                    keywords.append(question)
        
        logger.info("Found %d related keywords for '%s'", len(keywords), query)
        return keywords

    def find_position(
        self,
        query: str,
        target_domain: str,
        num_results: int = 100,
        **kwargs,
    ) -> int | None:
        """
        Find ranking position of a domain for a keyword.

        Args:
            query: Search query.
            target_domain: Domain to find (e.g., 'example.com').
            num_results: Max results to search through.
            **kwargs: Additional arguments for collect_full().

        Returns:
            Position (1-100) or None if not found.
        
        Example:
            >>> pos = collector.find_position("python", "python.org")
            >>> print(f"python.org ranks at position {pos}")
        """
        serp = self.collect_full(query, num_results=num_results, **kwargs)
        
        target_domain = target_domain.lower().replace("www.", "")
        
        for result in serp.organic:
            url = result.get("link", "")
            domain = urlparse(url).netloc.lower().replace("www.", "")
            
            if target_domain in domain:
                position = result.get("position", 0)
                logger.info(
                    "Found %s at position %d for '%s'",
                    target_domain,
                    position,
                    query,
                )
                return position
        
        logger.info("%s not found in top %d for '%s'", target_domain, num_results, query)
        return None

    def analyze_keyword(
        self,
        keyword: str,
        target_url: str | None = None,
        **kwargs,
    ) -> dict[str, Any]:
        """
        Complete keyword analysis with all metrics.
        
        Combines SERP data, competition metrics, and position
        tracking for comprehensive keyword analysis.

        Args:
            keyword: Keyword to analyze.
            target_url: Optional URL to check ranking position.
            **kwargs: Additional arguments for collect_full().

        Returns:
            Dictionary with complete analysis.
        
        Example:
            >>> analysis = collector.analyze_keyword(
            ...     "fastapi tutorial",
            ...     target_url="https://fastapi.tiangolo.com"
            ... )
            >>> print(analysis["competition"]["difficulty"])
            >>> print(analysis["opportunities"])
        """
        logger.info("Analyzing keyword: %s", keyword)
        
        # Fetch full SERP data
        serp = self.collect_full(keyword, num_results=100, **kwargs)
        
        # Compute competition metrics
        competition = CompetitionMetrics(serp)
        
        # Find target URL position if provided
        position = None
        if target_url:
            target_domain = urlparse(target_url).netloc.lower().replace("www.", "")
            for result in serp.organic:
                url = result.get("link", "")
                domain = urlparse(url).netloc.lower().replace("www.", "")
                if target_domain in domain:
                    position = result.get("position")
                    break
        
        # Identify opportunities
        opportunities = []
        
        if position is None:
            opportunities.append({
                "type": "not_ranking",
                "message": "Not ranking - potential new content opportunity",
                "priority": "medium",
            })
        elif position > 10:
            opportunities.append({
                "type": "position_improvement",
                "message": f"Ranking at position {position} - optimization opportunity",
                "priority": "high" if position <= 20 else "medium",
            })
        elif position <= 3:
            opportunities.append({
                "type": "maintain",
                "message": "Strong position - monitor and maintain",
                "priority": "low",
            })
        
        if competition.difficulty == "Low":
            opportunities.append({
                "type": "quick_win",
                "message": "Low competition - quick win potential",
                "priority": "high",
            })
        
        if serp.related_searches:
            opportunities.append({
                "type": "keyword_expansion",
                "message": f"{len(serp.related_searches)} related keywords found",
                "priority": "medium",
            })
        
        analysis = {
            "keyword": keyword,
            "timestamp": datetime.utcnow().isoformat(),
            "serp_summary": {
                "organic_count": len(serp.organic),
                "has_knowledge_graph": serp.knowledge_graph is not None,
                "paa_count": len(serp.people_also_ask),
                "related_count": len(serp.related_searches),
                "top_domains": serp.top_domains[:5],
            },
            "competition": competition.to_dict(),
            "target_url": target_url,
            "target_position": position,
            "is_ranking": position is not None,
            "opportunities": opportunities,
            "related_keywords": [s.get("query") for s in serp.related_searches[:10]],
            "paa_questions": [p.get("question") for p in serp.people_also_ask[:5]],
        }
        
        logger.info("Analysis complete for: %s", keyword)
        return analysis

    def batch_analyze(
        self,
        keywords: list[str],
        target_url: str | None = None,
        **kwargs,
    ) -> dict[str, dict[str, Any]]:
        """
        Analyze multiple keywords.
        
        Note: This makes sequential API calls. For high-volume
        analysis, consider rate limiting.

        Args:
            keywords: List of keywords to analyze.
            target_url: Optional URL to check ranking.
            **kwargs: Additional arguments for analyze_keyword().

        Returns:
            Dictionary mapping keyword to analysis result.
        
        Example:
            >>> results = collector.batch_analyze(
            ...     ["python seo", "seo automation", "serp api"],
            ...     target_url="https://example.com"
            ... )
            >>> for kw, analysis in results.items():
            ...     print(f"{kw}: {analysis['competition']['difficulty']}")
        """
        logger.info("Batch analyzing %d keywords", len(keywords))
        
        results = {}
        for keyword in keywords:
            try:
                results[keyword] = self.analyze_keyword(keyword, target_url, **kwargs)
                # Small delay to respect rate limits
                time.sleep(0.5)
            except Exception as e:
                logger.error("Failed to analyze '%s': %s", keyword, e)
                results[keyword] = {"error": str(e)}
        
        logger.info("Batch analysis complete: %d/%d succeeded", 
                      sum(1 for r in results.values() if "error" not in r),
                      len(keywords))
        return results

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
