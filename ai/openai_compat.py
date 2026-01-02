from typing import AsyncGenerator, List
import openai
from .base import LLMProvider

class OpenAICompatibleProvider(LLMProvider):
    def __init__(self, api_key: str, base_url: str = None, model: str = "gpt-3.5-turbo"):
        self.client = openai.AsyncOpenAI(
            api_key=api_key,
            base_url=base_url
        )
        self.model = model

    async def generate(self, prompt: str, context: str) -> AsyncGenerator[str, None]:
        try:
            stream = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a helpful AI assistant integrated into a terminal. You can answer questions about the terminal history or provide commands/explanations as requested."},
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
        try:
            models_page = await self.client.models.list()
            return [m.id for m in models_page.data]
        except Exception:
            return []

    async def validate_connection(self) -> bool:
        try:
            await self.client.models.list()
            return True
        except Exception:
            return False
