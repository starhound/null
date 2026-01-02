from abc import ABC, abstractmethod
from typing import AsyncGenerator, List, Optional

class LLMProvider(ABC):
    @abstractmethod
    async def generate(self, prompt: str, context: str, system_prompt: Optional[str] = None) -> AsyncGenerator[str, None]:
        """Stream response from the LLM."""
        pass

    @abstractmethod
    async def list_models(self) -> List[str]:
        """Return a list of available model names."""
        pass

    @abstractmethod
    async def validate_connection(self) -> bool:
        """Check if the provider is reachable."""
        pass
