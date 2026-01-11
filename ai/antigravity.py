"""Antigravity provider for Google's internal IDE API.

OAuth credentials are from the MIT-licensed opencode-antigravity-auth package:
https://github.com/NoeFabris/opencode-antigravity-auth

These are "installed application" OAuth credentials where the client secret
is not truly secret (distributed in client binaries). Google's OAuth spec
treats these as public credentials.
"""

from __future__ import annotations

import json
import os
import time
from collections.abc import AsyncGenerator
from pathlib import Path
from typing import Any

import httpx

from .base import LLMProvider, ModelInfo, StreamChunk, ToolCallData
from .oauth import BaseOAuthFlow, OAuthTokens, OAuthTokenStore, PKCEHelper

# OAuth credentials from opencode-antigravity-auth (MIT license)
# https://github.com/NoeFabris/opencode-antigravity-auth/blob/main/src/constants.ts
ANTIGRAVITY_CLIENT_ID = (
    "1071006060591-tmhssin2h21lcre235vtolojh4g403ep.apps.googleusercontent.com"
)
ANTIGRAVITY_CLIENT_SECRET = "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"

OAUTH_SCOPES = [
    "https://www.googleapis.com/auth/cloud-platform",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/userinfo.profile",
    "https://www.googleapis.com/auth/cclog",
    "https://www.googleapis.com/auth/experimentsandconfigs",
]

ANTIGRAVITY_API_BASE = "https://daily-cloudcode-pa.sandbox.googleapis.com"

# Path to OpenCode's antigravity token storage (for token reuse)
OPENCODE_ACCOUNTS_PATH = (
    Path.home() / ".config" / "opencode" / "antigravity-accounts.json"
)

AVAILABLE_MODELS = [
    "claude-sonnet-4-5",
    "claude-sonnet-4-5-thinking",
    "claude-sonnet-4-5-thinking-low",
    "claude-sonnet-4-5-thinking-medium",
    "claude-sonnet-4-5-thinking-high",
    "claude-opus-4-5-thinking",
    "claude-opus-4-5-thinking-low",
    "claude-opus-4-5-thinking-medium",
    "claude-opus-4-5-thinking-high",
    "gemini-3-pro",
    "gemini-3-pro-preview",
    "gemini-3-pro-low",
    "gemini-3-pro-high",
    "gemini-3-flash",
    "gemini-3-flash-preview",
    "gemini-3-flash-low",
    "gemini-3-flash-medium",
    "gemini-3-flash-high",
    "gemini-2.5-pro",
    "gemini-2.5-flash",
    "gemini-2.5-flash-lite",
    "gemini-2.5-computer-use-preview-10-2025",
    "gpt-oss-120b-medium",
]


class AntigravityOAuthFlow(BaseOAuthFlow):
    def __init__(self):
        super().__init__(callback_port=51121)

    def get_authorization_url(self) -> tuple[str, str]:
        verifier, challenge = PKCEHelper.generate()

        params = {
            "client_id": ANTIGRAVITY_CLIENT_ID,
            "response_type": "code",
            "redirect_uri": self.callback_url,
            "scope": " ".join(OAUTH_SCOPES),
            "code_challenge": challenge,
            "code_challenge_method": "S256",
            "access_type": "offline",
            "prompt": "consent",
        }

        query = "&".join(f"{k}={v}" for k, v in params.items())
        url = f"https://accounts.google.com/o/oauth2/v2/auth?{query}"

        return url, verifier

    async def exchange_code(self, code: str, verifier: str) -> OAuthTokens:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://oauth2.googleapis.com/token",
                data={
                    "client_id": ANTIGRAVITY_CLIENT_ID,
                    "client_secret": ANTIGRAVITY_CLIENT_SECRET,
                    "code": code,
                    "grant_type": "authorization_code",
                    "redirect_uri": self.callback_url,
                    "code_verifier": verifier,
                },
            )
            response.raise_for_status()
            data = response.json()

            return OAuthTokens(
                access_token=data["access_token"],
                refresh_token=data.get("refresh_token", ""),
                expires_at=time.time() + data.get("expires_in", 3600),
                provider="antigravity",
            )

    async def refresh_tokens(self, refresh_token: str) -> OAuthTokens:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://oauth2.googleapis.com/token",
                data={
                    "client_id": ANTIGRAVITY_CLIENT_ID,
                    "client_secret": ANTIGRAVITY_CLIENT_SECRET,
                    "refresh_token": refresh_token,
                    "grant_type": "refresh_token",
                },
            )
            response.raise_for_status()
            data = response.json()

            return OAuthTokens(
                access_token=data["access_token"],
                refresh_token=refresh_token,
                expires_at=time.time() + data.get("expires_in", 3600),
                provider="antigravity",
            )


def _load_opencode_account() -> tuple[OAuthTokens | None, str]:
    """Load tokens and projectId from OpenCode's antigravity-accounts.json."""
    if not OPENCODE_ACCOUNTS_PATH.exists():
        return None, ""

    try:
        data = json.loads(OPENCODE_ACCOUNTS_PATH.read_text())
        accounts = data.get("accounts", [])
        active_index = data.get("activeIndex", 0)

        if not accounts or active_index >= len(accounts):
            return None, ""

        account = accounts[active_index]
        refresh_token = account.get("refreshToken", "")
        project_id = account.get("projectId", "") or account.get("managedProjectId", "")

        if not refresh_token:
            return None, ""

        if "|" in refresh_token:
            parts = refresh_token.split("|")
            refresh_token = parts[0]
            if not project_id and len(parts) > 1:
                project_id = parts[1]

        tokens = OAuthTokens(
            access_token="",
            refresh_token=refresh_token,
            expires_at=0,
            provider="antigravity",
        )
        return tokens, project_id
    except (json.JSONDecodeError, KeyError, TypeError):
        return None, ""


DEFAULT_PROJECT_ID = "rising-fact-p41fc"


class AntigravityProvider(LLMProvider):
    def __init__(self, model: str = "claude-sonnet-4-5"):
        self.model = model
        self._tokens: OAuthTokens | None = None
        self._project_id: str = DEFAULT_PROJECT_ID
        self._oauth_flow = AntigravityOAuthFlow()
        self._load_tokens()

    def _load_tokens(self) -> None:
        self._tokens = OAuthTokenStore.load("antigravity")

        if not self._tokens:
            tokens, project_id = _load_opencode_account()
            self._tokens = tokens
            if project_id:
                self._project_id = project_id

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

        code, _, error = self._oauth_flow._wait_for_callback(timeout=120)

        if error or not code:
            return False

        try:
            tokens = await self._oauth_flow.exchange_code(code, verifier)
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
        OAuthTokenStore.delete("antigravity")
        self._tokens = None

    def _build_request_body(
        self,
        prompt: str,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        contents = []

        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")

            ag_role = "user" if role == "user" else "model"
            contents.append(
                {
                    "role": ag_role,
                    "parts": [{"text": content}],
                }
            )

        if prompt:
            contents.append(
                {
                    "role": "user",
                    "parts": [{"text": prompt}],
                }
            )

        request: dict[str, Any] = {
            "model": self.model,
            "contents": contents,
            "generationConfig": {
                "temperature": 0.7,
                "maxOutputTokens": 8192,
            },
        }

        if tools:
            ag_tools = []
            for tool in tools:
                if "function" in tool:
                    func = tool["function"]
                    ag_tools.append(
                        {
                            "name": func.get("name", ""),
                            "description": func.get("description", ""),
                            "parameters": func.get("parameters", {}),
                        }
                    )
            if ag_tools:
                request["tools"] = [{"functionDeclarations": ag_tools}]

        return {
            "project": self._project_id,
            "model": self.model,
            "request": request,
        }

    def _get_headers(self, access_token: str, stream: bool = False) -> dict[str, str]:
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
            "User-Agent": "antigravity/1.11.5 null-terminal/1.0",
            "X-Goog-Api-Client": "google-cloud-sdk vscode_cloudshelleditor/0.1",
        }
        if stream:
            headers["Accept"] = "text/event-stream"
        return headers

    async def generate(
        self,
        prompt: str,
        messages: list[dict[str, Any]],
        **kwargs: Any,
    ) -> AsyncGenerator[StreamChunk, None]:
        access_token = await self._ensure_valid_token()
        if not access_token:
            yield StreamChunk(
                text="Error: Not authenticated. Use /provider antigravity to login."
            )
            return

        body = self._build_request_body(prompt, messages)
        url = f"{ANTIGRAVITY_API_BASE}/v1internal:streamGenerateContent?alt=sse"
        headers = self._get_headers(access_token, stream=True)

        async with httpx.AsyncClient(timeout=120) as client:
            async with client.stream(
                "POST", url, json=body, headers=headers
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
                        data = json.loads(data_str)
                        candidates = data.get("candidates", [])
                        if candidates:
                            content = candidates[0].get("content", {})
                            parts = content.get("parts", [])
                            for part in parts:
                                if "text" in part:
                                    yield StreamChunk(text=part["text"])
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
                text="Error: Not authenticated. Use /provider antigravity to login."
            )
            return

        body = self._build_request_body(prompt, messages, tools)
        url = f"{ANTIGRAVITY_API_BASE}/v1internal:generateContent"
        headers = self._get_headers(access_token, stream=False)

        async with httpx.AsyncClient(timeout=120) as client:
            response = await client.post(url, json=body, headers=headers)

            if response.status_code != 200:
                yield StreamChunk(
                    text=f"Error: {response.status_code} - {response.text}"
                )
                return

            data = response.json()
            candidates = data.get("candidates", [])

            if candidates:
                content = candidates[0].get("content", {})
                parts = content.get("parts", [])

                for part in parts:
                    if "text" in part:
                        yield StreamChunk(text=part["text"])
                    elif "functionCall" in part:
                        fc = part["functionCall"]
                        yield StreamChunk(
                            tool_calls=[
                                ToolCallData(
                                    id=f"call_{fc['name']}",
                                    name=fc["name"],
                                    arguments=fc.get("args", {}),
                                )
                            ]
                        )

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
                    "https://www.googleapis.com/oauth2/v1/userinfo?alt=json",
                    headers={"Authorization": f"Bearer {access_token}"},
                )
                return response.status_code == 200
        except Exception:
            return False

    def supports_tools(self) -> bool:
        return True

    def get_model_info(self) -> ModelInfo:
        context_sizes = {
            "claude-sonnet-4-5": 200000,
            "claude-sonnet-4-5-thinking": 200000,
            "claude-opus-4-5-thinking": 200000,
            "gemini-3-pro": 1000000,
            "gemini-3-flash": 1000000,
            "gemini-2.5-pro": 1000000,
            "gemini-2.5-flash": 1000000,
        }

        return ModelInfo(
            name=self.model,
            max_tokens=8192,
            context_window=context_sizes.get(self.model, 200000),
        )
