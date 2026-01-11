from textual.app import ComposeResult
from textual.message import Message
from textual.reactive import reactive
from textual.widgets import Static, Button, ProgressBar
from textual.containers import Vertical

from managers.error_detector import DetectedError, CorrectionAttempt


class CorrectionLoopStopped(Message):
    pass


class CorrectionLoopBlock(Static):
    DEFAULT_CSS = """
    CorrectionLoopBlock {
        border: solid $warning;
        padding: 1;
        margin: 1 0;
    }
    
    .loop-header {
        text-style: bold;
        color: $warning;
    }
    
    .error-info {
        margin: 1 0;
        padding: 0 1;
        border-left: solid $error;
    }
    
    .attempt {
        margin: 0 0 1 2;
    }
    
    .attempt-success {
        color: $success;
    }
    
    .attempt-fail {
        color: $error;
    }
    
    .attempt-progress {
        color: $warning;
    }
    """

    loop_active = reactive(True)
    current_iteration = reactive(0)
    max_iterations = reactive(5)

    def __init__(self, error: DetectedError, max_iterations: int = 5, **kwargs):
        super().__init__(**kwargs)
        self.error = error
        self.max_iterations = max_iterations
        self.attempts: list[CorrectionAttempt] = []

    def compose(self) -> ComposeResult:
        yield Static("🔄 Auto-Correction Loop", classes="loop-header")

        with Vertical(classes="error-info"):
            yield Static(f"Error: {self.error.error_type.value}")
            yield Static(f"Message: {self.error.message[:80]}...")
            if self.error.file:
                yield Static(f"Location: {self.error.location}")

        yield Static("", id="attempts-container")

        yield ProgressBar(total=self.max_iterations, show_eta=False, id="progress")

        yield Button("Stop", id="stop-btn", variant="error")

    def add_attempt(self, attempt: CorrectionAttempt) -> None:
        self.attempts.append(attempt)
        self.current_iteration = len(self.attempts)
        self._update_display()

    def _update_display(self) -> None:
        container = self.query_one("#attempts-container", Static)
        progress = self.query_one("#progress", ProgressBar)

        lines = []
        for i, attempt in enumerate(self.attempts, 1):
            if attempt.success:
                lines.append(f"  ✓ Attempt {i}: {attempt.fix_description[:50]}...")
            else:
                lines.append(
                    f"  ✗ Attempt {i}: Failed - {attempt.verification_output[:40]}..."
                )

        if self.loop_active and self.current_iteration < self.max_iterations:
            lines.append(
                f"  ⏳ Attempt {self.current_iteration + 1}: Generating fix..."
            )

        container.update("\n".join(lines))
        progress.progress = self.current_iteration

    def mark_complete(self, success: bool) -> None:
        self.loop_active = False
        header = self.query_one(".loop-header", Static)
        if success:
            header.update("✓ Auto-Correction Complete")
            self.styles.border = ("solid", "green")
        else:
            header.update("✗ Auto-Correction Failed")
            self.styles.border = ("solid", "red")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "stop-btn":
            self.loop_active = False
            self.post_message(CorrectionLoopStopped())
