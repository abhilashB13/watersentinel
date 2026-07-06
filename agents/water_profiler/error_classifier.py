"""agents/water_profiler/error_classifier.py
Classifies API errors: retry-with-backoff (429, 5xx) vs fail-fast (4xx except 429) vs unknown (1 retry).
"""
import re

RETRY_BACKOFF_CODES = {"429", "500", "502", "503", "504"}
FAIL_FAST_CODES = {"400", "401", "403", "404"}


def classify_error(error_str: str) -> str:
    """Returns 'retry_backoff' | 'fail_fast' | 'unknown'."""
    codes_found = set(re.findall(r'\b(4\d{2}|5\d{2})\b', error_str))
    if codes_found & RETRY_BACKOFF_CODES:
        return "retry_backoff"
    if "RESOURCE_EXHAUSTED" in error_str or "UNAVAILABLE" in error_str:
        return "retry_backoff"
    if codes_found & FAIL_FAST_CODES:
        return "fail_fast"
    if "PERMISSION_DENIED" in error_str or "INVALID_ARGUMENT" in error_str or "UNAUTHENTICATED" in error_str:
        return "fail_fast"
    return "unknown"
