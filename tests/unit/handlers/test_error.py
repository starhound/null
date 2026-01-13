import pytest

from handlers.error import (
    ErrorSeverity,
    StructuredError,
    create_issue_url,
    format_error_message,
    format_exception,
)


class TestErrorSeverity:
    def test_enum_values(self):
        assert ErrorSeverity.INFO.value == "info"
        assert ErrorSeverity.WARNING.value == "warning"
        assert ErrorSeverity.ERROR.value == "error"
        assert ErrorSeverity.CRITICAL.value == "critical"


class TestStructuredError:
    def test_to_copyable_text_basic(self):
        error = StructuredError(
            error_type="TestError",
            message="Something went wrong",
            severity=ErrorSeverity.ERROR,
        )
        text = error.to_copyable_text()

        assert "Error Type: TestError" in text
        assert "Severity: ERROR" in text
        assert "Message: Something went wrong" in text

    def test_to_copyable_text_with_details(self):
        error = StructuredError(
            error_type="TestError",
            message="Something went wrong",
            details="More info here",
            severity=ErrorSeverity.WARNING,
        )
        text = error.to_copyable_text()

        assert "Details:" in text
        assert "More info here" in text

    def test_to_copyable_text_with_context(self):
        error = StructuredError(
            error_type="TestError",
            message="Something went wrong",
            context={"provider": "openai", "model": "gpt-4"},
        )
        text = error.to_copyable_text()

        assert "Context:" in text
        assert "provider: openai" in text
        assert "model: gpt-4" in text

    def test_to_copyable_text_with_suggestion(self):
        error = StructuredError(
            error_type="TestError",
            message="Something went wrong",
            suggestion="Try again later",
        )
        text = error.to_copyable_text()

        assert "Suggestion: Try again later" in text

    def test_to_copyable_text_with_stack_trace(self):
        error = StructuredError(
            error_type="TestError",
            message="Something went wrong",
            stack_trace="Traceback...\n  File...\nError",
        )
        text = error.to_copyable_text()

        assert "Stack Trace:" in text
        assert "Traceback..." in text


class TestFormatException:
    def test_basic_exception(self):
        try:
            raise ValueError("test message")
        except ValueError as e:
            result = format_exception(e)

        assert result.error_type == "ValueError"
        assert result.message == "test message"
        assert result.severity == ErrorSeverity.ERROR
        assert "ValueError" in result.stack_trace

    def test_with_context(self):
        try:
            raise RuntimeError("test")
        except RuntimeError as e:
            result = format_exception(e, context={"key": "value"})

        assert result.context == {"key": "value"}

    def test_severity_override(self):
        try:
            raise ValueError("test")
        except ValueError as e:
            result = format_exception(e, severity=ErrorSeverity.CRITICAL)

        assert result.severity == ErrorSeverity.CRITICAL

    def test_connection_error_warning_severity(self):
        result = format_exception(ConnectionError("connection failed"))
        assert result.severity == ErrorSeverity.WARNING

    def test_timeout_error_warning_severity(self):
        result = format_exception(TimeoutError("timed out"))
        assert result.severity == ErrorSeverity.WARNING

    def test_memory_error_critical_severity(self):
        result = format_exception(MemoryError("out of memory"))
        assert result.severity == ErrorSeverity.CRITICAL

    def test_generates_suggestion_for_value_error(self):
        result = format_exception(ValueError("bad value"))
        assert result.suggestion

    def test_generates_suggestion_for_file_not_found(self):
        result = format_exception(FileNotFoundError("file.txt"))
        assert "file path" in result.suggestion.lower()


class TestFormatErrorMessage:
    def test_creates_structured_error(self):
        result = format_error_message(
            error_type="CustomError",
            message="Custom message",
            severity=ErrorSeverity.WARNING,
            details="Extra details",
            suggestion="Try this",
            context={"foo": "bar"},
        )

        assert result.error_type == "CustomError"
        assert result.message == "Custom message"
        assert result.severity == ErrorSeverity.WARNING
        assert result.details == "Extra details"
        assert result.suggestion == "Try this"
        assert result.context == {"foo": "bar"}
        assert result.is_unexpected is False

    def test_defaults(self):
        result = format_error_message(
            error_type="TestError",
            message="Test",
        )

        assert result.severity == ErrorSeverity.ERROR
        assert result.details == ""
        assert result.suggestion == ""
        assert result.context == {}


class TestCreateIssueUrl:
    def test_generates_url(self):
        error = StructuredError(
            error_type="TestError",
            message="Test message",
            severity=ErrorSeverity.ERROR,
        )
        url = create_issue_url(error)

        assert url.startswith("https://github.com/starhound/null-terminal/issues/new")
        assert "title=" in url
        assert "body=" in url

    def test_truncates_long_message(self):
        error = StructuredError(
            error_type="TestError",
            message="A" * 100,
            severity=ErrorSeverity.ERROR,
        )
        url = create_issue_url(error)

        assert "..." in url

    def test_truncates_long_stack_trace(self):
        from urllib.parse import unquote

        error = StructuredError(
            error_type="TestError",
            message="Test",
            stack_trace="A" * 2000,
        )
        url = create_issue_url(error)

        assert "(truncated)" in unquote(url)


class TestUnexpectedErrorDetection:
    def test_value_error_is_expected(self):
        result = format_exception(ValueError("test"))
        assert result.is_unexpected is False

    def test_file_not_found_is_expected(self):
        result = format_exception(FileNotFoundError("test"))
        assert result.is_unexpected is False

    def test_runtime_error_is_unexpected(self):
        result = format_exception(RuntimeError("unexpected"))
        assert result.is_unexpected is True

    def test_assertion_error_is_unexpected(self):
        result = format_exception(AssertionError("test"))
        assert result.is_unexpected is True

    def test_api_key_message_is_expected(self):
        exc = RuntimeError("Invalid API_KEY provided")
        result = format_exception(exc)
        assert result.is_unexpected is False


class TestChainedExceptions:
    def test_extracts_cause(self):
        try:
            try:
                raise ValueError("inner")
            except ValueError as e:
                raise RuntimeError("outer") from e
        except RuntimeError as e:
            result = format_exception(e)

        assert "Caused by: ValueError" in result.details

    def test_extracts_context(self):
        try:
            try:
                raise ValueError("inner")
            except ValueError:
                raise RuntimeError("outer")
        except RuntimeError as e:
            result = format_exception(e)

        assert "During handling: ValueError" in result.details
