"""Plan block widget for displaying and managing AI-generated plans."""

from typing import ClassVar

from textual.app import ComposeResult
from textual.binding import Binding, BindingType
from textual.containers import Horizontal, Vertical
from textual.message import Message
from textual.reactive import reactive
from textual.widgets import Button, Label, ProgressBar, Static

from managers.planning import Plan, PlanStep, StepStatus, StepType


class PlanStepWidget(Static):
    """Widget for a single plan step."""

    BINDINGS: ClassVar[list[BindingType]] = [
        Binding("enter", "approve", "Approve", show=False),
        Binding("s", "skip", "Skip", show=False),
    ]

    class Approved(Message):
        def __init__(self, step_id: str):
            self.step_id = step_id
            super().__init__()

    class Skipped(Message):
        def __init__(self, step_id: str):
            self.step_id = step_id
            super().__init__()

    def __init__(self, step: PlanStep):
        super().__init__()
        self.step = step
        self.can_focus = True

    def compose(self) -> ComposeResult:
        status_icons = {
            StepStatus.PENDING: "☐",
            StepStatus.APPROVED: "☑",
            StepStatus.EXECUTING: "⏳",
            StepStatus.COMPLETED: "✓",
            StepStatus.SKIPPED: "⊘",
            StepStatus.FAILED: "✗",
        }
        type_icons = {
            StepType.PROMPT: "💭",
            StepType.TOOL: "🔧",
            StepType.CHECKPOINT: "🚧",
        }

        icon = status_icons.get(self.step.status, "☐")
        type_icon = type_icons.get(self.step.step_type, "")

        with Horizontal(classes="plan-step-row"):
            yield Label(f"{icon} {self.step.order}.", classes="step-number")
            yield Label(
                f"{type_icon} {self.step.description}", classes="step-description"
            )

        if self.step.tool_name:
            yield Label(f"    └─ {self.step.tool_name}", classes="step-tool")

        if self.step.result:
            yield Label(
                f"    Result: {self.step.result[:100]}...", classes="step-result"
            )

        if self.step.error:
            yield Label(f"    Error: {self.step.error}", classes="step-error")

    def on_mount(self) -> None:
        self._update_classes()

    def _update_classes(self) -> None:
        status_classes = [
            "step-pending",
            "step-approved",
            "step-executing",
            "step-completed",
            "step-skipped",
            "step-failed",
        ]
        for cls in status_classes:
            self.remove_class(cls)
        self.add_class(f"step-{self.step.status.value}")

    def action_approve(self) -> None:
        if self.step.status == StepStatus.PENDING:
            self.post_message(self.Approved(self.step.id))

    def action_skip(self) -> None:
        if self.step.status in (StepStatus.PENDING, StepStatus.APPROVED):
            self.post_message(self.Skipped(self.step.id))

    def update_step(self, step: PlanStep) -> None:
        self.step = step
        self._update_classes()
        self.refresh()


class PlanBlockWidget(Static):
    """Widget for displaying and interacting with an AI-generated plan."""

    BINDINGS: ClassVar[list[BindingType]] = [
        Binding("a", "approve_all", "Approve All", show=True),
        Binding("x", "execute_plan", "Execute", show=True),
        Binding("escape", "cancel_plan", "Cancel", show=True),
    ]

    class StepApproved(Message):
        def __init__(self, plan_id: str, step_id: str):
            self.plan_id = plan_id
            self.step_id = step_id
            super().__init__()

    class StepSkipped(Message):
        def __init__(self, plan_id: str, step_id: str):
            self.plan_id = plan_id
            self.step_id = step_id
            super().__init__()

    class ExecuteRequested(Message):
        def __init__(self, plan_id: str):
            self.plan_id = plan_id
            super().__init__()

    class CancelRequested(Message):
        def __init__(self, plan_id: str):
            self.plan_id = plan_id
            super().__init__()

    class ApproveAllRequested(Message):
        def __init__(self, plan_id: str):
            self.plan_id = plan_id
            super().__init__()

    progress = reactive(0.0)

    def __init__(self, plan: Plan):
        super().__init__()
        self.plan = plan
        self._step_widgets: dict[str, PlanStepWidget] = {}

    def compose(self) -> ComposeResult:
        yield Label(f"📋 Plan: {self.plan.goal}", classes="plan-title")
        yield ProgressBar(total=100, show_eta=False, classes="plan-progress")

        with Vertical(classes="plan-steps"):
            for step in self.plan.steps:
                widget = PlanStepWidget(step)
                self._step_widgets[step.id] = widget
                yield widget

        with Horizontal(classes="plan-actions"):
            yield Button("Approve All", id="btn-approve-all", variant="primary")
            yield Button("Execute", id="btn-execute", variant="success")
            yield Button("Cancel", id="btn-cancel", variant="error")

    def on_mount(self) -> None:
        self.add_class("plan-block")
        self._update_progress()

    def _update_progress(self) -> None:
        self.progress = self.plan.progress * 100
        try:
            progress_bar = self.query_one(ProgressBar)
            progress_bar.progress = self.progress
        except Exception:
            pass

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-approve-all":
            self.post_message(self.ApproveAllRequested(self.plan.id))
        elif event.button.id == "btn-execute":
            self.post_message(self.ExecuteRequested(self.plan.id))
        elif event.button.id == "btn-cancel":
            self.post_message(self.CancelRequested(self.plan.id))

    def on_plan_step_widget_approved(self, event: PlanStepWidget.Approved) -> None:
        self.post_message(self.StepApproved(self.plan.id, event.step_id))

    def on_plan_step_widget_skipped(self, event: PlanStepWidget.Skipped) -> None:
        self.post_message(self.StepSkipped(self.plan.id, event.step_id))

    def update_plan(self, plan: Plan) -> None:
        self.plan = plan
        for step in plan.steps:
            if step.id in self._step_widgets:
                self._step_widgets[step.id].update_step(step)
        self._update_progress()

    def action_approve_all(self) -> None:
        self.post_message(self.ApproveAllRequested(self.plan.id))

    def action_execute_plan(self) -> None:
        self.post_message(self.ExecuteRequested(self.plan.id))

    def action_cancel_plan(self) -> None:
        self.post_message(self.CancelRequested(self.plan.id))
