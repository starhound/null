"""Tests for ai/bedrock.py - BedrockProvider implementation."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from ai.bedrock import BedrockProvider
from ai.base import Message


class TestBedrockProviderInit:
    """Tests for BedrockProvider initialization."""

    def test_init_sets_region_and_model(self):
        """Provider stores region and model."""
        with patch("ai.bedrock.boto3") as mock_boto3:
            mock_boto3.client.return_value = MagicMock()
            provider = BedrockProvider(
                region_name="us-east-1", model="anthropic.claude-3-sonnet"
            )
            assert provider.model == "anthropic.claude-3-sonnet"

    def test_init_uses_default_model(self):
        """Provider uses default model when not specified."""
        with patch("ai.bedrock.boto3") as mock_boto3:
            mock_boto3.client.return_value = MagicMock()
            provider = BedrockProvider(region_name="us-west-2")
            assert provider.model == "anthropic.claude-v2"

    def test_init_creates_boto3_clients(self):
        """Should create both bedrock-runtime and bedrock clients."""
        with patch("ai.bedrock.boto3") as mock_boto3:
            mock_boto3.client.return_value = MagicMock()
            BedrockProvider(region_name="us-east-1")

            calls = mock_boto3.client.call_args_list
            service_names = [call[0][0] for call in calls]
            assert "bedrock-runtime" in service_names
            assert "bedrock" in service_names


class TestBedrockProviderSupportsTools:
    """Tests for supports_tools method."""

    def test_supports_tools_true_for_claude(self):
        """Claude models support tool calling."""
        with patch("ai.bedrock.boto3") as mock_boto3:
            mock_boto3.client.return_value = MagicMock()
            provider = BedrockProvider(
                region_name="us-east-1", model="anthropic.claude-3-sonnet"
            )
            assert provider.supports_tools() is True

    def test_supports_tools_false_for_non_claude(self):
        """Non-Claude models don't support tools."""
        with patch("ai.bedrock.boto3") as mock_boto3:
            mock_boto3.client.return_value = MagicMock()
            provider = BedrockProvider(
                region_name="us-east-1", model="meta.llama3-8b-instruct"
            )
            assert provider.supports_tools() is False


class TestBedrockProviderConvertTools:
    """Tests for _convert_tools method."""

    def test_convert_tools_to_bedrock_format(self):
        """Should convert OpenAI tool format to Bedrock."""
        with patch("ai.bedrock.boto3") as mock_boto3:
            mock_boto3.client.return_value = MagicMock()
            provider = BedrockProvider(region_name="us-east-1")

            tools = [
                {
                    "type": "function",
                    "function": {
                        "name": "search",
                        "description": "Search the web",
                        "parameters": {
                            "type": "object",
                            "properties": {"query": {"type": "string"}},
                        },
                    },
                }
            ]

            result = provider._convert_tools(tools)

            assert len(result) == 1
            assert result[0]["name"] == "search"
            assert result[0]["description"] == "Search the web"
            assert result[0]["input_schema"]["type"] == "object"

    def test_convert_tools_handles_missing_fields(self):
        """Should use defaults for missing fields."""
        with patch("ai.bedrock.boto3") as mock_boto3:
            mock_boto3.client.return_value = MagicMock()
            provider = BedrockProvider(region_name="us-east-1")

            tools = [{"type": "function", "function": {"name": "test_tool"}}]

            result = provider._convert_tools(tools)

            assert result[0]["description"] == ""
            assert result[0]["input_schema"] == {"type": "object", "properties": {}}

    def test_convert_tools_skips_non_function_types(self):
        """Should only convert function-type tools."""
        with patch("ai.bedrock.boto3") as mock_boto3:
            mock_boto3.client.return_value = MagicMock()
            provider = BedrockProvider(region_name="us-east-1")

            tools = [
                {"type": "other", "data": {}},
                {"type": "function", "function": {"name": "valid"}},
            ]

            result = provider._convert_tools(tools)

            assert len(result) == 1
            assert result[0]["name"] == "valid"


class TestBedrockProviderBuildClaudeMessages:
    """Tests for _build_claude_messages method."""

    def test_build_messages_adds_current_prompt(self):
        """Should add current prompt as final user message."""
        with patch("ai.bedrock.boto3") as mock_boto3:
            mock_boto3.client.return_value = MagicMock()
            provider = BedrockProvider(region_name="us-east-1")

            result = provider._build_claude_messages(prompt="Hello", messages=[])

            assert len(result) == 1
            assert result[0] == {"role": "user", "content": "Hello"}

    def test_build_messages_preserves_history(self):
        """Should include history messages."""
        with patch("ai.bedrock.boto3") as mock_boto3:
            mock_boto3.client.return_value = MagicMock()
            provider = BedrockProvider(region_name="us-east-1")

            messages: list[Message] = [
                {"role": "user", "content": "Hi"},
                {"role": "assistant", "content": "Hello!"},
            ]
            result = provider._build_claude_messages(
                prompt="How are you?", messages=messages
            )

            assert len(result) == 3
            assert result[0]["content"] == "Hi"
            assert result[1]["content"] == "Hello!"
            assert result[2]["content"] == "How are you?"

    def test_build_messages_skips_system_messages(self):
        """Should skip system role messages (handled separately)."""
        with patch("ai.bedrock.boto3") as mock_boto3:
            mock_boto3.client.return_value = MagicMock()
            provider = BedrockProvider(region_name="us-east-1")

            messages: list[Message] = [
                {"role": "system", "content": "Be helpful"},
                {"role": "user", "content": "Hi"},
            ]
            result = provider._build_claude_messages(prompt="Test", messages=messages)

            assert len(result) == 2
            assert all(m["role"] != "system" for m in result)

    def test_build_messages_converts_tool_calls(self):
        """Should convert tool_calls to Bedrock tool_use format."""
        with patch("ai.bedrock.boto3") as mock_boto3:
            mock_boto3.client.return_value = MagicMock()
            provider = BedrockProvider(region_name="us-east-1")

            messages: list[Message] = [
                {
                    "role": "assistant",
                    "tool_calls": [
                        {
                            "id": "call_1",
                            "function": {
                                "name": "search",
                                "arguments": '{"query": "test"}',
                            },
                        }
                    ],
                },
            ]
            result = provider._build_claude_messages(
                prompt="Continue", messages=messages
            )

            assert len(result) == 2
            tool_msg = result[0]
            assert tool_msg["role"] == "assistant"
            assert len(tool_msg["content"]) == 1
            assert tool_msg["content"][0]["type"] == "tool_use"
            assert tool_msg["content"][0]["name"] == "search"
            assert tool_msg["content"][0]["input"] == {"query": "test"}

    def test_build_messages_handles_tool_results(self):
        """Should convert tool role messages to user with tool_result."""
        with patch("ai.bedrock.boto3") as mock_boto3:
            mock_boto3.client.return_value = MagicMock()
            provider = BedrockProvider(region_name="us-east-1")

            messages: list[Message] = [
                {"role": "tool", "tool_call_id": "call_1", "content": "Result data"},
            ]
            result = provider._build_claude_messages(
                prompt="Continue", messages=messages
            )

            assert len(result) == 2
            tool_result_msg = result[0]
            assert tool_result_msg["role"] == "user"
            assert tool_result_msg["content"][0]["type"] == "tool_result"
            assert tool_result_msg["content"][0]["tool_use_id"] == "call_1"


class TestBedrockProviderGenerate:
    """Tests for generate method."""

    @pytest.mark.asyncio
    async def test_generate_yields_text_for_claude(self):
        """Should yield text from Claude streaming response."""
        with patch("ai.bedrock.boto3") as mock_boto3:
            mock_client = MagicMock()
            mock_boto3.client.return_value = mock_client

            provider = BedrockProvider(
                region_name="us-east-1", model="anthropic.claude-3-sonnet"
            )

            # Mock streaming response
            chunk1 = {
                "chunk": {
                    "bytes": json.dumps(
                        {
                            "type": "content_block_delta",
                            "delta": {"type": "text_delta", "text": "Hello"},
                        }
                    ).encode()
                }
            }
            chunk2 = {
                "chunk": {
                    "bytes": json.dumps(
                        {
                            "type": "content_block_delta",
                            "delta": {"type": "text_delta", "text": " world"},
                        }
                    ).encode()
                }
            }

            mock_client.invoke_model_with_response_stream.return_value = {
                "body": [chunk1, chunk2]
            }

            chunks = []
            async for chunk in provider.generate(
                prompt="Hi", messages=[], system_prompt="Be helpful"
            ):
                chunks.append(chunk)

            assert "Hello" in chunks
            assert " world" in chunks

    @pytest.mark.asyncio
    async def test_generate_handles_exception(self):
        """Should yield error message on exception."""
        with patch("ai.bedrock.boto3") as mock_boto3:
            mock_client = MagicMock()
            mock_boto3.client.return_value = mock_client

            provider = BedrockProvider(region_name="us-east-1")
            mock_client.invoke_model_with_response_stream.side_effect = Exception(
                "AWS error"
            )

            chunks = []
            async for chunk in provider.generate(prompt="Hi", messages=[]):
                chunks.append(chunk)

            assert len(chunks) == 1
            assert "Error: AWS error" in chunks[0]

    @pytest.mark.asyncio
    async def test_generate_unsupported_model_family(self):
        """Should yield error for unsupported model families."""
        with patch("ai.bedrock.boto3") as mock_boto3:
            mock_boto3.client.return_value = MagicMock()
            provider = BedrockProvider(
                region_name="us-east-1", model="amazon.titan-unsupported"
            )

            chunks = []
            async for chunk in provider.generate(prompt="Hi", messages=[]):
                chunks.append(chunk)

            assert any("Unsupported" in c for c in chunks)


class TestBedrockProviderGenerateWithTools:
    """Tests for generate_with_tools method."""

    @pytest.mark.asyncio
    async def test_generate_with_tools_yields_text(self):
        """Should yield text from content_block_delta events."""
        with patch("ai.bedrock.boto3") as mock_boto3:
            mock_client = MagicMock()
            mock_boto3.client.return_value = mock_client

            provider = BedrockProvider(
                region_name="us-east-1", model="anthropic.claude-3-sonnet"
            )

            chunk1 = {
                "chunk": {
                    "bytes": json.dumps(
                        {
                            "type": "content_block_delta",
                            "delta": {"type": "text_delta", "text": "Hello"},
                        }
                    ).encode()
                }
            }
            chunk2 = {"chunk": {"bytes": json.dumps({"type": "message_stop"}).encode()}}

            mock_client.invoke_model_with_response_stream.return_value = {
                "body": [chunk1, chunk2]
            }

            chunks = []
            async for chunk in provider.generate_with_tools(
                prompt="Hi", messages=[], tools=[]
            ):
                chunks.append(chunk)

            assert any(c.text == "Hello" for c in chunks)
            assert chunks[-1].is_complete

    @pytest.mark.asyncio
    async def test_generate_with_tools_handles_tool_use(self):
        """Should collect tool calls from tool_use events."""
        with patch("ai.bedrock.boto3") as mock_boto3:
            mock_client = MagicMock()
            mock_boto3.client.return_value = mock_client

            provider = BedrockProvider(
                region_name="us-east-1", model="anthropic.claude-3-sonnet"
            )

            events = [
                {
                    "chunk": {
                        "bytes": json.dumps(
                            {
                                "type": "content_block_start",
                                "content_block": {
                                    "type": "tool_use",
                                    "id": "call_1",
                                    "name": "search",
                                },
                            }
                        ).encode()
                    }
                },
                {
                    "chunk": {
                        "bytes": json.dumps(
                            {
                                "type": "content_block_delta",
                                "delta": {
                                    "type": "input_json_delta",
                                    "partial_json": '{"query": "test"}',
                                },
                            }
                        ).encode()
                    }
                },
                {
                    "chunk": {
                        "bytes": json.dumps({"type": "content_block_stop"}).encode()
                    }
                },
                {"chunk": {"bytes": json.dumps({"type": "message_stop"}).encode()}},
            ]

            mock_client.invoke_model_with_response_stream.return_value = {
                "body": events
            }

            chunks = []
            async for chunk in provider.generate_with_tools(
                prompt="Search for test", messages=[], tools=[]
            ):
                chunks.append(chunk)

            final = chunks[-1]
            assert final.is_complete
            assert len(final.tool_calls) == 1
            assert final.tool_calls[0].name == "search"
            assert final.tool_calls[0].arguments == {"query": "test"}

    @pytest.mark.asyncio
    async def test_generate_with_tools_handles_usage(self):
        """Should capture token usage from events."""
        with patch("ai.bedrock.boto3") as mock_boto3:
            mock_client = MagicMock()
            mock_boto3.client.return_value = mock_client

            provider = BedrockProvider(
                region_name="us-east-1", model="anthropic.claude-3-sonnet"
            )

            events = [
                {
                    "chunk": {
                        "bytes": json.dumps(
                            {
                                "type": "message_start",
                                "message": {"usage": {"input_tokens": 100}},
                            }
                        ).encode()
                    }
                },
                {
                    "chunk": {
                        "bytes": json.dumps(
                            {
                                "type": "message_delta",
                                "delta": {},
                                "usage": {"output_tokens": 50},
                            }
                        ).encode()
                    }
                },
                {"chunk": {"bytes": json.dumps({"type": "message_stop"}).encode()}},
            ]

            mock_client.invoke_model_with_response_stream.return_value = {
                "body": events
            }

            chunks = []
            async for chunk in provider.generate_with_tools(
                prompt="Hi", messages=[], tools=[]
            ):
                chunks.append(chunk)

            final = chunks[-1]
            assert final.usage is not None
            assert final.usage.input_tokens == 100
            assert final.usage.output_tokens == 50

    @pytest.mark.asyncio
    async def test_generate_with_tools_handles_exception(self):
        """Should yield error StreamChunk on exception."""
        with patch("ai.bedrock.boto3") as mock_boto3:
            mock_client = MagicMock()
            mock_boto3.client.return_value = mock_client

            provider = BedrockProvider(
                region_name="us-east-1", model="anthropic.claude-3-sonnet"
            )
            mock_client.invoke_model_with_response_stream.side_effect = Exception(
                "AWS error"
            )

            chunks = []
            async for chunk in provider.generate_with_tools(
                prompt="Hi", messages=[], tools=[]
            ):
                chunks.append(chunk)

            assert len(chunks) == 1
            assert "Error: AWS error" in chunks[0].text
            assert chunks[0].is_complete

    @pytest.mark.asyncio
    async def test_generate_with_tools_non_claude_falls_back(self):
        """Non-Claude models should fall back to regular generate."""
        with patch("ai.bedrock.boto3") as mock_boto3:
            mock_client = MagicMock()
            mock_boto3.client.return_value = mock_client

            provider = BedrockProvider(
                region_name="us-east-1", model="meta.llama3-8b-instruct"
            )

            chunk = {
                "chunk": {
                    "bytes": json.dumps({"generation": "Hello from Llama"}).encode()
                }
            }

            mock_client.invoke_model_with_response_stream.return_value = {
                "body": [chunk]
            }

            chunks = []
            async for chunk in provider.generate_with_tools(
                prompt="Hi", messages=[], tools=[]
            ):
                chunks.append(chunk)

            assert any(c.text == "Hello from Llama" for c in chunks)
            assert chunks[-1].is_complete


class TestBedrockProviderListModels:
    """Tests for list_models method."""

    @pytest.mark.asyncio
    async def test_list_models_returns_model_ids(self):
        """Should return list of model IDs from Bedrock."""
        with patch("ai.bedrock.boto3") as mock_boto3:
            mock_client = MagicMock()
            mock_bedrock = MagicMock()
            mock_boto3.client.side_effect = [mock_client, mock_bedrock]

            provider = BedrockProvider(region_name="us-east-1")

            mock_bedrock.list_foundation_models.return_value = {
                "modelSummaries": [
                    {"modelId": "anthropic.claude-v2"},
                    {"modelId": "anthropic.claude-3-sonnet"},
                ]
            }
            provider.bedrock = mock_bedrock

            models = await provider.list_models()

            assert "anthropic.claude-v2" in models
            assert "anthropic.claude-3-sonnet" in models

    @pytest.mark.asyncio
    async def test_list_models_returns_empty_on_error(self):
        """Should return empty list on exception."""
        with patch("ai.bedrock.boto3") as mock_boto3:
            mock_client = MagicMock()
            mock_bedrock = MagicMock()
            mock_boto3.client.side_effect = [mock_client, mock_bedrock]

            provider = BedrockProvider(region_name="us-east-1")
            mock_bedrock.list_foundation_models.side_effect = Exception("Access denied")
            provider.bedrock = mock_bedrock

            models = await provider.list_models()

            assert models == []


class TestBedrockProviderValidateConnection:
    """Tests for validate_connection method."""

    @pytest.mark.asyncio
    async def test_validate_connection_returns_true_on_success(self):
        """Should return True when Bedrock is reachable."""
        with patch("ai.bedrock.boto3") as mock_boto3:
            mock_client = MagicMock()
            mock_bedrock = MagicMock()
            mock_boto3.client.side_effect = [mock_client, mock_bedrock]

            provider = BedrockProvider(region_name="us-east-1")
            mock_bedrock.list_foundation_models.return_value = {"modelSummaries": []}
            provider.bedrock = mock_bedrock

            result = await provider.validate_connection()

            assert result is True

    @pytest.mark.asyncio
    async def test_validate_connection_returns_false_on_error(self):
        """Should return False on exception."""
        with patch("ai.bedrock.boto3") as mock_boto3:
            mock_client = MagicMock()
            mock_bedrock = MagicMock()
            mock_boto3.client.side_effect = [mock_client, mock_bedrock]

            provider = BedrockProvider(region_name="us-east-1")
            mock_bedrock.list_foundation_models.side_effect = Exception("Auth failed")
            provider.bedrock = mock_bedrock

            result = await provider.validate_connection()

            assert result is False
