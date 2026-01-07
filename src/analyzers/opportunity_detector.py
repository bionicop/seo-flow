"""
Opportunity detector for GSC and SERP data.

Identifies SEO opportunities from GSC performance data
and SERP analysis results.
"""

from datetime import datetime
from typing import Any

from config.logging import get_logger
from src.models import (
    GSCMetric,
    Opportunity,
    OpportunityType,
    Priority,
)

logger = get_logger(__name__)


class OpportunityDetector:
    """
    Detects SEO opportunities from performance data.
    
    Analyzes GSC metrics to identify:
    - Low CTR opportunities
    - Position 4-10 quick wins
    - High impression/low click keywords
    - Trending keywords
    """
    
    # Thresholds for opportunity detection
    LOW_CTR_THRESHOLD = 0.02  # 2%
    POSITION_RANGE = (4, 10)  # Quick win range
    HIGH_IMPRESSIONS_THRESHOLD = 1000
    
    def detect_from_gsc(
        self,
        metrics: list[GSCMetric],
    ) -> list[Opportunity]:
        """
        Detect opportunities from GSC metrics.
        
        Args:
            metrics: List of GSC performance metrics.
        
        Returns:
            List of identified opportunities.
        """
        logger.info("Detecting opportunities from %d GSC metrics", len(metrics))
        
        opportunities = []
        
        for metric in metrics:
            # Low CTR opportunity
            if self._is_low_ctr(metric):
                opportunities.append(
                    Opportunity(
                        query=metric.query,
                        opportunity_type=OpportunityType.LOW_CTR,
                        priority=Priority.HIGH,
                        current_position=int(metric.position),
                        current_ctr=metric.ctr,
                        current_clicks=metric.clicks,
                        current_impressions=metric.impressions,
                        estimated_impact=self._estimate_ctr_impact(metric),
                        recommendation=self._get_ctr_recommendation(metric),
                        confidence=0.85,
                    )
                )
            
            # Position 4-10 opportunity
            if self._is_position_4_10(metric):
                opportunities.append(
                    Opportunity(
                        query=metric.query,
                        opportunity_type=OpportunityType.POSITION_4_10,
                        priority=Priority.HIGH,
                        current_position=int(metric.position),
                        current_ctr=metric.ctr,
                        current_clicks=metric.clicks,
                        current_impressions=metric.impressions,
                        estimated_impact=self._estimate_position_impact(metric),
                        recommendation="Optimize content and meta tags to reach top 3",
                        confidence=0.80,
                    )
                )
            
            # High impressions but low clicks
            if self._is_high_impressions_low_clicks(metric):
                opportunities.append(
                    Opportunity(
                        query=metric.query,
                        opportunity_type=OpportunityType.HIGH_IMPRESSIONS,
                        priority=Priority.MEDIUM,
                        current_position=int(metric.position),
                        current_ctr=metric.ctr,
                        current_clicks=metric.clicks,
                        current_impressions=metric.impressions,
                        estimated_impact=f"+{int(metric.impressions * 0.02)} clicks potential",
                        recommendation="Improve title and meta description for better CTR",
                        confidence=0.75,
                    )
                )
        
        # Sort by priority and impressions
        opportunities.sort(
            key=lambda x: (
                x.priority != Priority.HIGH,
                -(x.current_impressions or 0),
            )
        )
        
        logger.info("Detected %d opportunities", len(opportunities))
        return opportunities
    
    def _is_low_ctr(self, metric: GSCMetric) -> bool:
        """Check if metric indicates low CTR opportunity."""
        return (
            metric.ctr < self.LOW_CTR_THRESHOLD
            and metric.position <= 10
            and metric.impressions >= 100
        )
    
    def _is_position_4_10(self, metric: GSCMetric) -> bool:
        """Check if keyword is in position 4-10 range."""
        return self.POSITION_RANGE[0] <= metric.position <= self.POSITION_RANGE[1]
    
    def _is_high_impressions_low_clicks(self, metric: GSCMetric) -> bool:
        """Check for high impressions but low click-through."""
        return (
            metric.impressions >= self.HIGH_IMPRESSIONS_THRESHOLD
            and metric.clicks < metric.impressions * 0.01  # Less than 1% CTR
        )
    
    def _estimate_ctr_impact(self, metric: GSCMetric) -> str:
        """Estimate impact of improving CTR."""
        # Typical CTR for position
        expected_ctr = self._get_expected_ctr(int(metric.position))
        potential_clicks = int(metric.impressions * expected_ctr)
        additional_clicks = potential_clicks - metric.clicks
        
        if additional_clicks > 0:
            return f"+{additional_clicks} clicks/month"
        return "Maintain current performance"
    
    def _estimate_position_impact(self, metric: GSCMetric) -> str:
        """Estimate impact of improving position."""
        # Moving to top 3 typically increases CTR
        current_ctr = metric.ctr
        target_ctr = 0.10  # ~10% for top 3
        
        additional_clicks = int(metric.impressions * (target_ctr - current_ctr))
        
        if additional_clicks > 0:
            return f"+{additional_clicks} clicks if top 3"
        return "Already performing well"
    
    def _get_expected_ctr(self, position: int) -> float:
        """Get expected CTR for a given position."""
        # Approximate CTR curve
        ctr_by_position = {
            1: 0.28,
            2: 0.15,
            3: 0.11,
            4: 0.08,
            5: 0.06,
            6: 0.05,
            7: 0.04,
            8: 0.03,
            9: 0.03,
            10: 0.02,
        }
        return ctr_by_position.get(position, 0.01)
    
    def _get_ctr_recommendation(self, metric: GSCMetric) -> str:
        """Get recommendation for improving CTR."""
        position = int(metric.position)
        
        if position <= 3:
            return "Add rich snippets and improve meta description"
        elif position <= 5:
            return "Optimize title tag with power words and numbers"
        elif position <= 10:
            return "Improve content depth and add FAQ section"
        else:
            return "Focus on building topical authority"
    
    def prioritize(
        self,
        opportunities: list[Opportunity],
        max_results: int = 10,
    ) -> list[Opportunity]:
        """
        Prioritize opportunities by potential impact.
        
        Args:
            opportunities: List of opportunities to prioritize.
            max_results: Maximum number to return.
        
        Returns:
            Top prioritized opportunities.
        """
        # Score each opportunity
        scored = []
        for opp in opportunities:
            score = 0
            
            # Priority weight
            if opp.priority == Priority.HIGH:
                score += 100
            elif opp.priority == Priority.MEDIUM:
                score += 50
            else:
                score += 10
            
            # Impressions weight
            if opp.current_impressions:
                score += min(opp.current_impressions / 100, 50)
            
            # Position weight (lower is better)
            if opp.current_position:
                score += max(0, 20 - opp.current_position)
            
            # Confidence weight
            score += opp.confidence * 20
            
            scored.append((score, opp))
        
        # Sort by score descending
        scored.sort(key=lambda x: x[0], reverse=True)
        
        return [opp for _, opp in scored[:max_results]]
