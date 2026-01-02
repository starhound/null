from typing import AsyncGenerator, List, Optional
import os
from openai import AsyncAzureOpenAI
from .base import LLMProvider, Message

class AzureProvider(LLMProvider):
    def __init__(self, endpoint: str, api_key: str, api_version: str, model: str):
        self.client = AsyncAzureOpenAI(
            azure_endpoint=endpoint,
            api_key=api_key,
            api_version=api_version
        )
        self.deployment_name = model  # In Azure, model usually refers to deployment name
        self.model = model

    async def generate(
        self,
        prompt: str,
        messages: List[Message],
        system_prompt: Optional[str] = None
    ) -> AsyncGenerator[str, None]:
        """Generate response using Azure OpenAI with proper message format."""
        if not system_prompt:
            system_prompt = "You are a helpful AI assistant integrated into a terminal."

        # Build messages array with system prompt first
        chat_messages = [{"role": "system", "content": system_prompt}]

        # Add conversation history
        for msg in messages:
            chat_messages.append({"role": msg["role"], "content": msg["content"]})

        # Add current user prompt
        chat_messages.append({"role": "user", "content": prompt})

        try:
            stream = await self.client.chat.completions.create(
                model=self.deployment_name,
                messages=chat_messages,
                stream=True
            )
            async for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
        except Exception as e:
            yield f"Error: {str(e)}"

    async def list_models(self) -> List[str]:
        # Azure doesn't easily list deployments via standard list_models in the same way,
        # but we can try to list models if permissible.
        # Often in Azure you just have specific deployments.
        return [self.deployment_name] 

    async def validate_connection(self) -> bool:
        # A bit tricky without a simple ping, but let's assume if client init worked it's okay-ish
        # or try a dummy completion.
        return True
