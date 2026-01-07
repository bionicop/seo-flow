"""
Input validation utilities for seo-flow.

Provides validation functions for user inputs and API responses.
"""

import re
from urllib.parse import urlparse

from src.utils.exceptions import ConfigurationError


def validate_url(url: str) -> str:
    """
    Validate and normalize a URL.

    Args:
        url: URL string to validate.

    Returns:
        Normalized URL.

    Raises:
        ConfigurationError: If URL is invalid.

    Example:
        >>> validate_url("example.com")
        'https://example.com'
    """
    if not url:
        raise ConfigurationError("URL cannot be empty")

    # Add scheme if missing
    if not url.startswith(("http://", "https://")):
        url = f"https://{url}"

    try:
        result = urlparse(url)
        if not all([result.scheme, result.netloc]):
            raise ConfigurationError(f"Invalid URL: {url}")
        return url
    except Exception as e:
        raise ConfigurationError(f"Failed to parse URL: {url}") from e


def validate_keywords(keywords: list[str] | str) -> list[str]:
    """
    Validate and normalize keywords.

    Args:
        keywords: Single keyword string or list of keywords.

    Returns:
        List of cleaned keywords.

    Raises:
        ConfigurationError: If no valid keywords provided.

    Example:
        >>> validate_keywords("python, AI, automation")
        ['python', 'ai', 'automation']
    """
    if isinstance(keywords, str):
        # Split by comma, semicolon, or newline
        keywords = re.split(r"[,;\n]+", keywords)

    # Clean and deduplicate
    cleaned = []
    seen = set()
    for kw in keywords:
        kw = kw.strip().lower()
        if kw and kw not in seen:
            cleaned.append(kw)
            seen.add(kw)

    if not cleaned:
        raise ConfigurationError("No valid keywords provided")

    return cleaned


def validate_country_code(code: str) -> str:
    """
    Validate country code (ISO 3166-1 alpha-2).

    Args:
        code: Two-letter country code.

    Returns:
        Lowercase country code.

    Raises:
        ConfigurationError: If code is invalid.
    """
    code = code.strip().lower()
    if not re.match(r"^[a-z]{2}$", code):
        raise ConfigurationError(f"Invalid country code: {code}")
    return code


def validate_language_code(code: str) -> str:
    """
    Validate language code (ISO 639-1).

    Args:
        code: Two-letter language code.

    Returns:
        Lowercase language code.

    Raises:
        ConfigurationError: If code is invalid.
    """
    code = code.strip().lower()
    if not re.match(r"^[a-z]{2}$", code):
        raise ConfigurationError(f"Invalid language code: {code}")
    return code


def sanitize_for_report(text: str) -> str:
    """
    Sanitize text for safe inclusion in reports.

    Args:
        text: Raw text to sanitize.

    Returns:
        Sanitized text safe for Markdown/HTML.
    """
    if not text:
        return ""

    # Remove null bytes
    text = text.replace("\x00", "")

    # Escape HTML entities for HTML output
    html_entities = {
        "&": "&amp;",
        "<": "&lt;",
        ">": "&gt;",
        '"': "&quot;",
        "'": "&#x27;",
    }
    for char, entity in html_entities.items():
        text = text.replace(char, entity)

    return text.strip()


def validate_api_response(response: dict, required_keys: list[str]) -> bool:
    """
    Validate API response contains required keys.

    Args:
        response: API response dictionary.
        required_keys: List of required keys.

    Returns:
        True if valid.

    Raises:
        ConfigurationError: If required keys missing.
    """
    if not isinstance(response, dict):
        raise ConfigurationError("API response must be a dictionary")

    missing = [key for key in required_keys if key not in response]
    if missing:
        raise ConfigurationError(f"Missing required keys: {missing}")

    return True
