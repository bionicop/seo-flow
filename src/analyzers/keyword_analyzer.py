"""
Keyword analyzer for SERP data analysis.

Processes SERP results to extract competition metrics,
related keywords, and ranking opportunities.
"""

from datetime import datetime
from typing import Any
from urllib.parse import urlparse

from config.logging import get_logger
from src.collectors import SerperCollector, DuckDuckGoCollector
from src.models import (
    CompetitionMetrics,
    KeywordAnalysis,
    OpportunityType,
    Priority,
)

logger = get_logger(__name__)


class KeywordAnalyzer:
    """
    Analyzes keywords using multiple data sources.
    
    Combines Serper and DuckDuckGo data to provide
    comprehensive keyword analysis with competition
    metrics and opportunity identification.
    """
    
    def __init__(
        self,
        serper_collector: SerperCollector | None = None,
        duckduckgo_collector: DuckDuckGoCollector | None = None,
    ):
        """
        Initialize analyzer with collectors.
        
        Args:
            serper_collector: Serper collector instance.
            duckduckgo_collector: DuckDuckGo collector instance.
        """
        self.serper = serper_collector or SerperCollector()
        self.ddg = duckduckgo_collector or DuckDuckGoCollector()
    
    @staticmethod
    def _validate_keyword(keyword: str) -> str:
        """
        Validate and sanitize keyword input.
        
        Args:
            keyword: Raw keyword input.
        
        Returns:
            Sanitized keyword string.
        
        Raises:
            ValueError: If keyword is invalid.
        """
        if not keyword:
            raise ValueError("Keyword cannot be empty")
        
        # Strip whitespace
        keyword = keyword.strip()
        
        if len(keyword) < 2:
            raise ValueError("Keyword must be at least 2 characters")
        
        if len(keyword) > 200:
            raise ValueError("Keyword cannot exceed 200 characters")
        
        return keyword
    
    def analyze(
        self,
        keyword: str,
        target_url: str | None = None,
        country: str = "in",
        language: str = "en",
    ) -> KeywordAnalysis:
        """
        Perform complete keyword analysis.
        
        Args:
            keyword: Target keyword to analyze (2-200 chars).
            target_url: URL to track ranking position.
            country: Country code for localization.
            language: Language code.
        
        Returns:
            KeywordAnalysis with all metrics and opportunities.
        
        Raises:
            ValueError: If keyword is invalid.
        """
        # Input validation
        keyword = self._validate_keyword(keyword)
        
        logger.info("Starting keyword analysis: %s", keyword)
        
        # Collect SERP data
        serp = self.serper.collect_full(
            keyword,
            num_results=100,
            country=country,
            language=language,
        )
        
        # Calculate competition metrics
        competition = self._calculate_competition(keyword, serp)
        
        # Find target position
        target_position = None
        is_ranking = False
        
        if target_url:
            target_domain = urlparse(target_url).netloc.lower().replace("www.", "")
            for result in serp.organic:
                domain = urlparse(str(result.get("link", ""))).netloc.lower().replace("www.", "")
                if target_domain in domain:
                    target_position = result.get("position")
                    is_ranking = True
                    break
        
        # Identify opportunities
        opportunities = self._identify_opportunities(
            keyword=keyword,
            competition=competition,
            target_position=target_position,
            serp=serp,
        )
        
        # Extract related keywords
        related_keywords = [
            s.get("query", "") for s in (serp.related_searches or [])
        ]
        
        # Extract PAA questions
        paa_questions = [
            p.get("question", "") for p in (serp.people_also_ask or [])
        ]
        
        # Build SERP summary
        serp_summary = {
            "organic_count": len(serp.organic),
            "has_knowledge_graph": serp.knowledge_graph is not None,
            "paa_count": len(serp.people_also_ask or []),
            "related_count": len(serp.related_searches or []),
            "top_domains": serp.top_domains[:5],
            "has_featured_snippet": serp.has_featured_snippet,
            "has_sitelinks": serp.has_sitelinks,
        }
        
        analysis = KeywordAnalysis(
            keyword=keyword,
            target_url=target_url,
            target_position=target_position,
            is_ranking=is_ranking,
            competition=competition,
            opportunities=opportunities,
            related_keywords=related_keywords,
            paa_questions=paa_questions,
            serp_summary=serp_summary,
        )
        
        logger.info(
            "Analysis complete: %s (difficulty=%s, opportunities=%d)",
            keyword,
            competition.difficulty,
            len(opportunities),
        )
        
        return analysis
    
    def _calculate_competition(
        self,
        query: str,
        serp: Any,
    ) -> CompetitionMetrics:
        """Calculate competition metrics from SERP data."""
        score = 0
        
        # Factor 1: Number of results
        if len(serp.organic) >= 10:
            score += 25
        elif len(serp.organic) >= 5:
            score += 15
        else:
            score += 5
        
        # Factor 2: Knowledge graph
        if serp.knowledge_graph:
            score += 20
        
        # Factor 3: Related searches
        related_count = len(serp.related_searches or [])
        score += min(related_count * 3, 15)
        
        # Factor 4: PAA questions
        paa_count = len(serp.people_also_ask or [])
        score += min(paa_count * 3, 15)
        
        # Factor 5: Sitelinks
        if serp.has_sitelinks:
            score += 15
        
        # Factor 6: Featured snippet
        if serp.has_featured_snippet:
            score += 10
        
        competition_score = min(score, 100)
        
        if competition_score >= 70:
            difficulty = "High"
        elif competition_score >= 40:
            difficulty = "Medium"
        else:
            difficulty = "Low"
        
        return CompetitionMetrics(
            query=query,
            competition_score=competition_score,
            difficulty=difficulty,
            opportunity_score=100 - competition_score,
            total_serp_results=len(serp.organic),
            has_knowledge_graph=serp.knowledge_graph is not None,
            has_featured_snippet=serp.has_featured_snippet,
            has_sitelinks=serp.has_sitelinks,
            top_domains=serp.top_domains,
            related_searches_count=related_count,
            paa_count=paa_count,
        )
    
    def _identify_opportunities(
        self,
        keyword: str,
        competition: CompetitionMetrics,
        target_position: int | None,
        serp: Any,
    ) -> list[dict[str, Any]]:
        """Identify SEO opportunities based on analysis."""
        opportunities = []
        
        # Not ranking opportunity
        if target_position is None:
            opportunities.append({
                "type": OpportunityType.NOT_RANKING.value,
                "message": "Not ranking - new content opportunity",
                "priority": Priority.MEDIUM.value,
            })
        
        # Position improvement
        elif target_position > 10:
            priority = Priority.HIGH.value if target_position <= 20 else Priority.MEDIUM.value
            opportunities.append({
                "type": OpportunityType.POSITION_IMPROVEMENT.value,
                "message": f"Ranking at position {target_position} - optimization needed",
                "priority": priority,
            })
        
        # Maintain position
        elif target_position <= 3:
            opportunities.append({
                "type": OpportunityType.MAINTAIN.value,
                "message": "Strong position - monitor and maintain",
                "priority": Priority.LOW.value,
            })
        
        # Position 4-10 opportunity
        elif 4 <= target_position <= 10:
            opportunities.append({
                "type": OpportunityType.POSITION_4_10.value,
                "message": f"Position {target_position} - push to top 3",
                "priority": Priority.HIGH.value,
            })
        
        # Quick win for low competition
        if competition.is_low_competition:
            opportunities.append({
                "type": OpportunityType.QUICK_WIN.value,
                "message": "Low competition - quick win potential",
                "priority": Priority.HIGH.value,
            })
        
        # Keyword expansion
        if serp.related_searches and len(serp.related_searches) > 3:
            opportunities.append({
                "type": OpportunityType.KEYWORD_EXPANSION.value,
                "message": f"{len(serp.related_searches)} related keywords found",
                "priority": Priority.MEDIUM.value,
            })
        
        return opportunities
    
    def batch_analyze(
        self,
        keywords: list[str],
        target_url: str | None = None,
        **kwargs,
    ) -> dict[str, KeywordAnalysis]:
        """
        Analyze multiple keywords.
        
        Args:
            keywords: List of keywords to analyze.
            target_url: URL to track ranking.
            **kwargs: Additional arguments passed to analyze().
        
        Returns:
            Dictionary mapping keyword to analysis result.
        """
        logger.info("Batch analyzing %d keywords", len(keywords))
        
        results = {}
        for keyword in keywords:
            try:
                results[keyword] = self.analyze(keyword, target_url, **kwargs)
            except Exception as e:
                logger.error("Failed to analyze '%s': %s", keyword, e)
                # Skip failed keywords
        
        logger.info(
            "Batch complete: %d/%d succeeded",
            len(results),
            len(keywords),
        )
        
        return results
