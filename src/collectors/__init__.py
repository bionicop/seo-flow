"""
Data collectors for seo-flow.

Exports:
    - BaseCollector: Abstract base class
    - CollectorResponse: Standardized response model
    - SERPResult: Individual search result
    - SerperCollector: Serper.dev API
    - GSCCollector: Google Search Console
    - DuckDuckGoCollector: Free backup search
"""

from src.collectors.base import BaseCollector, CollectorResponse, SERPResult
from src.collectors.serper import SerperCollector
from src.collectors.gsc import GSCCollector, GSCResult
from src.collectors.duckduckgo import DuckDuckGoCollector

__all__ = [
    "BaseCollector",
    "CollectorResponse",
    "SERPResult",
    "SerperCollector",
    "GSCCollector",
    "GSCResult",
    "DuckDuckGoCollector",
]


def get_collector(source: str = "serper") -> BaseCollector:
    """
    Factory function to get appropriate collector.

    Args:
        source: Collector type ('serper', 'gsc', 'duckduckgo').

    Returns:
        Collector instance.

    Raises:
        ValueError: If unknown source specified.

    Example:
        >>> collector = get_collector("serper")
        >>> response = collector.collect("python tutorial")
    """
    collectors = {
        "serper": SerperCollector,
        "gsc": GSCCollector,
        "duckduckgo": DuckDuckGoCollector,
    }

    if source not in collectors:
        raise ValueError(f"Unknown collector: {source}. Available: {list(collectors.keys())}")

    return collectors[source]()
