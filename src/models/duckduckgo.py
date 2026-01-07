"""
Pydantic models for DuckDuckGo search results.
"""

from datetime import datetime
from typing import Optional
from urllib.parse import urlparse

from pydantic import BaseModel, Field, HttpUrl, computed_field


class DuckDuckGoResult(BaseModel):
    """Single DuckDuckGo search result."""

    title: str = Field(description="Page title")
    url: HttpUrl = Field(description="Page URL")
    snippet: str = Field(default="", description="Result snippet text")
    position: int = Field(ge=1, description="Result position")

    class Config:
        extra = "allow"
        json_schema_extra = {
            "example": {
                "title": "Python Tutorial - W3Schools",
                "url": "https://www.w3schools.com/python/",
                "snippet": "Learn Python programming from scratch...",
                "position": 1,
            }
        }

    @computed_field
    @property
    def domain(self) -> str:
        """Extract domain from URL."""
        return urlparse(str(self.url)).netloc.replace("www.", "")


class DuckDuckGoResponse(BaseModel):
    """DuckDuckGo search response."""

    query: str = Field(description="Search query")
    results: list[DuckDuckGoResult] = Field(default=[], description="Search results")
    total_results: int = Field(ge=0, description="Number of results returned")
    fetched_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        json_schema_extra = {
            "example": {
                "query": "python tutorial",
                "results": [
                    {
                        "title": "Python Tutorial",
                        "url": "https://docs.python.org/3/tutorial/",
                        "snippet": "This tutorial introduces the reader...",
                        "position": 1,
                    }
                ],
                "total_results": 5,
                "fetched_at": "2026-01-08T00:00:00Z",
            }
        }

    @computed_field
    @property
    def top_domains(self) -> list[str]:
        """Extract unique domains from results."""
        domains = []
        for result in self.results:
            if result.domain and result.domain not in domains:
                domains.append(result.domain)
        return domains

    @classmethod
    def from_results(
        cls,
        query: str,
        results: list[DuckDuckGoResult],
    ) -> "DuckDuckGoResponse":
        """Create response from results list."""
        return cls(
            query=query,
            results=results,
            total_results=len(results),
        )
