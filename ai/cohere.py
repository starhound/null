"""Cohere API provider."""

from typing import AsyncGenerator, List, Optional, Dict, Any
from .base import LLMProvider, Message, StreamChunk


class CohereProvider(LLMProvider):
    """Cohere Command API provider."""

    def __init__(self, api_key: str, model: str = "command-r-plus"):
        self.api_key = api_key
        self.model = model
        self._client = None

    def _get_client(self):
        """Lazy-load the Cohere client."""
        if self._client is None:
            try:
                import cohere
                self._client = cohere.AsyncClientV2(api_key=self.api_key)
            except ImportError:
                raise ImportError(
                    "cohere package required. Install with: pip install cohere"
                )
        return self._client

    def supports_tools(self) -> bool:
        """Cohere Command models support tool calling."""
        return True

    def _build_messages(
        self,
        prompt: str,
        messages: List[Message],
        system_prompt: Optional[str]
    ) -> List[Dict[str, Any]]:
        """Build messages for Cohere API."""
        if not system_prompt:
            system_prompt = "You are a helpful AI assistant integrated into a terminal."

        chat_messages = [{"role": "system", "content": system_prompt}]

        for msg in messages:
            role = msg["role"]
            if role == "system":
                continue
            # Cohere uses 'user' and 'assistant'
            chat_messages.append({
                "role": role,
                "content": msg.get("content", "")
            })

        chat_messages.append({"role": "user", "content": prompt})
        return chat_messages

    async def generate(
        self,
        prompt: str,
        messages: List[Message],
        system_prompt: Optional[str] = None
    ) -> AsyncGenerator[str, None]:
        """Stream response from Cohere."""
        try:
            client = self._get_client()
            chat_messages = self._build_messages(prompt, messages, system_prompt)

            stream = client.chat_stream(
                model=self.model,
                messages=chat_messages
            )

            async for event in stream:
                if event.type == "content-delta":
                    if hasattr(event, 'delta') and hasattr(event.delta, 'message'):
                        if hasattr(event.delta.message, 'content'):
                            content = event.delta.message.content
                            if content and hasattr(content, 'text'):
                                yield content.text

        except Exception as e:
            yield f"Error: {str(e)}"

    async def generate_with_tools(
        self,
        prompt: str,
        messages: List[Message],
        tools: List[Dict[str, Any]],
        system_prompt: Optional[str] = None
    ) -> AsyncGenerator[StreamChunk, None]:
        """Generate with tool support."""
        # Fall back to regular generation for now
        # Cohere tool support requires different format conversion
        async for text in self.generate(prompt, messages, system_prompt):
            yield StreamChunk(text=text)

    async def list_models(self) -> List[str]:
        """Return available Cohere models."""
        try:
            client = self._get_client()
            response = await client.models.list()
            return [m.name for m in response.models if hasattr(m, 'name')]
        except Exception:
            # Return known models as fallback
            return [
                "command-r-plus",
                "command-r",
                "command",
                "command-light",
                "command-nightly",
            ]

    async def validate_connection(self) -> bool:
        """Check if Cohere API is reachable."""
        try:
            client = self._get_client()
            await client.models.list()
            return True
        except Exception:
            return False
