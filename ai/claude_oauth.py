from __future__ import annotations

import json
import time
from collections.abc import AsyncGenerator
from typing import Any

import httpx

from .base import LLMProvider, ModelInfo, StreamChunk, TokenUsage, ToolCallData
from .oauth import BaseOAuthFlow, OAuthTokens, OAuthTokenStore, PKCEHelper

CLAUDE_OAUTH_CLIENT_ID = "9d1c250a-e61b-44d9-88ed-5944d1962f5e"
CLAUDE_OAUTH_SCOPES = "org:create_api_key user:profile user:inference"
CLAUDE_REDIRECT_URI = "https://console.anthropic.com/oauth/code/callback"

AVAILABLE_MODELS = [
    "claude-sonnet-4-20250514",
    "claude-opus-4-20250514",
    "claude-3-5-sonnet-20241022",
    "claude-3-5-haiku-20241022",
    "claude-3-opus-20240229",
]


class ClaudeOAuthFlow(BaseOAuthFlow):
    def __init__(self, mode: str = "max"):
        super().__init__(callback_port=51122)
        self.mode = mode

    def get_authorization_url(self) -> tuple[str, str]:
        verifier, challenge = PKCEHelper.generate()

        base_url = (
            "https://claude.ai/oauth/authorize"
            if self.mode == "max"
            else "https://console.anthropic.com/oauth/authorize"
        )

        params = {
            "code": "true",
            "client_id": CLAUDE_OAUTH_CLIENT_ID,
            "response_type": "code",
            "redirect_uri": CLAUDE_REDIRECT_URI,
            "scope": CLAUDE_OAUTH_SCOPES,
            "code_challenge": challenge,
            "code_challenge_method": "S256",
            "state": verifier,
        }

        query = "&".join(f"{k}={v}" for k, v in params.items())
        url = f"{base_url}?{query}"

        return url, verifier

    async def exchange_code(self, code: str, state: str, verifier: str) -> OAuthTokens:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://console.anthropic.com/v1/oauth/token",
                json={
                    "code": code,
                    "state": state,
                    "grant_type": "authorization_code",
                    "client_id": CLAUDE_OAUTH_CLIENT_ID,
                    "redirect_uri": CLAUDE_REDIRECT_URI,
                    "code_verifier": verifier,
                },
            )
            response.raise_for_status()
            data = response.json()

            return OAuthTokens(
                access_token=data["access_token"],
                refresh_token=data.get("refresh_token", ""),
                expires_at=time.time() + data.get("expires_in", 3600),
                provider="claude_oauth",
            )

    async def refresh_tokens(self, refresh_token: str) -> OAuthTokens:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://console.anthropic.com/v1/oauth/token",
                json={
                    "grant_type": "refresh_token",
                    "refresh_token": refresh_token,
                    "client_id": CLAUDE_OAUTH_CLIENT_ID,
                },
            )
            response.raise_for_status()
            data = response.json()

            return OAuthTokens(
                access_token=data["access_token"],
                refresh_token=data.get("refresh_token", refresh_token),
                expires_at=time.time() + data.get("expires_in", 3600),
                provider="claude_oauth",
            )


class ClaudeOAuthProvider(LLMProvider):
    def __init__(self, model: str = "claude-sonnet-4-20250514", mode: str = "max"):
        self.model = model
        self.mode = mode
        self._tokens: OAuthTokens | None = None
        self._oauth_flow = ClaudeOAuthFlow(mode=mode)
        self._load_tokens()

    def _load_tokens(self) -> None:
        self._tokens = OAuthTokenStore.load("claude_oauth")

    def _save_tokens(self, tokens: OAuthTokens) -> None:
        self._tokens = tokens
        OAuthTokenStore.save(tokens)

    @property
    def is_authenticated(self) -> bool:
        return self._tokens is not None

    async def login(self) -> bool:
        url, verifier = self._oauth_flow.get_authorization_url()

        self._oauth_flow._start_callback_server()
        self._oauth_flow._open_browser(url)

        code, state, error = self._oauth_flow._wait_for_callback(timeout=120)

        if error or not code:
            return False

        try:
            tokens = await self._oauth_flow.exchange_code(code, state or "", verifier)
            self._save_tokens(tokens)
            return True
        except Exception:
            return False

    async def _ensure_valid_token(self) -> str | None:
        if not self._tokens:
            return None

        if self._tokens.is_expired():
            try:
                new_tokens = await self._oauth_flow.refresh_tokens(
                    self._tokens.refresh_token
                )
                self._save_tokens(new_tokens)
            except Exception:
                return None

        return self._tokens.access_token

    def logout(self) -> None:
        OAuthTokenStore.delete("claude_oauth")
        self._tokens = None

    def _get_headers(self, access_token: str) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
            "anthropic-version": "2023-06-01",
            "anthropic-beta": "oauth-2025-04-20,interleaved-thinking-2025-05-14",
            "User-Agent": "null-terminal/1.0 (external, cli)",
        }

    def _build_messages(
        self, prompt: str, messages: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        result = []

        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")

            if role == "system":
                continue

            result.append({"role": role, "content": content})

        if prompt:
            result.append({"role": "user", "content": prompt})

        return result

    def _get_system_message(self, messages: list[dict[str, Any]]) -> str | None:
        for msg in messages:
            if msg.get("role") == "system":
                return msg.get("content", "")
        return None

    def _convert_tools(self, tools: list[dict[str, Any]]) -> list[dict[str, Any]]:
        anthropic_tools = []
        for tool in tools:
            if "function" in tool:
                func = tool["function"]
                anthropic_tools.append(
                    {
                        "name": func.get("name", ""),
                        "description": func.get("description", ""),
                        "input_schema": func.get(
                            "parameters", {"type": "object", "properties": {}}
                        ),
                    }
                )
        return anthropic_tools

    async def generate(
        self,
        prompt: str,
        messages: list[dict[str, Any]],
        **kwargs: Any,
    ) -> AsyncGenerator[StreamChunk, None]:
        access_token = await self._ensure_valid_token()
        if not access_token:
            yield StreamChunk(
                text="Error: Not authenticated. Use /provider claude_oauth to login."
            )
            return

        api_messages = self._build_messages(prompt, messages)
        system = self._get_system_message(messages)
        headers = self._get_headers(access_token)

        body: dict[str, Any] = {
            "model": self.model,
            "messages": api_messages,
            "max_tokens": 8192,
            "stream": True,
        }

        if system:
            body["system"] = system

        async with httpx.AsyncClient(timeout=120) as client:
            async with client.stream(
                "POST",
                "https://api.anthropic.com/v1/messages",
                json=body,
                headers=headers,
            ) as response:
                if response.status_code != 200:
                    error_text = await response.aread()
                    yield StreamChunk(
                        text=f"Error: {response.status_code} - {error_text.decode()}"
                    )
                    return

                async for line in response.aiter_lines():
                    if not line or not line.startswith("data: "):
                        continue

                    data_str = line[6:]
                    if data_str == "[DONE]":
                        break

                    try:
                        event = json.loads(data_str)
                        event_type = event.get("type", "")

                        if event_type == "content_block_delta":
                            delta = event.get("delta", {})
                            if delta.get("type") == "text_delta":
                                yield StreamChunk(text=delta.get("text", ""))

                        elif event_type == "message_delta":
                            usage_data = event.get("usage", {})
                            if usage_data:
                                yield StreamChunk(
                                    usage=TokenUsage(
                                        input_tokens=usage_data.get("input_tokens", 0),
                                        output_tokens=usage_data.get(
                                            "output_tokens", 0
                                        ),
                                    )
                                )
                    except json.JSONDecodeError:
                        continue

    async def generate_with_tools(
        self,
        prompt: str,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
        **kwargs: Any,
    ) -> AsyncGenerator[StreamChunk, None]:
        access_token = await self._ensure_valid_token()
        if not access_token:
            yield StreamChunk(
                text="Error: Not authenticated. Use /provider claude_oauth to login."
            )
            return

        api_messages = self._build_messages(prompt, messages)
        system = self._get_system_message(messages)
        headers = self._get_headers(access_token)
        anthropic_tools = self._convert_tools(tools)

        body: dict[str, Any] = {
            "model": self.model,
            "messages": api_messages,
            "max_tokens": 8192,
            "stream": True,
        }

        if system:
            body["system"] = system

        if anthropic_tools:
            body["tools"] = anthropic_tools

        tool_calls: list[ToolCallData] = []
        current_tool_id = ""
        current_tool_name = ""
        current_tool_input = ""

        async with httpx.AsyncClient(timeout=120) as client:
            async with client.stream(
                "POST",
                "https://api.anthropic.com/v1/messages",
                json=body,
                headers=headers,
            ) as response:
                if response.status_code != 200:
                    error_text = await response.aread()
                    yield StreamChunk(
                        text=f"Error: {response.status_code} - {error_text.decode()}"
                    )
                    return

                async for line in response.aiter_lines():
                    if not line or not line.startswith("data: "):
                        continue

                    data_str = line[6:]
                    if data_str == "[DONE]":
                        break

                    try:
                        event = json.loads(data_str)
                        event_type = event.get("type", "")

                        if event_type == "content_block_start":
                            block = event.get("content_block", {})
                            if block.get("type") == "tool_use":
                                current_tool_id = block.get("id", "")
                                current_tool_name = block.get("name", "")
                                current_tool_input = ""

                        elif event_type == "content_block_delta":
                            delta = event.get("delta", {})
                            if delta.get("type") == "text_delta":
                                yield StreamChunk(text=delta.get("text", ""))
                            elif delta.get("type") == "input_json_delta":
                                current_tool_input += delta.get("partial_json", "")

                        elif event_type == "content_block_stop":
                            if current_tool_name:
                                try:
                                    args = (
                                        json.loads(current_tool_input)
                                        if current_tool_input
                                        else {}
                                    )
                                except json.JSONDecodeError:
                                    args = {}
                                tool_calls.append(
                                    ToolCallData(
                                        id=current_tool_id,
                                        name=current_tool_name,
                                        arguments=args,
                                    )
                                )
                                current_tool_id = ""
                                current_tool_name = ""
                                current_tool_input = ""

                        elif event_type == "message_delta":
                            usage_data = event.get("usage", {})
                            if usage_data:
                                yield StreamChunk(
                                    usage=TokenUsage(
                                        input_tokens=usage_data.get("input_tokens", 0),
                                        output_tokens=usage_data.get(
                                            "output_tokens", 0
                                        ),
                                    )
                                )

                    except json.JSONDecodeError:
                        continue

        if tool_calls:
            yield StreamChunk(tool_calls=tool_calls)

    async def list_models(self) -> list[str]:
        return AVAILABLE_MODELS

    async def validate_connection(self) -> bool:
        if not self._tokens:
            return False

        access_token = await self._ensure_valid_token()
        if not access_token:
            return False

        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(
                    "https://api.anthropic.com/v1/messages",
                    headers={
                        "Authorization": f"Bearer {access_token}",
                        "anthropic-version": "2023-06-01",
                        "anthropic-beta": "oauth-2025-04-20",
                    },
                )
                return response.status_code in (200, 400, 405)
        except Exception:
            return False

    def supports_tools(self) -> bool:
        return True

    def get_model_info(self) -> ModelInfo:
        context_sizes = {
            "claude-sonnet-4-20250514": 200000,
            "claude-opus-4-20250514": 200000,
            "claude-3-5-sonnet-20241022": 200000,
            "claude-3-5-haiku-20241022": 200000,
            "claude-3-opus-20240229": 200000,
        }

        return ModelInfo(
            name=self.model,
            max_tokens=8192,
            context_window=context_sizes.get(self.model, 200000),
        )
