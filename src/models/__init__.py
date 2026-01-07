"""
Data models for SEO Flow.

Pydantic models for validation, serialization, and type safety.
"""

from src.models.serper import (
    SerperOrganic,
    SerperKnowledgeGraph,
    SerperPeopleAlsoAsk,
    SerperRelatedSearch,
    SerperSearchParameters,
    SerperAPIResponse,
    SerperMetrics,
    SerperSitelink,
)
from src.models.duckduckgo import DuckDuckGoResult, DuckDuckGoResponse
from src.models.gsc import GSCMetric, GSCResponse
from src.models.analysis import (
    Opportunity,
    OpportunityType,
    Priority,
    TrendSnapshot,
    TrendAnalysis,
    CompetitionMetrics,
    KeywordAnalysis,
)

__all__ = [
    # Serper models
    "SerperOrganic",
    "SerperKnowledgeGraph",
    "SerperPeopleAlsoAsk",
    "SerperRelatedSearch",
    "SerperSearchParameters",
    "SerperAPIResponse",
    "SerperMetrics",
    "SerperSitelink",
    # DuckDuckGo models
    "DuckDuckGoResult",
    "DuckDuckGoResponse",
    # GSC models
    "GSCMetric",
    "GSCResponse",
    # Analysis models
    "Opportunity",
    "OpportunityType",
    "Priority",
    "TrendSnapshot",
    "TrendAnalysis",
    "CompetitionMetrics",
    "KeywordAnalysis",
]
