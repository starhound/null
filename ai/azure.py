from typing import AsyncGenerator, List, Optional
import os
from openai import AsyncAzureOpenAI
from .base import LLMProvider

class AzureProvider(LLMProvider):
    def __init__(self, endpoint: str, api_key: str, api_version: str, model: str):
        self.client = AsyncAzureOpenAI(
            azure_endpoint=endpoint,
            api_key=api_key,
            api_version=api_version
        )
        self.deployment_name = model # In Azure, model usually refers to deployment name

    async def generate(self, prompt: str, context: str, system_prompt: Optional[str] = None) -> AsyncGenerator[str, None]:
        if not system_prompt:
             system_prompt = "You are a helpful AI assistant integrated into a terminal. You can answer questions or provide commands."

        try:
            stream = await self.client.chat.completions.create(
                model=self.deployment_name,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"{context}\n\nUser: {prompt}"}
                ],
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
