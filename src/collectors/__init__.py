"""
Data collectors for seo-flow.

Exports:
    - BaseCollector: Abstract base class
    - CollectorResponse: Standardized response model
    - SERPResult: Individual search result
    - SerperCollector: Serper.dev API
"""

from src.collectors.base import BaseCollector, CollectorResponse, SERPResult
from src.collectors.serper import SerperCollector

__all__ = [
    "BaseCollector",
    "CollectorResponse",
    "SERPResult",
    "SerperCollector",
]


def get_collector(source: str = "serper") -> BaseCollector:
    """
    Factory function to get appropriate collector.

    Args:
        source: Collector type ('serper').

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
    }

    if source not in collectors:
        raise ValueError(f"Unknown collector: {source}. Available: {list(collectors.keys())}")

    return collectors[source]()
