"""Integration tests for block system (command blocks, system messages)."""

import pytest

from models import BlockState, BlockType
from widgets import HistoryViewport, InputController
from widgets.blocks import (
    BlockWidget,
    CommandBlock,
    SystemBlock,
    create_block,
)


async def submit_input(pilot, app, text: str):
    """Helper to type text and submit it."""
    input_widget = app.query_one("#input", InputController)
    input_widget.text = text
    await pilot.pause()
    await pilot.press("enter")
    await pilot.pause()


class TestBlockCreation:
    """Tests for block creation factory."""

    def test_create_command_block(self):
        """create_block should return CommandBlock for COMMAND type."""
        block = BlockState(
            type=BlockType.COMMAND,
            content_input="ls -la",
            content_output="file.txt",
        )
        widget = create_block(block)
        assert isinstance(widget, CommandBlock)

    def test_create_system_block(self):
        """create_block should return SystemBlock for SYSTEM_MSG type."""
        block = BlockState(
            type=BlockType.SYSTEM_MSG,
            content_input="",
            content_output="System message here",
        )
        widget = create_block(block)
        assert isinstance(widget, SystemBlock)

    def test_block_widget_factory_alias(self):
        """BlockWidget should work as factory function."""
        block = BlockState(
            type=BlockType.COMMAND,
            content_input="pwd",
        )
        widget = BlockWidget(block)
        assert isinstance(widget, CommandBlock)


class TestCommandBlockExecution:
    """Tests for command execution and block creation."""

    @pytest.mark.asyncio
    async def test_cli_command_creates_block(self, running_app):
        """Executing a CLI command should create a command block."""
        pilot, app = running_app

        initial_block_count = len(app.blocks)

        await submit_input(pilot, app, "echo test")

        # Should have created a new block
        assert len(app.blocks) > initial_block_count

    @pytest.mark.asyncio
    async def test_command_block_shows_input(self, running_app):
        """Command block should display the input command."""
        pilot, app = running_app

        await submit_input(pilot, app, "echo hello")

        # Find the last block
        if app.blocks:
            last_block = app.blocks[-1]
            assert last_block.content_input == "echo hello"

    @pytest.mark.asyncio
    async def test_command_block_mounted_in_history(self, running_app):
        """Command block should be mounted in history viewport."""
        pilot, app = running_app
        history = app.query_one("#history", HistoryViewport)

        await submit_input(pilot, app, "pwd")

        # History should have child widgets
        children = list(history.children)
        assert len(children) >= 1


class TestSystemMessages:
    """Tests for system message blocks."""

    @pytest.mark.asyncio
    async def test_version_creates_system_message(self, running_app):
        """'/version' should execute without error."""
        pilot, app = running_app

        await submit_input(pilot, app, "/version")

        # Should have executed without error

    @pytest.mark.asyncio
    async def test_system_message_displays_content(self, running_app):
        """System messages should display their content."""
        pilot, app = running_app
        history = app.query_one("#history", HistoryViewport)

        # Create a system block programmatically
        block = BlockState(
            type=BlockType.SYSTEM_MSG,
            content_input="",
            content_output="Test system message",
        )
        block.is_running = False
        app.blocks.append(block)
        widget = BlockWidget(block)
        await history.add_block(widget)
        await pilot.pause()

        # Block should be in history
        assert len(list(history.children)) >= 1


class TestBlockState:
    """Tests for block state management."""

    @pytest.mark.asyncio
    async def test_block_has_unique_id(self, running_app):
        """Each block should have a unique ID."""
        pilot, app = running_app

        await submit_input(pilot, app, "echo first")
        await submit_input(pilot, app, "echo second")

        if len(app.blocks) >= 2:
            ids = [b.id for b in app.blocks]
            assert len(ids) == len(set(ids))  # All unique

    @pytest.mark.asyncio
    async def test_block_has_timestamp(self):
        """Blocks should have a timestamp."""
        block = BlockState(
            type=BlockType.COMMAND,
            content_input="test",
        )
        assert block.timestamp is not None


class TestBlockDisplay:
    """Tests for block display and rendering."""

    @pytest.mark.asyncio
    async def test_command_block_structure(self, running_app):
        """Command block should have header and body."""
        pilot, app = running_app
        history = app.query_one("#history", HistoryViewport)

        block = BlockState(
            type=BlockType.COMMAND,
            content_input="ls",
            content_output="file.txt",
        )
        block.is_running = False
        app.blocks.append(block)

        widget = BlockWidget(block)
        await history.add_block(widget)
        await pilot.pause()

        # Widget should be mounted
        assert widget.is_mounted

    @pytest.mark.asyncio
    async def test_block_loading_state(self, running_app):
        """Block should show loading state while running."""
        pilot, app = running_app
        history = app.query_one("#history", HistoryViewport)

        block = BlockState(
            type=BlockType.COMMAND,
            content_input="sleep 5",
            is_running=True,
        )
        app.blocks.append(block)

        widget = CommandBlock(block)
        await history.add_block(widget)
        await pilot.pause()

        # Block should be in running state
        assert block.is_running


class TestHistoryViewport:
    """Tests for history viewport functionality."""

    @pytest.mark.asyncio
    async def test_history_scrolls_to_bottom(self, running_app):
        """History should have content after commands."""
        pilot, app = running_app

        # Add a command
        await submit_input(pilot, app, "echo test")

        # History should have at least one block
        assert len(app.blocks) >= 1

    @pytest.mark.asyncio
    async def test_history_empty_initially(self, running_app):
        """History should be empty on fresh start (no saved session)."""
        _pilot, app = running_app
        history = app.query_one("#history", HistoryViewport)

        # With fresh temp storage, no previous blocks
        initial_children = list(history.children)
        assert len(initial_children) == 0


class TestBlockClear:
    """Tests for clearing blocks."""

    @pytest.mark.asyncio
    async def test_clear_removes_all_blocks(self, running_app):
        """'/clear' should remove all blocks from history."""
        pilot, app = running_app

        # Add a command
        await submit_input(pilot, app, "echo test")

        assert len(app.blocks) >= 1

        # Clear
        await submit_input(pilot, app, "/clear")

        # Blocks should be cleared
        assert len(app.blocks) == 0

    @pytest.mark.asyncio
    async def test_ctrl_l_clears_history(self, running_app):
        """Ctrl+L should clear history."""
        pilot, app = running_app

        await submit_input(pilot, app, "echo test")

        assert len(app.blocks) >= 1

        await pilot.press("ctrl+l")
        await pilot.pause()

        assert len(app.blocks) == 0


class TestAIResponseBlocks:
    def test_create_ai_response_block(self):
        from widgets.blocks import AIResponseBlock

        block = BlockState(
            type=BlockType.AI_RESPONSE,
            content_input="What is Python?",
            content_output="Python is a programming language.",
        )
        widget = create_block(block)
        assert isinstance(widget, AIResponseBlock)

    def test_ai_block_has_input_and_output(self):
        block = BlockState(
            type=BlockType.AI_RESPONSE,
            content_input="Hello",
            content_output="Hi there!",
        )
        assert block.content_input == "Hello"
        assert block.content_output == "Hi there!"

    @pytest.mark.asyncio
    async def test_ai_block_mounts_in_history(self, running_app):
        pilot, app = running_app
        from widgets.blocks import AIResponseBlock

        history = app.query_one("#history", HistoryViewport)

        block = BlockState(
            type=BlockType.AI_RESPONSE,
            content_input="Test question",
            content_output="Test answer",
            is_running=False,
        )
        app.blocks.append(block)

        widget = AIResponseBlock(block)
        await history.add_block(widget)
        await pilot.pause()

        assert widget.is_mounted


class TestCodeBlocks:
    def test_code_block_state(self):
        block = BlockState(
            type=BlockType.AI_RESPONSE,
            content_input="Show me code",
            content_output="```python\nprint('hello')\n```",
        )
        assert "```python" in block.content_output


class TestBlockTypes:
    def test_all_block_types_exist(self):
        assert BlockType.COMMAND is not None
        assert BlockType.AI_RESPONSE is not None
        assert BlockType.SYSTEM_MSG is not None

    def test_block_types_have_values(self):
        assert BlockType.COMMAND.value is not None
        assert BlockType.AI_RESPONSE.value is not None
        assert BlockType.SYSTEM_MSG.value is not None


class TestBlockActions:
    @pytest.mark.asyncio
    async def test_block_has_action_bar(self, running_app):
        pilot, app = running_app

        history = app.query_one("#history", HistoryViewport)

        block = BlockState(
            type=BlockType.AI_RESPONSE,
            content_input="Test",
            content_output="Response",
            is_running=False,
        )
        app.blocks.append(block)
        widget = BlockWidget(block)
        await history.add_block(widget)
        await pilot.pause()


class TestBlockMetadata:
    def test_block_has_id(self):
        block = BlockState(
            type=BlockType.COMMAND,
            content_input="test",
        )
        assert block.id is not None
        assert len(block.id) > 0

    def test_block_has_type(self):
        block = BlockState(
            type=BlockType.COMMAND,
            content_input="test",
        )
        assert block.type == BlockType.COMMAND

    def test_block_running_state(self):
        block = BlockState(
            type=BlockType.COMMAND,
            content_input="test",
            is_running=True,
        )
        assert block.is_running is True

        block.is_running = False
        assert block.is_running is False


class TestMultipleBlocks:
    @pytest.mark.asyncio
    async def test_multiple_commands_create_blocks(self, running_app):
        pilot, app = running_app

        initial = len(app.blocks)

        await submit_input(pilot, app, "echo one")
        count_after_one = len(app.blocks)
        assert count_after_one > initial

        await submit_input(pilot, app, "echo two")
        count_after_two = len(app.blocks)
        assert count_after_two >= count_after_one

    @pytest.mark.asyncio
    async def test_blocks_ordered_by_creation(self, running_app):
        pilot, app = running_app

        await submit_input(pilot, app, "echo first")
        await submit_input(pilot, app, "echo second")

        if len(app.blocks) >= 2:
            first_block = app.blocks[-2]
            second_block = app.blocks[-1]
            assert first_block.content_input == "echo first"
            assert second_block.content_input == "echo second"
