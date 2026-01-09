from .openai_compat import OpenAICompatibleProvider

NVIDIA_FREE_MODELS = [
    "meta/llama-3.1-8b-instruct",
    "meta/llama-3.1-70b-instruct",
    "meta/llama-3.2-3b-instruct",
    "meta/llama-3.3-70b-instruct",
    "mistralai/mistral-7b-instruct-v0.3",
    "mistralai/mixtral-8x7b-instruct-v0.1",
    "mistralai/mixtral-8x22b-instruct-v0.1",
    "microsoft/phi-3-mini-128k-instruct",
    "microsoft/phi-3-small-128k-instruct",
    "microsoft/phi-3-medium-128k-instruct",
    "google/gemma-2-9b-it",
    "google/gemma-2-27b-it",
    "nvidia/nemotron-mini-4b-instruct",
    "nvidia/llama-3.1-nemotron-70b-instruct",
    "deepseek-ai/deepseek-coder-6.7b-instruct",
    "ibm/granite-3.0-8b-instruct",
    "qwen/qwen2-7b-instruct",
]


class NVIDIAProvider(OpenAICompatibleProvider):
    def __init__(self, api_key: str, model: str = "meta/llama-3.1-8b-instruct"):
        if not api_key:
            raise ValueError("NVIDIA API key is required")
        super().__init__(
            api_key=api_key,
            base_url="https://integrate.api.nvidia.com/v1",
            model=model,
        )

    async def list_models(self) -> list[str]:
        try:
            all_models = await super().list_models()
            free_set = set(NVIDIA_FREE_MODELS)
            free_available = [m for m in all_models if m in free_set]

            if free_available:
                return sorted(free_available)
            return NVIDIA_FREE_MODELS
        except Exception:
            return NVIDIA_FREE_MODELS
