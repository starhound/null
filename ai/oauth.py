from __future__ import annotations

import asyncio
import base64
import hashlib
import json
import os
import secrets
import webbrowser
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from threading import Thread
from typing import Any
from urllib.parse import parse_qs, urlparse

import httpx

CONFIG_DIR = Path.home() / ".null"
OAUTH_TOKENS_FILE = CONFIG_DIR / "oauth_tokens.json"


@dataclass
class OAuthTokens:
    access_token: str
    refresh_token: str
    expires_at: float
    provider: str

    def is_expired(self) -> bool:
        import time

        return time.time() >= self.expires_at - 60

    def to_dict(self) -> dict[str, Any]:
        return {
            "access_token": self.access_token,
            "refresh_token": self.refresh_token,
            "expires_at": self.expires_at,
            "provider": self.provider,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> OAuthTokens:
        return cls(
            access_token=data["access_token"],
            refresh_token=data["refresh_token"],
            expires_at=data["expires_at"],
            provider=data["provider"],
        )


class PKCEHelper:
    @staticmethod
    def generate() -> tuple[str, str]:
        verifier = secrets.token_urlsafe(32)
        challenge = (
            base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest())
            .rstrip(b"=")
            .decode()
        )
        return verifier, challenge


class OAuthCallbackHandler(BaseHTTPRequestHandler):
    auth_code: str | None = None
    state: str | None = None
    error: str | None = None

    def log_message(self, format: str, *args: Any) -> None:
        pass

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)

        if "error" in params:
            OAuthCallbackHandler.error = params["error"][0]
        elif "code" in params:
            OAuthCallbackHandler.auth_code = params["code"][0]
            OAuthCallbackHandler.state = params.get("state", [None])[0]

        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()

        if OAuthCallbackHandler.error:
            html = "<html><body><h1>Authentication Failed</h1><p>You can close this window.</p></body></html>"
        else:
            html = "<html><body><h1>Authentication Successful</h1><p>You can close this window and return to Null Terminal.</p></body></html>"
        self.wfile.write(html.encode())


class OAuthTokenStore:
    @staticmethod
    def save(tokens: OAuthTokens) -> None:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)

        all_tokens: dict[str, Any] = {}
        if OAUTH_TOKENS_FILE.exists():
            try:
                all_tokens = json.loads(OAUTH_TOKENS_FILE.read_text())
            except (json.JSONDecodeError, OSError):
                pass

        all_tokens[tokens.provider] = tokens.to_dict()
        OAUTH_TOKENS_FILE.write_text(json.dumps(all_tokens, indent=2))

    @staticmethod
    def load(provider: str) -> OAuthTokens | None:
        if not OAUTH_TOKENS_FILE.exists():
            return None

        try:
            all_tokens = json.loads(OAUTH_TOKENS_FILE.read_text())
            if provider in all_tokens:
                return OAuthTokens.from_dict(all_tokens[provider])
        except (json.JSONDecodeError, OSError, KeyError):
            pass

        return None

    @staticmethod
    def delete(provider: str) -> None:
        if not OAUTH_TOKENS_FILE.exists():
            return

        try:
            all_tokens = json.loads(OAUTH_TOKENS_FILE.read_text())
            if provider in all_tokens:
                del all_tokens[provider]
                OAUTH_TOKENS_FILE.write_text(json.dumps(all_tokens, indent=2))
        except (json.JSONDecodeError, OSError):
            pass


class BaseOAuthFlow:
    def __init__(self, callback_port: int = 51121):
        self.callback_port = callback_port
        self.callback_url = f"http://localhost:{callback_port}/oauth-callback"
        self._server: HTTPServer | None = None
        self._server_thread: Thread | None = None

    def _start_callback_server(self) -> None:
        OAuthCallbackHandler.auth_code = None
        OAuthCallbackHandler.state = None
        OAuthCallbackHandler.error = None

        self._server = HTTPServer(
            ("localhost", self.callback_port), OAuthCallbackHandler
        )
        self._server_thread = Thread(target=self._server.handle_request, daemon=True)
        self._server_thread.start()

    def _wait_for_callback(
        self, timeout: float = 120
    ) -> tuple[str | None, str | None, str | None]:
        if self._server_thread:
            self._server_thread.join(timeout=timeout)

        if self._server:
            self._server.server_close()

        return (
            OAuthCallbackHandler.auth_code,
            OAuthCallbackHandler.state,
            OAuthCallbackHandler.error,
        )

    def _open_browser(self, url: str) -> None:
        webbrowser.open(url)
