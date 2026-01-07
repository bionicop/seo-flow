"""
Pydantic models for Serper.dev API responses.

Provides validation for all Serper API data including organic results,
knowledge graphs, People Also Ask, and related searches.
"""

from datetime import datetime
from typing import Any, Optional
from urllib.parse import urlparse

from pydantic import BaseModel, Field, HttpUrl, computed_field, model_validator


class SerperSitelink(BaseModel):
    """Sitelink under an organic result."""

    title: str
    link: HttpUrl


class SerperOrganic(BaseModel):
    """Single organic search result from Serper."""

    position: int = Field(ge=0, le=100, description="SERP position (0 = featured snippet)")
    title: str = Field(description="Page title")
    link: HttpUrl = Field(description="Page URL")
    snippet: str = Field(default="", description="Result snippet text")
    sitelinks: Optional[list[SerperSitelink]] = Field(
        default=None, description="Expanded sitelinks under result"
    )
    date: Optional[str] = Field(default=None, description="Published date if available")

    class Config:
        extra = "allow"
        json_schema_extra = {
            "example": {
                "position": 1,
                "title": "Python Tutorial - W3Schools",
                "link": "https://www.w3schools.com/python/",
                "snippet": "Learn Python programming from scratch...",
                "date": "Jan 5, 2026",
            }
        }

    @computed_field
    @property
    def domain(self) -> str:
        """Extract domain from URL."""
        return urlparse(str(self.link)).netloc.replace("www.", "")


class SerperKnowledgeGraph(BaseModel):
    """Knowledge graph data from Google SERP."""

    title: str = Field(description="Entity title")
    type: Optional[str] = Field(default=None, description="Entity type (e.g., 'Company')")
    description: Optional[str] = Field(default=None, description="Entity description")
    website: Optional[HttpUrl] = Field(default=None, description="Official website")
    imageUrl: Optional[HttpUrl] = Field(default=None, description="Entity image URL")
    attributes: Optional[dict[str, str]] = Field(
        default=None, description="Key-value attributes (e.g., CEO, Founded)"
    )

    class Config:
        extra = "allow"
        json_schema_extra = {
            "example": {
                "title": "Python",
                "type": "Programming language",
                "description": "Python is a high-level programming language...",
                "website": "https://python.org",
                "attributes": {
                    "Developer": "Guido van Rossum",
                    "First appeared": "1991",
                },
            }
        }


class SerperPeopleAlsoAsk(BaseModel):
    """People Also Ask question from SERP."""

    question: str = Field(description="The question text")
    snippet: str = Field(description="Answer snippet")
    title: str = Field(description="Source page title")
    link: HttpUrl = Field(description="Source page URL")

    class Config:
        json_schema_extra = {
            "example": {
                "question": "What is Python used for?",
                "snippet": "Python is used for web development, data science...",
                "title": "Python Uses - Real Python",
                "link": "https://realpython.com/what-can-i-do-with-python/",
            }
        }


class SerperRelatedSearch(BaseModel):
    """Related search query suggestion."""

    query: str = Field(description="Related search query")

    class Config:
        json_schema_extra = {"example": {"query": "python tutorial for beginners"}}


class SerperSearchParameters(BaseModel):
    """Search parameters used in the request."""

    q: str = Field(description="Search query")
    gl: str = Field(default="in", description="Country code (in, us, uk, etc.)")
    hl: str = Field(default="en", description="Language code")
    num: int = Field(default=10, ge=1, le=100, description="Number of results")
    type: str = Field(default="search", description="Search type")
    location: Optional[str] = Field(default=None, description="Geographic location")
    tbs: Optional[str] = Field(default=None, description="Time filter (qdr:h, qdr:d, etc.)")

    class Config:
        extra = "allow"


class SerperAPIResponse(BaseModel):
    """
    Complete Serper API response.

    Contains all sections returned by the API including organic results,
    knowledge graph, People Also Ask, and related searches.
    """

    searchParameters: SerperSearchParameters
    organic: list[SerperOrganic] = Field(default=[], description="Organic search results")
    knowledgeGraph: Optional[SerperKnowledgeGraph] = Field(
        default=None, description="Knowledge graph panel if present"
    )
    peopleAlsoAsk: Optional[list[SerperPeopleAlsoAsk]] = Field(
        default=[], description="People Also Ask questions"
    )
    relatedSearches: Optional[list[SerperRelatedSearch]] = Field(
        default=[], description="Related search queries"
    )
    credits: int = Field(default=1, ge=0, description="API credits used")
    fetched_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        extra = "allow"

    @computed_field
    @property
    def top_domains(self) -> list[str]:
        """Extract unique domains from top 10 results."""
        domains = []
        for result in self.organic[:10]:
            domain = result.domain
            if domain and domain not in domains:
                domains.append(domain)
        return domains

    @computed_field
    @property
    def has_featured_snippet(self) -> bool:
        """Check if position 0 (featured snippet) exists."""
        return any(r.position == 0 for r in self.organic)

    @computed_field
    @property
    def has_sitelinks(self) -> bool:
        """Check if any result has sitelinks."""
        return any(r.sitelinks for r in self.organic)

    @computed_field
    @property
    def organic_count(self) -> int:
        """Number of organic results."""
        return len(self.organic)

    @computed_field
    @property
    def paa_count(self) -> int:
        """Number of People Also Ask questions."""
        return len(self.peopleAlsoAsk or [])

    @computed_field
    @property
    def related_count(self) -> int:
        """Number of related searches."""
        return len(self.relatedSearches or [])


class SerperMetrics(BaseModel):
    """
    Extracted metrics from Serper response.

    Computed values for storage, trend analysis, and reporting.
    """

    query: str = Field(description="Search query")
    total_results: int = Field(ge=0, description="Number of organic results")
    top_position: Optional[int] = Field(
        default=None, ge=0, le=100, description="Position of top result"
    )
    top_url: Optional[HttpUrl] = Field(default=None, description="URL of top result")
    top_domain: Optional[str] = Field(default=None, description="Domain of top result")
    has_knowledge_graph: bool = Field(default=False, description="Knowledge graph present")
    has_featured_snippet: bool = Field(default=False, description="Featured snippet present")
    has_sitelinks: bool = Field(default=False, description="Any result has sitelinks")
    related_searches_count: int = Field(default=0, ge=0, description="Related searches count")
    paa_count: int = Field(default=0, ge=0, description="People Also Ask count")
    competition_score: int = Field(ge=0, le=100, description="Competition score (0-100)")
    difficulty: str = Field(
        pattern="^(Low|Medium|High)$", description="Keyword difficulty level"
    )
    opportunity_score: int = Field(ge=0, le=100, description="Opportunity score (0-100)")
    top_domains: list[str] = Field(default=[], description="Top ranking domains")
    fetched_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        json_schema_extra = {
            "example": {
                "query": "python async programming",
                "total_results": 10,
                "top_position": 1,
                "top_url": "https://realpython.com/async-io-python/",
                "top_domain": "realpython.com",
                "has_knowledge_graph": False,
                "has_featured_snippet": False,
                "has_sitelinks": True,
                "related_searches_count": 8,
                "paa_count": 4,
                "competition_score": 65,
                "difficulty": "Medium",
                "opportunity_score": 35,
                "top_domains": ["realpython.com", "docs.python.org"],
                "fetched_at": "2026-01-08T00:00:00Z",
            }
        }

    @classmethod
    def from_api_response(cls, response: SerperAPIResponse) -> "SerperMetrics":
        """Create metrics from API response."""
        top_result = response.organic[0] if response.organic else None

        # Calculate competition score
        score = 0
        if len(response.organic) >= 10:
            score += 25
        if response.knowledgeGraph:
            score += 20
        score += min(len(response.relatedSearches or []) * 3, 15)
        score += min(len(response.peopleAlsoAsk or []) * 3, 15)
        if response.has_sitelinks:
            score += 15
        if response.has_featured_snippet:
            score += 10

        competition_score = min(score, 100)

        if competition_score >= 70:
            difficulty = "High"
        elif competition_score >= 40:
            difficulty = "Medium"
        else:
            difficulty = "Low"

        return cls(
            query=response.searchParameters.q,
            total_results=len(response.organic),
            top_position=top_result.position if top_result else None,
            top_url=top_result.link if top_result else None,
            top_domain=top_result.domain if top_result else None,
            has_knowledge_graph=response.knowledgeGraph is not None,
            has_featured_snippet=response.has_featured_snippet,
            has_sitelinks=response.has_sitelinks,
            related_searches_count=len(response.relatedSearches or []),
            paa_count=len(response.peopleAlsoAsk or []),
            competition_score=competition_score,
            difficulty=difficulty,
            opportunity_score=100 - competition_score,
            top_domains=response.top_domains,
        )
