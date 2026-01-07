"""
Google Search Console collector.

Fetches real SEO data from GSC API for verified websites.
Requires service account credentials.
"""

import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from config import get_settings
from config.logging import get_logger
from src.collectors.base import BaseCollector, CollectorResponse, SERPResult
from src.utils.decorators import log_execution_time
from src.utils.exceptions import AuthenticationError, CollectorError

logger = get_logger(__name__)


class GSCResult(SERPResult):
    """Extended result with GSC-specific metrics."""

    clicks: int = 0
    impressions: int = 0
    ctr: float = 0.0
    average_position: float = 0.0


class GSCCollector(BaseCollector):
    """
    Collector using Google Search Console API.

    Fetches real performance data for verified websites.
    Requires service account credentials with GSC access.

    Example:
        >>> collector = GSCCollector()
        >>> response = collector.collect(
        ...     query="site:example.com",
        ...     num_results=10,
        ... )
    """

    source_name: str = "gsc"

    def __init__(self, credentials_path: Path | str | None = None):
        """
        Initialize GSC collector.

        Args:
            credentials_path: Path to service account JSON file.
        """
        settings = get_settings()
        self.credentials_path = Path(credentials_path) if credentials_path else settings.gsc_credentials_path
        self._service = None

    def health_check(self) -> bool:
        """Check if credentials are configured and valid."""
        if not self.credentials_path:
            logger.warning("GSC credentials path not configured")
            return False
        if not self.credentials_path.exists():
            logger.warning("GSC credentials file not found: %s", self.credentials_path)
            return False
        return True

    def _get_service(self) -> Any:
        """
        Get authenticated GSC service.

        Returns:
            Google Search Console service object.
        """
        if self._service:
            return self._service

        try:
            from google.oauth2 import service_account
            from googleapiclient.discovery import build

            credentials = service_account.Credentials.from_service_account_file(
                str(self.credentials_path),
                scopes=["https://www.googleapis.com/auth/webmasters.readonly"],
            )

            self._service = build("searchconsole", "v1", credentials=credentials)
            return self._service

        except Exception as e:
            raise AuthenticationError(f"Failed to authenticate with GSC: {e}")

    @log_execution_time
    def collect(
        self,
        query: str,
        num_results: int = 10,
        country: str = "us",
        language: str = "en",
    ) -> CollectorResponse:
        """
        Fetch data from Google Search Console.

        Args:
            query: Website URL (e.g., 'sc-domain:example.com' or 'https://example.com/').
            num_results: Number of rows to fetch.
            country: Filter by country.
            language: Not used for GSC.

        Returns:
            CollectorResponse with GSC data.
        """
        start_time = time.perf_counter()

        if not self.health_check():
            return CollectorResponse.error_response(
                error="GSC credentials not configured",
                source=self.source_name,
                query=query,
            )

        try:
            service = self._get_service()

            # Date range: last 28 days (GSC has ~48hr delay)
            end_date = datetime.now() - timedelta(days=3)
            start_date = end_date - timedelta(days=28)

            request_body = {
                "startDate": start_date.strftime("%Y-%m-%d"),
                "endDate": end_date.strftime("%Y-%m-%d"),
                "dimensions": ["query", "page"],
                "rowLimit": num_results,
                "dimensionFilterGroups": [
                    {
                        "filters": [
                            {
                                "dimension": "country",
                                "expression": country.upper(),
                            }
                        ]
                    }
                ],
            }

            response = (
                service.searchanalytics()
                .query(siteUrl=query, body=request_body)
                .execute()
            )

            results = self._parse_results(response.get("rows", []))
            duration_ms = int((time.perf_counter() - start_time) * 1000)

            logger.info(
                "Collected %d results for '%s' from GSC",
                len(results),
                query,
            )

            return CollectorResponse.success_response(
                data=results,
                source=self.source_name,
                query=query,
                duration_ms=duration_ms,
            )

        except AuthenticationError:
            raise
        except Exception as e:
            logger.exception("GSC collection failed")
            return CollectorResponse.error_response(
                error=f"GSC error: {str(e)}",
                source=self.source_name,
                query=query,
            )

    def _parse_results(self, rows: list[dict]) -> list[SERPResult]:
        """
        Parse GSC response into SERPResult objects.

        Args:
            rows: Raw rows from GSC API.

        Returns:
            List of GSCResult objects.
        """
        results = []

        for idx, row in enumerate(rows, start=1):
            try:
                keys = row.get("keys", [])
                keyword = keys[0] if len(keys) > 0 else ""
                url = keys[1] if len(keys) > 1 else ""

                # GSC doesn't provide domain separately
                from urllib.parse import urlparse

                domain = urlparse(url).netloc if url else ""

                results.append(
                    GSCResult(
                        position=idx,
                        title=keyword,  # Use keyword as title
                        url=url,
                        snippet="",  # GSC doesn't provide snippets
                        domain=domain,
                        clicks=int(row.get("clicks", 0)),
                        impressions=int(row.get("impressions", 0)),
                        ctr=float(row.get("ctr", 0.0)),
                        average_position=float(row.get("position", 0.0)),
                    )
                )
            except Exception as e:
                logger.warning("Failed to parse GSC row: %s", e)
                continue

        return results
