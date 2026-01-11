"""Tests for BlockState and related models."""

import json

from models import AgentIteration, BlockState, BlockType, ToolCallState


class TestBlockType:
    """Tests for BlockType enum."""

    def test_block_types_exist(self):
        """Verify all block types are defined."""
        assert BlockType.COMMAND.value == "command"
        assert BlockType.AI_RESPONSE.value == "ai"
        assert BlockType.AGENT_RESPONSE.value == "agent"
        assert BlockType.SYSTEM_MSG.value == "system"
        assert BlockType.TOOL_CALL.value == "tool_call"


class TestToolCallState:
    """Tests for ToolCallState dataclass."""

    def test_create_tool_call(self):
        """Test creating a tool call state."""
        tc = ToolCallState(
            id="tc-123",
            tool_name="run_command",
            arguments='{"command": "ls"}',
            status="pending",
        )
        assert tc.id == "tc-123"
        assert tc.tool_name == "run_command"
        assert tc.status == "pending"

    def test_tool_call_to_dict(self):
        """Test serializing tool call to dict."""
        tc = ToolCallState(
            id="tc-123",
            tool_name="run_command",
            arguments='{"command": "ls"}',
            output="file.txt",
            status="success",
            duration=0.5,
        )
        data = tc.to_dict()

        assert data["id"] == "tc-123"
        assert data["tool_name"] == "run_command"
        assert data["status"] == "success"
        assert data["duration"] == 0.5
        assert "timestamp" in data

    def test_tool_call_from_dict(self):
        """Test deserializing tool call from dict."""
        data = {
            "id": "tc-456",
            "tool_name": "read_file",
            "arguments": '{"path": "/tmp/test"}',
            "output": "content",
            "status": "success",
            "duration": 0.1,
            "timestamp": "2024-01-01T12:00:00",
        }
        tc = ToolCallState.from_dict(data)

        assert tc.id == "tc-456"
        assert tc.tool_name == "read_file"
        assert tc.status == "success"

    def test_tool_call_from_dict_minimal(self):
        """Test deserializing with minimal data."""
        data = {"tool_name": "test_tool"}
        tc = ToolCallState.from_dict(data)

        assert tc.tool_name == "test_tool"
        assert tc.status == "pending"
        assert tc.id is not None  # Auto-generated


class TestAgentIteration:
    """Tests for AgentIteration dataclass."""

    def test_create_iteration(self):
        """Test creating an agent iteration."""
        iteration = AgentIteration(
            iteration_number=1,
            thinking="I need to list files",
            status="complete",
        )
        assert iteration.iteration_number == 1
        assert iteration.thinking == "I need to list files"
        assert iteration.status == "complete"

    def test_iteration_with_tool_calls(self):
        """Test iteration with tool calls."""
        tc = ToolCallState(id="tc-1", tool_name="run_command")
        iteration = AgentIteration(
            iteration_number=1,
            tool_calls=[tc],
        )
        assert len(iteration.tool_calls) == 1
        assert iteration.tool_calls[0].tool_name == "run_command"

    def test_iteration_to_dict(self):
        """Test serializing iteration to dict."""
        tc = ToolCallState(id="tc-1", tool_name="run_command")
        iteration = AgentIteration(
            iteration_number=1,
            thinking="thinking...",
            tool_calls=[tc],
            response_fragment="result",
            status="complete",
        )
        data = iteration.to_dict()

        assert data["iteration_number"] == 1
        assert data["thinking"] == "thinking..."
        assert len(data["tool_calls"]) == 1
        assert data["status"] == "complete"

    def test_iteration_from_dict(self):
        """Test deserializing iteration from dict."""
        data = {
            "id": "iter-1",
            "iteration_number": 2,
            "thinking": "Let me check",
            "tool_calls": [{"tool_name": "read_file", "id": "tc-1"}],
            "response_fragment": "Done",
            "status": "complete",
        }
        iteration = AgentIteration.from_dict(data)

        assert iteration.iteration_number == 2
        assert iteration.thinking == "Let me check"
        assert len(iteration.tool_calls) == 1


class TestBlockState:
    """Tests for BlockState dataclass."""

    def test_create_command_block(self):
        """Test creating a command block."""
        block = BlockState(
            type=BlockType.COMMAND,
            content_input="ls -la",
            content_output="total 0",
        )
        assert block.type == BlockType.COMMAND
        assert block.content_input == "ls -la"
        assert block.is_running is True  # Default is True (block starts as running)

    def test_create_ai_block(self):
        """Test creating an AI response block."""
        block = BlockState(
            type=BlockType.AI_RESPONSE,
            content_input="Hello",
            content_output="Hi there!",
            metadata={"provider": "test", "model": "test-model"},
        )
        assert block.type == BlockType.AI_RESPONSE
        assert block.metadata["provider"] == "test"

    def test_block_has_uuid(self):
        """Test that blocks get unique IDs."""
        block1 = BlockState(type=BlockType.COMMAND, content_input="ls")
        block2 = BlockState(type=BlockType.COMMAND, content_input="pwd")
        assert block1.id != block2.id

    def test_block_to_dict(self):
        """Test serializing block to dict."""
        block = BlockState(
            type=BlockType.COMMAND,
            content_input="echo hello",
            content_output="hello",
            exit_code=0,
        )
        data = block.to_dict()

        assert data["type"] == "command"
        assert data["content_input"] == "echo hello"
        assert data["exit_code"] == 0

    def test_block_from_dict(self):
        """Test deserializing block from dict."""
        data = {
            "type": "ai",
            "content_input": "What is Python?",
            "content_output": "A programming language",
            "id": "block-123",
            "timestamp": "2024-01-01T12:00:00",
            "metadata": {"model": "test"},
        }
        block = BlockState.from_dict(data)

        assert block.type == BlockType.AI_RESPONSE
        assert block.content_input == "What is Python?"
        assert block.id == "block-123"

    def test_block_with_iterations(self):
        """Test agent block with iterations."""
        iteration = AgentIteration(iteration_number=1, thinking="test")
        block = BlockState(
            type=BlockType.AGENT_RESPONSE,
            content_input="Do something",
            iterations=[iteration],
        )
        assert len(block.iterations) == 1

    def test_block_roundtrip(self):
        """Test serialization roundtrip."""
        original = BlockState(
            type=BlockType.AI_RESPONSE,
            content_input="test input",
            content_output="test output",
            content_thinking="thinking...",
            metadata={"key": "value"},
        )

        data = original.to_dict()
        restored = BlockState.from_dict(data)

        assert restored.type == original.type
        assert restored.content_input == original.content_input
        assert restored.content_output == original.content_output
        assert restored.content_thinking == original.content_thinking


class TestBlockStateExport:
    """Tests for BlockState export functionality."""

    def test_export_to_json(self):
        """Test exporting blocks to JSON."""
        blocks = [
            BlockState(
                type=BlockType.COMMAND, content_input="ls", content_output="file.txt"
            ),
            BlockState(
                type=BlockType.AI_RESPONSE, content_input="hi", content_output="hello"
            ),
        ]

        # Test that to_dict produces valid JSON
        for block in blocks:
            data = block.to_dict()
            json_str = json.dumps(data)
            assert json_str is not None
            parsed = json.loads(json_str)
            assert parsed["content_input"] == block.content_input
