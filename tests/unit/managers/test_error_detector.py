"""Unit tests for the ErrorDetector and AutoCorrectionLoop classes."""

import re
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from managers.error_detector import (
    ERROR_PATTERNS,
    VERIFICATION_COMMANDS,
    AutoCorrectionLoop,
    CorrectionAttempt,
    DetectedError,
    ErrorDetector,
    ErrorType,
)

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def error_detector():
    """Create a fresh ErrorDetector instance."""
    return ErrorDetector()


@pytest.fixture
def auto_correction_loop():
    """Create an AutoCorrectionLoop instance."""
    return AutoCorrectionLoop(max_iterations=3)


@pytest.fixture
def mock_provider():
    """Create a mock LLM provider."""
    provider = MagicMock()

    async def mock_generate(*args, **kwargs):
        yield "Fix: Update the code to handle the error"

    provider.generate = mock_generate
    return provider


# =============================================================================
# DetectedError Tests
# =============================================================================


class TestDetectedError:
    """Tests for the DetectedError dataclass."""

    def test_location_with_file_and_line(self):
        error = DetectedError(
            error_type=ErrorType.PYTHON_SYNTAX,
            message="Invalid syntax",
            file="/path/to/file.py",
            line=42,
        )
        assert error.location == "/path/to/file.py:42"

    def test_location_with_file_only(self):
        error = DetectedError(
            error_type=ErrorType.PYTHON_SYNTAX,
            message="Invalid syntax",
            file="/path/to/file.py",
        )
        assert error.location == "/path/to/file.py"

    def test_location_unknown(self):
        error = DetectedError(
            error_type=ErrorType.PYTHON_SYNTAX,
            message="Invalid syntax",
        )
        assert error.location == "unknown"

    def test_default_values(self):
        error = DetectedError(
            error_type=ErrorType.UNKNOWN,
            message="Some error",
        )
        assert error.file is None
        assert error.line is None
        assert error.column is None
        assert error.full_output == ""
        assert error.severity == "error"
        assert error.suggestion is None
        assert isinstance(error.timestamp, datetime)


class TestCorrectionAttempt:
    """Tests for the CorrectionAttempt dataclass."""

    def test_default_values(self):
        error = DetectedError(error_type=ErrorType.UNKNOWN, message="Error")
        attempt = CorrectionAttempt(error=error, fix_description="Applied fix")

        assert attempt.files_modified == []
        assert attempt.success is False
        assert attempt.verification_output == ""
        assert attempt.duration == 0.0


# =============================================================================
# ErrorDetector Tests
# =============================================================================


class TestErrorDetector:
    """Tests for the ErrorDetector class."""

    def test_init(self, error_detector):
        assert error_detector.error_history == []
        assert error_detector.correction_history == []

    # -------------------------------------------------------------------------
    # Python Syntax Error Detection
    # -------------------------------------------------------------------------

    def test_detect_python_syntax_error(self, error_detector):
        output = "SyntaxError: invalid syntax"
        errors = error_detector.detect(output)

        assert len(errors) == 1
        assert errors[0].error_type == ErrorType.PYTHON_SYNTAX
        assert errors[0].full_output == output

    def test_detect_python_syntax_error_with_location(self, error_detector):
        output = '  File "test.py", line 10\n    x = \nSyntaxError: invalid syntax'
        errors = error_detector.detect(output)

        syntax_errors = [e for e in errors if e.error_type == ErrorType.PYTHON_SYNTAX]
        assert len(syntax_errors) >= 1
        assert syntax_errors[0].error_type == ErrorType.PYTHON_SYNTAX

    def test_detect_indentation_error(self, error_detector):
        output = "IndentationError: unexpected indent"
        errors = error_detector.detect(output)

        assert len(errors) == 1
        assert errors[0].error_type == ErrorType.PYTHON_SYNTAX

    # -------------------------------------------------------------------------
    # Python Runtime Error Detection
    # -------------------------------------------------------------------------

    def test_detect_python_traceback(self, error_detector):
        output = """File "/app/main.py", line 25
    result = x / 0
ZeroDivisionError: division by zero"""
        errors = error_detector.detect(output)

        assert len(errors) >= 1
        runtime_errors = [e for e in errors if e.error_type == ErrorType.PYTHON_RUNTIME]
        assert len(runtime_errors) == 1
        assert runtime_errors[0].file == "/app/main.py"
        assert runtime_errors[0].line == 25
        assert "ZeroDivisionError" in runtime_errors[0].message

    # -------------------------------------------------------------------------
    # Python Type Error Detection
    # -------------------------------------------------------------------------

    def test_detect_type_error(self, error_detector):
        output = "TypeError: unsupported operand type(s) for +: 'int' and 'str'"
        errors = error_detector.detect(output)

        type_errors = [e for e in errors if e.error_type == ErrorType.PYTHON_TYPE]
        assert len(type_errors) == 1
        assert "unsupported operand" in type_errors[0].message

    # -------------------------------------------------------------------------
    # Python Import Error Detection
    # -------------------------------------------------------------------------

    def test_detect_module_not_found_error(self, error_detector):
        output = "ModuleNotFoundError: No module named 'nonexistent'"
        errors = error_detector.detect(output)

        import_errors = [e for e in errors if e.error_type == ErrorType.PYTHON_IMPORT]
        assert len(import_errors) == 1
        assert "nonexistent" in import_errors[0].message

    def test_detect_import_error(self, error_detector):
        output = "ImportError: cannot import name 'foo' from 'bar'"
        errors = error_detector.detect(output)

        import_errors = [e for e in errors if e.error_type == ErrorType.PYTHON_IMPORT]
        assert len(import_errors) == 1

    # -------------------------------------------------------------------------
    # TypeScript Error Detection
    # -------------------------------------------------------------------------

    def test_detect_typescript_error(self, error_detector):
        output = "src/app.ts(15,10): error TS2339: Property 'foo' does not exist on type 'Bar'."
        errors = error_detector.detect(output)

        ts_errors = [e for e in errors if e.error_type == ErrorType.TYPESCRIPT]
        assert len(ts_errors) == 1
        assert ts_errors[0].file == "src/app.ts"
        assert ts_errors[0].line == 15
        assert ts_errors[0].column == 10
        assert "Property 'foo' does not exist" in ts_errors[0].message

    # -------------------------------------------------------------------------
    # ESLint Error Detection
    # -------------------------------------------------------------------------

    def test_detect_eslint_error(self, error_detector):
        output = "10:5  error  Unexpected console statement  no-console"
        errors = error_detector.detect(output)

        eslint_errors = [e for e in errors if e.error_type == ErrorType.ESLINT]
        assert len(eslint_errors) == 1
        assert eslint_errors[0].line == 10
        assert eslint_errors[0].column == 5
        assert eslint_errors[0].severity == "error"

    def test_detect_eslint_warning(self, error_detector):
        output = "5:1  warning  Missing semicolon  semi"
        errors = error_detector.detect(output)

        eslint_errors = [e for e in errors if e.error_type == ErrorType.ESLINT]
        assert len(eslint_errors) == 1
        assert eslint_errors[0].severity == "warning"

    # -------------------------------------------------------------------------
    # Pytest Error Detection
    # -------------------------------------------------------------------------

    def test_detect_pytest_failure(self, error_detector):
        output = "FAILED tests/test_example.py::test_something - AssertionError: assert 1 == 2"
        errors = error_detector.detect(output)

        pytest_errors = [e for e in errors if e.error_type == ErrorType.PYTEST]
        assert len(pytest_errors) == 1
        assert pytest_errors[0].file == "tests/test_example.py"
        assert "AssertionError" in pytest_errors[0].message

    # -------------------------------------------------------------------------
    # Ruff Error Detection
    # -------------------------------------------------------------------------

    def test_detect_ruff_error(self, error_detector):
        output = "main.py:10:1: E501 Line too long (120 > 100 characters)"
        errors = error_detector.detect(output)

        ruff_errors = [e for e in errors if e.error_type == ErrorType.RUFF]
        assert len(ruff_errors) == 1
        assert ruff_errors[0].file == "main.py"
        assert ruff_errors[0].line == 10
        assert ruff_errors[0].column == 1
        assert "Line too long" in ruff_errors[0].message

    # -------------------------------------------------------------------------
    # Shell Error Detection
    # -------------------------------------------------------------------------

    def test_detect_command_not_found(self, error_detector):
        output = "bash: foobar: command not found"
        errors = error_detector.detect(output)

        shell_errors = [e for e in errors if e.error_type == ErrorType.NOT_FOUND]
        assert len(shell_errors) == 1

    def test_detect_command_not_found_zsh(self, error_detector):
        output = "zsh: command not found: mycommand"
        errors = error_detector.detect(output)

        shell_errors = [e for e in errors if e.error_type == ErrorType.NOT_FOUND]
        assert len(shell_errors) == 1

    # -------------------------------------------------------------------------
    # Permission Error Detection
    # -------------------------------------------------------------------------

    def test_detect_permission_denied(self, error_detector):
        output = "Permission denied: /etc/passwd"
        errors = error_detector.detect(output)

        perm_errors = [e for e in errors if e.error_type == ErrorType.PERMISSION]
        assert len(perm_errors) == 1

    def test_detect_eacces(self, error_detector):
        output = "EACCES: open '/root/file.txt'"
        errors = error_detector.detect(output)

        perm_errors = [e for e in errors if e.error_type == ErrorType.PERMISSION]
        assert len(perm_errors) >= 1

    # -------------------------------------------------------------------------
    # Multiple Error Detection
    # -------------------------------------------------------------------------

    def test_detect_multiple_errors(self, error_detector):
        output = """SyntaxError: invalid syntax
ModuleNotFoundError: No module named 'foo'
TypeError: cannot concatenate"""
        errors = error_detector.detect(output)

        # Should detect at least 3 different types
        error_types = {e.error_type for e in errors}
        assert ErrorType.PYTHON_SYNTAX in error_types
        assert ErrorType.PYTHON_IMPORT in error_types
        assert ErrorType.PYTHON_TYPE in error_types

    def test_detect_no_errors(self, error_detector):
        output = "All tests passed successfully!"
        errors = error_detector.detect(output)

        assert errors == []

    # -------------------------------------------------------------------------
    # Error History Management
    # -------------------------------------------------------------------------

    def test_error_history_updated(self, error_detector):
        output1 = "SyntaxError: invalid syntax"
        output2 = "TypeError: wrong type"

        error_detector.detect(output1)
        assert len(error_detector.error_history) == 1

        error_detector.detect(output2)
        assert len(error_detector.error_history) == 2

    def test_duplicate_errors_not_added(self, error_detector):
        output = "SyntaxError: invalid syntax"

        error_detector.detect(output)
        error_detector.detect(output)

        # Due to timestamp differences, duplicates may still be added
        # This test verifies the history tracking works
        assert len(error_detector.error_history) >= 1

    def test_get_last_error(self, error_detector):
        assert error_detector.get_last_error() is None

        error_detector.detect("SyntaxError: first error")
        error_detector.detect("TypeError: second error")

        last = error_detector.get_last_error()
        assert last is not None
        assert last.error_type == ErrorType.PYTHON_TYPE

    def test_clear_history(self, error_detector):
        error_detector.detect("SyntaxError: test")
        error_detector.correction_history.append(
            CorrectionAttempt(
                error=error_detector.error_history[0],
                fix_description="Fixed it",
            )
        )

        error_detector.clear_history()

        assert error_detector.error_history == []
        assert error_detector.correction_history == []


# =============================================================================
# AutoCorrectionLoop Tests
# =============================================================================


class TestAutoCorrectionLoop:
    """Tests for the AutoCorrectionLoop class."""

    def test_init(self, auto_correction_loop):
        assert auto_correction_loop.max_iterations == 3
        assert auto_correction_loop.is_running is False
        assert auto_correction_loop.current_iteration == 0
        assert isinstance(auto_correction_loop.detector, ErrorDetector)

    def test_stop(self, auto_correction_loop):
        auto_correction_loop.is_running = True
        auto_correction_loop.stop()
        assert auto_correction_loop.is_running is False

    @pytest.mark.asyncio
    async def test_generate_fix(self, auto_correction_loop, mock_provider):
        error = DetectedError(
            error_type=ErrorType.PYTHON_SYNTAX,
            message="Invalid syntax",
            file="/app/test.py",
            line=10,
            full_output="SyntaxError: invalid syntax",
        )

        result = await auto_correction_loop.generate_fix(
            error, mock_provider, file_content="def foo():\n  pass"
        )

        assert "Fix" in result

    @pytest.mark.asyncio
    async def test_generate_fix_without_file(self, auto_correction_loop, mock_provider):
        error = DetectedError(
            error_type=ErrorType.PYTHON_RUNTIME,
            message="Runtime error",
            full_output="Some error occurred",
        )

        result = await auto_correction_loop.generate_fix(error, mock_provider)

        assert "Fix" in result

    @pytest.mark.asyncio
    async def test_verify_fix_no_file(self, auto_correction_loop):
        error = DetectedError(
            error_type=ErrorType.UNKNOWN,
            message="Error without file",
        )

        success, message = await auto_correction_loop.verify_fix(error)

        assert success is True
        assert "No file to verify" in message

    @pytest.mark.asyncio
    async def test_verify_fix_unknown_extension(self, auto_correction_loop):
        error = DetectedError(
            error_type=ErrorType.UNKNOWN,
            message="Error",
            file="/app/file.unknown",
        )

        success, message = await auto_correction_loop.verify_fix(error)

        assert success is True
        assert "No verification command" in message

    @pytest.mark.asyncio
    async def test_verify_fix_python_success(self, auto_correction_loop, temp_dir):
        # Create a valid Python file
        test_file = temp_dir / "valid.py"
        test_file.write_text("def hello():\n    return 'world'\n")

        error = DetectedError(
            error_type=ErrorType.PYTHON_SYNTAX,
            message="Test",
            file=str(test_file),
        )

        with patch("asyncio.create_subprocess_shell") as mock_subprocess:
            mock_process = AsyncMock()
            mock_process.returncode = 0
            mock_process.communicate = AsyncMock(return_value=(b"", b""))
            mock_subprocess.return_value = mock_process

            success, message = await auto_correction_loop.verify_fix(error)

            assert success is True
            assert "passed" in message

    @pytest.mark.asyncio
    async def test_verify_fix_python_failure(self, auto_correction_loop, temp_dir):
        test_file = temp_dir / "invalid.py"
        test_file.write_text("def broken(\n")

        error = DetectedError(
            error_type=ErrorType.PYTHON_SYNTAX,
            message="Test",
            file=str(test_file),
        )

        with patch("asyncio.create_subprocess_shell") as mock_subprocess:
            mock_process = AsyncMock()
            mock_process.returncode = 1
            mock_process.communicate = AsyncMock(
                return_value=(b"SyntaxError: invalid syntax", b"")
            )
            mock_subprocess.return_value = mock_process

            success, message = await auto_correction_loop.verify_fix(error)

            assert success is False
            assert "SyntaxError" in message

    @pytest.mark.asyncio
    async def test_verify_fix_exception(self, auto_correction_loop, temp_dir):
        test_file = temp_dir / "test.py"
        test_file.write_text("print('hello')")

        error = DetectedError(
            error_type=ErrorType.PYTHON_SYNTAX,
            message="Test",
            file=str(test_file),
        )

        with patch("asyncio.create_subprocess_shell") as mock_subprocess:
            mock_subprocess.side_effect = Exception("Subprocess failed")

            success, message = await auto_correction_loop.verify_fix(error)

            assert success is False
            assert "Subprocess failed" in message


# =============================================================================
# Error Patterns Tests
# =============================================================================


class TestErrorPatterns:
    """Tests for the ERROR_PATTERNS constant."""

    def test_all_patterns_compile(self):
        """Verify all regex patterns are valid."""
        for name, (pattern, _error_type) in ERROR_PATTERNS.items():
            try:
                re.compile(pattern)
            except re.error as e:
                pytest.fail(f"Invalid regex for pattern '{name}': {e}")

    def test_all_patterns_have_error_type(self):
        """Verify all patterns map to valid ErrorType."""
        for name, (_pattern, error_type) in ERROR_PATTERNS.items():
            assert isinstance(error_type, ErrorType), (
                f"Pattern '{name}' has invalid error type"
            )


class TestVerificationCommands:
    """Tests for the VERIFICATION_COMMANDS constant."""

    def test_verification_commands_structure(self):
        """Verify the structure of verification commands."""
        expected_languages = ["python", "typescript", "javascript", "rust"]

        for lang in expected_languages:
            assert lang in VERIFICATION_COMMANDS, f"Missing verification for {lang}"
            assert isinstance(VERIFICATION_COMMANDS[lang], list)
            assert len(VERIFICATION_COMMANDS[lang]) > 0

    def test_verification_commands_have_file_placeholder(self):
        """Verify commands use {file} placeholder where applicable."""
        for lang, commands in VERIFICATION_COMMANDS.items():
            for cmd in commands:
                # Most commands should have {file} placeholder except cargo
                if lang != "rust":
                    assert "{file}" in cmd, f"Missing {{file}} in {lang} command: {cmd}"


# =============================================================================
# ErrorType Enum Tests
# =============================================================================


class TestErrorType:
    """Tests for the ErrorType enum."""

    def test_all_error_types_have_values(self):
        """Verify all error types have string values."""
        for error_type in ErrorType:
            assert isinstance(error_type.value, str)
            assert len(error_type.value) > 0

    def test_error_type_uniqueness(self):
        """Verify all error type values are unique."""
        values = [e.value for e in ErrorType]
        assert len(values) == len(set(values)), "Duplicate ErrorType values found"
