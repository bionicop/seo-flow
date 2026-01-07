#!/usr/bin/env python3
"""
SEO Flow - AI-Powered SEO Automation

Entry point for the SEO analysis pipeline.
"""

import sys


def main():
    """Main entry point."""
    from config import get_settings
    from config.logging import setup_logging
    from src.utils import validate_keywords, SEOFlowError
    from src.collectors import get_collector, SerperCollector
    
    # Initialize
    logger = setup_logging()
    settings = get_settings()
    
    print("=" * 60)
    print("SEO Flow v0.5.0")
    print("AI-Powered SEO Automation Workflow")
    print("=" * 60)
    
    print("\n[Config]")
    print(f"  Data Source: {settings.default_data_source}")
    print(f"  Serper API: {'configured' if settings.has_serper_key() else 'not set'}")
    print(f"  GSC Credentials: {'configured' if settings.has_gsc_credentials() else 'not set'}")
    
    # Test basic collector
    print("\n[1. Basic SERP Collection]")
    try:
        collector = get_collector(settings.default_data_source)
        
        if not collector.health_check():
            print("  Collector not ready - API key missing")
            return 1
        
        # Fetch real data
        query = "python seo automation"
        print(f"  Query: {query}")
        response = collector.collect(query, num_results=5)
        
        if response.success:
            print(f"  Results: {len(response.data)} found")
            for result in response.data[:3]:
                print(f"    #{result.position}: {result.title[:50]}...")
        else:
            print(f"  Error: {response.error}")
            
    except SEOFlowError as e:
        print(f"  Error: {e}")
    
    # Test enhanced Serper features
    print("\n[2. Enhanced Serper Features]")
    try:
        serper = SerperCollector()
        
        if serper.health_check():
            # Full SERP collection
            print("  Full SERP collection:")
            full_response = serper.collect_full("fastapi tutorial", num_results=10)
            print(f"    Organic: {len(full_response.organic)} results")
            print(f"    Knowledge Graph: {'Yes' if full_response.knowledge_graph else 'No'}")
            print(f"    People Also Ask: {len(full_response.people_also_ask)} questions")
            print(f"    Related Searches: {len(full_response.related_searches)} keywords")
            print(f"    Top Domains: {', '.join(full_response.top_domains[:3])}")
            
            # Competition metrics
            print("\n  Competition Analysis:")
            metrics = serper.get_competition_metrics("python web scraping")
            print(f"    Competition Score: {metrics.competition_score}/100")
            print(f"    Difficulty: {metrics.difficulty}")
            print(f"    Opportunity Score: {metrics.opportunity_score}/100")
            
            # Related keywords
            print("\n  Related Keywords:")
            keywords = serper.get_related_keywords("seo tools", include_paa=True)
            for kw in keywords[:5]:
                print(f"    - {kw}")
            
            # Full keyword analysis
            print("\n  Full Keyword Analysis:")
            analysis = serper.analyze_keyword(
                "digital garden seo",
                target_url=None  # No target for now
            )
            print(f"    Keyword: {analysis['keyword']}")
            print(f"    Difficulty: {analysis['competition']['difficulty']}")
            print(f"    Opportunities: {len(analysis['opportunities'])}")
            for opp in analysis['opportunities']:
                print(f"      - [{opp['priority'].upper()}] {opp['message']}")
        else:
            print("  Serper API key not configured")
            
    except Exception as e:
        print(f"  Error: {e}")
    
    print("\n" + "=" * 60)
    print("All tests completed!")
    print("=" * 60)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
