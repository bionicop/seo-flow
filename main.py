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
    from src.utils import validate_url, validate_keywords, SEOFlowError
    
    # Initialize logging
    logger = setup_logging()
    
    # Load settings
    settings = get_settings()
    
    print("=" * 50)
    print("SEO Flow v0.3.0")
    print("AI-Powered SEO Automation Workflow")
    print("=" * 50)
    
    # Test utils
    print("\n[Config]")
    print(f"  Data Source: {settings.default_data_source}")
    print(f"  Serper API: {'configured' if settings.has_serper_key() else 'not set'}")
    print(f"  Gemini API: {'configured' if settings.has_gemini_key() else 'not set'}")
    
    print("\n[Utils Test]")
    try:
        url = validate_url("example.com")
        print(f"  URL validated: {url}")
        
        keywords = validate_keywords("python, SEO, automation")
        print(f"  Keywords: {keywords}")
    except SEOFlowError as e:
        print(f"  Validation error: {e}")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
