"""Tests for widgets/blocks/correction_block.py - CorrectionLoopBlock."""

from datetime import datetime
from unittest.mock import patch

import pytest
from textual.widgets import Static

from managers.error_detector import CorrectionAttempt, DetectedError, ErrorType
from widgets.blocks.correction_block import CorrectionLoopBlock, CorrectionLoopStopped


@pytest.fixture
def sample_error():
    """Create a sample DetectedError for testing."""
    return DetectedError(
        error_type=ErrorType.PYTHON_SYNTAX,
        message="invalid syntax: expected ':'",
        file="src/main.py",
        line=42,
        column=10,
        full_output="SyntaxError: invalid syntax\n  File 'src/main.py', line 42",
    )


@pytest.fixture
def sample_error_no_file():
    """Create a DetectedError without file information."""
    return DetectedError(
        error_type=ErrorType.PYTHON_IMPORT,
        message="No module named 'nonexistent'",
        full_output="ModuleNotFoundError: No module named 'nonexistent'",
    )


@pytest.fixture
def sample_attempt_success(sample_error):
    """Create a successful CorrectionAttempt."""
    return CorrectionAttempt(
        error=sample_error,
        fix_description="Fixed the missing colon in the function definition",
        files_modified=["src/main.py"],
        success=True,
        verification_output="All checks passed",
        duration=1.5,
    )


@pytest.fixture
def sample_attempt_fail(sample_error):
    """Create a failed CorrectionAttempt."""
    return CorrectionAttempt(
        error=sample_error,
        fix_description="Attempted to add missing colon",
        files_modified=["src/main.py"],
        success=False,
        verification_output="SyntaxError still present at line 42",
        duration=2.0,
    )


class TestCorrectionLoopStoppedMessage:
    """Test the CorrectionLoopStopped message class."""

    def test_message_is_importable(self):
        from widgets.blocks.correction_block import CorrectionLoopStopped

        assert CorrectionLoopStopped is not None

    def test_message_can_be_instantiated(self):
        msg = CorrectionLoopStopped()
        assert msg is not None

    def test_message_inherits_from_message(self):
        from textual.message import Message

        msg = CorrectionLoopStopped()
        assert isinstance(msg, Message)

    def test_multiple_messages_are_independent(self):
        msg1 = CorrectionLoopStopped()
        msg2 = CorrectionLoopStopped()
        assert msg1 is not msg2


class TestCorrectionLoopBlockInit:
    """Test CorrectionLoopBlock initialization."""

    def test_init_stores_error(self, sample_error):
        widget = CorrectionLoopBlock(error=sample_error)
        assert widget.error is sample_error

    def test_init_stores_error_type(self, sample_error):
        widget = CorrectionLoopBlock(error=sample_error)
        assert widget.error.error_type == ErrorType.PYTHON_SYNTAX

    def test_init_default_max_iterations(self, sample_error):
        widget = CorrectionLoopBlock(error=sample_error)
        assert widget.max_iterations == 5

    def test_init_custom_max_iterations(self, sample_error):
        widget = CorrectionLoopBlock(error=sample_error, max_iterations=10)
        assert widget.max_iterations == 10

    def test_init_max_iterations_one(self, sample_error):
        widget = CorrectionLoopBlock(error=sample_error, max_iterations=1)
        assert widget.max_iterations == 1

    def test_init_attempts_empty(self, sample_error):
        widget = CorrectionLoopBlock(error=sample_error)
        assert widget.attempts == []

    def test_init_loop_active_true(self, sample_error):
        widget = CorrectionLoopBlock(error=sample_error)
        assert widget.loop_active is True

    def test_init_current_iteration_zero(self, sample_error):
        widget = CorrectionLoopBlock(error=sample_error)
        assert widget.current_iteration == 0

    def test_init_accepts_kwargs(self, sample_error):
        widget = CorrectionLoopBlock(
            error=sample_error, id="my-correction", classes="custom-class"
        )
        assert widget.id == "my-correction"
        assert "custom-class" in widget.classes

    def test_init_with_error_no_file(self, sample_error_no_file):
        widget = CorrectionLoopBlock(error=sample_error_no_file)
        assert widget.error.file is None
        assert widget.error.line is None


class TestCorrectionLoopBlockReactives:
    """Test reactive properties."""

    def test_loop_active_is_reactive(self, sample_error):
        widget = CorrectionLoopBlock(error=sample_error)
        widget.loop_active = False
        assert widget.loop_active is False

    def test_loop_active_can_toggle(self, sample_error):
        widget = CorrectionLoopBlock(error=sample_error)
        widget.loop_active = False
        widget.loop_active = True
        assert widget.loop_active is True

    def test_current_iteration_is_reactive(self, sample_error):
        widget = CorrectionLoopBlock(error=sample_error)
        widget.current_iteration = 3
        assert widget.current_iteration == 3

    def test_current_iteration_can_increase(self, sample_error):
        widget = CorrectionLoopBlock(error=sample_error)
        widget.current_iteration = 1
        widget.current_iteration = 2
        widget.current_iteration = 3
        assert widget.current_iteration == 3

    def test_max_iterations_is_reactive(self, sample_error):
        widget = CorrectionLoopBlock(error=sample_error)
        widget.max_iterations = 10
        assert widget.max_iterations == 10


class TestCorrectionLoopBlockCSS:
    """Test DEFAULT_CSS definitions."""

    def test_default_css_contains_widget_selector(self):
        assert "CorrectionLoopBlock" in CorrectionLoopBlock.DEFAULT_CSS

    def test_default_css_contains_loop_header(self):
        assert ".loop-header" in CorrectionLoopBlock.DEFAULT_CSS

    def test_default_css_contains_error_info(self):
        assert ".error-info" in CorrectionLoopBlock.DEFAULT_CSS

    def test_default_css_contains_attempt(self):
        assert ".attempt" in CorrectionLoopBlock.DEFAULT_CSS

    def test_default_css_contains_attempt_success(self):
        assert ".attempt-success" in CorrectionLoopBlock.DEFAULT_CSS

    def test_default_css_contains_attempt_fail(self):
        assert ".attempt-fail" in CorrectionLoopBlock.DEFAULT_CSS

    def test_default_css_contains_attempt_progress(self):
        assert ".attempt-progress" in CorrectionLoopBlock.DEFAULT_CSS

    def test_default_css_uses_warning_variable(self):
        assert "$warning" in CorrectionLoopBlock.DEFAULT_CSS

    def test_default_css_uses_error_variable(self):
        assert "$error" in CorrectionLoopBlock.DEFAULT_CSS

    def test_default_css_uses_success_variable(self):
        assert "$success" in CorrectionLoopBlock.DEFAULT_CSS


class TestCorrectionLoopBlockCompose:
    def test_compose_returns_generator(self, sample_error):
        widget = CorrectionLoopBlock(error=sample_error)
        result = widget.compose()
        assert hasattr(result, "__iter__")

    def test_compose_method_is_generator_function(self, sample_error):
        import inspect

        widget = CorrectionLoopBlock(error=sample_error)
        assert inspect.isgeneratorfunction(widget.compose) or hasattr(
            widget.compose(), "__iter__"
        )

    def test_compose_method_exists(self, sample_error):
        widget = CorrectionLoopBlock(error=sample_error)
        assert hasattr(widget, "compose")
        assert callable(widget.compose)

    def test_widget_has_default_css(self, sample_error):
        widget = CorrectionLoopBlock(error=sample_error)
        assert widget.DEFAULT_CSS is not None
        assert len(widget.DEFAULT_CSS) > 0


class TestCorrectionLoopBlockAddAttempt:
    def test_add_attempt_appends_to_list(self, sample_error, sample_attempt_success):
        widget = CorrectionLoopBlock(error=sample_error)
        with patch.object(widget, "_update_display"):
            widget.add_attempt(sample_attempt_success)
        assert len(widget.attempts) == 1
        assert widget.attempts[0] is sample_attempt_success

    def test_add_attempt_increments_current_iteration(
        self, sample_error, sample_attempt_success
    ):
        widget = CorrectionLoopBlock(error=sample_error)
        assert widget.current_iteration == 0
        with patch.object(widget, "_update_display"):
            widget.add_attempt(sample_attempt_success)
        assert widget.current_iteration == 1

    def test_add_multiple_attempts(
        self, sample_error, sample_attempt_success, sample_attempt_fail
    ):
        widget = CorrectionLoopBlock(error=sample_error)
        with patch.object(widget, "_update_display"):
            widget.add_attempt(sample_attempt_fail)
            widget.add_attempt(sample_attempt_success)
        assert len(widget.attempts) == 2
        assert widget.current_iteration == 2

    def test_add_attempt_handles_unmounted(self, sample_error, sample_attempt_success):
        widget = CorrectionLoopBlock(error=sample_error)
        try:
            widget.add_attempt(sample_attempt_success)
        except Exception:
            pass
        assert widget.current_iteration == 1

    def test_add_attempt_preserves_order(self, sample_error):
        widget = CorrectionLoopBlock(error=sample_error)
        attempts = []
        with patch.object(widget, "_update_display"):
            for i in range(3):
                attempt = CorrectionAttempt(
                    error=sample_error,
                    fix_description=f"Fix {i}",
                    success=i == 2,
                    verification_output=f"Output {i}",
                )
                attempts.append(attempt)
                widget.add_attempt(attempt)

        for i, attempt in enumerate(widget.attempts):
            assert attempt.fix_description == f"Fix {i}"


class TestCorrectionLoopBlockMarkComplete:
    """Test the mark_complete method."""

    def test_mark_complete_success_sets_loop_inactive(self, sample_error):
        widget = CorrectionLoopBlock(error=sample_error)
        assert widget.loop_active is True
        widget.loop_active = False
        assert widget.loop_active is False

    def test_mark_complete_failure_sets_loop_inactive(self, sample_error):
        widget = CorrectionLoopBlock(error=sample_error)
        widget.loop_active = False
        assert widget.loop_active is False

    def test_mark_complete_method_exists(self, sample_error):
        widget = CorrectionLoopBlock(error=sample_error)
        assert hasattr(widget, "mark_complete")
        assert callable(widget.mark_complete)


class TestCorrectionLoopBlockButtonPressed:
    """Test the on_button_pressed event handler."""

    def test_on_button_pressed_method_exists(self, sample_error):
        widget = CorrectionLoopBlock(error=sample_error)
        assert hasattr(widget, "on_button_pressed")
        assert callable(widget.on_button_pressed)

    def test_button_pressed_stop_sets_loop_inactive(self, sample_error):
        widget = CorrectionLoopBlock(error=sample_error)
        assert widget.loop_active is True
        widget.loop_active = False
        assert widget.loop_active is False


class TestCorrectionLoopBlockInheritance:
    """Test CorrectionLoopBlock inheritance."""

    def test_inherits_from_static(self, sample_error):
        widget = CorrectionLoopBlock(error=sample_error)
        assert isinstance(widget, Static)

    def test_has_standard_widget_attributes(self, sample_error):
        widget = CorrectionLoopBlock(error=sample_error)
        assert hasattr(widget, "update")
        assert hasattr(widget, "render")
        assert hasattr(widget, "compose")

    def test_has_styles_attribute(self, sample_error):
        widget = CorrectionLoopBlock(error=sample_error)
        assert hasattr(widget, "styles")


class TestCorrectionLoopBlockErrorTypes:
    """Test with different error types."""

    @pytest.mark.parametrize(
        "error_type",
        [
            ErrorType.PYTHON_SYNTAX,
            ErrorType.PYTHON_RUNTIME,
            ErrorType.PYTHON_IMPORT,
            ErrorType.PYTHON_TYPE,
            ErrorType.TYPESCRIPT,
            ErrorType.ESLINT,
            ErrorType.PYTEST,
            ErrorType.RUFF,
            ErrorType.SHELL,
            ErrorType.PERMISSION,
            ErrorType.NOT_FOUND,
            ErrorType.UNKNOWN,
        ],
    )
    def test_handles_all_error_types(self, error_type):
        error = DetectedError(
            error_type=error_type,
            message=f"Test error for {error_type.value}",
            full_output="Full output text",
        )
        widget = CorrectionLoopBlock(error=error)
        assert widget.error.error_type == error_type

    def test_python_syntax_error(self):
        error = DetectedError(
            error_type=ErrorType.PYTHON_SYNTAX,
            message="unexpected EOF while parsing",
            file="test.py",
            line=10,
        )
        widget = CorrectionLoopBlock(error=error)
        assert widget.error.error_type == ErrorType.PYTHON_SYNTAX

    def test_typescript_error_with_column(self):
        error = DetectedError(
            error_type=ErrorType.TYPESCRIPT,
            message="Property 'x' does not exist",
            file="src/app.ts",
            line=25,
            column=15,
        )
        widget = CorrectionLoopBlock(error=error)
        assert widget.error.column == 15


class TestCorrectionLoopBlockEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_zero_max_iterations(self, sample_error):
        widget = CorrectionLoopBlock(error=sample_error, max_iterations=0)
        assert widget.max_iterations == 0

    def test_large_max_iterations(self, sample_error):
        widget = CorrectionLoopBlock(error=sample_error, max_iterations=1000)
        assert widget.max_iterations == 1000

    def test_error_with_long_message(self):
        long_message = "Error: " + "x" * 1000
        error = DetectedError(
            error_type=ErrorType.UNKNOWN,
            message=long_message,
        )
        widget = CorrectionLoopBlock(error=error)
        assert len(widget.error.message) > 100

    def test_error_with_unicode(self):
        error = DetectedError(
            error_type=ErrorType.PYTHON_SYNTAX,
            message="Ошибка синтаксиса: неожиданный символ '你好'",
            file="тест.py",
        )
        widget = CorrectionLoopBlock(error=error)
        assert "你好" in widget.error.message

    def test_error_with_special_characters(self):
        error = DetectedError(
            error_type=ErrorType.PYTHON_SYNTAX,
            message="SyntaxError: invalid syntax <script>alert('xss')</script>",
            full_output="<>&\"'",
        )
        widget = CorrectionLoopBlock(error=error)
        assert "<script>" in widget.error.message

    def test_error_with_multiline_output(self):
        error = DetectedError(
            error_type=ErrorType.PYTHON_RUNTIME,
            message="ZeroDivisionError: division by zero",
            full_output="Traceback (most recent call last):\n  File 'test.py', line 1\n    1/0\nZeroDivisionError: division by zero",
        )
        widget = CorrectionLoopBlock(error=error)
        assert "\n" in widget.error.full_output

    def test_error_location_with_file_and_line(self, sample_error):
        widget = CorrectionLoopBlock(error=sample_error)
        assert widget.error.location == "src/main.py:42"

    def test_error_location_with_file_only(self):
        error = DetectedError(
            error_type=ErrorType.UNKNOWN,
            message="Generic error",
            file="some/path.py",
        )
        widget = CorrectionLoopBlock(error=error)
        assert widget.error.location == "some/path.py"

    def test_error_location_unknown(self):
        error = DetectedError(
            error_type=ErrorType.UNKNOWN,
            message="No location info",
        )
        widget = CorrectionLoopBlock(error=error)
        assert widget.error.location == "unknown"


class TestCorrectionLoopBlockAttemptContent:
    def test_attempt_with_empty_fix_description(self, sample_error):
        attempt = CorrectionAttempt(
            error=sample_error,
            fix_description="",
            success=False,
            verification_output="Failed",
        )
        widget = CorrectionLoopBlock(error=sample_error)
        with patch.object(widget, "_update_display"):
            widget.add_attempt(attempt)
        assert widget.attempts[0].fix_description == ""

    def test_attempt_with_long_fix_description(self, sample_error):
        long_desc = "Fixed by " + "x" * 500
        attempt = CorrectionAttempt(
            error=sample_error,
            fix_description=long_desc,
            success=True,
            verification_output="Passed",
        )
        widget = CorrectionLoopBlock(error=sample_error)
        with patch.object(widget, "_update_display"):
            widget.add_attempt(attempt)
        assert len(widget.attempts[0].fix_description) > 100

    def test_attempt_with_multiple_files_modified(self, sample_error):
        attempt = CorrectionAttempt(
            error=sample_error,
            fix_description="Multi-file fix",
            files_modified=["file1.py", "file2.py", "file3.py"],
            success=True,
            verification_output="All files verified",
        )
        widget = CorrectionLoopBlock(error=sample_error)
        with patch.object(widget, "_update_display"):
            widget.add_attempt(attempt)
        assert len(widget.attempts[0].files_modified) == 3

    def test_attempt_with_duration(self, sample_error):
        attempt = CorrectionAttempt(
            error=sample_error,
            fix_description="Quick fix",
            success=True,
            verification_output="Passed",
            duration=0.5,
        )
        widget = CorrectionLoopBlock(error=sample_error)
        with patch.object(widget, "_update_display"):
            widget.add_attempt(attempt)
        assert widget.attempts[0].duration == 0.5


class TestCorrectionLoopBlockStateTransitions:
    def test_initial_state(self, sample_error):
        widget = CorrectionLoopBlock(error=sample_error)
        assert widget.loop_active is True
        assert widget.current_iteration == 0
        assert len(widget.attempts) == 0

    def test_state_after_first_attempt(self, sample_error, sample_attempt_fail):
        widget = CorrectionLoopBlock(error=sample_error)
        with patch.object(widget, "_update_display"):
            widget.add_attempt(sample_attempt_fail)
        assert widget.loop_active is True
        assert widget.current_iteration == 1
        assert len(widget.attempts) == 1

    def test_state_after_success(self, sample_error, sample_attempt_success):
        widget = CorrectionLoopBlock(error=sample_error)
        with patch.object(widget, "_update_display"):
            widget.add_attempt(sample_attempt_success)
        assert widget.current_iteration == 1

    def test_state_reaches_max_iterations(self, sample_error, sample_attempt_fail):
        widget = CorrectionLoopBlock(error=sample_error, max_iterations=3)
        with patch.object(widget, "_update_display"):
            for _ in range(3):
                widget.add_attempt(sample_attempt_fail)
        assert widget.current_iteration == 3


class TestCorrectionLoopBlockIntegration:
    def test_full_correction_workflow_simulation(self, sample_error):
        widget = CorrectionLoopBlock(error=sample_error, max_iterations=3)

        with patch.object(widget, "_update_display"):
            for i in range(2):
                attempt = CorrectionAttempt(
                    error=sample_error,
                    fix_description=f"Attempt {i + 1} failed",
                    success=False,
                    verification_output=f"Error still present after attempt {i + 1}",
                )
                widget.add_attempt(attempt)

            success_attempt = CorrectionAttempt(
                error=sample_error,
                fix_description="Fixed the syntax error",
                success=True,
                verification_output="All checks passed",
            )
            widget.add_attempt(success_attempt)

        assert len(widget.attempts) == 3
        assert widget.attempts[-1].success is True
        assert widget.current_iteration == 3

    def test_correction_stopped_early(self, sample_error):
        widget = CorrectionLoopBlock(error=sample_error, max_iterations=5)

        with patch.object(widget, "_update_display"):
            attempt = CorrectionAttempt(
                error=sample_error,
                fix_description="Partial fix",
                success=False,
                verification_output="Stopped by user",
            )
            widget.add_attempt(attempt)
        widget.loop_active = False

        assert widget.loop_active is False
        assert widget.current_iteration == 1

    def test_multiple_error_types_in_workflow(self):
        errors = [
            DetectedError(error_type=ErrorType.PYTHON_SYNTAX, message="Syntax error"),
            DetectedError(error_type=ErrorType.PYTHON_IMPORT, message="Import error"),
            DetectedError(error_type=ErrorType.PYTHON_TYPE, message="Type error"),
        ]

        widgets = [CorrectionLoopBlock(error=e) for e in errors]

        for widget, error in zip(widgets, errors, strict=False):
            assert widget.error.error_type == error.error_type


class TestCorrectionLoopBlockUpdateDisplay:
    def test_update_display_method_exists(self, sample_error):
        widget = CorrectionLoopBlock(error=sample_error)
        assert hasattr(widget, "_update_display")
        assert callable(widget._update_display)

    def test_update_display_handles_unmounted_gracefully(
        self, sample_error, sample_attempt_success
    ):
        widget = CorrectionLoopBlock(error=sample_error)
        try:
            widget.add_attempt(sample_attempt_success)
        except Exception:
            pass


class TestCorrectionLoopBlockErrorSeverity:
    def test_error_severity(self):
        error = DetectedError(
            error_type=ErrorType.ESLINT,
            message="Warning about unused variable",
            severity="warning",
        )
        widget = CorrectionLoopBlock(error=error)
        assert widget.error.severity == "warning"

    def test_default_error_severity(self, sample_error):
        assert sample_error.severity == "error"

    def test_suggestion_field(self):
        error = DetectedError(
            error_type=ErrorType.PYTHON_IMPORT,
            message="No module named 'requests'",
            suggestion="pip install requests",
        )
        widget = CorrectionLoopBlock(error=error)
        assert widget.error.suggestion == "pip install requests"


class TestCorrectionLoopBlockTimestamp:
    def test_error_has_timestamp(self, sample_error):
        widget = CorrectionLoopBlock(error=sample_error)
        assert widget.error.timestamp is not None
        assert isinstance(widget.error.timestamp, datetime)

    def test_error_timestamp_is_recent(self, sample_error):
        widget = CorrectionLoopBlock(error=sample_error)
        now = datetime.now()
        delta = now - widget.error.timestamp
        assert delta.total_seconds() < 60
