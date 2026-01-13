"""Error handling utilities for structured error display."""

import traceback
import webbrowser
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any
from urllib.parse import quote


class ErrorSeverity(Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class StructuredError:
    error_type: str
    message: str
    severity: ErrorSeverity = ErrorSeverity.ERROR
    details: str = ""
    stack_trace: str = ""
    timestamp: datetime = field(default_factory=datetime.now)
    context: dict[str, Any] = field(default_factory=dict)
    suggestion: str = ""
    is_unexpected: bool = False

    def to_copyable_text(self) -> str:
        lines = [
            f"Error Type: {self.error_type}",
            f"Severity: {self.severity.value.upper()}",
            f"Timestamp: {self.timestamp.isoformat()}",
            f"Message: {self.message}",
        ]

        if self.details:
            lines.append(f"\nDetails:\n{self.details}")

        if self.context:
            lines.append("\nContext:")
            for key, value in self.context.items():
                lines.append(f"  {key}: {value}")

        if self.suggestion:
            lines.append(f"\nSuggestion: {self.suggestion}")

        if self.stack_trace:
            lines.append(f"\nStack Trace:\n{self.stack_trace}")

        return "\n".join(lines)


def format_exception(
    exc: BaseException,
    severity: ErrorSeverity | None = None,
    context: dict[str, Any] | None = None,
) -> StructuredError:
    error_type = type(exc).__name__
    message = str(exc) or "An error occurred"
    stack_trace = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))

    if severity is None:
        severity = _detect_severity(exc)

    return StructuredError(
        error_type=error_type,
        message=message,
        severity=severity,
        details=_extract_details(exc),
        stack_trace=stack_trace,
        context=context or {},
        suggestion=_generate_suggestion(exc, error_type),
        is_unexpected=_is_unexpected_error(exc),
    )


def format_error_message(
    error_type: str,
    message: str,
    severity: ErrorSeverity = ErrorSeverity.ERROR,
    details: str = "",
    suggestion: str = "",
    context: dict[str, Any] | None = None,
) -> StructuredError:
    return StructuredError(
        error_type=error_type,
        message=message,
        severity=severity,
        details=details,
        suggestion=suggestion,
        context=context or {},
        is_unexpected=False,
    )


def _detect_severity(exc: BaseException) -> ErrorSeverity:
    if isinstance(exc, (SystemExit, KeyboardInterrupt, MemoryError, SystemError)):
        return ErrorSeverity.CRITICAL

    if isinstance(exc, (DeprecationWarning, UserWarning, FutureWarning)):
        return ErrorSeverity.WARNING

    if isinstance(exc, (ConnectionError, TimeoutError)):
        return ErrorSeverity.WARNING

    return ErrorSeverity.ERROR


SUGGESTION_MAP = {
    "ConnectionError": "Check your network connection and try again.",
    "TimeoutError": "The operation timed out. Try again or increase timeout.",
    "FileNotFoundError": "Verify the file path exists and is accessible.",
    "PermissionError": "Check file permissions or run with elevated privileges.",
    "JSONDecodeError": "The response was not valid JSON. Check the API response.",
    "KeyError": "A required key was missing from the data.",
    "ValueError": "An invalid value was provided. Check input parameters.",
    "TypeError": "A type mismatch occurred. Check parameter types.",
    "ImportError": "A required module could not be imported. Check dependencies.",
    "ModuleNotFoundError": "Install the missing module with pip or uv.",
    "AttributeError": "An object is missing an expected attribute.",
    "RuntimeError": "A runtime error occurred. Check the operation context.",
    "AuthenticationError": "Check your API key or credentials.",
    "RateLimitError": "You've hit a rate limit. Wait before retrying.",
}


def _generate_suggestion(exc: BaseException, error_type: str) -> str:
    error_msg = str(exc).lower()

    if "api_key" in error_msg or "api key" in error_msg:
        return "Check that your API key is configured correctly in settings."

    if "rate limit" in error_msg or "ratelimit" in error_msg:
        return "You've hit a rate limit. Wait a moment and try again."

    if "timeout" in error_msg:
        return "The request timed out. Check your connection or try again."

    if "connection" in error_msg or "network" in error_msg:
        return "Check your internet connection and try again."

    return SUGGESTION_MAP.get(error_type, "")


EXPECTED_ERROR_TYPES = (
    ConnectionError,
    TimeoutError,
    FileNotFoundError,
    PermissionError,
    ValueError,
    KeyError,
)

EXPECTED_PATTERNS = [
    "api_key",
    "rate limit",
    "timeout",
    "connection",
    "not found",
    "permission denied",
    "authentication",
]


def _is_unexpected_error(exc: BaseException) -> bool:
    if isinstance(exc, EXPECTED_ERROR_TYPES):
        return False

    error_msg = str(exc).lower()
    for pattern in EXPECTED_PATTERNS:
        if pattern in error_msg:
            return False

    return isinstance(
        exc,
        (RuntimeError, AssertionError, NotImplementedError, AttributeError, IndexError),
    )


def _extract_details(exc: BaseException) -> str:
    details_parts = []

    if exc.__cause__:
        details_parts.append(
            f"Caused by: {type(exc.__cause__).__name__}: {exc.__cause__}"
        )

    if exc.__context__ and exc.__context__ != exc.__cause__:
        details_parts.append(
            f"During handling: {type(exc.__context__).__name__}: {exc.__context__}"
        )

    if hasattr(exc, "response") and exc.response is not None:
        try:
            response = exc.response
            if hasattr(response, "status_code"):
                details_parts.append(f"HTTP Status: {response.status_code}")
            if hasattr(response, "text"):
                text = (
                    response.text[:500] if len(response.text) > 500 else response.text
                )
                details_parts.append(f"Response: {text}")
        except Exception:
            pass

    if hasattr(exc, "errno"):
        details_parts.append(f"Error number: {exc.errno}")

    if hasattr(exc, "filename"):
        details_parts.append(f"Filename: {exc.filename}")

    return "\n".join(details_parts)


def create_issue_url(error: StructuredError) -> str:
    title = f"[Bug] {error.error_type}: {error.message[:50]}"
    if len(error.message) > 50:
        title += "..."

    stack_trace = error.stack_trace
    if len(stack_trace) > 1000:
        stack_trace = stack_trace[:1000] + "\n... (truncated)"

    body = f"""## Error Report

**Error Type:** {error.error_type}
**Severity:** {error.severity.value}
**Timestamp:** {error.timestamp.isoformat()}

### Message
{error.message}

### Details
{error.details or "N/A"}

### Stack Trace
```
{stack_trace}
```

### Context
{_format_context_for_issue(error.context)}

### Environment
- OS: (please fill in)
- Python version: (please fill in)
- Null Terminal version: (please fill in)

### Steps to Reproduce
1. (please fill in)
"""

    base_url = "https://github.com/starhound/null-terminal/issues/new"
    return f"{base_url}?title={quote(title)}&body={quote(body)}"


def _format_context_for_issue(context: dict[str, Any]) -> str:
    if not context:
        return "N/A"

    lines = []
    for key, value in context.items():
        if any(s in key.lower() for s in ["key", "token", "secret", "password"]):
            value = "[REDACTED]"
        lines.append(f"- {key}: {value}")

    return "\n".join(lines)


def open_issue_report(error: StructuredError) -> bool:
    try:
        webbrowser.open(create_issue_url(error))
        return True
    except Exception:
        return False
