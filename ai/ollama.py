import httpx
import json
from typing import AsyncGenerator, List, Optional
from .base import LLMProvider

class OllamaProvider(LLMProvider):
    def __init__(self, endpoint: str, model: str):
        self.endpoint = endpoint
        self.model = model
        self.client = httpx.AsyncClient(timeout=30.0)

    async def generate(self, prompt: str, context: str) -> AsyncGenerator[str, None]:
        url = f"{self.endpoint}/api/generate"
        payload = {
            "model": self.model,
            "prompt": f"{context}\n\nUser Question: {prompt}\n\nStrict Command Line Answer:",
            "stream": True
        }
        
        try:
            async with self.client.stream("POST", url, json=payload) as response:
                async for line in response.aiter_lines():
                    if not line:
                        continue
                    try:
                        data = json.loads(line)
                        if "response" in data:
                            yield data["response"]
                        if data.get("done", False):
                            break
                    except json.JSONDecodeError:
                        continue
        except httpx.HTTPError:
            yield "Error: Could not connect to Ollama."

    async def list_models(self) -> List[str]:
        url = f"{self.endpoint}/api/tags"
        try:
            response = await self.client.get(url)
            if response.status_code == 200:
                data = response.json()
                return [model["name"] for model in data.get("models", [])]
        except httpx.HTTPError:
            pass
        return []

    async def validate_connection(self) -> bool:
        url = f"{self.endpoint}/api/tags" # Just checking if reachable
        try:
            response = await self.client.get(url)
            return response.status_code == 200
        except httpx.HTTPError:
            return False

    async def close(self):
        await self.client.aclose()
