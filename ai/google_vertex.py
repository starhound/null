"""Google Vertex AI provider."""

from typing import AsyncGenerator, List, Optional, Dict, Any
from .base import LLMProvider, Message, StreamChunk


class GoogleVertexProvider(LLMProvider):
    """Google Vertex AI / Gemini provider."""

    def __init__(
        self,
        project_id: str,
        location: str = "us-central1",
        model: str = "gemini-1.5-flash",
        api_key: str = None
    ):
        self.project_id = project_id
        self.location = location
        self.model = model
        self.api_key = api_key
        self._client = None

    def _get_client(self):
        """Lazy-load the Vertex AI client."""
        if self._client is None:
            try:
                import google.generativeai as genai

                if self.api_key:
                    # Use API key auth (simpler, works for Gemini API)
                    genai.configure(api_key=self.api_key)
                # else: uses ADC (Application Default Credentials)

                self._client = genai.GenerativeModel(self.model)
            except ImportError:
                raise ImportError(
                    "google-generativeai package required. "
                    "Install with: pip install google-generativeai"
                )
        return self._client

    def _build_contents(
        self,
        prompt: str,
        messages: List[Message],
        system_prompt: Optional[str]
    ) -> tuple:
        """Build contents for Gemini API."""
        # Gemini uses 'user' and 'model' roles
        contents = []

        for msg in messages:
            role = "model" if msg["role"] == "assistant" else "user"
            if msg.get("content"):
                contents.append({"role": role, "parts": [msg["content"]]})

        # Add current prompt
        contents.append({"role": "user", "parts": [prompt]})

        return contents, system_prompt

    async def generate(
        self,
        prompt: str,
        messages: List[Message],
        system_prompt: Optional[str] = None
    ) -> AsyncGenerator[str, None]:
        """Stream response from Gemini."""
        try:
            client = self._get_client()
            contents, sys_prompt = self._build_contents(prompt, messages, system_prompt)

            # Configure generation
            generation_config = {
                "temperature": 0.7,
                "max_output_tokens": 8192,
            }

            # Start chat with history if we have messages
            if len(contents) > 1:
                history = contents[:-1]
                chat = client.start_chat(history=history)
                response = await chat.send_message_async(
                    contents[-1]["parts"][0],
                    generation_config=generation_config,
                    stream=True
                )
            else:
                response = await client.generate_content_async(
                    contents[-1]["parts"][0],
                    generation_config=generation_config,
                    stream=True
                )

            async for chunk in response:
                if chunk.text:
                    yield chunk.text

        except Exception as e:
            yield f"Error: {str(e)}"

    async def generate_with_tools(
        self,
        prompt: str,
        messages: List[Message],
        tools: List[Dict[str, Any]],
        system_prompt: Optional[str] = None
    ) -> AsyncGenerator[StreamChunk, None]:
        """Generate with tool support (Gemini supports function calling)."""
        # For now, fall back to regular generation
        # Full tool support requires converting OpenAI tool format to Gemini format
        async for text in self.generate(prompt, messages, system_prompt):
            yield StreamChunk(text=text)

    async def list_models(self) -> List[str]:
        """List available Gemini models."""
        try:
            import google.generativeai as genai

            if self.api_key:
                genai.configure(api_key=self.api_key)

            models = []
            for model in genai.list_models():
                if "generateContent" in model.supported_generation_methods:
                    # Strip 'models/' prefix
                    name = model.name.replace("models/", "")
                    models.append(name)
            return models
        except Exception:
            # Return common models as fallback
            return [
                "gemini-1.5-flash",
                "gemini-1.5-flash-8b",
                "gemini-1.5-pro",
                "gemini-1.0-pro",
                "gemini-2.0-flash-exp",
            ]

    async def validate_connection(self) -> bool:
        """Check if Gemini API is reachable."""
        try:
            client = self._get_client()
            # Quick test with minimal tokens
            response = await client.generate_content_async("Hi", stream=False)
            return response is not None
        except Exception:
            return False
