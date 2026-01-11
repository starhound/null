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


class TestExportToJson:
    def test_returns_valid_json_string(self):
        from models import export_to_json

        blocks = [
            BlockState(
                type=BlockType.COMMAND, content_input="ls", content_output="file.txt"
            ),
        ]
        result = export_to_json(blocks)
        parsed = json.loads(result)
        assert "blocks" in parsed
        assert "exported_at" in parsed
        assert "version" in parsed

    def test_empty_blocks_produces_empty_array(self):
        from models import export_to_json

        result = export_to_json([])
        parsed = json.loads(result)
        assert parsed["blocks"] == []

    def test_preserves_block_content(self):
        from models import export_to_json

        blocks = [
            BlockState(
                type=BlockType.COMMAND,
                content_input="echo hello",
                content_output="hello",
            ),
        ]
        result = export_to_json(blocks)
        parsed = json.loads(result)
        assert parsed["blocks"][0]["content_input"] == "echo hello"
        assert parsed["blocks"][0]["content_output"] == "hello"

    def test_multiple_blocks_serialized(self):
        from models import export_to_json

        blocks = [
            BlockState(type=BlockType.COMMAND, content_input="cmd1"),
            BlockState(type=BlockType.AI_RESPONSE, content_input="query"),
            BlockState(type=BlockType.SYSTEM_MSG, content_input="notice"),
        ]
        result = export_to_json(blocks)
        parsed = json.loads(result)
        assert len(parsed["blocks"]) == 3


class TestExportToMarkdown:
    def test_returns_string(self):
        from models import export_to_markdown

        blocks = [BlockState(type=BlockType.COMMAND, content_input="ls")]
        result = export_to_markdown(blocks)
        assert isinstance(result, str)

    def test_contains_header(self):
        from models import export_to_markdown

        result = export_to_markdown([])
        assert "# Null Session" in result

    def test_command_block_formatted(self):
        from models import export_to_markdown

        blocks = [
            BlockState(
                type=BlockType.COMMAND,
                content_input="ls -la",
                content_output="file.txt",
            ),
        ]
        result = export_to_markdown(blocks)
        assert "## Command" in result
        assert "$ ls -la" in result
        assert "file.txt" in result

    def test_command_with_non_zero_exit_shows_code(self):
        from models import export_to_markdown

        block = BlockState(type=BlockType.COMMAND, content_input="bad_cmd")
        block.exit_code = 127
        result = export_to_markdown([block])
        assert "Exit code: 127" in result

    def test_ai_response_formatted(self):
        from models import export_to_markdown

        blocks = [
            BlockState(
                type=BlockType.AI_RESPONSE,
                content_input="What is Python?",
                content_output="A programming language",
            ),
        ]
        result = export_to_markdown(blocks)
        assert "## AI Conversation" in result
        assert "What is Python?" in result
        assert "A programming language" in result

    def test_ai_response_with_metadata(self):
        from models import export_to_markdown

        block = BlockState(
            type=BlockType.AI_RESPONSE,
            content_input="test",
            content_output="response",
        )
        block.metadata = {"model": "gpt-4", "tokens": "100/50"}
        result = export_to_markdown([block])
        assert "Model: gpt-4" in result
        assert "Tokens: 100/50" in result

    def test_agent_response_with_iterations(self):
        from models import export_to_markdown

        tc = ToolCallState(
            id="tc1",
            tool_name="run_command",
            arguments='{"cmd": "ls"}',
            output="file.txt",
            status="success",
        )
        iteration = AgentIteration(
            iteration_number=1, thinking="I will list files", tool_calls=[tc]
        )
        block = BlockState(
            type=BlockType.AGENT_RESPONSE,
            content_input="List files",
            iterations=[iteration],
            content_output="Done listing files",
        )
        result = export_to_markdown([block])
        assert "## Agent Session" in result
        assert "### Iteration 1" in result
        assert "I will list files" in result
        assert "run_command" in result

    def test_tool_call_block_formatted(self):
        from models import export_to_markdown

        block = BlockState(type=BlockType.TOOL_CALL, content_input="tool")
        block.metadata = {"tool_name": "read_file", "arguments": '{"path": "/tmp"}'}
        block.content_output = "file content"
        result = export_to_markdown([block])
        assert "## Tool Call" in result
        assert "read_file" in result

    def test_ai_query_formatted(self):
        from models import export_to_markdown

        blocks = [BlockState(type=BlockType.AI_QUERY, content_input="How do I?")]
        result = export_to_markdown(blocks)
        assert "How do I?" in result

    def test_contains_footer(self):
        from models import export_to_markdown

        result = export_to_markdown([])
        assert "Exported from Null Terminal" in result


class TestSaveExport:
    def test_creates_json_file(self, tmp_path, monkeypatch):
        from models import save_export

        monkeypatch.setattr("models.Path.home", lambda: tmp_path)
        blocks = [BlockState(type=BlockType.COMMAND, content_input="ls")]

        filepath = save_export(blocks, format="json")

        assert filepath.exists()
        assert filepath.suffix == ".json"
        assert "null-export" in filepath.name

    def test_creates_markdown_file(self, tmp_path, monkeypatch):
        from models import save_export

        monkeypatch.setattr("models.Path.home", lambda: tmp_path)
        blocks = [BlockState(type=BlockType.COMMAND, content_input="ls")]

        filepath = save_export(blocks, format="md")

        assert filepath.exists()
        assert filepath.suffix == ".md"

    def test_creates_export_directory(self, tmp_path, monkeypatch):
        from models import save_export

        monkeypatch.setattr("models.Path.home", lambda: tmp_path)
        blocks = [BlockState(type=BlockType.COMMAND, content_input="ls")]

        save_export(blocks, format="md")

        export_dir = tmp_path / ".null" / "exports"
        assert export_dir.exists()

    def test_json_file_contains_valid_json(self, tmp_path, monkeypatch):
        from models import save_export

        monkeypatch.setattr("models.Path.home", lambda: tmp_path)
        blocks = [BlockState(type=BlockType.COMMAND, content_input="test_cmd")]

        filepath = save_export(blocks, format="json")

        content = filepath.read_text()
        parsed = json.loads(content)
        assert parsed["blocks"][0]["content_input"] == "test_cmd"

    def test_default_format_is_markdown(self, tmp_path, monkeypatch):
        from models import save_export

        monkeypatch.setattr("models.Path.home", lambda: tmp_path)
        blocks = [BlockState(type=BlockType.COMMAND, content_input="ls")]

        filepath = save_export(blocks)

        assert filepath.suffix == ".md"
