"""
Base collector and shared models for data collection.

All collectors inherit from BaseCollector and return CollectorResponse.
"""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class SERPResult(BaseModel):
    """Single search result from SERP."""

    position: int = Field(ge=1, le=100, description="Ranking position")
    title: str = Field(description="Page title")
    url: str = Field(description="Page URL")
    snippet: str = Field(default="", description="Result snippet")
    domain: str = Field(default="", description="Domain name")


class CollectorResponse(BaseModel):
    """Standardized response from all collectors."""

    success: bool = Field(description="Whether collection succeeded")
    data: list[SERPResult] = Field(default_factory=list, description="Collected results")
    error: str | None = Field(default=None, description="Error message if failed")
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata",
    )

    @classmethod
    def success_response(
        cls,
        data: list[SERPResult],
        source: str,
        query: str,
        duration_ms: int,
    ) -> "CollectorResponse":
        """Create a successful response."""
        return cls(
            success=True,
            data=data,
            metadata={
                "source": source,
                "query": query,
                "timestamp": datetime.utcnow().isoformat(),
                "duration_ms": duration_ms,
                "result_count": len(data),
            },
        )

    @classmethod
    def error_response(
        cls,
        error: str,
        source: str,
        query: str,
    ) -> "CollectorResponse":
        """Create an error response."""
        return cls(
            success=False,
            data=[],
            error=error,
            metadata={
                "source": source,
                "query": query,
                "timestamp": datetime.utcnow().isoformat(),
            },
        )


class BaseCollector(ABC):
    """
    Abstract base class for all data collectors.

    All collectors must implement the collect method and return
    a CollectorResponse with consistent structure.
    """

    source_name: str = "base"

    @abstractmethod
    def collect(
        self,
        query: str,
        num_results: int = 10,
        country: str = "us",
        language: str = "en",
    ) -> CollectorResponse:
        """
        Collect SERP data for a given query.

        Args:
            query: Search query or keyword.
            num_results: Number of results to fetch.
            country: Country code for localization.
            language: Language code for results.

        Returns:
            CollectorResponse with results or error.
        """
        pass

    def health_check(self) -> bool:
        """
        Verify collector is properly configured.

        Returns:
            True if collector is ready to use.
        """
        return True
