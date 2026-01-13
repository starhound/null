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


class ErrorCategory(Enum):
    """Categorization of errors for better user understanding."""
    NETWORK = "network"
    AUTH = "authentication"
    CONFIG = "configuration"
    FILE = "file_system"
    PERMISSION = "permission"
    VALIDATION = "validation"
    RESOURCE = "resource"
    PROVIDER = "provider"
    MCP = "mcp"
    INTERNAL = "internal"
    UNKNOWN = "unknown"


# Comprehensive error message dictionary with patterns, friendly messages, and suggestions
ERROR_MESSAGES: dict[str, dict[str, Any]] = {
    # Network errors
    "connection_refused": {
        "patterns": ["connection refused", "connect call failed", "[errno 111]"],
        "category": ErrorCategory.NETWORK,
        "friendly": "Unable to connect to the server",
        "suggestion": "Check if the server is running and the address is correct. For Ollama, ensure it's started with 'ollama serve'.",
    },
    "connection_reset": {
        "patterns": ["connection reset", "connection aborted", "broken pipe"],
        "category": ErrorCategory.NETWORK,
        "friendly": "Connection was unexpectedly closed",
        "suggestion": "The server closed the connection. Try again or check server logs for issues.",
    },
    "timeout": {
        "patterns": ["timeout", "timed out", "deadline exceeded"],
        "category": ErrorCategory.NETWORK,
        "friendly": "Request timed out",
        "suggestion": "The operation took too long. Check your connection speed or increase timeout in settings.",
    },
    "dns_failure": {
        "patterns": ["nodename nor servname", "name or service not known", "getaddrinfo failed", "dns"],
        "category": ErrorCategory.NETWORK,
        "friendly": "Could not resolve server address",
        "suggestion": "Check the server URL in settings. Ensure you have internet connectivity.",
    },
    "ssl_error": {
        "patterns": ["ssl", "certificate", "cert verify failed", "https"],
        "category": ErrorCategory.NETWORK,
        "friendly": "SSL/TLS connection error",
        "suggestion": "There's a certificate issue. For local servers, you may need to disable SSL verification.",
    },
    
    # Authentication errors
    "api_key_missing": {
        "patterns": ["api_key", "api key", "no api key", "missing key", "key not found", "apikey"],
        "category": ErrorCategory.AUTH,
        "friendly": "API key is missing or not configured",
        "suggestion": "Set your API key in Settings (F3) under the provider configuration.",
    },
    "api_key_invalid": {
        "patterns": ["invalid api key", "invalid key", "incorrect api key", "authentication failed", "invalid_api_key"],
        "category": ErrorCategory.AUTH,
        "friendly": "API key is invalid or expired",
        "suggestion": "Verify your API key is correct. You may need to regenerate it from the provider's dashboard.",
    },
    "unauthorized": {
        "patterns": ["401", "unauthorized", "not authorized", "access denied"],
        "category": ErrorCategory.AUTH,
        "friendly": "Authentication failed",
        "suggestion": "Check your credentials. The API key may have been revoked or lack required permissions.",
    },
    "forbidden": {
        "patterns": ["403", "forbidden", "permission denied", "access forbidden"],
        "category": ErrorCategory.AUTH,
        "friendly": "Access forbidden",
        "suggestion": "Your account may not have access to this resource. Check your subscription or permissions.",
    },
    
    # Rate limiting
    "rate_limit": {
        "patterns": ["rate limit", "ratelimit", "429", "too many requests", "quota exceeded", "throttl"],
        "category": ErrorCategory.RESOURCE,
        "friendly": "Rate limit exceeded",
        "suggestion": "You've made too many requests. Wait a few minutes before trying again, or upgrade your plan.",
    },
    "quota_exceeded": {
        "patterns": ["quota", "billing", "insufficient_quota", "exceeded your current quota", "credit"],
        "category": ErrorCategory.RESOURCE,
        "friendly": "Usage quota exceeded",
        "suggestion": "You've exceeded your usage limit. Check your billing dashboard and add credits if needed.",
    },
    
    # Model errors
    "model_not_found": {
        "patterns": ["model not found", "model_not_found", "does not exist", "unknown model", "no such model"],
        "category": ErrorCategory.PROVIDER,
        "friendly": "Model not found",
        "suggestion": "The selected model doesn't exist or isn't available. Use /model to select a different model.",
    },
    "model_overloaded": {
        "patterns": ["overloaded", "capacity", "server is busy", "try again later"],
        "category": ErrorCategory.PROVIDER,
        "friendly": "Model is currently overloaded",
        "suggestion": "The server is experiencing high demand. Try again in a few moments or select a different model.",
    },
    "context_length": {
        "patterns": ["context length", "max.*token", "context_length_exceeded", "too long", "maximum context"],
        "category": ErrorCategory.VALIDATION,
        "friendly": "Input exceeds model's context limit",
        "suggestion": "Your message is too long. Try shortening it or use /clear to reset the conversation.",
    },
    
    # File system errors
    "file_not_found": {
        "patterns": ["file not found", "no such file", "does not exist", "[errno 2]"],
        "category": ErrorCategory.FILE,
        "friendly": "File not found",
        "suggestion": "The file doesn't exist at the specified path. Check the path and try again.",
    },
    "permission_denied": {
        "patterns": ["permission denied", "[errno 13]", "access is denied", "operation not permitted"],
        "category": ErrorCategory.PERMISSION,
        "friendly": "Permission denied",
        "suggestion": "You don't have permission to access this file. Check file permissions or run with elevated privileges.",
    },
    "directory_not_found": {
        "patterns": ["directory not found", "no such directory", "is not a directory"],
        "category": ErrorCategory.FILE,
        "friendly": "Directory not found",
        "suggestion": "The directory doesn't exist. Create it first or check the path.",
    },
    "disk_full": {
        "patterns": ["no space left", "disk full", "[errno 28]", "out of disk space"],
        "category": ErrorCategory.RESOURCE,
        "friendly": "Disk space full",
        "suggestion": "Free up disk space and try again.",
    },
    
    # Configuration errors
    "json_parse": {
        "patterns": ["json", "expecting value", "decode", "invalid json", "parse error"],
        "category": ErrorCategory.CONFIG,
        "friendly": "Invalid JSON format",
        "suggestion": "The configuration file has invalid JSON syntax. Check for missing commas or brackets.",
    },
    "config_missing": {
        "patterns": ["config not found", "configuration missing", "settings not found"],
        "category": ErrorCategory.CONFIG,
        "friendly": "Configuration missing",
        "suggestion": "Run /settings to configure the application, or check ~/.null/ directory.",
    },
    "invalid_config": {
        "patterns": ["invalid config", "configuration error", "bad configuration"],
        "category": ErrorCategory.CONFIG,
        "friendly": "Invalid configuration",
        "suggestion": "Check your configuration values in Settings (F3) or ~/.null/config.json.",
    },
    
    # MCP errors
    "mcp_connection": {
        "patterns": ["mcp", "server not running", "mcp server", "tool server"],
        "category": ErrorCategory.MCP,
        "friendly": "MCP server connection failed",
        "suggestion": "Check if the MCP server is running. Use /mcp list to see server status.",
    },
    "mcp_tool_error": {
        "patterns": ["tool error", "tool execution failed", "tool call failed"],
        "category": ErrorCategory.MCP,
        "friendly": "Tool execution failed",
        "suggestion": "The tool encountered an error. Check the tool's requirements and try again.",
    },
    
    # Provider-specific
    "ollama_not_running": {
        "patterns": ["ollama", "11434", "localhost:11434"],
        "category": ErrorCategory.PROVIDER,
        "friendly": "Ollama is not running",
        "suggestion": "Start Ollama with 'ollama serve' in a terminal, then try again.",
    },
    "openai_error": {
        "patterns": ["openai", "gpt-"],
        "category": ErrorCategory.PROVIDER,
        "friendly": "OpenAI API error",
        "suggestion": "Check your OpenAI API key and account status at platform.openai.com.",
    },
    "anthropic_error": {
        "patterns": ["anthropic", "claude"],
        "category": ErrorCategory.PROVIDER,
        "friendly": "Anthropic API error",
        "suggestion": "Check your Anthropic API key and account status at console.anthropic.com.",
    },
    
    # Validation errors
    "invalid_input": {
        "patterns": ["invalid input", "invalid value", "validation error", "invalid parameter"],
        "category": ErrorCategory.VALIDATION,
        "friendly": "Invalid input provided",
        "suggestion": "Check the input values and ensure they match the expected format.",
    },
    "missing_required": {
        "patterns": ["required", "missing", "must provide", "is required"],
        "category": ErrorCategory.VALIDATION,
        "friendly": "Required field missing",
        "suggestion": "Provide all required fields and try again.",
    },
}


def get_error_category(exc: BaseException) -> ErrorCategory:
    """Determine the category of an error for better organization."""
    error_msg = str(exc).lower()
    error_type = type(exc).__name__
    
    # Check exception types first
    if isinstance(exc, (ConnectionError, TimeoutError)):
        return ErrorCategory.NETWORK
    if isinstance(exc, (FileNotFoundError, IsADirectoryError, NotADirectoryError)):
        return ErrorCategory.FILE
    if isinstance(exc, PermissionError):
        return ErrorCategory.PERMISSION
    if isinstance(exc, (ValueError, TypeError)):
        return ErrorCategory.VALIDATION
    
    # Check message patterns
    for error_info in ERROR_MESSAGES.values():
        patterns = error_info.get("patterns", [])
        for pattern in patterns:
            if pattern in error_msg:
                return error_info.get("category", ErrorCategory.UNKNOWN)
    
    return ErrorCategory.UNKNOWN


def get_friendly_error_message(exc: BaseException) -> tuple[str, str, ErrorCategory]:
    """
    Get a user-friendly error message and suggestion based on the exception.
    
    Returns:
        tuple: (friendly_message, suggestion, category)
    """
    error_msg = str(exc).lower()
    error_type = type(exc).__name__
    
    # Search through error patterns for a match
    for error_key, error_info in ERROR_MESSAGES.items():
        patterns = error_info.get("patterns", [])
        for pattern in patterns:
            if pattern in error_msg:
                return (
                    error_info.get("friendly", str(exc)),
                    error_info.get("suggestion", ""),
                    error_info.get("category", ErrorCategory.UNKNOWN),
                )
    
    # Fallback to type-based messages
    type_messages = {
        "ConnectionError": ("Connection failed", "Check your network connection.", ErrorCategory.NETWORK),
        "TimeoutError": ("Operation timed out", "Try again or check your connection.", ErrorCategory.NETWORK),
        "FileNotFoundError": ("File not found", "Verify the file path exists.", ErrorCategory.FILE),
        "PermissionError": ("Permission denied", "Check file permissions.", ErrorCategory.PERMISSION),
        "ValueError": ("Invalid value", "Check the input parameters.", ErrorCategory.VALIDATION),
        "TypeError": ("Type error", "Check the parameter types.", ErrorCategory.VALIDATION),
        "KeyError": ("Missing key", "A required key was not found.", ErrorCategory.VALIDATION),
        "JSONDecodeError": ("Invalid JSON", "Check the JSON syntax.", ErrorCategory.CONFIG),
    }
    
    if error_type in type_messages:
        return type_messages[error_type]
    
    return (str(exc) or "An unexpected error occurred", "", ErrorCategory.UNKNOWN)


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
    category: ErrorCategory = ErrorCategory.UNKNOWN
    friendly_message: str = ""

    def to_copyable_text(self) -> str:
        lines = [
            f"Error Type: {self.error_type}",
            f"Category: {self.category.value}",
            f"Severity: {self.severity.value.upper()}",
            f"Timestamp: {self.timestamp.isoformat()}",
            f"Message: {self.friendly_message or self.message}",
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

    # Get enhanced error information
    friendly_msg, suggestion, category = get_friendly_error_message(exc)
    
    # Use pattern-based suggestion if available, otherwise fall back to type-based
    if not suggestion:
        suggestion = _generate_suggestion(exc, error_type)

    return StructuredError(
        error_type=error_type,
        message=message,
        severity=severity,
        details=_extract_details(exc),
        stack_trace=stack_trace,
        context=context or {},
        suggestion=suggestion,
        is_unexpected=_is_unexpected_error(exc),
        category=category,
        friendly_message=friendly_msg,
    )


def format_error_message(
    error_type: str,
    message: str,
    severity: ErrorSeverity = ErrorSeverity.ERROR,
    details: str = "",
    suggestion: str = "",
    context: dict[str, Any] | None = None,
    category: ErrorCategory = ErrorCategory.UNKNOWN,
) -> StructuredError:
    return StructuredError(
        error_type=error_type,
        message=message,
        severity=severity,
        details=details,
        suggestion=suggestion,
        context=context or {},
        is_unexpected=False,
        category=category,
        friendly_message=message,
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
    """Generate a helpful suggestion based on the error."""
    error_msg = str(exc).lower()
    
    # First check comprehensive error patterns
    for error_info in ERROR_MESSAGES.values():
        patterns = error_info.get("patterns", [])
        for pattern in patterns:
            if pattern in error_msg:
                return error_info.get("suggestion", "")
    
    # Fallback to simple keyword matching
    if "api_key" in error_msg or "api key" in error_msg:
        return "Check that your API key is configured correctly in Settings (F3)."

    if "rate limit" in error_msg or "ratelimit" in error_msg:
        return "You've hit a rate limit. Wait a moment and try again."

    if "timeout" in error_msg:
        return "The request timed out. Check your connection or try again."

    if "connection" in error_msg or "network" in error_msg:
        return "Check your internet connection and try again."
    
    if "ollama" in error_msg or "11434" in error_msg:
        return "Ensure Ollama is running with 'ollama serve'."
    
    if "model" in error_msg and ("not found" in error_msg or "does not exist" in error_msg):
        return "The model doesn't exist. Use /model to select an available model."

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
**Category:** {error.category.value}
**Severity:** {error.severity.value}
**Timestamp:** {error.timestamp.isoformat()}

### Message
{error.friendly_message or error.message}

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
