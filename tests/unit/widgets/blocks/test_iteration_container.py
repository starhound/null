"""Tests for widgets/blocks/iteration_container.py - IterationContainer widget."""

from unittest.mock import MagicMock, patch

import pytest

from models import AgentIteration, ToolCallState
from widgets.blocks.iteration_container import IterationContainer


class TestIterationContainerInit:
    """Tests for IterationContainer initialization."""

    def test_init_default_show_thinking_true(self):
        """Default show_thinking is True."""
        container = IterationContainer()
        assert container.show_thinking is True

    def test_init_show_thinking_can_be_false(self):
        """show_thinking can be set to False."""
        container = IterationContainer(show_thinking=False)
        assert container.show_thinking is False

    def test_init_iterations_dict_empty(self):
        """_iterations dict starts empty."""
        container = IterationContainer()
        assert container._iterations == {}

    def test_init_with_id(self):
        """Container can be initialized with id."""
        container = IterationContainer(id="test-container")
        assert container.id == "test-container"

    def test_init_with_classes(self):
        """Container can be initialized with classes."""
        container = IterationContainer(classes="custom-class")
        assert "custom-class" in container.classes

    def test_init_combined_parameters(self):
        """Container can be initialized with multiple parameters."""
        container = IterationContainer(
            show_thinking=False,
            id="combo-container",
            classes="class1 class2",
        )
        assert container.show_thinking is False
        assert container.id == "combo-container"
        assert "class1" in container.classes
        assert "class2" in container.classes


class TestIterationContainerCompose:
    """Tests for IterationContainer.compose method."""

    def test_compose_yields_empty(self):
        """compose yields nothing by default (iterations added dynamically)."""
        container = IterationContainer()
        result = list(container.compose())
        assert result == []


class TestIterationContainerAddIteration:
    """Tests for IterationContainer.add_iteration method."""

    def test_add_iteration_returns_widget(self):
        """add_iteration returns an IterationWidget."""
        container = IterationContainer()
        iteration = AgentIteration(id="iter-1", iteration_number=1)

        with patch.object(container, "mount"):
            widget = container.add_iteration(iteration)

        from widgets.blocks.iteration import IterationWidget

        assert isinstance(widget, IterationWidget)

    def test_add_iteration_stores_widget_by_id(self):
        """add_iteration stores widget in _iterations dict by iteration id."""
        container = IterationContainer()
        iteration = AgentIteration(id="iter-123", iteration_number=1)

        with patch.object(container, "mount"):
            widget = container.add_iteration(iteration)

        assert container._iterations["iter-123"] is widget

    def test_add_iteration_mounts_widget(self):
        """add_iteration mounts the widget to the container."""
        container = IterationContainer()
        iteration = AgentIteration(id="iter-1", iteration_number=1)

        with patch.object(container, "mount") as mock_mount:
            widget = container.add_iteration(iteration)
            mock_mount.assert_called_once_with(widget)

    def test_add_iteration_removes_empty_class(self):
        """add_iteration removes 'empty' class if present."""
        container = IterationContainer(classes="empty")
        iteration = AgentIteration(id="iter-1", iteration_number=1)

        with patch.object(container, "mount"):
            container.add_iteration(iteration)

        assert "empty" not in container.classes

    def test_add_iteration_no_empty_class_no_op(self):
        """add_iteration handles case where 'empty' class doesn't exist."""
        container = IterationContainer()
        iteration = AgentIteration(id="iter-1", iteration_number=1)

        with patch.object(container, "mount"):
            # Should not raise
            container.add_iteration(iteration)

    def test_add_iteration_passes_show_thinking(self):
        """add_iteration passes show_thinking to IterationWidget."""
        container = IterationContainer(show_thinking=False)
        iteration = AgentIteration(id="iter-1", iteration_number=1)

        with patch.object(container, "mount"):
            widget = container.add_iteration(iteration)

        assert widget.show_thinking is False

    def test_add_iteration_show_thinking_true(self):
        """add_iteration passes show_thinking=True to IterationWidget."""
        container = IterationContainer(show_thinking=True)
        iteration = AgentIteration(id="iter-1", iteration_number=1)

        with patch.object(container, "mount"):
            widget = container.add_iteration(iteration)

        assert widget.show_thinking is True

    def test_add_multiple_iterations(self):
        """Multiple iterations can be added."""
        container = IterationContainer()
        iter1 = AgentIteration(id="iter-1", iteration_number=1)
        iter2 = AgentIteration(id="iter-2", iteration_number=2)
        iter3 = AgentIteration(id="iter-3", iteration_number=3)

        with patch.object(container, "mount"):
            container.add_iteration(iter1)
            container.add_iteration(iter2)
            container.add_iteration(iter3)

        assert len(container._iterations) == 3
        assert "iter-1" in container._iterations
        assert "iter-2" in container._iterations
        assert "iter-3" in container._iterations


class TestIterationContainerGetIteration:
    """Tests for IterationContainer.get_iteration method."""

    def test_get_iteration_returns_widget(self):
        """get_iteration returns the widget for given id."""
        container = IterationContainer()
        iteration = AgentIteration(id="iter-1", iteration_number=1)

        with patch.object(container, "mount"):
            added_widget = container.add_iteration(iteration)

        result = container.get_iteration("iter-1")
        assert result is added_widget

    def test_get_iteration_returns_none_for_unknown_id(self):
        """get_iteration returns None for unknown iteration id."""
        container = IterationContainer()
        result = container.get_iteration("unknown-id")
        assert result is None

    def test_get_iteration_with_empty_container(self):
        """get_iteration returns None on empty container."""
        container = IterationContainer()
        result = container.get_iteration("any-id")
        assert result is None


class TestIterationContainerGetCurrentIteration:
    """Tests for IterationContainer.get_current_iteration method."""

    def test_get_current_iteration_returns_none_when_empty(self):
        """get_current_iteration returns None when no iterations."""
        container = IterationContainer()
        result = container.get_current_iteration()
        assert result is None

    def test_get_current_iteration_returns_last_added(self):
        """get_current_iteration returns the last added iteration."""
        container = IterationContainer()
        iter1 = AgentIteration(id="iter-1", iteration_number=1)
        iter2 = AgentIteration(id="iter-2", iteration_number=2)

        with patch.object(container, "mount"):
            container.add_iteration(iter1)
            widget2 = container.add_iteration(iter2)

        result = container.get_current_iteration()
        assert result is widget2

    def test_get_current_iteration_single_iteration(self):
        """get_current_iteration returns the only iteration."""
        container = IterationContainer()
        iteration = AgentIteration(id="iter-1", iteration_number=1)

        with patch.object(container, "mount"):
            widget = container.add_iteration(iteration)

        result = container.get_current_iteration()
        assert result is widget


class TestIterationContainerUpdateIteration:
    """Tests for IterationContainer.update_iteration method."""

    def test_update_iteration_status(self):
        """update_iteration can update status."""
        container = IterationContainer()
        iteration = AgentIteration(id="iter-1", iteration_number=1, status="pending")

        with patch.object(container, "mount"):
            widget = container.add_iteration(iteration)

        with patch.object(widget, "update_status") as mock_update:
            container.update_iteration("iter-1", status="thinking")
            mock_update.assert_called_once_with("thinking", 0.0)

    def test_update_iteration_thinking(self):
        """update_iteration can update thinking content."""
        container = IterationContainer()
        iteration = AgentIteration(id="iter-1", iteration_number=1)

        with patch.object(container, "mount"):
            widget = container.add_iteration(iteration)

        with patch.object(widget, "update_thinking") as mock_update:
            container.update_iteration("iter-1", thinking="I'm thinking about this...")
            mock_update.assert_called_once_with("I'm thinking about this...")

    def test_update_iteration_response(self):
        """update_iteration can update response."""
        container = IterationContainer()
        iteration = AgentIteration(id="iter-1", iteration_number=1)

        with patch.object(container, "mount"):
            widget = container.add_iteration(iteration)

        with patch.object(widget, "update_response") as mock_update:
            container.update_iteration("iter-1", response="Here's my response")
            mock_update.assert_called_once_with("Here's my response")

    def test_update_iteration_duration(self):
        """update_iteration can pass duration with status."""
        container = IterationContainer()
        iteration = AgentIteration(id="iter-1", iteration_number=1)

        with patch.object(container, "mount"):
            widget = container.add_iteration(iteration)

        with patch.object(widget, "update_status") as mock_update:
            container.update_iteration("iter-1", status="complete", duration=2.5)
            mock_update.assert_called_once_with("complete", 2.5)

    def test_update_iteration_multiple_fields(self):
        """update_iteration can update multiple fields at once."""
        container = IterationContainer()
        iteration = AgentIteration(id="iter-1", iteration_number=1)

        with patch.object(container, "mount"):
            widget = container.add_iteration(iteration)

        with (
            patch.object(widget, "update_status") as mock_status,
            patch.object(widget, "update_thinking") as mock_thinking,
            patch.object(widget, "update_response") as mock_response,
        ):
            container.update_iteration(
                "iter-1",
                status="complete",
                thinking="done thinking",
                response="final answer",
                duration=1.5,
            )
            mock_status.assert_called_once_with("complete", 1.5)
            mock_thinking.assert_called_once_with("done thinking")
            mock_response.assert_called_once_with("final answer")

    def test_update_iteration_unknown_id_no_error(self):
        """update_iteration silently handles unknown iteration id."""
        container = IterationContainer()
        # Should not raise
        container.update_iteration("unknown-id", status="thinking")

    def test_update_iteration_empty_container_no_error(self):
        """update_iteration handles empty container gracefully."""
        container = IterationContainer()
        container.update_iteration("any-id", thinking="test")


class TestIterationContainerAddToolCall:
    """Tests for IterationContainer.add_tool_call method."""

    def test_add_tool_call_returns_widget(self):
        """add_tool_call returns the IterationWidget."""
        container = IterationContainer()
        iteration = AgentIteration(id="iter-1", iteration_number=1)
        tool_call = ToolCallState(id="tool-1", tool_name="read_file")

        with patch.object(container, "mount"):
            widget = container.add_iteration(iteration)

        with patch.object(widget, "add_tool_call"):
            result = container.add_tool_call("iter-1", tool_call)

        assert result is widget

    def test_add_tool_call_delegates_to_widget(self):
        """add_tool_call calls add_tool_call on the widget."""
        container = IterationContainer()
        iteration = AgentIteration(id="iter-1", iteration_number=1)
        tool_call = ToolCallState(id="tool-1", tool_name="run_command")

        with patch.object(container, "mount"):
            widget = container.add_iteration(iteration)

        with patch.object(widget, "add_tool_call") as mock_add:
            container.add_tool_call("iter-1", tool_call)
            mock_add.assert_called_once_with(tool_call)

    def test_add_tool_call_unknown_iteration_returns_none(self):
        """add_tool_call returns None for unknown iteration."""
        container = IterationContainer()
        tool_call = ToolCallState(id="tool-1", tool_name="test")

        result = container.add_tool_call("unknown-iter", tool_call)
        assert result is None


class TestIterationContainerUpdateToolCall:
    """Tests for IterationContainer.update_tool_call method."""

    def test_update_tool_call_delegates_to_widget(self):
        """update_tool_call delegates to the iteration widget."""
        container = IterationContainer()
        iteration = AgentIteration(id="iter-1", iteration_number=1)

        with patch.object(container, "mount"):
            widget = container.add_iteration(iteration)

        with patch.object(widget, "update_tool_call") as mock_update:
            container.update_tool_call(
                "iter-1", "tool-123", status="running", duration=0.5
            )
            mock_update.assert_called_once_with("tool-123", "running", 0.5)

    def test_update_tool_call_status_only(self):
        """update_tool_call can pass status only."""
        container = IterationContainer()
        iteration = AgentIteration(id="iter-1", iteration_number=1)

        with patch.object(container, "mount"):
            widget = container.add_iteration(iteration)

        with patch.object(widget, "update_tool_call") as mock_update:
            container.update_tool_call("iter-1", "tool-1", status="success")
            mock_update.assert_called_once_with("tool-1", "success", None)

    def test_update_tool_call_unknown_iteration_no_error(self):
        """update_tool_call handles unknown iteration silently."""
        container = IterationContainer()
        # Should not raise
        container.update_tool_call("unknown-iter", "tool-1", status="error")


class TestIterationContainerIterationCount:
    """Tests for IterationContainer.iteration_count property."""

    def test_iteration_count_empty(self):
        """iteration_count is 0 when empty."""
        container = IterationContainer()
        assert container.iteration_count == 0

    def test_iteration_count_with_iterations(self):
        """iteration_count returns correct count."""
        container = IterationContainer()
        iter1 = AgentIteration(id="iter-1", iteration_number=1)
        iter2 = AgentIteration(id="iter-2", iteration_number=2)

        with patch.object(container, "mount"):
            container.add_iteration(iter1)
            container.add_iteration(iter2)

        assert container.iteration_count == 2

    def test_iteration_count_after_removal(self):
        """iteration_count updates after removal."""
        container = IterationContainer()
        iter1 = AgentIteration(id="iter-1", iteration_number=1)
        iter2 = AgentIteration(id="iter-2", iteration_number=2)

        with patch.object(container, "mount"):
            container.add_iteration(iter1)
            widget2 = container.add_iteration(iter2)

        with patch.object(widget2, "remove"):
            container.remove_iteration("iter-2")

        assert container.iteration_count == 1


class TestIterationContainerRemoveIteration:
    """Tests for IterationContainer.remove_iteration method."""

    def test_remove_iteration_removes_from_dict(self):
        """remove_iteration removes widget from _iterations dict."""
        container = IterationContainer()
        iteration = AgentIteration(id="iter-1", iteration_number=1)

        with patch.object(container, "mount"):
            widget = container.add_iteration(iteration)

        with patch.object(widget, "remove"):
            container.remove_iteration("iter-1")

        assert "iter-1" not in container._iterations

    def test_remove_iteration_calls_widget_remove(self):
        """remove_iteration calls remove() on the widget."""
        container = IterationContainer()
        iteration = AgentIteration(id="iter-1", iteration_number=1)

        with patch.object(container, "mount"):
            widget = container.add_iteration(iteration)

        with patch.object(widget, "remove") as mock_remove:
            container.remove_iteration("iter-1")
            mock_remove.assert_called_once()

    def test_remove_iteration_adds_empty_class_when_last(self):
        """remove_iteration adds 'empty' class when last iteration removed."""
        container = IterationContainer()
        iteration = AgentIteration(id="iter-1", iteration_number=1)

        with patch.object(container, "mount"):
            widget = container.add_iteration(iteration)

        with patch.object(widget, "remove"):
            container.remove_iteration("iter-1")

        assert "empty" in container.classes

    def test_remove_iteration_no_empty_class_if_others_remain(self):
        """remove_iteration doesn't add 'empty' class if iterations remain."""
        container = IterationContainer()
        iter1 = AgentIteration(id="iter-1", iteration_number=1)
        iter2 = AgentIteration(id="iter-2", iteration_number=2)

        with patch.object(container, "mount"):
            widget1 = container.add_iteration(iter1)
            container.add_iteration(iter2)

        with patch.object(widget1, "remove"):
            container.remove_iteration("iter-1")

        assert "empty" not in container.classes

    def test_remove_iteration_unknown_id_no_error(self):
        """remove_iteration handles unknown id gracefully."""
        container = IterationContainer()
        # Should not raise
        container.remove_iteration("unknown-id")


class TestIterationContainerHasIterations:
    """Tests for IterationContainer.has_iterations property."""

    def test_has_iterations_false_when_empty(self):
        """has_iterations is False when empty."""
        container = IterationContainer()
        assert container.has_iterations is False

    def test_has_iterations_true_with_iterations(self):
        """has_iterations is True when iterations exist."""
        container = IterationContainer()
        iteration = AgentIteration(id="iter-1", iteration_number=1)

        with patch.object(container, "mount"):
            container.add_iteration(iteration)

        assert container.has_iterations is True

    def test_has_iterations_false_after_clear(self):
        """has_iterations is False after clear()."""
        container = IterationContainer()
        iteration = AgentIteration(id="iter-1", iteration_number=1)

        with patch.object(container, "mount"):
            widget = container.add_iteration(iteration)

        with patch.object(widget, "remove"):
            container.clear()

        assert container.has_iterations is False


class TestIterationContainerClear:
    """Tests for IterationContainer.clear method."""

    def test_clear_removes_all_iterations(self):
        """clear removes all iterations from dict."""
        container = IterationContainer()
        iter1 = AgentIteration(id="iter-1", iteration_number=1)
        iter2 = AgentIteration(id="iter-2", iteration_number=2)

        with patch.object(container, "mount"):
            widget1 = container.add_iteration(iter1)
            widget2 = container.add_iteration(iter2)

        with patch.object(widget1, "remove"), patch.object(widget2, "remove"):
            container.clear()

        assert len(container._iterations) == 0

    def test_clear_calls_remove_on_all_widgets(self):
        """clear calls remove() on each widget."""
        container = IterationContainer()
        iter1 = AgentIteration(id="iter-1", iteration_number=1)
        iter2 = AgentIteration(id="iter-2", iteration_number=2)

        with patch.object(container, "mount"):
            widget1 = container.add_iteration(iter1)
            widget2 = container.add_iteration(iter2)

        with (
            patch.object(widget1, "remove") as mock1,
            patch.object(widget2, "remove") as mock2,
        ):
            container.clear()
            mock1.assert_called_once()
            mock2.assert_called_once()

    def test_clear_adds_empty_class(self):
        """clear adds 'empty' class."""
        container = IterationContainer()
        iteration = AgentIteration(id="iter-1", iteration_number=1)

        with patch.object(container, "mount"):
            widget = container.add_iteration(iteration)

        with patch.object(widget, "remove"):
            container.clear()

        assert "empty" in container.classes

    def test_clear_on_empty_container(self):
        """clear on empty container still adds 'empty' class."""
        container = IterationContainer()
        container.clear()
        assert "empty" in container.classes


class TestIterationContainerGetAllToolCalls:
    """Tests for IterationContainer.get_all_tool_calls method."""

    def test_get_all_tool_calls_empty_container(self):
        """get_all_tool_calls returns empty list on empty container."""
        container = IterationContainer()
        result = container.get_all_tool_calls()
        assert result == []

    def test_get_all_tool_calls_no_tools(self):
        """get_all_tool_calls returns empty when iterations have no tools."""
        container = IterationContainer()
        iter1 = AgentIteration(id="iter-1", iteration_number=1, tool_calls=[])

        with patch.object(container, "mount"):
            container.add_iteration(iter1)

        result = container.get_all_tool_calls()
        assert result == []

    def test_get_all_tool_calls_single_iteration(self):
        """get_all_tool_calls returns tools from single iteration."""
        container = IterationContainer()
        tool1 = ToolCallState(id="tool-1", tool_name="read_file")
        tool2 = ToolCallState(id="tool-2", tool_name="write_file")
        iter1 = AgentIteration(
            id="iter-1", iteration_number=1, tool_calls=[tool1, tool2]
        )

        with patch.object(container, "mount"):
            container.add_iteration(iter1)

        result = container.get_all_tool_calls()
        assert len(result) == 2
        assert tool1 in result
        assert tool2 in result

    def test_get_all_tool_calls_multiple_iterations(self):
        """get_all_tool_calls aggregates tools from all iterations."""
        container = IterationContainer()
        tool1 = ToolCallState(id="tool-1", tool_name="read_file")
        tool2 = ToolCallState(id="tool-2", tool_name="write_file")
        tool3 = ToolCallState(id="tool-3", tool_name="run_command")

        iter1 = AgentIteration(id="iter-1", iteration_number=1, tool_calls=[tool1])
        iter2 = AgentIteration(
            id="iter-2", iteration_number=2, tool_calls=[tool2, tool3]
        )

        with patch.object(container, "mount"):
            container.add_iteration(iter1)
            container.add_iteration(iter2)

        result = container.get_all_tool_calls()
        assert len(result) == 3
        assert tool1 in result
        assert tool2 in result
        assert tool3 in result


class TestIterationContainerInheritance:
    """Tests for IterationContainer inheritance."""

    def test_inherits_from_container(self):
        """IterationContainer inherits from Textual Container."""
        from textual.containers import Container

        assert issubclass(IterationContainer, Container)

    def test_instance_is_container(self):
        """IterationContainer instance is a Container."""
        from textual.containers import Container

        container = IterationContainer()
        assert isinstance(container, Container)


class TestIterationContainerIterationDataIntegrity:
    """Tests for data integrity when managing iterations."""

    def test_widget_stores_correct_iteration(self):
        """Widget stores reference to correct AgentIteration."""
        container = IterationContainer()
        iteration = AgentIteration(
            id="iter-1",
            iteration_number=1,
            thinking="test thinking",
            status="pending",
        )

        with patch.object(container, "mount"):
            widget = container.add_iteration(iteration)

        assert widget.iteration is iteration
        assert widget.iteration.thinking == "test thinking"

    def test_multiple_iterations_maintain_order(self):
        """Iterations maintain insertion order in dict."""
        container = IterationContainer()
        iterations = [
            AgentIteration(id=f"iter-{i}", iteration_number=i) for i in range(1, 6)
        ]

        with patch.object(container, "mount"):
            for it in iterations:
                container.add_iteration(it)

        ids = list(container._iterations.keys())
        assert ids == ["iter-1", "iter-2", "iter-3", "iter-4", "iter-5"]


class TestIterationContainerEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_add_iteration_with_minimal_data(self):
        """add_iteration works with minimal AgentIteration data."""
        container = IterationContainer()
        iteration = AgentIteration(id="minimal")

        with patch.object(container, "mount"):
            widget = container.add_iteration(iteration)

        assert widget is not None
        assert widget.iteration.id == "minimal"

    def test_update_iteration_with_none_values(self):
        """update_iteration handles None values correctly."""
        container = IterationContainer()
        iteration = AgentIteration(id="iter-1", iteration_number=1)

        with patch.object(container, "mount"):
            widget = container.add_iteration(iteration)

        with (
            patch.object(widget, "update_status") as mock_status,
            patch.object(widget, "update_thinking") as mock_thinking,
            patch.object(widget, "update_response") as mock_response,
        ):
            container.update_iteration(
                "iter-1",
                status=None,
                thinking=None,
                response=None,
                duration=None,
            )
            # None values should not trigger updates
            mock_status.assert_not_called()
            mock_thinking.assert_not_called()
            mock_response.assert_not_called()

    def test_remove_same_iteration_twice(self):
        """Removing same iteration twice doesn't raise error."""
        container = IterationContainer()
        iteration = AgentIteration(id="iter-1", iteration_number=1)

        with patch.object(container, "mount"):
            widget = container.add_iteration(iteration)

        with patch.object(widget, "remove"):
            container.remove_iteration("iter-1")

        # Second removal should not raise
        container.remove_iteration("iter-1")

    def test_add_iteration_with_same_id_overwrites(self):
        """Adding iteration with same id overwrites previous."""
        container = IterationContainer()
        iter1 = AgentIteration(id="same-id", iteration_number=1)
        iter2 = AgentIteration(id="same-id", iteration_number=2)

        with patch.object(container, "mount"):
            widget1 = container.add_iteration(iter1)
            widget2 = container.add_iteration(iter2)

        # Should have only one entry
        assert container.iteration_count == 1
        assert container._iterations["same-id"] is widget2

    def test_get_all_tool_calls_preserves_tool_call_state(self):
        """get_all_tool_calls returns actual ToolCallState objects."""
        container = IterationContainer()
        tool = ToolCallState(
            id="tool-1",
            tool_name="read_file",
            arguments='{"path": "/test"}',
            status="success",
            duration=0.5,
        )
        iteration = AgentIteration(id="iter-1", iteration_number=1, tool_calls=[tool])

        with patch.object(container, "mount"):
            container.add_iteration(iteration)

        result = container.get_all_tool_calls()
        assert len(result) == 1
        assert result[0].tool_name == "read_file"
        assert result[0].arguments == '{"path": "/test"}'
        assert result[0].status == "success"
        assert result[0].duration == 0.5
