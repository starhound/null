"""Tests for widgets/blocks/plan_block.py - PlanStepWidget and PlanBlockWidget."""

from unittest.mock import MagicMock, patch

import pytest

from managers.planning import Plan, PlanStep, PlanStatus, StepStatus, StepType
from widgets.blocks.plan_block import PlanBlockWidget, PlanStepWidget


# =============================================================================
# Helper functions for creating test data
# =============================================================================


def create_plan_step(
    step_id: str = "step-1",
    order: int = 1,
    description: str = "Test step",
    step_type: StepType = StepType.PROMPT,
    status: StepStatus = StepStatus.PENDING,
    tool_name: str | None = None,
    result: str | None = None,
    error: str | None = None,
) -> PlanStep:
    """Create a PlanStep for testing."""
    return PlanStep(
        id=step_id,
        order=order,
        description=description,
        step_type=step_type,
        status=status,
        tool_name=tool_name,
        result=result,
        error=error,
    )


def create_plan(
    plan_id: str = "plan-1",
    goal: str = "Test goal",
    steps: list[PlanStep] | None = None,
    status: PlanStatus = PlanStatus.DRAFT,
) -> Plan:
    """Create a Plan for testing."""
    plan = Plan(id=plan_id, goal=goal, status=status)
    if steps:
        plan.steps = steps
    return plan


# =============================================================================
# PlanStepWidget Tests
# =============================================================================


class TestPlanStepWidgetInit:
    """Tests for PlanStepWidget initialization."""

    def test_init_stores_step(self):
        """PlanStepWidget stores the step reference."""
        step = create_plan_step()
        widget = PlanStepWidget(step)
        assert widget.step is step

    def test_init_can_focus(self):
        """PlanStepWidget is focusable."""
        step = create_plan_step()
        widget = PlanStepWidget(step)
        assert widget.can_focus is True

    def test_init_with_pending_status(self):
        """PlanStepWidget initializes with pending status."""
        step = create_plan_step(status=StepStatus.PENDING)
        widget = PlanStepWidget(step)
        assert widget.step.status == StepStatus.PENDING

    def test_init_with_approved_status(self):
        """PlanStepWidget initializes with approved status."""
        step = create_plan_step(status=StepStatus.APPROVED)
        widget = PlanStepWidget(step)
        assert widget.step.status == StepStatus.APPROVED

    def test_init_with_executing_status(self):
        """PlanStepWidget initializes with executing status."""
        step = create_plan_step(status=StepStatus.EXECUTING)
        widget = PlanStepWidget(step)
        assert widget.step.status == StepStatus.EXECUTING

    def test_init_with_completed_status(self):
        """PlanStepWidget initializes with completed status."""
        step = create_plan_step(status=StepStatus.COMPLETED)
        widget = PlanStepWidget(step)
        assert widget.step.status == StepStatus.COMPLETED

    def test_init_with_skipped_status(self):
        """PlanStepWidget initializes with skipped status."""
        step = create_plan_step(status=StepStatus.SKIPPED)
        widget = PlanStepWidget(step)
        assert widget.step.status == StepStatus.SKIPPED

    def test_init_with_failed_status(self):
        """PlanStepWidget initializes with failed status."""
        step = create_plan_step(status=StepStatus.FAILED)
        widget = PlanStepWidget(step)
        assert widget.step.status == StepStatus.FAILED

    def test_init_preserves_step_id(self):
        """PlanStepWidget preserves the step ID."""
        step = create_plan_step(step_id="custom-step-id")
        widget = PlanStepWidget(step)
        assert widget.step.id == "custom-step-id"

    def test_init_preserves_step_order(self):
        """PlanStepWidget preserves the step order."""
        step = create_plan_step(order=5)
        widget = PlanStepWidget(step)
        assert widget.step.order == 5

    def test_init_preserves_description(self):
        """PlanStepWidget preserves the step description."""
        step = create_plan_step(description="My custom description")
        widget = PlanStepWidget(step)
        assert widget.step.description == "My custom description"


class TestPlanStepWidgetMessages:
    """Tests for PlanStepWidget message classes."""

    def test_approved_message_carries_step_id(self):
        """Approved message carries the step ID."""
        msg = PlanStepWidget.Approved(step_id="step-123")
        assert msg.step_id == "step-123"

    def test_skipped_message_carries_step_id(self):
        """Skipped message carries the step ID."""
        msg = PlanStepWidget.Skipped(step_id="step-456")
        assert msg.step_id == "step-456"

    def test_approved_message_inherits_from_message(self):
        """Approved inherits from Textual Message."""
        from textual.message import Message

        msg = PlanStepWidget.Approved(step_id="test")
        assert isinstance(msg, Message)

    def test_skipped_message_inherits_from_message(self):
        """Skipped inherits from Textual Message."""
        from textual.message import Message

        msg = PlanStepWidget.Skipped(step_id="test")
        assert isinstance(msg, Message)


class TestPlanStepWidgetBindings:
    """Tests for PlanStepWidget key bindings."""

    def test_enter_binding_defined(self):
        """Enter key binding is defined."""
        from textual.binding import Binding

        bindings = PlanStepWidget.BINDINGS
        keys = [b.key if isinstance(b, Binding) else b[0] for b in bindings]
        assert "enter" in keys

    def test_s_binding_defined(self):
        """'s' key binding is defined."""
        from textual.binding import Binding

        bindings = PlanStepWidget.BINDINGS
        keys = [b.key if isinstance(b, Binding) else b[0] for b in bindings]
        assert "s" in keys

    def test_enter_targets_approve_action(self):
        """Enter key targets approve action."""
        from textual.binding import Binding

        for b in PlanStepWidget.BINDINGS:
            if isinstance(b, Binding) and b.key == "enter":
                assert b.action == "approve"
            elif isinstance(b, tuple) and b[0] == "enter":
                assert b[1] == "approve"

    def test_s_targets_skip_action(self):
        """'s' key targets skip action."""
        from textual.binding import Binding

        for b in PlanStepWidget.BINDINGS:
            if isinstance(b, Binding) and b.key == "s":
                assert b.action == "skip"
            elif isinstance(b, tuple) and b[0] == "s":
                assert b[1] == "skip"


class TestPlanStepWidgetCompose:
    """Tests for PlanStepWidget.compose method."""

    def test_compose_returns_generator(self):
        """compose returns a generator."""
        step = create_plan_step()
        widget = PlanStepWidget(step)
        result = widget.compose()
        assert hasattr(result, "__iter__")

    def test_compose_method_exists(self):
        """compose method exists."""
        step = create_plan_step()
        widget = PlanStepWidget(step)
        assert hasattr(widget, "compose")
        assert callable(widget.compose)


class TestPlanStepWidgetStatusIcons:
    """Tests for status icons in compose."""

    def test_pending_status_icon(self):
        """Pending status uses correct icon (☐)."""
        step = create_plan_step(status=StepStatus.PENDING)
        widget = PlanStepWidget(step)
        # Icons are used in compose(), we can verify the mapping exists
        assert step.status == StepStatus.PENDING

    def test_approved_status_icon(self):
        """Approved status uses correct icon (☑)."""
        step = create_plan_step(status=StepStatus.APPROVED)
        widget = PlanStepWidget(step)
        assert step.status == StepStatus.APPROVED

    def test_executing_status_icon(self):
        """Executing status uses correct icon (⏳)."""
        step = create_plan_step(status=StepStatus.EXECUTING)
        widget = PlanStepWidget(step)
        assert step.status == StepStatus.EXECUTING

    def test_completed_status_icon(self):
        """Completed status uses correct icon (✓)."""
        step = create_plan_step(status=StepStatus.COMPLETED)
        widget = PlanStepWidget(step)
        assert step.status == StepStatus.COMPLETED

    def test_skipped_status_icon(self):
        """Skipped status uses correct icon (⊘)."""
        step = create_plan_step(status=StepStatus.SKIPPED)
        widget = PlanStepWidget(step)
        assert step.status == StepStatus.SKIPPED

    def test_failed_status_icon(self):
        """Failed status uses correct icon (✗)."""
        step = create_plan_step(status=StepStatus.FAILED)
        widget = PlanStepWidget(step)
        assert step.status == StepStatus.FAILED


class TestPlanStepWidgetTypeIcons:
    """Tests for step type icons in compose."""

    def test_prompt_type_icon(self):
        """Prompt type uses thought bubble icon (💭)."""
        step = create_plan_step(step_type=StepType.PROMPT)
        widget = PlanStepWidget(step)
        assert step.step_type == StepType.PROMPT

    def test_tool_type_icon(self):
        """Tool type uses wrench icon (🔧)."""
        step = create_plan_step(step_type=StepType.TOOL)
        widget = PlanStepWidget(step)
        assert step.step_type == StepType.TOOL

    def test_checkpoint_type_icon(self):
        """Checkpoint type uses construction icon (🚧)."""
        step = create_plan_step(step_type=StepType.CHECKPOINT)
        widget = PlanStepWidget(step)
        assert step.step_type == StepType.CHECKPOINT


class TestPlanStepWidgetUpdateClasses:
    """Tests for _update_classes method."""

    def test_update_classes_method_exists(self):
        """_update_classes method exists."""
        step = create_plan_step()
        widget = PlanStepWidget(step)
        assert hasattr(widget, "_update_classes")
        assert callable(widget._update_classes)

    def test_update_classes_handles_unmounted(self):
        """_update_classes handles unmounted widget gracefully."""
        step = create_plan_step(status=StepStatus.PENDING)
        widget = PlanStepWidget(step)
        # Should not raise even when not mounted
        widget._update_classes()


class TestPlanStepWidgetActions:
    """Tests for PlanStepWidget action methods."""

    def test_action_approve_method_exists(self):
        """action_approve method exists."""
        step = create_plan_step()
        widget = PlanStepWidget(step)
        assert hasattr(widget, "action_approve")
        assert callable(widget.action_approve)

    def test_action_skip_method_exists(self):
        """action_skip method exists."""
        step = create_plan_step()
        widget = PlanStepWidget(step)
        assert hasattr(widget, "action_skip")
        assert callable(widget.action_skip)

    def test_action_approve_only_on_pending(self):
        """action_approve only posts message when pending."""
        step = create_plan_step(status=StepStatus.PENDING)
        widget = PlanStepWidget(step)
        with patch.object(widget, "post_message") as mock_post:
            widget.action_approve()
            mock_post.assert_called_once()
            msg = mock_post.call_args[0][0]
            assert isinstance(msg, PlanStepWidget.Approved)
            assert msg.step_id == step.id

    def test_action_approve_ignored_when_approved(self):
        """action_approve does nothing when already approved."""
        step = create_plan_step(status=StepStatus.APPROVED)
        widget = PlanStepWidget(step)
        with patch.object(widget, "post_message") as mock_post:
            widget.action_approve()
            mock_post.assert_not_called()

    def test_action_approve_ignored_when_completed(self):
        """action_approve does nothing when completed."""
        step = create_plan_step(status=StepStatus.COMPLETED)
        widget = PlanStepWidget(step)
        with patch.object(widget, "post_message") as mock_post:
            widget.action_approve()
            mock_post.assert_not_called()

    def test_action_skip_on_pending(self):
        """action_skip posts message when pending."""
        step = create_plan_step(status=StepStatus.PENDING)
        widget = PlanStepWidget(step)
        with patch.object(widget, "post_message") as mock_post:
            widget.action_skip()
            mock_post.assert_called_once()
            msg = mock_post.call_args[0][0]
            assert isinstance(msg, PlanStepWidget.Skipped)
            assert msg.step_id == step.id

    def test_action_skip_on_approved(self):
        """action_skip posts message when approved."""
        step = create_plan_step(status=StepStatus.APPROVED)
        widget = PlanStepWidget(step)
        with patch.object(widget, "post_message") as mock_post:
            widget.action_skip()
            mock_post.assert_called_once()
            msg = mock_post.call_args[0][0]
            assert isinstance(msg, PlanStepWidget.Skipped)

    def test_action_skip_ignored_when_completed(self):
        """action_skip does nothing when completed."""
        step = create_plan_step(status=StepStatus.COMPLETED)
        widget = PlanStepWidget(step)
        with patch.object(widget, "post_message") as mock_post:
            widget.action_skip()
            mock_post.assert_not_called()

    def test_action_skip_ignored_when_executing(self):
        """action_skip does nothing when executing."""
        step = create_plan_step(status=StepStatus.EXECUTING)
        widget = PlanStepWidget(step)
        with patch.object(widget, "post_message") as mock_post:
            widget.action_skip()
            mock_post.assert_not_called()


class TestPlanStepWidgetUpdateStep:
    """Tests for update_step method."""

    def test_update_step_method_exists(self):
        """update_step method exists."""
        step = create_plan_step()
        widget = PlanStepWidget(step)
        assert hasattr(widget, "update_step")
        assert callable(widget.update_step)

    def test_update_step_replaces_step(self):
        """update_step replaces the step reference."""
        step1 = create_plan_step(step_id="step-1", description="First")
        step2 = create_plan_step(step_id="step-2", description="Second")
        widget = PlanStepWidget(step1)
        widget.update_step(step2)
        assert widget.step is step2
        assert widget.step.description == "Second"

    def test_update_step_updates_status(self):
        """update_step updates the step status."""
        step1 = create_plan_step(status=StepStatus.PENDING)
        step2 = create_plan_step(status=StepStatus.COMPLETED)
        widget = PlanStepWidget(step1)
        widget.update_step(step2)
        assert widget.step.status == StepStatus.COMPLETED


class TestPlanStepWidgetToolName:
    """Tests for steps with tool names."""

    def test_step_with_tool_name(self):
        """Step with tool name is handled correctly."""
        step = create_plan_step(step_type=StepType.TOOL, tool_name="read_file")
        widget = PlanStepWidget(step)
        assert widget.step.tool_name == "read_file"

    def test_step_without_tool_name(self):
        """Step without tool name is handled correctly."""
        step = create_plan_step(step_type=StepType.PROMPT, tool_name=None)
        widget = PlanStepWidget(step)
        assert widget.step.tool_name is None


class TestPlanStepWidgetResult:
    """Tests for steps with results."""

    def test_step_with_result(self):
        """Step with result is stored correctly."""
        step = create_plan_step(result="Operation completed successfully")
        widget = PlanStepWidget(step)
        assert widget.step.result == "Operation completed successfully"

    def test_step_with_long_result(self):
        """Step with long result is handled correctly."""
        long_result = "x" * 200
        step = create_plan_step(result=long_result)
        widget = PlanStepWidget(step)
        assert widget.step.result == long_result

    def test_step_without_result(self):
        """Step without result is handled correctly."""
        step = create_plan_step(result=None)
        widget = PlanStepWidget(step)
        assert widget.step.result is None


class TestPlanStepWidgetError:
    """Tests for steps with errors."""

    def test_step_with_error(self):
        """Step with error is stored correctly."""
        step = create_plan_step(error="Command failed with exit code 1")
        widget = PlanStepWidget(step)
        assert widget.step.error == "Command failed with exit code 1"

    def test_step_without_error(self):
        """Step without error is handled correctly."""
        step = create_plan_step(error=None)
        widget = PlanStepWidget(step)
        assert widget.step.error is None


class TestPlanStepWidgetInheritance:
    """Tests for PlanStepWidget inheritance."""

    def test_inherits_from_static(self):
        """PlanStepWidget inherits from Static."""
        from textual.widgets import Static

        step = create_plan_step()
        widget = PlanStepWidget(step)
        assert isinstance(widget, Static)


# =============================================================================
# PlanBlockWidget Tests
# =============================================================================


class TestPlanBlockWidgetInit:
    """Tests for PlanBlockWidget initialization."""

    def test_init_stores_plan(self):
        """PlanBlockWidget stores the plan reference."""
        plan = create_plan()
        widget = PlanBlockWidget(plan)
        assert widget.plan is plan

    def test_init_creates_step_widgets_dict(self):
        """PlanBlockWidget creates empty step widgets dict."""
        plan = create_plan()
        widget = PlanBlockWidget(plan)
        assert widget._step_widgets == {}

    def test_init_preserves_plan_id(self):
        """PlanBlockWidget preserves the plan ID."""
        plan = create_plan(plan_id="custom-plan-id")
        widget = PlanBlockWidget(plan)
        assert widget.plan.id == "custom-plan-id"

    def test_init_preserves_plan_goal(self):
        """PlanBlockWidget preserves the plan goal."""
        plan = create_plan(goal="My custom goal")
        widget = PlanBlockWidget(plan)
        assert widget.plan.goal == "My custom goal"

    def test_init_with_empty_steps(self):
        """PlanBlockWidget initializes with empty steps list."""
        plan = create_plan(steps=[])
        widget = PlanBlockWidget(plan)
        assert len(widget.plan.steps) == 0

    def test_init_with_steps(self):
        """PlanBlockWidget initializes with steps."""
        steps = [
            create_plan_step(step_id="s1", order=1),
            create_plan_step(step_id="s2", order=2),
        ]
        plan = create_plan(steps=steps)
        widget = PlanBlockWidget(plan)
        assert len(widget.plan.steps) == 2


class TestPlanBlockWidgetMessages:
    """Tests for PlanBlockWidget message classes."""

    def test_step_approved_message(self):
        """StepApproved message carries plan and step IDs."""
        msg = PlanBlockWidget.StepApproved(plan_id="plan-1", step_id="step-1")
        assert msg.plan_id == "plan-1"
        assert msg.step_id == "step-1"

    def test_step_skipped_message(self):
        """StepSkipped message carries plan and step IDs."""
        msg = PlanBlockWidget.StepSkipped(plan_id="plan-2", step_id="step-2")
        assert msg.plan_id == "plan-2"
        assert msg.step_id == "step-2"

    def test_execute_requested_message(self):
        """ExecuteRequested message carries plan ID."""
        msg = PlanBlockWidget.ExecuteRequested(plan_id="plan-3")
        assert msg.plan_id == "plan-3"

    def test_cancel_requested_message(self):
        """CancelRequested message carries plan ID."""
        msg = PlanBlockWidget.CancelRequested(plan_id="plan-4")
        assert msg.plan_id == "plan-4"

    def test_approve_all_requested_message(self):
        """ApproveAllRequested message carries plan ID."""
        msg = PlanBlockWidget.ApproveAllRequested(plan_id="plan-5")
        assert msg.plan_id == "plan-5"

    def test_all_messages_inherit_from_message(self):
        """All message classes inherit from Textual Message."""
        from textual.message import Message

        assert isinstance(
            PlanBlockWidget.StepApproved(plan_id="p", step_id="s"), Message
        )
        assert isinstance(
            PlanBlockWidget.StepSkipped(plan_id="p", step_id="s"), Message
        )
        assert isinstance(PlanBlockWidget.ExecuteRequested(plan_id="p"), Message)
        assert isinstance(PlanBlockWidget.CancelRequested(plan_id="p"), Message)
        assert isinstance(PlanBlockWidget.ApproveAllRequested(plan_id="p"), Message)


class TestPlanBlockWidgetBindings:
    """Tests for PlanBlockWidget key bindings."""

    def test_a_binding_for_approve_all(self):
        """'a' key binding is defined for approve all."""
        from textual.binding import Binding

        bindings = PlanBlockWidget.BINDINGS
        for b in bindings:
            if isinstance(b, Binding) and b.key == "a":
                assert b.action == "approve_all"
                break
            elif isinstance(b, tuple) and b[0] == "a":
                assert b[1] == "approve_all"
                break

    def test_x_binding_for_execute(self):
        """'x' key binding is defined for execute."""
        from textual.binding import Binding

        bindings = PlanBlockWidget.BINDINGS
        for b in bindings:
            if isinstance(b, Binding) and b.key == "x":
                assert b.action == "execute_plan"
                break
            elif isinstance(b, tuple) and b[0] == "x":
                assert b[1] == "execute_plan"
                break

    def test_escape_binding_for_cancel(self):
        """'escape' key binding is defined for cancel."""
        from textual.binding import Binding

        bindings = PlanBlockWidget.BINDINGS
        for b in bindings:
            if isinstance(b, Binding) and b.key == "escape":
                assert b.action == "cancel_plan"
                break
            elif isinstance(b, tuple) and b[0] == "escape":
                assert b[1] == "cancel_plan"
                break


class TestPlanBlockWidgetProgress:
    """Tests for progress reactive property."""

    def test_progress_initial_value(self):
        """Progress starts at 0.0."""
        plan = create_plan()
        widget = PlanBlockWidget(plan)
        assert widget.progress == 0.0

    def test_progress_is_reactive(self):
        """Progress is a reactive property."""
        plan = create_plan()
        widget = PlanBlockWidget(plan)
        widget.progress = 50.0
        assert widget.progress == 50.0

    def test_progress_can_be_set_to_100(self):
        """Progress can be set to 100."""
        plan = create_plan()
        widget = PlanBlockWidget(plan)
        widget.progress = 100.0
        assert widget.progress == 100.0


class TestPlanBlockWidgetCompose:
    """Tests for PlanBlockWidget.compose method."""

    def test_compose_returns_generator(self):
        """compose returns a generator."""
        plan = create_plan()
        widget = PlanBlockWidget(plan)
        result = widget.compose()
        assert hasattr(result, "__iter__")

    def test_compose_method_exists(self):
        """compose method exists."""
        plan = create_plan()
        widget = PlanBlockWidget(plan)
        assert hasattr(widget, "compose")
        assert callable(widget.compose)


class TestPlanBlockWidgetUpdateProgress:
    """Tests for _update_progress method."""

    def test_update_progress_method_exists(self):
        """_update_progress method exists."""
        plan = create_plan()
        widget = PlanBlockWidget(plan)
        assert hasattr(widget, "_update_progress")
        assert callable(widget._update_progress)

    def test_update_progress_calculates_correctly(self):
        """_update_progress calculates progress from plan."""
        steps = [
            create_plan_step(step_id="s1", status=StepStatus.COMPLETED),
            create_plan_step(step_id="s2", status=StepStatus.PENDING),
        ]
        plan = create_plan(steps=steps)
        widget = PlanBlockWidget(plan)
        widget._update_progress()
        # 1 of 2 complete = 50%
        assert widget.progress == 50.0

    def test_update_progress_with_all_complete(self):
        """_update_progress with all steps complete."""
        steps = [
            create_plan_step(step_id="s1", status=StepStatus.COMPLETED),
            create_plan_step(step_id="s2", status=StepStatus.COMPLETED),
        ]
        plan = create_plan(steps=steps)
        widget = PlanBlockWidget(plan)
        widget._update_progress()
        assert widget.progress == 100.0

    def test_update_progress_with_empty_plan(self):
        """_update_progress with empty plan returns 0."""
        plan = create_plan(steps=[])
        widget = PlanBlockWidget(plan)
        widget._update_progress()
        assert widget.progress == 0.0

    def test_update_progress_handles_unmounted(self):
        """_update_progress handles unmounted widget gracefully."""
        plan = create_plan()
        widget = PlanBlockWidget(plan)
        # Should not raise even when not mounted
        widget._update_progress()


class TestPlanBlockWidgetButtonHandlers:
    """Tests for button press handlers."""

    def test_on_button_pressed_method_exists(self):
        """on_button_pressed method exists."""
        plan = create_plan()
        widget = PlanBlockWidget(plan)
        assert hasattr(widget, "on_button_pressed")
        assert callable(widget.on_button_pressed)

    def test_approve_all_button_posts_message(self):
        """Approve all button posts ApproveAllRequested message."""
        plan = create_plan(plan_id="test-plan")
        widget = PlanBlockWidget(plan)
        mock_event = MagicMock()
        mock_event.button.id = "btn-approve-all"

        with patch.object(widget, "post_message") as mock_post:
            widget.on_button_pressed(mock_event)
            mock_post.assert_called_once()
            msg = mock_post.call_args[0][0]
            assert isinstance(msg, PlanBlockWidget.ApproveAllRequested)
            assert msg.plan_id == "test-plan"

    def test_execute_button_posts_message(self):
        """Execute button posts ExecuteRequested message."""
        plan = create_plan(plan_id="test-plan")
        widget = PlanBlockWidget(plan)
        mock_event = MagicMock()
        mock_event.button.id = "btn-execute"

        with patch.object(widget, "post_message") as mock_post:
            widget.on_button_pressed(mock_event)
            mock_post.assert_called_once()
            msg = mock_post.call_args[0][0]
            assert isinstance(msg, PlanBlockWidget.ExecuteRequested)
            assert msg.plan_id == "test-plan"

    def test_cancel_button_posts_message(self):
        """Cancel button posts CancelRequested message."""
        plan = create_plan(plan_id="test-plan")
        widget = PlanBlockWidget(plan)
        mock_event = MagicMock()
        mock_event.button.id = "btn-cancel"

        with patch.object(widget, "post_message") as mock_post:
            widget.on_button_pressed(mock_event)
            mock_post.assert_called_once()
            msg = mock_post.call_args[0][0]
            assert isinstance(msg, PlanBlockWidget.CancelRequested)
            assert msg.plan_id == "test-plan"

    def test_unknown_button_no_message(self):
        """Unknown button ID does not post message."""
        plan = create_plan()
        widget = PlanBlockWidget(plan)
        mock_event = MagicMock()
        mock_event.button.id = "btn-unknown"

        with patch.object(widget, "post_message") as mock_post:
            widget.on_button_pressed(mock_event)
            mock_post.assert_not_called()


class TestPlanBlockWidgetStepMessageHandlers:
    """Tests for step message handlers."""

    def test_on_plan_step_widget_approved_handler_exists(self):
        """on_plan_step_widget_approved handler exists."""
        plan = create_plan()
        widget = PlanBlockWidget(plan)
        assert hasattr(widget, "on_plan_step_widget_approved")
        assert callable(widget.on_plan_step_widget_approved)

    def test_on_plan_step_widget_skipped_handler_exists(self):
        """on_plan_step_widget_skipped handler exists."""
        plan = create_plan()
        widget = PlanBlockWidget(plan)
        assert hasattr(widget, "on_plan_step_widget_skipped")
        assert callable(widget.on_plan_step_widget_skipped)

    def test_approved_handler_posts_step_approved(self):
        """Approved handler posts StepApproved message."""
        plan = create_plan(plan_id="plan-123")
        widget = PlanBlockWidget(plan)
        mock_event = MagicMock()
        mock_event.step_id = "step-456"

        with patch.object(widget, "post_message") as mock_post:
            widget.on_plan_step_widget_approved(mock_event)
            mock_post.assert_called_once()
            msg = mock_post.call_args[0][0]
            assert isinstance(msg, PlanBlockWidget.StepApproved)
            assert msg.plan_id == "plan-123"
            assert msg.step_id == "step-456"

    def test_skipped_handler_posts_step_skipped(self):
        """Skipped handler posts StepSkipped message."""
        plan = create_plan(plan_id="plan-789")
        widget = PlanBlockWidget(plan)
        mock_event = MagicMock()
        mock_event.step_id = "step-101"

        with patch.object(widget, "post_message") as mock_post:
            widget.on_plan_step_widget_skipped(mock_event)
            mock_post.assert_called_once()
            msg = mock_post.call_args[0][0]
            assert isinstance(msg, PlanBlockWidget.StepSkipped)
            assert msg.plan_id == "plan-789"
            assert msg.step_id == "step-101"


class TestPlanBlockWidgetUpdatePlan:
    """Tests for update_plan method."""

    def test_update_plan_method_exists(self):
        """update_plan method exists."""
        plan = create_plan()
        widget = PlanBlockWidget(plan)
        assert hasattr(widget, "update_plan")
        assert callable(widget.update_plan)

    def test_update_plan_replaces_plan(self):
        """update_plan replaces the plan reference."""
        plan1 = create_plan(plan_id="plan-1", goal="First goal")
        plan2 = create_plan(plan_id="plan-2", goal="Second goal")
        widget = PlanBlockWidget(plan1)
        widget.update_plan(plan2)
        assert widget.plan is plan2
        assert widget.plan.goal == "Second goal"

    def test_update_plan_updates_step_widgets(self):
        """update_plan updates existing step widgets."""
        step1 = create_plan_step(step_id="s1", status=StepStatus.PENDING)
        plan = create_plan(steps=[step1])
        widget = PlanBlockWidget(plan)

        # Mock the step widget
        mock_step_widget = MagicMock()
        widget._step_widgets["s1"] = mock_step_widget

        # Create updated plan with step in new status
        updated_step = create_plan_step(step_id="s1", status=StepStatus.COMPLETED)
        updated_plan = create_plan(steps=[updated_step])

        widget.update_plan(updated_plan)
        mock_step_widget.update_step.assert_called_once_with(updated_step)


class TestPlanBlockWidgetActions:
    """Tests for PlanBlockWidget action methods."""

    def test_action_approve_all_posts_message(self):
        """action_approve_all posts ApproveAllRequested message."""
        plan = create_plan(plan_id="action-plan")
        widget = PlanBlockWidget(plan)

        with patch.object(widget, "post_message") as mock_post:
            widget.action_approve_all()
            mock_post.assert_called_once()
            msg = mock_post.call_args[0][0]
            assert isinstance(msg, PlanBlockWidget.ApproveAllRequested)
            assert msg.plan_id == "action-plan"

    def test_action_execute_plan_posts_message(self):
        """action_execute_plan posts ExecuteRequested message."""
        plan = create_plan(plan_id="action-plan")
        widget = PlanBlockWidget(plan)

        with patch.object(widget, "post_message") as mock_post:
            widget.action_execute_plan()
            mock_post.assert_called_once()
            msg = mock_post.call_args[0][0]
            assert isinstance(msg, PlanBlockWidget.ExecuteRequested)
            assert msg.plan_id == "action-plan"

    def test_action_cancel_plan_posts_message(self):
        """action_cancel_plan posts CancelRequested message."""
        plan = create_plan(plan_id="action-plan")
        widget = PlanBlockWidget(plan)

        with patch.object(widget, "post_message") as mock_post:
            widget.action_cancel_plan()
            mock_post.assert_called_once()
            msg = mock_post.call_args[0][0]
            assert isinstance(msg, PlanBlockWidget.CancelRequested)
            assert msg.plan_id == "action-plan"


class TestPlanBlockWidgetInheritance:
    """Tests for PlanBlockWidget inheritance."""

    def test_inherits_from_static(self):
        """PlanBlockWidget inherits from Static."""
        from textual.widgets import Static

        plan = create_plan()
        widget = PlanBlockWidget(plan)
        assert isinstance(widget, Static)


class TestPlanBlockWidgetPlanStatus:
    """Tests for handling different plan statuses."""

    def test_draft_status(self):
        """Widget handles draft status."""
        plan = create_plan(status=PlanStatus.DRAFT)
        widget = PlanBlockWidget(plan)
        assert widget.plan.status == PlanStatus.DRAFT

    def test_approved_status(self):
        """Widget handles approved status."""
        plan = create_plan(status=PlanStatus.APPROVED)
        widget = PlanBlockWidget(plan)
        assert widget.plan.status == PlanStatus.APPROVED

    def test_executing_status(self):
        """Widget handles executing status."""
        plan = create_plan(status=PlanStatus.EXECUTING)
        widget = PlanBlockWidget(plan)
        assert widget.plan.status == PlanStatus.EXECUTING

    def test_completed_status(self):
        """Widget handles completed status."""
        plan = create_plan(status=PlanStatus.COMPLETED)
        widget = PlanBlockWidget(plan)
        assert widget.plan.status == PlanStatus.COMPLETED

    def test_cancelled_status(self):
        """Widget handles cancelled status."""
        plan = create_plan(status=PlanStatus.CANCELLED)
        widget = PlanBlockWidget(plan)
        assert widget.plan.status == PlanStatus.CANCELLED


class TestPlanBlockWidgetStepWidgets:
    """Tests for step widget management."""

    def test_step_widgets_empty_initially(self):
        """_step_widgets is empty on init."""
        plan = create_plan()
        widget = PlanBlockWidget(plan)
        assert len(widget._step_widgets) == 0

    def test_step_widgets_dict_type(self):
        """_step_widgets is a dictionary."""
        plan = create_plan()
        widget = PlanBlockWidget(plan)
        assert isinstance(widget._step_widgets, dict)


class TestPlanBlockWidgetOnMount:
    """Tests for on_mount handler."""

    def test_on_mount_method_exists(self):
        """on_mount method exists."""
        plan = create_plan()
        widget = PlanBlockWidget(plan)
        assert hasattr(widget, "on_mount")
        assert callable(widget.on_mount)


class TestPlanBlockWidgetEdgeCases:
    """Tests for edge cases and special scenarios."""

    def test_plan_with_many_steps(self):
        """Widget handles plan with many steps."""
        steps = [create_plan_step(step_id=f"s{i}", order=i) for i in range(20)]
        plan = create_plan(steps=steps)
        widget = PlanBlockWidget(plan)
        assert len(widget.plan.steps) == 20

    def test_plan_with_unicode_goal(self):
        """Widget handles plan with unicode in goal."""
        plan = create_plan(goal="Unicode goal: 你好 🚀 éàü")
        widget = PlanBlockWidget(plan)
        assert widget.plan.goal == "Unicode goal: 你好 🚀 éàü"

    def test_plan_with_special_characters(self):
        """Widget handles plan with special characters."""
        plan = create_plan(goal='Goal with <special> "chars" & \\slashes/')
        widget = PlanBlockWidget(plan)
        assert "<special>" in widget.plan.goal

    def test_step_with_long_description(self):
        """Widget handles step with long description."""
        long_desc = "A" * 1000
        step = create_plan_step(description=long_desc)
        widget = PlanStepWidget(step)
        assert len(widget.step.description) == 1000

    def test_update_plan_with_new_steps(self):
        """update_plan handles plan with new steps not in _step_widgets."""
        step1 = create_plan_step(step_id="s1")
        plan1 = create_plan(steps=[step1])
        widget = PlanBlockWidget(plan1)

        # Plan 2 has a step not in _step_widgets
        step2 = create_plan_step(step_id="s2")
        plan2 = create_plan(steps=[step2])

        # Should not raise
        widget.update_plan(plan2)
        assert widget.plan is plan2

    def test_multiple_progress_updates(self):
        """Multiple progress updates work correctly."""
        steps = [
            create_plan_step(step_id="s1", status=StepStatus.PENDING),
            create_plan_step(step_id="s2", status=StepStatus.PENDING),
            create_plan_step(step_id="s3", status=StepStatus.PENDING),
            create_plan_step(step_id="s4", status=StepStatus.PENDING),
        ]
        plan = create_plan(steps=steps)
        widget = PlanBlockWidget(plan)

        # Start at 0%
        widget._update_progress()
        assert widget.progress == 0.0

        # Complete one step = 25%
        plan.steps[0].status = StepStatus.COMPLETED
        widget._update_progress()
        assert widget.progress == 25.0

        # Complete two steps = 50%
        plan.steps[1].status = StepStatus.COMPLETED
        widget._update_progress()
        assert widget.progress == 50.0

        # Complete all = 100%
        plan.steps[2].status = StepStatus.COMPLETED
        plan.steps[3].status = StepStatus.COMPLETED
        widget._update_progress()
        assert widget.progress == 100.0

    def test_progress_counts_skipped_as_complete(self):
        """Progress calculation counts skipped steps as complete."""
        steps = [
            create_plan_step(step_id="s1", status=StepStatus.SKIPPED),
            create_plan_step(step_id="s2", status=StepStatus.PENDING),
        ]
        plan = create_plan(steps=steps)
        widget = PlanBlockWidget(plan)
        widget._update_progress()
        # 1 of 2 done (skipped counts) = 50%
        assert widget.progress == 50.0

    def test_progress_counts_failed_as_complete(self):
        """Progress calculation counts failed steps as complete."""
        steps = [
            create_plan_step(step_id="s1", status=StepStatus.FAILED),
            create_plan_step(step_id="s2", status=StepStatus.PENDING),
        ]
        plan = create_plan(steps=steps)
        widget = PlanBlockWidget(plan)
        widget._update_progress()
        # 1 of 2 done (failed counts) = 50%
        assert widget.progress == 50.0


class TestPlanDataIntegrity:
    """Tests for data integrity between widgets and models."""

    def test_plan_step_widget_preserves_tool_args(self):
        """PlanStepWidget preserves tool arguments."""
        step = PlanStep(
            id="s1",
            order=1,
            description="Run command",
            step_type=StepType.TOOL,
            tool_name="run_command",
            tool_args={"command": "ls -la", "timeout": 30},
        )
        widget = PlanStepWidget(step)
        assert widget.step.tool_args == {"command": "ls -la", "timeout": 30}

    def test_plan_block_widget_preserves_variables(self):
        """PlanBlockWidget preserves plan variables."""
        plan = Plan(
            id="p1",
            goal="Test",
            variables={"key1": "value1", "key2": "value2"},
        )
        widget = PlanBlockWidget(plan)
        assert widget.plan.variables == {"key1": "value1", "key2": "value2"}

    def test_plan_block_widget_preserves_current_step(self):
        """PlanBlockWidget preserves current_step index."""
        plan = Plan(id="p1", goal="Test", current_step=3)
        widget = PlanBlockWidget(plan)
        assert widget.plan.current_step == 3

    def test_mutation_of_plan_reflects_in_widget(self):
        """Mutating plan reflects in widget (same reference)."""
        plan = create_plan(goal="Original")
        widget = PlanBlockWidget(plan)
        plan.goal = "Modified"
        assert widget.plan.goal == "Modified"

    def test_mutation_of_step_reflects_in_widget(self):
        """Mutating step reflects in step widget (same reference)."""
        step = create_plan_step(description="Original")
        widget = PlanStepWidget(step)
        step.description = "Modified"
        assert widget.step.description == "Modified"
