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
    
    # Initialize logging
    logger = setup_logging()
    
    # Load settings
    settings = get_settings()
    
    print("=" * 50)
    print("SEO Flow v0.2.0")
    print("AI-Powered SEO Automation Workflow")
    print("=" * 50)
    print(f"\nData Source: {settings.default_data_source}")
    print(f"Output Format: {settings.output_format}")
    print(f"Serper API: {'Configured' if settings.has_serper_key() else 'Not configured'}")
    print(f"Gemini API: {'Configured' if settings.has_gemini_key() else 'Not configured'}")
    print("\nStatus: Configuration loaded")
    print("Next: Add data collectors")
    return 0


if __name__ == "__main__":
    sys.exit(main())
