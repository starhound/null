"""Tests for widgets/blocks/agent_response.py - AgentResponseBlock."""

from models import AgentIteration, BlockState, BlockType, ToolCallState
from widgets.blocks.agent_response import AgentResponseBlock
from widgets.blocks.base import BaseBlockWidget


class TestAgentResponseBlockInitialization:
    def test_initialization_stores_block_reference(self):
        block = BlockState(type=BlockType.AGENT_RESPONSE, content_input="test task")
        widget = AgentResponseBlock(block)
        assert widget.block is block

    def test_initialization_creates_header(self):
        block = BlockState(type=BlockType.AGENT_RESPONSE, content_input="test")
        widget = AgentResponseBlock(block)
        assert widget.header is not None

    def test_initialization_creates_meta_widget(self):
        block = BlockState(type=BlockType.AGENT_RESPONSE, content_input="test")
        widget = AgentResponseBlock(block)
        assert widget.meta_widget is not None

    def test_initialization_creates_exec_widget(self):
        block = BlockState(type=BlockType.AGENT_RESPONSE, content_input="test")
        widget = AgentResponseBlock(block)
        assert widget.exec_widget is not None

    def test_initialization_creates_iteration_container(self):
        block = BlockState(type=BlockType.AGENT_RESPONSE, content_input="test")
        widget = AgentResponseBlock(block)
        assert widget.iteration_container is not None

    def test_initialization_creates_response_widget(self):
        block = BlockState(type=BlockType.AGENT_RESPONSE, content_input="test")
        widget = AgentResponseBlock(block)
        assert widget.response_widget is not None

    def test_initialization_creates_action_bar(self):
        block = BlockState(type=BlockType.AGENT_RESPONSE, content_input="test")
        widget = AgentResponseBlock(block)
        assert widget.action_bar is not None

    def test_initialization_creates_footer_widget(self):
        block = BlockState(type=BlockType.AGENT_RESPONSE, content_input="test")
        widget = AgentResponseBlock(block)
        assert widget.footer_widget is not None

    def test_initialization_adds_mode_agent_class(self):
        block = BlockState(type=BlockType.AGENT_RESPONSE, content_input="test")
        widget = AgentResponseBlock(block)
        assert "mode-agent" in widget.classes

    def test_inherits_from_base_block_widget(self):
        block = BlockState(type=BlockType.AGENT_RESPONSE, content_input="test")
        widget = AgentResponseBlock(block)
        assert isinstance(widget, BaseBlockWidget)


class TestAgentResponseBlockIterationContainer:
    def test_iteration_container_show_thinking_enabled(self):
        block = BlockState(type=BlockType.AGENT_RESPONSE, content_input="test")
        widget = AgentResponseBlock(block)
        assert widget.iteration_container.show_thinking is True

    def test_iteration_container_empty_class_when_no_iterations(self):
        block = BlockState(type=BlockType.AGENT_RESPONSE, content_input="test")
        block.iterations = []
        widget = AgentResponseBlock(block)
        assert "empty" in widget.iteration_container.classes

    def test_iteration_container_no_empty_class_when_has_iterations(self):
        iteration = AgentIteration(id="iter-1", iteration_number=1)
        block = BlockState(
            type=BlockType.AGENT_RESPONSE,
            content_input="test",
            iterations=[iteration],
        )
        widget = AgentResponseBlock(block)
        assert "empty" not in widget.iteration_container.classes


class TestAgentResponseBlockBuildMetaText:
    def test_build_meta_text_empty_when_no_metadata(self):
        block = BlockState(type=BlockType.AGENT_RESPONSE, content_input="test")
        block.metadata = {}
        widget = AgentResponseBlock(block)
        result = widget._build_meta_text()
        assert result == ""

    def test_build_meta_text_includes_model(self):
        block = BlockState(
            type=BlockType.AGENT_RESPONSE,
            content_input="test",
            metadata={"model": "gpt-4"},
        )
        widget = AgentResponseBlock(block)
        result = widget._build_meta_text()
        assert "gpt-4" in result

    def test_build_meta_text_truncates_long_model_name(self):
        long_model = "a" * 30
        block = BlockState(
            type=BlockType.AGENT_RESPONSE,
            content_input="test",
            metadata={"model": long_model},
        )
        widget = AgentResponseBlock(block)
        result = widget._build_meta_text()
        assert len(result) <= 20
        assert "..." in result

    def test_build_meta_text_model_under_20_not_truncated(self):
        model = "gpt-4-turbo"
        block = BlockState(
            type=BlockType.AGENT_RESPONSE,
            content_input="test",
            metadata={"model": model},
        )
        widget = AgentResponseBlock(block)
        result = widget._build_meta_text()
        assert model in result
        assert "..." not in result

    def test_build_meta_text_includes_tokens(self):
        block = BlockState(
            type=BlockType.AGENT_RESPONSE,
            content_input="test",
            metadata={"tokens": 150},
        )
        widget = AgentResponseBlock(block)
        result = widget._build_meta_text()
        assert "150 tok" in result

    def test_build_meta_text_includes_cost(self):
        block = BlockState(
            type=BlockType.AGENT_RESPONSE,
            content_input="test",
            metadata={"cost": 0.0025},
        )
        widget = AgentResponseBlock(block)
        result = widget._build_meta_text()
        assert "$0.0025" in result

    def test_build_meta_text_multiple_parts_joined_with_dot(self):
        block = BlockState(
            type=BlockType.AGENT_RESPONSE,
            content_input="test",
            metadata={"model": "gpt-4", "tokens": 100, "cost": 0.01},
        )
        widget = AgentResponseBlock(block)
        result = widget._build_meta_text()
        assert " · " in result or ("gpt-4" in result and "tok" in result)


class TestAgentResponseBlockCompose:
    def test_compose_returns_generator(self):
        block = BlockState(type=BlockType.AGENT_RESPONSE, content_input="test")
        widget = AgentResponseBlock(block)
        result = widget.compose()
        assert hasattr(result, "__iter__")

    def test_compose_yields_widgets(self):
        block = BlockState(type=BlockType.AGENT_RESPONSE, content_input="test")
        widget = AgentResponseBlock(block)
        composed = list(widget.compose())
        assert len(composed) >= 4


class TestAgentResponseBlockUpdateOutput:
    def test_update_output_sets_response_content(self):
        block = BlockState(type=BlockType.AGENT_RESPONSE, content_input="test")
        block.content_output = "Final response"
        widget = AgentResponseBlock(block)

        widget.update_output()

        assert widget.response_widget.content_text == "Final response"

    def test_update_output_with_empty_content(self):
        block = BlockState(type=BlockType.AGENT_RESPONSE, content_input="test")
        block.content_output = ""
        widget = AgentResponseBlock(block)

        widget.update_output()

        assert widget.response_widget.content_text == ""

    def test_update_output_ignores_new_content_parameter(self):
        block = BlockState(type=BlockType.AGENT_RESPONSE, content_input="test")
        block.content_output = "Block content"
        widget = AgentResponseBlock(block)

        widget.update_output("ignored")

        assert widget.response_widget.content_text == "Block content"

    def test_update_output_simple_mode_when_no_exec_and_no_iterations(self):
        block = BlockState(type=BlockType.AGENT_RESPONSE, content_input="test")
        block.content_output = "Simple answer"
        block.content_exec_output = ""
        block.iterations = []
        widget = AgentResponseBlock(block)

        widget.update_output()

    def test_update_output_updates_exec_widget(self):
        block = BlockState(type=BlockType.AGENT_RESPONSE, content_input="test")
        block.content_exec_output = "Execution output"
        widget = AgentResponseBlock(block)

        widget.update_output()

        assert widget.exec_widget.exec_output == "Execution output"


class TestAgentResponseBlockSetLoadingState:
    def test_set_loading_false_updates_block_state(self):
        block = BlockState(type=BlockType.AGENT_RESPONSE, content_input="test")
        block.is_running = True
        widget = AgentResponseBlock(block)

        widget.set_loading(False)

        assert block.is_running is False


class TestAgentResponseBlockIterationManagement:
    def test_remove_nonexistent_iteration_does_not_raise(self):
        block = BlockState(type=BlockType.AGENT_RESPONSE, content_input="test")
        widget = AgentResponseBlock(block)

        widget.remove_iteration("nonexistent")

    def test_get_current_iteration_empty_returns_none(self):
        block = BlockState(type=BlockType.AGENT_RESPONSE, content_input="test")
        widget = AgentResponseBlock(block)

        current = widget.get_current_iteration()

        assert current is None


class TestAgentResponseBlockToolCallManagement:
    def test_add_tool_call_to_nonexistent_iteration(self):
        block = BlockState(type=BlockType.AGENT_RESPONSE, content_input="test")
        widget = AgentResponseBlock(block)

        tool_call = ToolCallState(id="tool-1", tool_name="run_command")

        widget.add_iteration_tool_call("nonexistent", tool_call)


class TestAgentResponseBlockActionHandling:
    def test_action_bar_shows_fork(self):
        block = BlockState(type=BlockType.AGENT_RESPONSE, content_input="test")
        widget = AgentResponseBlock(block)
        assert widget.action_bar.show_fork is True

    def test_action_bar_shows_edit(self):
        block = BlockState(type=BlockType.AGENT_RESPONSE, content_input="test")
        widget = AgentResponseBlock(block)
        assert widget.action_bar.show_edit is True

    def test_action_bar_block_id_matches(self):
        block = BlockState(
            type=BlockType.AGENT_RESPONSE,
            content_input="test",
            id="my-block-123",
        )
        widget = AgentResponseBlock(block)
        assert widget.action_bar.block_id == "my-block-123"


class TestAgentResponseBlockMessages:
    def test_retry_message_available(self):
        msg = AgentResponseBlock.RetryRequested(block_id="block-1")
        assert msg.block_id == "block-1"

    def test_edit_message_available(self):
        msg = AgentResponseBlock.EditRequested(
            block_id="block-1", content="edit content"
        )
        assert msg.block_id == "block-1"
        assert msg.content == "edit content"

    def test_copy_message_available(self):
        msg = AgentResponseBlock.CopyRequested(
            block_id="block-1", content="copy content"
        )
        assert msg.block_id == "block-1"
        assert msg.content == "copy content"

    def test_fork_message_available(self):
        msg = AgentResponseBlock.ForkRequested(block_id="block-1")
        assert msg.block_id == "block-1"


class TestAgentResponseBlockWithPreexistingIterations:
    def test_block_with_existing_iterations(self):
        iteration = AgentIteration(
            id="pre-iter-1",
            iteration_number=1,
            thinking="Pre-existing thought",
            status="complete",
        )
        block = BlockState(
            type=BlockType.AGENT_RESPONSE,
            content_input="test",
            iterations=[iteration],
        )
        AgentResponseBlock(block)

        assert len(block.iterations) == 1

    def test_block_with_multiple_existing_iterations(self):
        iterations = [
            AgentIteration(id=f"iter-{i}", iteration_number=i) for i in range(3)
        ]
        block = BlockState(
            type=BlockType.AGENT_RESPONSE,
            content_input="test",
            iterations=iterations,
        )
        AgentResponseBlock(block)

        assert len(block.iterations) == 3

    def test_block_with_iterations_containing_tool_calls(self):
        tool_call = ToolCallState(
            id="tool-1",
            tool_name="read_file",
            arguments='{"path": "/tmp/test.txt"}',
            output="file contents",
            status="success",
        )
        iteration = AgentIteration(
            id="iter-1",
            iteration_number=1,
            tool_calls=[tool_call],
        )
        block = BlockState(
            type=BlockType.AGENT_RESPONSE,
            content_input="test",
            iterations=[iteration],
        )
        AgentResponseBlock(block)

        assert len(block.iterations[0].tool_calls) == 1


class TestAgentResponseBlockMetadataVariations:
    def test_metadata_with_only_model(self):
        block = BlockState(
            type=BlockType.AGENT_RESPONSE,
            content_input="test",
            metadata={"model": "claude-3-opus"},
        )
        widget = AgentResponseBlock(block)
        meta = widget._build_meta_text()
        assert "claude-3-opus" in meta

    def test_metadata_with_only_tokens(self):
        block = BlockState(
            type=BlockType.AGENT_RESPONSE,
            content_input="test",
            metadata={"tokens": 500},
        )
        widget = AgentResponseBlock(block)
        meta = widget._build_meta_text()
        assert "500 tok" in meta

    def test_metadata_with_only_cost(self):
        block = BlockState(
            type=BlockType.AGENT_RESPONSE,
            content_input="test",
            metadata={"cost": 0.1234},
        )
        widget = AgentResponseBlock(block)
        meta = widget._build_meta_text()
        assert "$0.1234" in meta

    def test_metadata_with_zero_cost_not_displayed(self):
        block = BlockState(
            type=BlockType.AGENT_RESPONSE,
            content_input="test",
            metadata={"cost": 0.0},
        )
        widget = AgentResponseBlock(block)
        meta = widget._build_meta_text()
        assert meta == ""

    def test_metadata_with_extra_fields_ignored(self):
        block = BlockState(
            type=BlockType.AGENT_RESPONSE,
            content_input="test",
            metadata={
                "model": "gpt-4",
                "unknown_field": "ignored",
                "another": 123,
            },
        )
        widget = AgentResponseBlock(block)
        meta = widget._build_meta_text()
        assert "gpt-4" in meta
        assert "ignored" not in meta


class TestAgentResponseBlockEdgeCases:
    def test_empty_content_input(self):
        block = BlockState(type=BlockType.AGENT_RESPONSE, content_input="")
        widget = AgentResponseBlock(block)
        assert widget.block.content_input == ""

    def test_unicode_content(self):
        block = BlockState(
            type=BlockType.AGENT_RESPONSE,
            content_input="Unicode: \u4f60\u597d \U0001f680 \xd1 \xfc \xdf",
        )
        widget = AgentResponseBlock(block)
        assert "\u4f60\u597d" in widget.block.content_input

    def test_very_long_content_input(self):
        long_input = "x" * 10000
        block = BlockState(type=BlockType.AGENT_RESPONSE, content_input=long_input)
        widget = AgentResponseBlock(block)
        assert len(widget.block.content_input) == 10000

    def test_update_output_does_not_raise(self):
        block = BlockState(type=BlockType.AGENT_RESPONSE, content_input="test")
        widget = AgentResponseBlock(block)

        widget.update_output()


class TestAgentResponseBlockStateIntegration:
    def test_widget_maintains_block_reference_integrity(self):
        block = BlockState(type=BlockType.AGENT_RESPONSE, content_input="original")
        widget = AgentResponseBlock(block)

        block.content_output = "modified"
        widget.update_output()

        assert widget.response_widget.content_text == "modified"

    def test_widget_with_running_block(self):
        block = BlockState(type=BlockType.AGENT_RESPONSE, content_input="test")
        block.is_running = True
        widget = AgentResponseBlock(block)

        assert widget.block.is_running is True

    def test_widget_with_completed_block(self):
        block = BlockState(type=BlockType.AGENT_RESPONSE, content_input="test")
        block.is_running = False
        block.content_output = "Final answer"
        widget = AgentResponseBlock(block)
        widget.update_output()

        assert widget.block.is_running is False
        assert widget.response_widget.content_text == "Final answer"

    def test_widget_preserves_block_id(self):
        block = BlockState(
            type=BlockType.AGENT_RESPONSE,
            content_input="test",
            id="custom-id-456",
        )
        widget = AgentResponseBlock(block)

        assert widget.block.id == "custom-id-456"

    def test_widget_preserves_block_timestamp(self):
        from datetime import datetime

        timestamp = datetime(2025, 1, 10, 12, 0, 0)
        block = BlockState(
            type=BlockType.AGENT_RESPONSE,
            content_input="test",
            timestamp=timestamp,
        )
        widget = AgentResponseBlock(block)

        assert widget.block.timestamp == timestamp


class TestAgentResponseBlockActionBarConfiguration:
    def test_action_bar_meta_text_set_on_init(self):
        block = BlockState(
            type=BlockType.AGENT_RESPONSE,
            content_input="test",
            metadata={"model": "gpt-4", "tokens": 100},
        )
        widget = AgentResponseBlock(block)

        assert widget.action_bar.meta_text != ""
        assert "gpt-4" in widget.action_bar.meta_text

    def test_action_bar_meta_text_empty_when_no_metadata(self):
        block = BlockState(type=BlockType.AGENT_RESPONSE, content_input="test")
        widget = AgentResponseBlock(block)

        assert widget.action_bar.meta_text == ""


class TestAgentResponseBlockFooterWidget:
    def test_footer_widget_created(self):
        block = BlockState(type=BlockType.AGENT_RESPONSE, content_input="test")
        widget = AgentResponseBlock(block)

        assert widget.footer_widget is not None

    def test_footer_widget_with_running_block(self):
        block = BlockState(type=BlockType.AGENT_RESPONSE, content_input="test")
        block.is_running = True
        widget = AgentResponseBlock(block)

        assert widget.footer_widget._has_content() is True

    def test_footer_widget_with_completed_block(self):
        block = BlockState(type=BlockType.AGENT_RESPONSE, content_input="test")
        block.is_running = False
        block.exit_code = 0
        widget = AgentResponseBlock(block)

        assert widget.footer_widget._has_content() is False


class TestAgentResponseBlockComposeOutput:
    def test_compose_includes_header(self):
        block = BlockState(type=BlockType.AGENT_RESPONSE, content_input="test")
        widget = AgentResponseBlock(block)
        composed = list(widget.compose())

        assert widget.header in composed

    def test_compose_includes_meta_widget(self):
        block = BlockState(type=BlockType.AGENT_RESPONSE, content_input="test")
        widget = AgentResponseBlock(block)
        composed = list(widget.compose())

        assert widget.meta_widget in composed

    def test_compose_includes_iteration_container(self):
        block = BlockState(type=BlockType.AGENT_RESPONSE, content_input="test")
        widget = AgentResponseBlock(block)
        composed = list(widget.compose())

        assert widget.iteration_container in composed

    def test_compose_includes_response_widget(self):
        block = BlockState(type=BlockType.AGENT_RESPONSE, content_input="test")
        widget = AgentResponseBlock(block)
        composed = list(widget.compose())

        assert widget.response_widget in composed

    def test_compose_includes_action_bar(self):
        block = BlockState(type=BlockType.AGENT_RESPONSE, content_input="test")
        widget = AgentResponseBlock(block)
        composed = list(widget.compose())

        assert widget.action_bar in composed

    def test_compose_excludes_footer_when_no_content(self):
        block = BlockState(type=BlockType.AGENT_RESPONSE, content_input="test")
        block.is_running = False
        block.exit_code = 0
        widget = AgentResponseBlock(block)
        composed = list(widget.compose())

        assert widget.footer_widget not in composed

    def test_compose_includes_footer_when_has_content(self):
        block = BlockState(type=BlockType.AGENT_RESPONSE, content_input="test")
        block.is_running = True
        widget = AgentResponseBlock(block)
        composed = list(widget.compose())

        assert widget.footer_widget in composed


class TestAgentResponseBlockModelTruncation:
    def test_model_exactly_20_chars_not_truncated(self):
        model = "a" * 20
        block = BlockState(
            type=BlockType.AGENT_RESPONSE,
            content_input="test",
            metadata={"model": model},
        )
        widget = AgentResponseBlock(block)
        result = widget._build_meta_text()
        assert model in result
        assert "..." not in result

    def test_model_21_chars_truncated(self):
        model = "a" * 21
        block = BlockState(
            type=BlockType.AGENT_RESPONSE,
            content_input="test",
            metadata={"model": model},
        )
        widget = AgentResponseBlock(block)
        result = widget._build_meta_text()
        assert "..." in result
        assert model not in result

    def test_model_empty_string(self):
        block = BlockState(
            type=BlockType.AGENT_RESPONSE,
            content_input="test",
            metadata={"model": ""},
        )
        widget = AgentResponseBlock(block)
        result = widget._build_meta_text()
        assert result == ""


class TestAgentResponseBlockIterationContainerState:
    def test_iteration_container_has_iterations_property(self):
        block = BlockState(type=BlockType.AGENT_RESPONSE, content_input="test")
        widget = AgentResponseBlock(block)

        assert hasattr(widget.iteration_container, "has_iterations")

    def test_iteration_container_iteration_count_property(self):
        block = BlockState(type=BlockType.AGENT_RESPONSE, content_input="test")
        widget = AgentResponseBlock(block)

        assert hasattr(widget.iteration_container, "iteration_count")
        assert widget.iteration_container.iteration_count == 0

    def test_iteration_container_initially_empty(self):
        block = BlockState(type=BlockType.AGENT_RESPONSE, content_input="test")
        widget = AgentResponseBlock(block)

        assert widget.iteration_container.has_iterations is False
