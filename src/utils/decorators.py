"""
Utility decorators for seo-flow.

Provides retry logic, timing, and error handling decorators.
"""

import functools
import logging
import time
from typing import Callable, TypeVar

from src.utils.exceptions import RateLimitError, SEOFlowError

T = TypeVar("T")
logger = logging.getLogger("seo-flow.decorators")


def retry(
    max_attempts: int = 3,
    delay_seconds: int = 5,
    backoff_factor: float = 2.0,
    exceptions: tuple = (Exception,),
) -> Callable:
    """
    Retry decorator with exponential backoff.

    Args:
        max_attempts: Maximum number of retry attempts.
        delay_seconds: Initial delay between retries.
        backoff_factor: Multiplier for delay after each retry.
        exceptions: Tuple of exceptions to catch and retry.

    Returns:
        Decorated function.

    Example:
        >>> @retry(max_attempts=3, delay_seconds=2)
        ... def fetch_data():
        ...     return requests.get(url)
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> T:
            last_exception = None
            delay = delay_seconds

            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt < max_attempts:
                        # Check for rate limit with retry_after
                        if isinstance(e, RateLimitError) and e.retry_after:
                            delay = e.retry_after

                        logger.warning(
                            "Attempt %d/%d failed: %s. Retrying in %ds...",
                            attempt,
                            max_attempts,
                            str(e),
                            delay,
                        )
                        time.sleep(delay)
                        delay = int(delay * backoff_factor)
                    else:
                        logger.error(
                            "All %d attempts failed for %s",
                            max_attempts,
                            func.__name__,
                        )

            raise last_exception  # type: ignore

        return wrapper

    return decorator


def log_execution_time(func: Callable[..., T]) -> Callable[..., T]:
    """
    Log function execution time.

    Args:
        func: Function to wrap.

    Returns:
        Decorated function.

    Example:
        >>> @log_execution_time
        ... def process_data(df):
        ...     return df.groupby("keyword").sum()
    """

    @functools.wraps(func)
    def wrapper(*args, **kwargs) -> T:
        start = time.perf_counter()
        try:
            result = func(*args, **kwargs)
            elapsed = (time.perf_counter() - start) * 1000
            logger.debug("%s completed in %.2fms", func.__name__, elapsed)
            return result
        except Exception as e:
            elapsed = (time.perf_counter() - start) * 1000
            logger.error("%s failed after %.2fms: %s", func.__name__, elapsed, str(e))
            raise

    return wrapper


def handle_errors(
    default_return: T | None = None,
    log_level: int = logging.ERROR,
) -> Callable:
    """
    Catch exceptions and return default value.

    Args:
        default_return: Value to return on error.
        log_level: Logging level for errors.

    Returns:
        Decorated function.

    Example:
        >>> @handle_errors(default_return=[])
        ... def get_keywords():
        ...     return api.fetch_keywords()
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T | None]:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> T | None:
            try:
                return func(*args, **kwargs)
            except SEOFlowError as e:
                logger.log(log_level, "%s: %s", func.__name__, e.message)
                return default_return
            except Exception as e:
                logger.log(log_level, "%s: Unexpected error - %s", func.__name__, e)
                return default_return

        return wrapper

    return decorator
