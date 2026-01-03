"""Container for managing agent iterations."""

from textual.app import ComposeResult
from textual.containers import Container
from typing import Optional, Dict

from models import AgentIteration, ToolCallState
from .iteration import IterationWidget


class IterationContainer(Container):
    """Container holding all agent iterations for an AI response block.

    Manages the lifecycle of iterations and their widgets, providing
    a clean interface for the execution handler to update iteration state.
    """

    def __init__(
        self,
        show_thinking: bool = True,
        id: str | None = None,
        classes: str | None = None
    ):
        super().__init__(id=id, classes=classes)
        self._iterations: Dict[str, IterationWidget] = {}
        self.show_thinking = show_thinking

    def compose(self) -> ComposeResult:
        # Empty by default - iterations added dynamically
        yield from []

    def add_iteration(self, iteration: AgentIteration) -> IterationWidget:
        """Add a new iteration to the container.

        Args:
            iteration: The AgentIteration data model

        Returns:
            The created IterationWidget
        """
        # Remove empty class if this is first iteration
        if "empty" in self.classes:
            self.remove_class("empty")

        widget = IterationWidget(
            iteration=iteration,
            show_thinking=self.show_thinking
        )
        self._iterations[iteration.id] = widget
        self.mount(widget)
        return widget

    def get_iteration(self, iteration_id: str) -> Optional[IterationWidget]:
        """Get an iteration widget by ID."""
        return self._iterations.get(iteration_id)

    def get_current_iteration(self) -> Optional[IterationWidget]:
        """Get the most recently added iteration."""
        if not self._iterations:
            return None
        # Return the last added iteration
        return list(self._iterations.values())[-1]

    def update_iteration(
        self,
        iteration_id: str,
        status: str | None = None,
        thinking: str | None = None,
        response: str | None = None,
        duration: float | None = None
    ) -> None:
        """Update an existing iteration.

        Args:
            iteration_id: ID of the iteration to update
            status: New status (pending, thinking, executing, waiting_approval, complete)
            thinking: New thinking content
            response: Response fragment
            duration: Iteration duration in seconds
        """
        widget = self._iterations.get(iteration_id)
        if not widget:
            return

        if status is not None:
            widget.update_status(status, duration or 0.0)
        if thinking is not None:
            widget.update_thinking(thinking)
        if response is not None:
            widget.update_response(response)

    def add_tool_call(
        self,
        iteration_id: str,
        tool_call: ToolCallState
    ) -> Optional["IterationWidget"]:
        """Add a tool call to an iteration.

        Args:
            iteration_id: ID of the iteration
            tool_call: The tool call state to add

        Returns:
            The IterationWidget if found
        """
        widget = self._iterations.get(iteration_id)
        if widget:
            widget.add_tool_call(tool_call)
        return widget

    def update_tool_call(
        self,
        iteration_id: str,
        tool_id: str,
        status: str | None = None,
        duration: float | None = None
    ) -> None:
        """Update a tool call within an iteration.

        Args:
            iteration_id: ID of the iteration
            tool_id: ID of the tool call
            status: New status (pending, running, success, error)
            duration: Tool execution duration
        """
        widget = self._iterations.get(iteration_id)
        if widget:
            widget.update_tool_call(tool_id, status, duration)

    @property
    def iteration_count(self) -> int:
        """Number of iterations in the container."""
        return len(self._iterations)

    def remove_iteration(self, iteration_id: str) -> None:
        """Remove a specific iteration by ID."""
        widget = self._iterations.get(iteration_id)
        if widget:
            widget.remove()
            del self._iterations[iteration_id]
            if not self._iterations:
                self.add_class("empty")

    @property
    def has_iterations(self) -> bool:
        """Whether there are any iterations."""
        return bool(self._iterations)

    def clear(self) -> None:
        """Remove all iterations."""
        for widget in self._iterations.values():
            widget.remove()
        self._iterations.clear()
        self.add_class("empty")

    def get_all_tool_calls(self) -> list[ToolCallState]:
        """Get all tool calls from all iterations."""
        all_calls = []
        for widget in self._iterations.values():
            all_calls.extend(widget.iteration.tool_calls)
        return all_calls
