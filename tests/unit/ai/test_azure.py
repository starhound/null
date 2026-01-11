import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from ai.azure import AzureProvider
from ai.base import Message, StreamChunk, TokenUsage


class TestAzureProviderInit:
    def test_init_sets_model(self):
        with patch("ai.azure.AsyncAzureOpenAI"):
            provider = AzureProvider(
                endpoint="https://test.openai.azure.com",
                api_key="test-key",
                api_version="2024-02-15-preview",
                model="gpt-4-deployment",
            )
        assert provider.model == "gpt-4-deployment"

    def test_init_sets_deployment_name(self):
        with patch("ai.azure.AsyncAzureOpenAI"):
            provider = AzureProvider(
                endpoint="https://test.openai.azure.com",
                api_key="test-key",
                api_version="2024-02-15-preview",
                model="my-deployment",
            )
        assert provider.deployment_name == "my-deployment"

    def test_init_creates_client_with_correct_params(self):
        with patch("ai.azure.AsyncAzureOpenAI") as mock_client:
            AzureProvider(
                endpoint="https://test.openai.azure.com",
                api_key="test-key",
                api_version="2024-02-15-preview",
                model="gpt-4",
            )
        call_kwargs = mock_client.call_args[1]
        assert call_kwargs["azure_endpoint"] == "https://test.openai.azure.com"
        assert call_kwargs["api_key"] == "test-key"
        assert call_kwargs["api_version"] == "2024-02-15-preview"

    def test_init_sets_timeout(self):
        with patch("ai.azure.AsyncAzureOpenAI") as mock_client:
            AzureProvider(
                endpoint="https://test.openai.azure.com",
                api_key="test-key",
                api_version="2024-02-15-preview",
                model="gpt-4",
            )
        call_kwargs = mock_client.call_args[1]
        timeout = call_kwargs["timeout"]
        assert timeout.read == 120.0
        assert timeout.connect == 3.0


class TestAzureProviderSupportsTools:
    def test_supports_tools_returns_true(self):
        with patch("ai.azure.AsyncAzureOpenAI"):
            provider = AzureProvider(
                endpoint="https://test.openai.azure.com",
                api_key="test-key",
                api_version="2024-02-15-preview",
                model="gpt-4",
            )
        assert provider.supports_tools() is True


class TestAzureProviderBuildMessages:
    def test_build_messages_adds_system_prompt(self):
        with patch("ai.azure.AsyncAzureOpenAI"):
            provider = AzureProvider(
                endpoint="https://test.openai.azure.com",
                api_key="test-key",
                api_version="2024-02-15-preview",
                model="gpt-4",
            )

        result = provider._build_messages(
            prompt="Hello", messages=[], system_prompt="Be concise"
        )

        assert result[0]["role"] == "system"
        assert result[0]["content"] == "Be concise"

    def test_build_messages_uses_default_system_prompt(self):
        with patch("ai.azure.AsyncAzureOpenAI"):
            provider = AzureProvider(
                endpoint="https://test.openai.azure.com",
                api_key="test-key",
                api_version="2024-02-15-preview",
                model="gpt-4",
            )

        result = provider._build_messages(
            prompt="Hello", messages=[], system_prompt=None
        )

        assert result[0]["role"] == "system"
        assert "terminal" in result[0]["content"].lower()

    def test_build_messages_includes_history(self):
        with patch("ai.azure.AsyncAzureOpenAI"):
            provider = AzureProvider(
                endpoint="https://test.openai.azure.com",
                api_key="test-key",
                api_version="2024-02-15-preview",
                model="gpt-4",
            )

        messages: list[Message] = [
            {"role": "user", "content": "Hi"},
            {"role": "assistant", "content": "Hello!"},
        ]
        result = provider._build_messages(
            prompt="Test", messages=messages, system_prompt="Be helpful"
        )

        assert len(result) == 4
        assert result[1]["content"] == "Hi"
        assert result[2]["content"] == "Hello!"
        assert result[3]["content"] == "Test"

    def test_build_messages_preserves_tool_calls(self):
        with patch("ai.azure.AsyncAzureOpenAI"):
            provider = AzureProvider(
                endpoint="https://test.openai.azure.com",
                api_key="test-key",
                api_version="2024-02-15-preview",
                model="gpt-4",
            )

        tool_calls = [{"id": "call_1", "function": {"name": "test"}}]
        messages: list[Message] = [
            {"role": "assistant", "content": "", "tool_calls": tool_calls}
        ]
        result = provider._build_messages(
            prompt="Continue", messages=messages, system_prompt=None
        )

        assert result[1]["tool_calls"] == tool_calls

    def test_build_messages_preserves_tool_call_id(self):
        with patch("ai.azure.AsyncAzureOpenAI"):
            provider = AzureProvider(
                endpoint="https://test.openai.azure.com",
                api_key="test-key",
                api_version="2024-02-15-preview",
                model="gpt-4",
            )

        messages: list[Message] = [
            {"role": "tool", "content": "Result", "tool_call_id": "call_1"}
        ]
        result = provider._build_messages(
            prompt="Continue", messages=messages, system_prompt=None
        )

        assert result[1]["tool_call_id"] == "call_1"


class TestAzureProviderGenerate:
    @pytest.mark.asyncio
    async def test_generate_yields_content(self):
        with patch("ai.azure.AsyncAzureOpenAI"):
            provider = AzureProvider(
                endpoint="https://test.openai.azure.com",
                api_key="test-key",
                api_version="2024-02-15-preview",
                model="gpt-4",
            )

        mock_chunk1 = MagicMock()
        mock_chunk1.choices = [MagicMock(delta=MagicMock(content="Hello"))]
        mock_chunk2 = MagicMock()
        mock_chunk2.choices = [MagicMock(delta=MagicMock(content=" world"))]

        async def mock_stream():
            yield mock_chunk1
            yield mock_chunk2

        provider.client.chat.completions.create = AsyncMock(return_value=mock_stream())

        chunks = []
        async for chunk in provider.generate(prompt="Hi", messages=[]):
            chunks.append(chunk)

        assert chunks == ["Hello", " world"]

    @pytest.mark.asyncio
    async def test_generate_handles_empty_content(self):
        with patch("ai.azure.AsyncAzureOpenAI"):
            provider = AzureProvider(
                endpoint="https://test.openai.azure.com",
                api_key="test-key",
                api_version="2024-02-15-preview",
                model="gpt-4",
            )

        mock_chunk = MagicMock()
        mock_chunk.choices = [MagicMock(delta=MagicMock(content=None))]

        async def mock_stream():
            yield mock_chunk

        provider.client.chat.completions.create = AsyncMock(return_value=mock_stream())

        chunks = []
        async for chunk in provider.generate(prompt="Hi", messages=[]):
            chunks.append(chunk)

        assert chunks == []

    @pytest.mark.asyncio
    async def test_generate_handles_empty_choices(self):
        with patch("ai.azure.AsyncAzureOpenAI"):
            provider = AzureProvider(
                endpoint="https://test.openai.azure.com",
                api_key="test-key",
                api_version="2024-02-15-preview",
                model="gpt-4",
            )

        mock_chunk = MagicMock()
        mock_chunk.choices = []

        async def mock_stream():
            yield mock_chunk

        provider.client.chat.completions.create = AsyncMock(return_value=mock_stream())

        chunks = []
        async for chunk in provider.generate(prompt="Hi", messages=[]):
            chunks.append(chunk)

        assert chunks == []

    @pytest.mark.asyncio
    async def test_generate_handles_exception(self):
        with patch("ai.azure.AsyncAzureOpenAI"):
            provider = AzureProvider(
                endpoint="https://test.openai.azure.com",
                api_key="test-key",
                api_version="2024-02-15-preview",
                model="gpt-4",
            )

        provider.client.chat.completions.create = AsyncMock(
            side_effect=Exception("API error")
        )

        chunks = []
        async for chunk in provider.generate(prompt="Hi", messages=[]):
            chunks.append(chunk)

        assert len(chunks) == 1
        assert "Error: API error" in chunks[0]

    @pytest.mark.asyncio
    async def test_generate_with_system_prompt(self):
        with patch("ai.azure.AsyncAzureOpenAI"):
            provider = AzureProvider(
                endpoint="https://test.openai.azure.com",
                api_key="test-key",
                api_version="2024-02-15-preview",
                model="gpt-4",
            )

        mock_chunk = MagicMock()
        mock_chunk.choices = [MagicMock(delta=MagicMock(content="OK"))]

        async def mock_stream():
            yield mock_chunk

        mock_create = AsyncMock(return_value=mock_stream())
        provider.client.chat.completions.create = mock_create

        chunks = []
        async for chunk in provider.generate(
            prompt="Test", messages=[], system_prompt="Custom prompt"
        ):
            chunks.append(chunk)

        call_kwargs = mock_create.call_args[1]
        assert call_kwargs["messages"][0]["content"] == "Custom prompt"


class TestAzureProviderGenerateWithTools:
    @pytest.mark.asyncio
    async def test_generate_with_tools_yields_text(self):
        with patch("ai.azure.AsyncAzureOpenAI"):
            provider = AzureProvider(
                endpoint="https://test.openai.azure.com",
                api_key="test-key",
                api_version="2024-02-15-preview",
                model="gpt-4",
            )

        mock_chunk1 = MagicMock()
        mock_chunk1.choices = [
            MagicMock(
                delta=MagicMock(content="Hello", tool_calls=None),
                finish_reason=None,
            )
        ]
        mock_chunk1.usage = None

        mock_chunk2 = MagicMock()
        mock_chunk2.choices = [
            MagicMock(
                delta=MagicMock(content=None, tool_calls=None),
                finish_reason="stop",
            )
        ]
        mock_chunk2.usage = MagicMock(prompt_tokens=10, completion_tokens=5)

        async def mock_stream():
            yield mock_chunk1
            yield mock_chunk2

        provider.client.chat.completions.create = AsyncMock(return_value=mock_stream())

        chunks = []
        async for chunk in provider.generate_with_tools(
            prompt="Hi", messages=[], tools=[]
        ):
            chunks.append(chunk)

        assert chunks[0].text == "Hello"
        assert chunks[-1].is_complete
        assert chunks[-1].usage.input_tokens == 10
        assert chunks[-1].usage.output_tokens == 5

    @pytest.mark.asyncio
    async def test_generate_with_tools_handles_tool_calls(self):
        with patch("ai.azure.AsyncAzureOpenAI"):
            provider = AzureProvider(
                endpoint="https://test.openai.azure.com",
                api_key="test-key",
                api_version="2024-02-15-preview",
                model="gpt-4",
            )

        mock_tc = MagicMock()
        mock_tc.index = 0
        mock_tc.id = "call_1"
        mock_tc.function = MagicMock()
        mock_tc.function.name = "search"
        mock_tc.function.arguments = '{"query": "test"}'

        mock_chunk1 = MagicMock()
        mock_chunk1.choices = [
            MagicMock(
                delta=MagicMock(content=None, tool_calls=[mock_tc]),
                finish_reason=None,
            )
        ]
        mock_chunk1.usage = None

        mock_chunk2 = MagicMock()
        mock_chunk2.choices = [
            MagicMock(
                delta=MagicMock(content=None, tool_calls=None),
                finish_reason="tool_calls",
            )
        ]
        mock_chunk2.usage = None

        async def mock_stream():
            yield mock_chunk1
            yield mock_chunk2

        provider.client.chat.completions.create = AsyncMock(return_value=mock_stream())

        chunks = []
        async for chunk in provider.generate_with_tools(
            prompt="Search", messages=[], tools=[{"type": "function"}]
        ):
            chunks.append(chunk)

        final = chunks[-1]
        assert final.is_complete
        assert len(final.tool_calls) == 1
        assert final.tool_calls[0].id == "call_1"
        assert final.tool_calls[0].name == "search"
        assert final.tool_calls[0].arguments == {"query": "test"}

    @pytest.mark.asyncio
    async def test_generate_with_tools_handles_multiple_tool_calls(self):
        with patch("ai.azure.AsyncAzureOpenAI"):
            provider = AzureProvider(
                endpoint="https://test.openai.azure.com",
                api_key="test-key",
                api_version="2024-02-15-preview",
                model="gpt-4",
            )

        mock_tc1 = MagicMock()
        mock_tc1.index = 0
        mock_tc1.id = "call_1"
        mock_tc1.function = MagicMock()
        mock_tc1.function.name = "search"
        mock_tc1.function.arguments = '{"q": "1"}'

        mock_tc2 = MagicMock()
        mock_tc2.index = 1
        mock_tc2.id = "call_2"
        mock_tc2.function = MagicMock()
        mock_tc2.function.name = "read_file"
        mock_tc2.function.arguments = '{"path": "/test"}'

        mock_chunk1 = MagicMock()
        mock_chunk1.choices = [
            MagicMock(
                delta=MagicMock(content=None, tool_calls=[mock_tc1, mock_tc2]),
                finish_reason=None,
            )
        ]
        mock_chunk1.usage = None

        mock_chunk2 = MagicMock()
        mock_chunk2.choices = [
            MagicMock(
                delta=MagicMock(content=None, tool_calls=None),
                finish_reason="tool_calls",
            )
        ]
        mock_chunk2.usage = None

        async def mock_stream():
            yield mock_chunk1
            yield mock_chunk2

        provider.client.chat.completions.create = AsyncMock(return_value=mock_stream())

        chunks = []
        async for chunk in provider.generate_with_tools(
            prompt="Multi", messages=[], tools=[{"type": "function"}]
        ):
            chunks.append(chunk)

        final = chunks[-1]
        assert len(final.tool_calls) == 2
        assert final.tool_calls[0].name == "search"
        assert final.tool_calls[1].name == "read_file"

    @pytest.mark.asyncio
    async def test_generate_with_tools_handles_streamed_tool_args(self):
        with patch("ai.azure.AsyncAzureOpenAI"):
            provider = AzureProvider(
                endpoint="https://test.openai.azure.com",
                api_key="test-key",
                api_version="2024-02-15-preview",
                model="gpt-4",
            )

        mock_tc1 = MagicMock()
        mock_tc1.index = 0
        mock_tc1.id = "call_1"
        mock_tc1.function = MagicMock()
        mock_tc1.function.name = "test"
        mock_tc1.function.arguments = '{"ke'

        mock_tc2 = MagicMock()
        mock_tc2.index = 0
        mock_tc2.id = None
        mock_tc2.function = MagicMock()
        mock_tc2.function.name = None
        mock_tc2.function.arguments = 'y": "value"}'

        mock_chunk1 = MagicMock()
        mock_chunk1.choices = [
            MagicMock(
                delta=MagicMock(content=None, tool_calls=[mock_tc1]),
                finish_reason=None,
            )
        ]
        mock_chunk1.usage = None

        mock_chunk2 = MagicMock()
        mock_chunk2.choices = [
            MagicMock(
                delta=MagicMock(content=None, tool_calls=[mock_tc2]),
                finish_reason=None,
            )
        ]
        mock_chunk2.usage = None

        mock_chunk3 = MagicMock()
        mock_chunk3.choices = [
            MagicMock(
                delta=MagicMock(content=None, tool_calls=None),
                finish_reason="tool_calls",
            )
        ]
        mock_chunk3.usage = None

        async def mock_stream():
            yield mock_chunk1
            yield mock_chunk2
            yield mock_chunk3

        provider.client.chat.completions.create = AsyncMock(return_value=mock_stream())

        chunks = []
        async for chunk in provider.generate_with_tools(
            prompt="Test", messages=[], tools=[]
        ):
            chunks.append(chunk)

        final = chunks[-1]
        assert final.tool_calls[0].arguments == {"key": "value"}

    @pytest.mark.asyncio
    async def test_generate_with_tools_handles_invalid_json(self):
        with patch("ai.azure.AsyncAzureOpenAI"):
            provider = AzureProvider(
                endpoint="https://test.openai.azure.com",
                api_key="test-key",
                api_version="2024-02-15-preview",
                model="gpt-4",
            )

        mock_tc = MagicMock()
        mock_tc.index = 0
        mock_tc.id = "call_1"
        mock_tc.function = MagicMock()
        mock_tc.function.name = "test"
        mock_tc.function.arguments = "invalid json"

        mock_chunk1 = MagicMock()
        mock_chunk1.choices = [
            MagicMock(
                delta=MagicMock(content=None, tool_calls=[mock_tc]),
                finish_reason=None,
            )
        ]
        mock_chunk1.usage = None

        mock_chunk2 = MagicMock()
        mock_chunk2.choices = [
            MagicMock(
                delta=MagicMock(content=None, tool_calls=None),
                finish_reason="tool_calls",
            )
        ]
        mock_chunk2.usage = None

        async def mock_stream():
            yield mock_chunk1
            yield mock_chunk2

        provider.client.chat.completions.create = AsyncMock(return_value=mock_stream())

        chunks = []
        async for chunk in provider.generate_with_tools(
            prompt="Test", messages=[], tools=[]
        ):
            chunks.append(chunk)

        final = chunks[-1]
        assert final.tool_calls[0].arguments == {}

    @pytest.mark.asyncio
    async def test_generate_with_tools_handles_empty_args(self):
        with patch("ai.azure.AsyncAzureOpenAI"):
            provider = AzureProvider(
                endpoint="https://test.openai.azure.com",
                api_key="test-key",
                api_version="2024-02-15-preview",
                model="gpt-4",
            )

        mock_tc = MagicMock()
        mock_tc.index = 0
        mock_tc.id = "call_1"
        mock_tc.function = MagicMock()
        mock_tc.function.name = "no_args_tool"
        mock_tc.function.arguments = ""

        mock_chunk1 = MagicMock()
        mock_chunk1.choices = [
            MagicMock(
                delta=MagicMock(content=None, tool_calls=[mock_tc]),
                finish_reason=None,
            )
        ]
        mock_chunk1.usage = None

        mock_chunk2 = MagicMock()
        mock_chunk2.choices = [
            MagicMock(
                delta=MagicMock(content=None, tool_calls=None),
                finish_reason="tool_calls",
            )
        ]
        mock_chunk2.usage = None

        async def mock_stream():
            yield mock_chunk1
            yield mock_chunk2

        provider.client.chat.completions.create = AsyncMock(return_value=mock_stream())

        chunks = []
        async for chunk in provider.generate_with_tools(
            prompt="Test", messages=[], tools=[]
        ):
            chunks.append(chunk)

        final = chunks[-1]
        assert final.tool_calls[0].arguments == {}

    @pytest.mark.asyncio
    async def test_generate_with_tools_handles_exception(self):
        with patch("ai.azure.AsyncAzureOpenAI"):
            provider = AzureProvider(
                endpoint="https://test.openai.azure.com",
                api_key="test-key",
                api_version="2024-02-15-preview",
                model="gpt-4",
            )

        provider.client.chat.completions.create = AsyncMock(
            side_effect=Exception("API error")
        )

        chunks = []
        async for chunk in provider.generate_with_tools(
            prompt="Hi", messages=[], tools=[]
        ):
            chunks.append(chunk)

        assert len(chunks) == 1
        assert "Error: API error" in chunks[0].text
        assert chunks[0].is_complete

    @pytest.mark.asyncio
    async def test_generate_with_tools_skips_empty_choices(self):
        with patch("ai.azure.AsyncAzureOpenAI"):
            provider = AzureProvider(
                endpoint="https://test.openai.azure.com",
                api_key="test-key",
                api_version="2024-02-15-preview",
                model="gpt-4",
            )

        mock_chunk1 = MagicMock()
        mock_chunk1.choices = []
        mock_chunk1.usage = None

        mock_chunk2 = MagicMock()
        mock_chunk2.choices = [
            MagicMock(
                delta=MagicMock(content="Hi", tool_calls=None),
                finish_reason="stop",
            )
        ]
        mock_chunk2.usage = None

        async def mock_stream():
            yield mock_chunk1
            yield mock_chunk2

        provider.client.chat.completions.create = AsyncMock(return_value=mock_stream())

        chunks = []
        async for chunk in provider.generate_with_tools(
            prompt="Hi", messages=[], tools=[]
        ):
            chunks.append(chunk)

        assert any(c.text == "Hi" for c in chunks)

    @pytest.mark.asyncio
    async def test_generate_with_tools_falls_back_without_stream_options(self):
        with patch("ai.azure.AsyncAzureOpenAI"):
            provider = AzureProvider(
                endpoint="https://test.openai.azure.com",
                api_key="test-key",
                api_version="2024-02-15-preview",
                model="gpt-4",
            )

        mock_chunk = MagicMock()
        mock_chunk.choices = [
            MagicMock(
                delta=MagicMock(content="Fallback", tool_calls=None),
                finish_reason="stop",
            )
        ]
        mock_chunk.usage = None

        async def mock_stream():
            yield mock_chunk

        call_count = 0

        async def mock_create(**kwargs):
            nonlocal call_count
            call_count += 1
            if "stream_options" in kwargs:
                raise Exception("stream_options not supported")
            return mock_stream()

        provider.client.chat.completions.create = mock_create

        chunks = []
        async for chunk in provider.generate_with_tools(
            prompt="Hi", messages=[], tools=[]
        ):
            chunks.append(chunk)

        assert any(c.text == "Fallback" for c in chunks)
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_generate_with_tools_includes_tools_in_params(self):
        with patch("ai.azure.AsyncAzureOpenAI"):
            provider = AzureProvider(
                endpoint="https://test.openai.azure.com",
                api_key="test-key",
                api_version="2024-02-15-preview",
                model="gpt-4",
            )

        mock_chunk = MagicMock()
        mock_chunk.choices = [
            MagicMock(
                delta=MagicMock(content="OK", tool_calls=None),
                finish_reason="stop",
            )
        ]
        mock_chunk.usage = None

        async def mock_stream():
            yield mock_chunk

        mock_create = AsyncMock(return_value=mock_stream())
        provider.client.chat.completions.create = mock_create

        tools = [{"type": "function", "function": {"name": "test"}}]
        chunks = []
        async for chunk in provider.generate_with_tools(
            prompt="Hi", messages=[], tools=tools
        ):
            chunks.append(chunk)

        call_kwargs = mock_create.call_args[1]
        assert "tools" in call_kwargs
        assert call_kwargs["tool_choice"] == "auto"

    @pytest.mark.asyncio
    async def test_generate_with_tools_without_tools_in_params(self):
        with patch("ai.azure.AsyncAzureOpenAI"):
            provider = AzureProvider(
                endpoint="https://test.openai.azure.com",
                api_key="test-key",
                api_version="2024-02-15-preview",
                model="gpt-4",
            )

        mock_chunk = MagicMock()
        mock_chunk.choices = [
            MagicMock(
                delta=MagicMock(content="OK", tool_calls=None),
                finish_reason="stop",
            )
        ]
        mock_chunk.usage = None

        async def mock_stream():
            yield mock_chunk

        mock_create = AsyncMock(return_value=mock_stream())
        provider.client.chat.completions.create = mock_create

        chunks = []
        async for chunk in provider.generate_with_tools(
            prompt="Hi", messages=[], tools=[]
        ):
            chunks.append(chunk)

        call_kwargs = mock_create.call_args[1]
        assert "tools" not in call_kwargs
        assert "tool_choice" not in call_kwargs

    @pytest.mark.asyncio
    async def test_generate_with_tools_handles_usage_in_chunk(self):
        with patch("ai.azure.AsyncAzureOpenAI"):
            provider = AzureProvider(
                endpoint="https://test.openai.azure.com",
                api_key="test-key",
                api_version="2024-02-15-preview",
                model="gpt-4",
            )

        mock_chunk1 = MagicMock()
        mock_chunk1.choices = [
            MagicMock(
                delta=MagicMock(content="Test", tool_calls=None),
                finish_reason=None,
            )
        ]
        mock_chunk1.usage = None

        mock_chunk2 = MagicMock()
        mock_chunk2.choices = [
            MagicMock(
                delta=MagicMock(content=None, tool_calls=None),
                finish_reason="stop",
            )
        ]
        mock_chunk2.usage = MagicMock(prompt_tokens=100, completion_tokens=50)

        async def mock_stream():
            yield mock_chunk1
            yield mock_chunk2

        provider.client.chat.completions.create = AsyncMock(return_value=mock_stream())

        chunks = []
        async for chunk in provider.generate_with_tools(
            prompt="Hi", messages=[], tools=[]
        ):
            chunks.append(chunk)

        final = chunks[-1]
        assert final.usage is not None
        assert final.usage.input_tokens == 100
        assert final.usage.output_tokens == 50


class TestAzureProviderListModels:
    @pytest.mark.asyncio
    async def test_list_models_returns_deployment_name(self):
        with patch("ai.azure.AsyncAzureOpenAI"):
            provider = AzureProvider(
                endpoint="https://test.openai.azure.com",
                api_key="test-key",
                api_version="2024-02-15-preview",
                model="my-gpt4-deployment",
            )

        result = await provider.list_models()

        assert result == ["my-gpt4-deployment"]


class TestAzureProviderValidateConnection:
    @pytest.mark.asyncio
    async def test_validate_connection_returns_true_on_success(self):
        with patch("ai.azure.AsyncAzureOpenAI"):
            provider = AzureProvider(
                endpoint="https://test.openai.azure.com",
                api_key="test-key",
                api_version="2024-02-15-preview",
                model="gpt-4",
            )

        provider.client.chat.completions.create = AsyncMock(return_value=MagicMock())

        result = await provider.validate_connection()
        assert result is True

    @pytest.mark.asyncio
    async def test_validate_connection_returns_false_on_error(self):
        with patch("ai.azure.AsyncAzureOpenAI"):
            provider = AzureProvider(
                endpoint="https://test.openai.azure.com",
                api_key="test-key",
                api_version="2024-02-15-preview",
                model="gpt-4",
            )

        provider.client.chat.completions.create = AsyncMock(
            side_effect=Exception("Connection failed")
        )

        result = await provider.validate_connection()
        assert result is False

    @pytest.mark.asyncio
    async def test_validate_connection_makes_minimal_request(self):
        with patch("ai.azure.AsyncAzureOpenAI"):
            provider = AzureProvider(
                endpoint="https://test.openai.azure.com",
                api_key="test-key",
                api_version="2024-02-15-preview",
                model="gpt-4",
            )

        mock_create = AsyncMock(return_value=MagicMock())
        provider.client.chat.completions.create = mock_create

        await provider.validate_connection()

        call_kwargs = mock_create.call_args[1]
        assert call_kwargs["max_tokens"] == 1
        assert call_kwargs["model"] == "gpt-4"
        assert call_kwargs["messages"][0]["content"] == "Hi"
