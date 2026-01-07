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
    from src.collectors import get_collector
    
    # Initialize
    logger = setup_logging()
    settings = get_settings()
    
    print("=" * 50)
    print("SEO Flow v0.4.2")
    print("AI-Powered SEO Automation Workflow")
    print("=" * 50)
    
    print("\n[Config]")
    print(f"  Data Source: {settings.default_data_source}")
    print(f"  Serper API: {'configured' if settings.has_serper_key() else 'not set'}")
    print(f"  GSC Credentials: {'configured' if settings.has_gsc_credentials() else 'not set'}")
    
    # Test collector
    print("\n[Collector Test]")
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
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
