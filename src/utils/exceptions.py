"""
Custom exceptions for seo-flow.

All exceptions inherit from SEOFlowError for consistent handling.
"""


class SEOFlowError(Exception):
    """Base exception for all seo-flow errors."""

    def __init__(self, message: str, details: dict | None = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}

    def to_dict(self) -> dict:
        """Convert exception to dictionary for JSON responses."""
        return {
            "error": self.__class__.__name__,
            "message": self.message,
            "details": self.details,
        }


class CollectorError(SEOFlowError):
    """Raised when data collection fails."""

    pass


class RateLimitError(CollectorError):
    """Raised when API rate limit is exceeded."""

    def __init__(self, message: str, retry_after: int | None = None):
        super().__init__(message, {"retry_after": retry_after})
        self.retry_after = retry_after


class AuthenticationError(CollectorError):
    """Raised when API authentication fails."""

    pass


class AnalysisError(SEOFlowError):
    """Raised when data analysis fails."""

    pass


class InsufficientDataError(AnalysisError):
    """Raised when there is not enough data for analysis."""

    pass


class AIError(SEOFlowError):
    """Raised when AI generation fails."""

    pass


class TokenLimitError(AIError):
    """Raised when AI input exceeds token limit."""

    def __init__(self, message: str, token_count: int | None = None):
        super().__init__(message, {"token_count": token_count})
        self.token_count = token_count


class ReportError(SEOFlowError):
    """Raised when report generation fails."""

    pass


class ConfigurationError(SEOFlowError):
    """Raised when configuration is invalid."""

    pass
