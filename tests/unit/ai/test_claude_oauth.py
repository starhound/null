"""Tests for ai/claude_oauth.py - ClaudeOAuthProvider implementation."""

import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from ai.claude_oauth import (
    AVAILABLE_MODELS,
    CLAUDE_OAUTH_CLIENT_ID,
    ClaudeOAuthFlow,
    ClaudeOAuthProvider,
)
from ai.oauth import OAuthTokens


class TestClaudeOAuthFlowInit:
    """Tests for ClaudeOAuthFlow initialization."""

    def test_init_default_mode(self):
        """Should default to 'max' mode."""
        flow = ClaudeOAuthFlow()
        assert flow.mode == "max"

    def test_init_custom_mode(self):
        """Should accept custom mode."""
        flow = ClaudeOAuthFlow(mode="console")
        assert flow.mode == "console"

    def test_init_sets_callback_port(self):
        """Should use port 51122 for Claude OAuth."""
        flow = ClaudeOAuthFlow()
        assert flow.callback_port == 51122


class TestClaudeOAuthFlowGetAuthorizationUrl:
    """Tests for get_authorization_url method."""

    def test_returns_url_and_verifier(self):
        """Should return authorization URL and PKCE verifier."""
        flow = ClaudeOAuthFlow()
        url, verifier = flow.get_authorization_url()

        assert isinstance(url, str)
        assert isinstance(verifier, str)
        assert len(verifier) > 0

    def test_url_contains_required_params(self):
        """Should include all required OAuth parameters."""
        flow = ClaudeOAuthFlow()
        url, _ = flow.get_authorization_url()

        assert "client_id=" + CLAUDE_OAUTH_CLIENT_ID in url
        assert "response_type=code" in url
        assert "redirect_uri=" in url
        assert "code_challenge=" in url
        assert "code_challenge_method=S256" in url
        assert "scope=" in url
        assert "state=" in url

    def test_max_mode_uses_claude_ai_url(self):
        """Max mode should use claude.ai authorization URL."""
        flow = ClaudeOAuthFlow(mode="max")
        url, _ = flow.get_authorization_url()

        assert "https://claude.ai/oauth/authorize" in url

    def test_console_mode_uses_console_url(self):
        """Console mode should use console.anthropic.com URL."""
        flow = ClaudeOAuthFlow(mode="console")
        url, _ = flow.get_authorization_url()

        assert "https://console.anthropic.com/oauth/authorize" in url


class TestClaudeOAuthFlowExchangeCode:
    """Tests for exchange_code method."""

    @pytest.mark.asyncio
    async def test_exchange_code_returns_tokens(self):
        """Should return OAuthTokens on success."""
        flow = ClaudeOAuthFlow()

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "access_token": "test_access",
            "refresh_token": "test_refresh",
            "expires_in": 3600,
        }
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            tokens = await flow.exchange_code("code123", "state123", "verifier123")

        assert isinstance(tokens, OAuthTokens)
        assert tokens.access_token == "test_access"
        assert tokens.refresh_token == "test_refresh"
        assert tokens.provider == "claude_oauth"

    @pytest.mark.asyncio
    async def test_exchange_code_posts_to_token_endpoint(self):
        """Should POST to Anthropic token endpoint."""
        flow = ClaudeOAuthFlow()

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "access_token": "test",
            "expires_in": 3600,
        }
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            await flow.exchange_code("code", "state", "verifier")

            call_args = mock_client.post.call_args
            assert call_args[0][0] == "https://console.anthropic.com/v1/oauth/token"
            assert call_args[1]["json"]["grant_type"] == "authorization_code"
            assert call_args[1]["json"]["code"] == "code"


class TestClaudeOAuthFlowRefreshTokens:
    """Tests for refresh_tokens method."""

    @pytest.mark.asyncio
    async def test_refresh_returns_new_tokens(self):
        """Should return new OAuthTokens on refresh."""
        flow = ClaudeOAuthFlow()

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "access_token": "new_access",
            "refresh_token": "new_refresh",
            "expires_in": 3600,
        }
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            tokens = await flow.refresh_tokens("old_refresh")

        assert tokens.access_token == "new_access"
        assert tokens.refresh_token == "new_refresh"

    @pytest.mark.asyncio
    async def test_refresh_preserves_old_refresh_token(self):
        """Should preserve old refresh token if new one not provided."""
        flow = ClaudeOAuthFlow()

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "access_token": "new_access",
            "expires_in": 3600,
        }
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            tokens = await flow.refresh_tokens("old_refresh")

        assert tokens.refresh_token == "old_refresh"


class TestClaudeOAuthProviderInit:
    """Tests for ClaudeOAuthProvider initialization."""

    def test_init_default_model(self, mock_home):
        """Should use default model."""
        with patch.object(ClaudeOAuthProvider, "_load_tokens"):
            provider = ClaudeOAuthProvider()
        assert provider.model == "claude-sonnet-4-20250514"

    def test_init_custom_model(self, mock_home):
        """Should accept custom model."""
        with patch.object(ClaudeOAuthProvider, "_load_tokens"):
            provider = ClaudeOAuthProvider(model="claude-3-opus-20240229")
        assert provider.model == "claude-3-opus-20240229"

    def test_init_default_mode(self, mock_home):
        """Should default to 'max' mode."""
        with patch.object(ClaudeOAuthProvider, "_load_tokens"):
            provider = ClaudeOAuthProvider()
        assert provider.mode == "max"

    def test_init_loads_tokens(self, mock_home):
        """Should attempt to load tokens on init."""
        with patch("ai.claude_oauth.OAuthTokenStore.load") as mock_load:
            mock_load.return_value = None
            provider = ClaudeOAuthProvider()
            mock_load.assert_called_once_with("claude_oauth")


class TestClaudeOAuthProviderIsAuthenticated:
    """Tests for is_authenticated property."""

    def test_not_authenticated_when_no_tokens(self, mock_home):
        """Should return False when tokens are None."""
        with patch.object(ClaudeOAuthProvider, "_load_tokens"):
            provider = ClaudeOAuthProvider()
            provider._tokens = None
        assert provider.is_authenticated is False

    def test_authenticated_when_tokens_exist(self, mock_home):
        """Should return True when tokens exist."""
        with patch.object(ClaudeOAuthProvider, "_load_tokens"):
            provider = ClaudeOAuthProvider()
            provider._tokens = OAuthTokens(
                access_token="test",
                refresh_token="test",
                expires_at=time.time() + 3600,
                provider="claude_oauth",
            )
        assert provider.is_authenticated is True


class TestClaudeOAuthProviderEnsureValidToken:
    """Tests for _ensure_valid_token method."""

    @pytest.mark.asyncio
    async def test_returns_none_when_no_tokens(self, mock_home):
        """Should return None if not authenticated."""
        with patch.object(ClaudeOAuthProvider, "_load_tokens"):
            provider = ClaudeOAuthProvider()
            provider._tokens = None

        result = await provider._ensure_valid_token()
        assert result is None

    @pytest.mark.asyncio
    async def test_returns_access_token_when_valid(self, mock_home):
        """Should return access token if not expired."""
        with patch.object(ClaudeOAuthProvider, "_load_tokens"):
            provider = ClaudeOAuthProvider()
            provider._tokens = OAuthTokens(
                access_token="valid_token",
                refresh_token="refresh",
                expires_at=time.time() + 3600,
                provider="claude_oauth",
            )

        result = await provider._ensure_valid_token()
        assert result == "valid_token"

    @pytest.mark.asyncio
    async def test_refreshes_expired_token(self, mock_home):
        """Should refresh token if expired."""
        with patch.object(ClaudeOAuthProvider, "_load_tokens"):
            provider = ClaudeOAuthProvider()
            provider._tokens = OAuthTokens(
                access_token="old_token",
                refresh_token="refresh",
                expires_at=time.time() - 100,
                provider="claude_oauth",
            )

            new_tokens = OAuthTokens(
                access_token="new_token",
                refresh_token="new_refresh",
                expires_at=time.time() + 3600,
                provider="claude_oauth",
            )

            with patch.object(
                provider._oauth_flow,
                "refresh_tokens",
                AsyncMock(return_value=new_tokens),
            ):
                with patch("ai.claude_oauth.OAuthTokenStore.save"):
                    result = await provider._ensure_valid_token()

            assert result == "new_token"

    @pytest.mark.asyncio
    async def test_returns_none_on_refresh_failure(self, mock_home):
        """Should return None if refresh fails."""
        with patch.object(ClaudeOAuthProvider, "_load_tokens"):
            provider = ClaudeOAuthProvider()
            provider._tokens = OAuthTokens(
                access_token="old_token",
                refresh_token="refresh",
                expires_at=time.time() - 100,
                provider="claude_oauth",
            )

        with patch.object(
            provider._oauth_flow,
            "refresh_tokens",
            AsyncMock(side_effect=Exception("Refresh failed")),
        ):
            result = await provider._ensure_valid_token()

        assert result is None


class TestClaudeOAuthProviderLogout:
    """Tests for logout method."""

    def test_logout_deletes_tokens(self, mock_home):
        """Should delete tokens from store."""
        with patch.object(ClaudeOAuthProvider, "_load_tokens"):
            provider = ClaudeOAuthProvider()
            provider._tokens = OAuthTokens(
                access_token="test",
                refresh_token="test",
                expires_at=time.time() + 3600,
                provider="claude_oauth",
            )

        with patch("ai.claude_oauth.OAuthTokenStore.delete") as mock_delete:
            provider.logout()
            mock_delete.assert_called_once_with("claude_oauth")

        assert provider._tokens is None


class TestClaudeOAuthProviderBuildMessages:
    """Tests for _build_messages method."""

    def test_adds_prompt_as_user_message(self, mock_home):
        """Should add prompt as final user message."""
        with patch.object(ClaudeOAuthProvider, "_load_tokens"):
            provider = ClaudeOAuthProvider()

        result = provider._build_messages("Hello", [])
        assert len(result) == 1
        assert result[0] == {"role": "user", "content": "Hello"}

    def test_preserves_message_history(self, mock_home):
        """Should include history messages."""
        with patch.object(ClaudeOAuthProvider, "_load_tokens"):
            provider = ClaudeOAuthProvider()

        messages = [
            {"role": "user", "content": "Hi"},
            {"role": "assistant", "content": "Hello!"},
        ]
        result = provider._build_messages("How are you?", messages)

        assert len(result) == 3
        assert result[0]["content"] == "Hi"
        assert result[2]["content"] == "How are you?"

    def test_skips_system_messages(self, mock_home):
        """Should skip system role messages."""
        with patch.object(ClaudeOAuthProvider, "_load_tokens"):
            provider = ClaudeOAuthProvider()

        messages = [
            {"role": "system", "content": "Be helpful"},
            {"role": "user", "content": "Hi"},
        ]
        result = provider._build_messages("Test", messages)

        assert len(result) == 2
        assert all(m["role"] != "system" for m in result)


class TestClaudeOAuthProviderConvertTools:
    """Tests for _convert_tools method."""

    def test_converts_openai_format_to_anthropic(self, mock_home):
        """Should convert OpenAI tool format to Anthropic."""
        with patch.object(ClaudeOAuthProvider, "_load_tokens"):
            provider = ClaudeOAuthProvider()

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

    def test_handles_missing_parameters(self, mock_home):
        """Should use default schema if parameters not provided."""
        with patch.object(ClaudeOAuthProvider, "_load_tokens"):
            provider = ClaudeOAuthProvider()

        tools = [{"function": {"name": "test", "description": "A tool"}}]
        result = provider._convert_tools(tools)

        assert result[0]["input_schema"] == {"type": "object", "properties": {}}


class TestClaudeOAuthProviderGenerate:
    """Tests for generate method."""

    @pytest.mark.asyncio
    async def test_generate_yields_error_when_not_authenticated(self, mock_home):
        """Should yield error when not authenticated."""
        with patch.object(ClaudeOAuthProvider, "_load_tokens"):
            provider = ClaudeOAuthProvider()
            provider._tokens = None

        chunks = []
        async for chunk in provider.generate("Hi", []):
            chunks.append(chunk)

        assert len(chunks) == 1
        assert "Not authenticated" in chunks[0].text

    @pytest.mark.asyncio
    async def test_generate_streams_text(self, mock_home):
        """Should yield text from SSE stream."""
        with patch.object(ClaudeOAuthProvider, "_load_tokens"):
            provider = ClaudeOAuthProvider()
            provider._tokens = OAuthTokens(
                access_token="valid",
                refresh_token="refresh",
                expires_at=time.time() + 3600,
                provider="claude_oauth",
            )

            async def mock_iter_lines():
                yield 'data: {"type": "content_block_delta", "delta": {"type": "text_delta", "text": "Hello"}}'
                yield 'data: {"type": "content_block_delta", "delta": {"type": "text_delta", "text": " world"}}'
                yield "data: [DONE]"

            mock_response = AsyncMock()
            mock_response.status_code = 200
            mock_response.aiter_lines = mock_iter_lines

            mock_stream_ctx = AsyncMock()
            mock_stream_ctx.__aenter__ = AsyncMock(return_value=mock_response)
            mock_stream_ctx.__aexit__ = AsyncMock(return_value=None)

            mock_client = AsyncMock()
            mock_client.stream = MagicMock(return_value=mock_stream_ctx)

            with patch("httpx.AsyncClient") as mock_client_class:
                mock_client_class.return_value.__aenter__ = AsyncMock(
                    return_value=mock_client
                )
                mock_client_class.return_value.__aexit__ = AsyncMock(return_value=None)

                chunks = []
                async for chunk in provider.generate("Hi", []):
                    chunks.append(chunk)

            texts = [c.text for c in chunks if c.text]
            assert "Hello" in texts
            assert " world" in texts

    @pytest.mark.asyncio
    async def test_generate_handles_api_error(self, mock_home):
        """Should yield error on non-200 response."""
        with patch.object(ClaudeOAuthProvider, "_load_tokens"):
            provider = ClaudeOAuthProvider()
            provider._tokens = OAuthTokens(
                access_token="valid",
                refresh_token="refresh",
                expires_at=time.time() + 3600,
                provider="claude_oauth",
            )

            mock_response = AsyncMock()
            mock_response.status_code = 401
            mock_response.aread = AsyncMock(return_value=b"Unauthorized")

            mock_stream_ctx = AsyncMock()
            mock_stream_ctx.__aenter__ = AsyncMock(return_value=mock_response)
            mock_stream_ctx.__aexit__ = AsyncMock(return_value=None)

            mock_client = AsyncMock()
            mock_client.stream = MagicMock(return_value=mock_stream_ctx)

            with patch("httpx.AsyncClient") as mock_client_class:
                mock_client_class.return_value.__aenter__ = AsyncMock(
                    return_value=mock_client
                )
                mock_client_class.return_value.__aexit__ = AsyncMock(return_value=None)

                chunks = []
                async for chunk in provider.generate("Hi", []):
                    chunks.append(chunk)

            assert len(chunks) == 1
            assert "401" in chunks[0].text


class TestClaudeOAuthProviderGenerateWithTools:
    """Tests for generate_with_tools method."""

    @pytest.mark.asyncio
    async def test_yields_error_when_not_authenticated(self, mock_home):
        """Should yield error when not authenticated."""
        with patch.object(ClaudeOAuthProvider, "_load_tokens"):
            provider = ClaudeOAuthProvider()
            provider._tokens = None

        chunks = []
        async for chunk in provider.generate_with_tools("Hi", [], []):
            chunks.append(chunk)

        assert len(chunks) == 1
        assert "Not authenticated" in chunks[0].text

    @pytest.mark.asyncio
    async def test_collects_tool_calls(self, mock_home):
        """Should collect tool calls from stream."""
        with patch.object(ClaudeOAuthProvider, "_load_tokens"):
            provider = ClaudeOAuthProvider()
            provider._tokens = OAuthTokens(
                access_token="valid",
                refresh_token="refresh",
                expires_at=time.time() + 3600,
                provider="claude_oauth",
            )

            async def mock_iter_lines():
                yield 'data: {"type": "content_block_start", "content_block": {"type": "tool_use", "id": "call_1", "name": "search"}}'
                yield 'data: {"type": "content_block_delta", "delta": {"type": "input_json_delta", "partial_json": "{\\"query\\": \\"test\\"}"}}'
                yield 'data: {"type": "content_block_stop"}'
                yield "data: [DONE]"

            mock_response = AsyncMock()
            mock_response.status_code = 200
            mock_response.aiter_lines = mock_iter_lines

            mock_stream_ctx = AsyncMock()
            mock_stream_ctx.__aenter__ = AsyncMock(return_value=mock_response)
            mock_stream_ctx.__aexit__ = AsyncMock(return_value=None)

            mock_client = AsyncMock()
            mock_client.stream = MagicMock(return_value=mock_stream_ctx)

            with patch("httpx.AsyncClient") as mock_client_class:
                mock_client_class.return_value.__aenter__ = AsyncMock(
                    return_value=mock_client
                )
                mock_client_class.return_value.__aexit__ = AsyncMock(return_value=None)

                chunks = []
                async for chunk in provider.generate_with_tools("Search", [], []):
                    chunks.append(chunk)

            final = chunks[-1]
            assert len(final.tool_calls) == 1
            assert final.tool_calls[0].name == "search"
            assert final.tool_calls[0].arguments == {"query": "test"}


class TestClaudeOAuthProviderListModels:
    """Tests for list_models method."""

    @pytest.mark.asyncio
    async def test_returns_available_models(self, mock_home):
        """Should return list of available models."""
        with patch.object(ClaudeOAuthProvider, "_load_tokens"):
            provider = ClaudeOAuthProvider()

        models = await provider.list_models()

        assert models == AVAILABLE_MODELS
        assert "claude-sonnet-4-20250514" in models


class TestClaudeOAuthProviderValidateConnection:
    """Tests for validate_connection method."""

    @pytest.mark.asyncio
    async def test_returns_false_when_no_tokens(self, mock_home):
        """Should return False if not authenticated."""
        with patch.object(ClaudeOAuthProvider, "_load_tokens"):
            provider = ClaudeOAuthProvider()
            provider._tokens = None

        result = await provider.validate_connection()
        assert result is False

    @pytest.mark.asyncio
    async def test_returns_true_on_valid_response(self, mock_home):
        """Should return True on successful API call."""
        with patch.object(ClaudeOAuthProvider, "_load_tokens"):
            provider = ClaudeOAuthProvider()
            provider._tokens = OAuthTokens(
                access_token="valid",
                refresh_token="refresh",
                expires_at=time.time() + 3600,
                provider="claude_oauth",
            )

        mock_response = MagicMock()
        mock_response.status_code = 200

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            result = await provider.validate_connection()

        assert result is True

    @pytest.mark.asyncio
    async def test_returns_false_on_exception(self, mock_home):
        """Should return False on exception."""
        with patch.object(ClaudeOAuthProvider, "_load_tokens"):
            provider = ClaudeOAuthProvider()
            provider._tokens = OAuthTokens(
                access_token="valid",
                refresh_token="refresh",
                expires_at=time.time() + 3600,
                provider="claude_oauth",
            )

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(side_effect=Exception("Network error"))
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            result = await provider.validate_connection()

        assert result is False


class TestClaudeOAuthProviderSupportsTools:
    """Tests for supports_tools method."""

    def test_returns_true(self, mock_home):
        """Claude OAuth provider supports tools."""
        with patch.object(ClaudeOAuthProvider, "_load_tokens"):
            provider = ClaudeOAuthProvider()
        assert provider.supports_tools() is True


class TestClaudeOAuthProviderGetModelInfo:
    """Tests for get_model_info method."""

    def test_returns_model_info(self, mock_home):
        """Should return ModelInfo for current model."""
        with patch.object(ClaudeOAuthProvider, "_load_tokens"):
            provider = ClaudeOAuthProvider(model="claude-3-5-sonnet-20241022")

        info = provider.get_model_info()

        assert info.name == "claude-3-5-sonnet-20241022"
        assert info.max_tokens == 8192
        assert info.context_window == 200000
