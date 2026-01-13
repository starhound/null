"""Branch diff screen with syntax highlighting and navigation."""

from __future__ import annotations

import difflib
from dataclasses import dataclass
from typing import TYPE_CHECKING, ClassVar

from rich.syntax import Syntax
from textual.app import ComposeResult
from textual.binding import Binding, BindingType
from textual.containers import Horizontal, ScrollableContainer, Vertical
from textual.reactive import reactive
from textual.screen import ModalScreen
from textual.widgets import Button, Collapsible, Label, Static

if TYPE_CHECKING:
    from managers.branch import BranchManager
    from models import BlockState


@dataclass
class DiffHunk:
    """A hunk of diff content."""

    start_line_a: int
    start_line_b: int
    lines: list[
        tuple[str, str, str]
    ]  # (type, line_a, line_b) - type: 'same', 'add', 'remove', 'change'
    is_change: bool = False


class DiffLineWidget(Static):
    """A single line in the diff view with syntax highlighting."""

    def __init__(
        self,
        line_type: str,
        line_num_a: str,
        line_num_b: str,
        content: str,
        language: str = "python",
    ):
        super().__init__()
        self.line_type = line_type
        self.line_num_a = line_num_a
        self.line_num_b = line_num_b
        self.content = content
        self.language = language

    def compose(self) -> ComposeResult:
        # Build the line with line numbers and syntax-highlighted content
        line_class = f"diff-line diff-{self.line_type}"

        with Horizontal(classes=line_class):
            # Line numbers
            yield Static(
                self.line_num_a.rjust(4), classes="diff-line-num diff-line-num-a"
            )
            yield Static(
                self.line_num_b.rjust(4), classes="diff-line-num diff-line-num-b"
            )

            # Type indicator
            indicator = {
                "add": "+",
                "remove": "-",
                "change": "~",
                "same": " ",
            }.get(self.line_type, " ")
            yield Static(indicator, classes="diff-indicator")

            # Syntax-highlighted content
            if self.content.strip():
                try:
                    syntax = Syntax(
                        self.content,
                        self.language,
                        theme="monokai",
                        line_numbers=False,
                        word_wrap=False,
                    )
                    yield Static(syntax, classes="diff-content")
                except Exception:
                    yield Static(self.content, classes="diff-content")
            else:
                yield Static(self.content, classes="diff-content")


class DiffHunkWidget(Static):
    """A hunk of changes in the diff."""

    def __init__(self, hunk: DiffHunk, hunk_index: int, language: str = "python"):
        super().__init__()
        self.hunk = hunk
        self.hunk_index = hunk_index
        self.language = language

    def compose(self) -> ComposeResult:
        classes = "diff-hunk"
        if self.hunk.is_change:
            classes += " diff-hunk-changed"

        with Vertical(classes=classes, id=f"hunk-{self.hunk_index}"):
            # Hunk header
            yield Static(
                f"@@ -{self.hunk.start_line_a},{len(self.hunk.lines)} +{self.hunk.start_line_b},{len(self.hunk.lines)} @@",
                classes="diff-hunk-header",
            )

            line_num_a = self.hunk.start_line_a
            line_num_b = self.hunk.start_line_b

            for line_type, line_a, line_b in self.hunk.lines:
                if line_type == "remove":
                    yield DiffLineWidget(
                        line_type,
                        str(line_num_a),
                        "",
                        line_a,
                        self.language,
                    )
                    line_num_a += 1
                elif line_type == "add":
                    yield DiffLineWidget(
                        line_type,
                        "",
                        str(line_num_b),
                        line_b,
                        self.language,
                    )
                    line_num_b += 1
                elif line_type == "change":
                    # Show both old and new
                    yield DiffLineWidget(
                        "remove",
                        str(line_num_a),
                        "",
                        line_a,
                        self.language,
                    )
                    yield DiffLineWidget(
                        "add",
                        "",
                        str(line_num_b),
                        line_b,
                        self.language,
                    )
                    line_num_a += 1
                    line_num_b += 1
                else:  # same
                    yield DiffLineWidget(
                        line_type,
                        str(line_num_a),
                        str(line_num_b),
                        line_a,
                        self.language,
                    )
                    line_num_a += 1
                    line_num_b += 1


class UnchangedSection(Collapsible):
    """Collapsible section for unchanged lines."""

    def __init__(self, lines: list[tuple[int, int, str]], language: str = "python"):
        self.lines_data = lines
        self.language = language
        title = f"... {len(lines)} unchanged lines ..."
        super().__init__(title=title, collapsed=True)

    def compose(self) -> ComposeResult:
        with Vertical(classes="diff-unchanged-content"):
            for line_num_a, line_num_b, content in self.lines_data:
                yield DiffLineWidget(
                    "same",
                    str(line_num_a),
                    str(line_num_b),
                    content,
                    self.language,
                )


class BranchDiffScreen(ModalScreen):
    """Screen for viewing diff between two conversation branches."""

    BINDINGS: ClassVar[list[BindingType]] = [
        Binding("escape", "dismiss", "Close"),
        Binding("q", "dismiss", "Close", show=False),
        Binding("n", "next_change", "Next Change"),
        Binding("p", "prev_change", "Prev Change"),
        Binding("j", "scroll_down", "Scroll Down", show=False),
        Binding("k", "scroll_up", "Scroll Up", show=False),
        Binding("g", "scroll_top", "Go to Top", show=False),
        Binding("G", "scroll_bottom", "Go to Bottom", show=False),
    ]

    current_change: reactive[int] = reactive(0)

    def __init__(
        self, branch_a_id: str, branch_b_id: str, branch_manager: BranchManager
    ):
        super().__init__()
        self.branch_a_id = branch_a_id
        self.branch_b_id = branch_b_id
        self.branch_manager = branch_manager
        self.change_positions: list[int] = []  # Hunk indices that contain changes
        self._diff_hunks: list[DiffHunk] = []

    def compose(self) -> ComposeResult:
        # Compute diff
        self._diff_hunks = self._compute_diff()
        self.change_positions = [
            i for i, h in enumerate(self._diff_hunks) if h.is_change
        ]

        with Vertical(id="diff-screen-container"):
            # Header
            with Horizontal(classes="diff-header"):
                yield Label(
                    f"Comparing: {self.branch_a_id} ↔ {self.branch_b_id}",
                    classes="diff-title",
                )
                yield Static(
                    f"{len(self.change_positions)} changes",
                    classes="diff-stats",
                )

            # Navigation bar
            with Horizontal(classes="diff-nav-bar"):
                yield Button(
                    "◀ Prev (p)",
                    id="btn-prev",
                    variant="default",
                    classes="diff-nav-btn",
                )
                yield Static("", id="change-indicator", classes="diff-change-indicator")
                yield Button(
                    "Next (n) ▶",
                    id="btn-next",
                    variant="default",
                    classes="diff-nav-btn",
                )

            # Jump buttons for each change
            if self.change_positions:
                with Horizontal(classes="diff-jump-bar"):
                    yield Label("Jump to:", classes="diff-jump-label")
                    for i, pos in enumerate(self.change_positions):
                        yield Button(
                            f"#{i + 1}",
                            id=f"jump-{pos}",
                            variant="default",
                            classes="diff-jump-btn",
                        )

            # Diff content
            with ScrollableContainer(id="diff-scroll"):
                for i, hunk in enumerate(self._diff_hunks):
                    if not hunk.is_change and len(hunk.lines) > 5:
                        # Collapse unchanged sections > 5 lines
                        lines_data = []
                        line_a = hunk.start_line_a
                        line_b = hunk.start_line_b
                        for _, line_a_content, _ in hunk.lines:
                            lines_data.append((line_a, line_b, line_a_content))
                            line_a += 1
                            line_b += 1
                        yield UnchangedSection(lines_data, language="python")
                    else:
                        yield DiffHunkWidget(hunk, i, language="python")

            # Footer
            with Horizontal(classes="diff-footer"):
                yield Static(
                    "Keys: [n]ext [p]rev [j/k]scroll [g/G]top/bottom [q]close",
                    classes="diff-help",
                )
                yield Button(
                    "Close", variant="primary", id="close", classes="btn-primary"
                )

    def _compute_diff(self) -> list[DiffHunk]:
        """Compute diff between two branches."""
        blocks_a = self.branch_manager.branches.get(self.branch_a_id, [])
        blocks_b = self.branch_manager.branches.get(self.branch_b_id, [])

        # Convert blocks to text lines for diffing
        lines_a = self._blocks_to_lines(blocks_a)
        lines_b = self._blocks_to_lines(blocks_b)

        # Use difflib to compute the diff
        matcher = difflib.SequenceMatcher(None, lines_a, lines_b)
        hunks: list[DiffHunk] = []

        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            if tag == "equal":
                # Unchanged section
                lines = [
                    (
                        "same",
                        lines_a[i] if i < len(lines_a) else "",
                        lines_b[j] if j < len(lines_b) else "",
                    )
                    for i, j in zip(range(i1, i2), range(j1, j2), strict=True)
                ]
                if lines:
                    hunks.append(
                        DiffHunk(
                            start_line_a=i1 + 1,
                            start_line_b=j1 + 1,
                            lines=lines,
                            is_change=False,
                        )
                    )
            elif tag == "replace":
                # Changed section
                lines = []
                max_len = max(i2 - i1, j2 - j1)
                for k in range(max_len):
                    old_idx = i1 + k
                    new_idx = j1 + k
                    if old_idx < i2 and new_idx < j2:
                        lines.append(("change", lines_a[old_idx], lines_b[new_idx]))
                    elif old_idx < i2:
                        lines.append(("remove", lines_a[old_idx], ""))
                    else:
                        lines.append(("add", "", lines_b[new_idx]))
                hunks.append(
                    DiffHunk(
                        start_line_a=i1 + 1,
                        start_line_b=j1 + 1,
                        lines=lines,
                        is_change=True,
                    )
                )
            elif tag == "delete":
                # Removed lines
                lines = [("remove", lines_a[i], "") for i in range(i1, i2)]
                hunks.append(
                    DiffHunk(
                        start_line_a=i1 + 1,
                        start_line_b=j1 + 1,
                        lines=lines,
                        is_change=True,
                    )
                )
            elif tag == "insert":
                # Added lines
                lines = [("add", "", lines_b[j]) for j in range(j1, j2)]
                hunks.append(
                    DiffHunk(
                        start_line_a=i1 + 1,
                        start_line_b=j1 + 1,
                        lines=lines,
                        is_change=True,
                    )
                )

        return hunks

    def _blocks_to_lines(self, blocks: list[BlockState]) -> list[str]:
        """Convert blocks to text lines for diffing."""
        lines = []
        for block in blocks:
            # Add block header
            lines.append(f"[{block.type.name}]")
            # Add content lines
            content = block.content_input or ""
            lines.extend(content.split("\n"))
            lines.append("")  # Separator
        return lines

    def on_mount(self) -> None:
        """Update the change indicator on mount."""
        self._update_change_indicator()

    def _update_change_indicator(self) -> None:
        """Update the change navigation indicator."""
        try:
            indicator = self.query_one("#change-indicator", Static)
            if not self.change_positions:
                indicator.update("No changes")
            else:
                indicator.update(
                    f"Change {self.current_change + 1} of {len(self.change_positions)}"
                )
        except Exception:
            pass  # Widget not yet mounted

    def watch_current_change(self, value: int) -> None:
        """React to current change updates."""
        self._update_change_indicator()
        self._scroll_to_current_change()

    def _scroll_to_current_change(self) -> None:
        """Scroll to the current change hunk."""
        if not self.change_positions:
            return

        try:
            hunk_idx = self.change_positions[self.current_change]
            hunk_widget = self.query_one(f"#hunk-{hunk_idx}")
            hunk_widget.scroll_visible(animate=True)
            # Highlight the current hunk
            for i, pos in enumerate(self.change_positions):
                widget = self.query_one(f"#hunk-{pos}", DiffHunkWidget)
                if i == self.current_change:
                    widget.add_class("diff-hunk-current")
                else:
                    widget.remove_class("diff-hunk-current")
        except Exception:
            pass

    def action_dismiss(self) -> None:
        """Close the screen."""
        self.dismiss()

    def action_next_change(self) -> None:
        """Navigate to the next change."""
        if self.change_positions:
            self.current_change = (self.current_change + 1) % len(self.change_positions)

    def action_prev_change(self) -> None:
        """Navigate to the previous change."""
        if self.change_positions:
            self.current_change = (self.current_change - 1) % len(self.change_positions)

    def action_scroll_down(self) -> None:
        """Scroll the diff view down."""
        try:
            scroll = self.query_one("#diff-scroll", ScrollableContainer)
            scroll.scroll_relative(y=3)
        except Exception:
            pass

    def action_scroll_up(self) -> None:
        """Scroll the diff view up."""
        try:
            scroll = self.query_one("#diff-scroll", ScrollableContainer)
            scroll.scroll_relative(y=-3)
        except Exception:
            pass

    def action_scroll_top(self) -> None:
        """Scroll to top of diff."""
        try:
            scroll = self.query_one("#diff-scroll", ScrollableContainer)
            scroll.scroll_home()
        except Exception:
            pass

    def action_scroll_bottom(self) -> None:
        """Scroll to bottom of diff."""
        try:
            scroll = self.query_one("#diff-scroll", ScrollableContainer)
            scroll.scroll_end()
        except Exception:
            pass

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        button_id = event.button.id
        if button_id == "close":
            self.dismiss()
        elif button_id == "btn-next":
            self.action_next_change()
        elif button_id == "btn-prev":
            self.action_prev_change()
        elif button_id and button_id.startswith("jump-"):
            # Jump to specific change
            try:
                hunk_idx = int(button_id.split("-")[1])
                if hunk_idx in self.change_positions:
                    self.current_change = self.change_positions.index(hunk_idx)
            except (ValueError, IndexError):
                pass
