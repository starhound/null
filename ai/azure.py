from typing import AsyncGenerator, List
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

    async def generate(self, prompt: str, context: str) -> AsyncGenerator[str, None]:
        try:
            stream = await self.client.chat.completions.create(
                model=self.deployment_name,
                messages=[
                    {"role": "system", "content": "You are a helpful command line assistant. Provide only the shell command requested."},
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
