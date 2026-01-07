"""
Pydantic models for SEO analysis results.

Includes opportunities, trends, competition metrics,
and complete keyword analysis structures.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field, computed_field


class Priority(str, Enum):
    """Opportunity priority levels."""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class OpportunityType(str, Enum):
    """Types of SEO opportunities."""

    NOT_RANKING = "not_ranking"
    POSITION_IMPROVEMENT = "position_improvement"
    LOW_CTR = "low_ctr"
    POSITION_4_10 = "position_4_10"
    QUICK_WIN = "quick_win"
    TRENDING_UP = "trending_up"
    HIGH_IMPRESSIONS = "high_impressions"
    NEW_KEYWORD = "new_keyword"
    KEYWORD_EXPANSION = "keyword_expansion"
    MAINTAIN = "maintain"


class Opportunity(BaseModel):
    """Single SEO opportunity with actionable recommendation."""

    query: str = Field(description="Target keyword")
    opportunity_type: OpportunityType = Field(description="Type of opportunity")
    priority: Priority = Field(description="Priority level")
    current_position: Optional[int] = Field(
        default=None, ge=0, le=100, description="Current SERP position"
    )
    current_ctr: Optional[float] = Field(
        default=None, ge=0.0, le=1.0, description="Current CTR (0-1)"
    )
    current_clicks: Optional[int] = Field(default=None, ge=0, description="Current clicks")
    current_impressions: Optional[int] = Field(
        default=None, ge=0, description="Current impressions"
    )
    estimated_impact: str = Field(description="Estimated impact of taking action")
    recommendation: str = Field(description="Actionable recommendation")
    confidence: float = Field(
        ge=0.0, le=1.0, default=0.8, description="Confidence score (0-1)"
    )
    competition_score: Optional[int] = Field(
        default=None, ge=0, le=100, description="Keyword competition score"
    )
    detected_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        json_schema_extra = {
            "example": {
                "query": "python async programming",
                "opportunity_type": "position_4_10",
                "priority": "high",
                "current_position": 5,
                "current_ctr": 0.042,
                "current_clicks": 8,
                "current_impressions": 190,
                "estimated_impact": "+15 clicks/month",
                "recommendation": "Improve title tag and add FAQ section",
                "confidence": 0.85,
                "competition_score": 65,
                "detected_at": "2026-01-08T00:00:00Z",
            }
        }

    @computed_field
    @property
    def ctr_percentage(self) -> Optional[float]:
        """CTR as percentage."""
        return round(self.current_ctr * 100, 2) if self.current_ctr else None


class TrendSnapshot(BaseModel):
    """Single point-in-time snapshot for trend analysis."""

    timestamp: datetime = Field(description="When snapshot was taken")
    time_range: str = Field(description="Time filter used: hour, day, week, month, year")
    query: str = Field(description="Search query")
    organic_count: int = Field(ge=0, description="Number of organic results")
    top_position: Optional[int] = Field(
        default=None, ge=0, le=100, description="Top result position"
    )
    top_url: Optional[str] = Field(default=None, description="Top result URL")
    top_domain: Optional[str] = Field(default=None, description="Top result domain")
    related_searches_count: int = Field(ge=0, default=0, description="Related searches count")
    paa_count: int = Field(ge=0, default=0, description="People Also Ask count")
    has_knowledge_graph: bool = Field(default=False, description="Knowledge graph present")
    has_featured_snippet: bool = Field(default=False, description="Featured snippet present")

    class Config:
        json_schema_extra = {
            "example": {
                "timestamp": "2026-01-08T00:00:00Z",
                "time_range": "week",
                "query": "python async",
                "organic_count": 10,
                "top_position": 1,
                "top_url": "https://realpython.com/async-io-python/",
                "top_domain": "realpython.com",
                "related_searches_count": 8,
                "paa_count": 4,
                "has_knowledge_graph": False,
                "has_featured_snippet": False,
            }
        }


class TrendAnalysis(BaseModel):
    """Trend analysis result for a keyword over time."""

    query: str = Field(description="Search query")
    period_days: int = Field(ge=1, description="Analysis period in days")
    snapshots: list[TrendSnapshot] = Field(default=[], description="Time-series snapshots")
    growth_percentage: float = Field(description="Growth rate over period")
    is_trending_up: bool = Field(description="Keyword is gaining traction")
    is_trending_down: bool = Field(description="Keyword is losing traction")
    is_stable: bool = Field(default=False, description="Keyword is stable")
    analyzed_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        json_schema_extra = {
            "example": {
                "query": "python async",
                "period_days": 7,
                "snapshots": [],
                "growth_percentage": 12.5,
                "is_trending_up": True,
                "is_trending_down": False,
                "is_stable": False,
                "analyzed_at": "2026-01-08T00:00:00Z",
            }
        }

    @computed_field
    @property
    def snapshot_count(self) -> int:
        """Number of snapshots in analysis."""
        return len(self.snapshots)


class CompetitionMetrics(BaseModel):
    """Competition analysis for a keyword."""

    query: str = Field(description="Search query")
    competition_score: int = Field(ge=0, le=100, description="Competition score (0-100)")
    difficulty: str = Field(
        pattern="^(Low|Medium|High)$", description="Keyword difficulty level"
    )
    opportunity_score: int = Field(ge=0, le=100, description="Opportunity score (0-100)")
    total_serp_results: int = Field(ge=0, description="Number of organic results")
    has_knowledge_graph: bool = Field(default=False, description="Knowledge graph present")
    has_featured_snippet: bool = Field(default=False, description="Featured snippet present")
    has_sitelinks: bool = Field(default=False, description="Results have sitelinks")
    top_domains: list[str] = Field(default=[], description="Top ranking domains")
    related_searches_count: int = Field(ge=0, default=0, description="Related searches count")
    paa_count: int = Field(ge=0, default=0, description="People Also Ask count")
    analyzed_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        json_schema_extra = {
            "example": {
                "query": "seo automation",
                "competition_score": 68,
                "difficulty": "Medium",
                "opportunity_score": 32,
                "total_serp_results": 10,
                "has_knowledge_graph": False,
                "has_featured_snippet": True,
                "has_sitelinks": True,
                "top_domains": ["moz.com", "semrush.com", "ahrefs.com"],
                "related_searches_count": 8,
                "paa_count": 4,
                "analyzed_at": "2026-01-08T00:00:00Z",
            }
        }

    @computed_field
    @property
    def is_low_competition(self) -> bool:
        """Check if keyword has low competition."""
        return self.difficulty == "Low"

    @computed_field
    @property
    def is_quick_win(self) -> bool:
        """Check if keyword is a quick win (low competition, high opportunity)."""
        return self.competition_score < 40 and self.opportunity_score > 60


class KeywordAnalysis(BaseModel):
    """Complete keyword analysis result."""

    keyword: str = Field(description="Target keyword")
    target_url: Optional[str] = Field(default=None, description="Target URL to track")
    target_position: Optional[int] = Field(
        default=None, ge=0, le=100, description="Target URL position"
    )
    is_ranking: bool = Field(default=False, description="Target URL is ranking")
    competition: CompetitionMetrics = Field(description="Competition analysis")
    opportunities: list[dict[str, Any]] = Field(
        default=[], description="Identified opportunities"
    )
    related_keywords: list[str] = Field(default=[], description="Related keyword suggestions")
    paa_questions: list[str] = Field(default=[], description="People Also Ask questions")
    serp_summary: dict[str, Any] = Field(default={}, description="SERP data summary")
    analyzed_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        json_schema_extra = {
            "example": {
                "keyword": "fastapi tutorial",
                "target_url": "https://fastapi.tiangolo.com",
                "target_position": 1,
                "is_ranking": True,
                "competition": {
                    "query": "fastapi tutorial",
                    "competition_score": 45,
                    "difficulty": "Medium",
                    "opportunity_score": 55,
                    "total_serp_results": 10,
                },
                "opportunities": [
                    {
                        "type": "maintain",
                        "message": "Strong position - monitor and maintain",
                        "priority": "low",
                    }
                ],
                "related_keywords": ["fastapi docs", "fastapi example", "fastapi vs flask"],
                "paa_questions": ["What is FastAPI?", "Is FastAPI faster than Flask?"],
                "serp_summary": {"organic_count": 10, "has_knowledge_graph": False},
                "analyzed_at": "2026-01-08T00:00:00Z",
            }
        }

    @computed_field
    @property
    def opportunity_count(self) -> int:
        """Number of identified opportunities."""
        return len(self.opportunities)

    @computed_field
    @property
    def has_opportunities(self) -> bool:
        """Check if there are actionable opportunities."""
        return len(self.opportunities) > 0

    @computed_field
    @property
    def related_keyword_count(self) -> int:
        """Number of related keywords found."""
        return len(self.related_keywords)
