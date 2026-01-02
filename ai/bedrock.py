from typing import AsyncGenerator, List, Optional
import boto3
import json
import asyncio
from .base import LLMProvider, Message

class BedrockProvider(LLMProvider):
    def __init__(self, region_name: str, model: str = "anthropic.claude-v2"):
        self.client = boto3.client("bedrock-runtime", region_name=region_name)
        self.bedrock = boto3.client("bedrock", region_name=region_name)
        self.model = model

    async def generate(
        self,
        prompt: str,
        messages: List[Message],
        system_prompt: Optional[str] = None
    ) -> AsyncGenerator[str, None]:
        """Generate response using Bedrock with proper message format."""
        if not system_prompt:
            system_prompt = "You are a helpful AI assistant."

        body = {}
        if "claude" in self.model:
            # Build proper messages array for Claude
            claude_messages = []
            for msg in messages:
                claude_messages.append({
                    "role": msg["role"],
                    "content": msg["content"]
                })
            # Add current prompt
            claude_messages.append({"role": "user", "content": prompt})

            body = json.dumps({
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 4096,
                "system": system_prompt,
                "messages": claude_messages
            })
        elif "llama" in self.model:
            # Build context string for Llama
            context_parts = []
            for msg in messages:
                if msg["role"] == "user":
                    context_parts.append(f"User: {msg['content']}")
                else:
                    context_parts.append(f"Assistant: {msg['content']}")
            context = "\n".join(context_parts)

            body = json.dumps({
                "prompt": f"[INST] <<SYS>>{system_prompt}<</SYS>>\n\n{context}\n\nUser: {prompt} [/INST]",
                "max_gen_len": 2048,
                "temperature": 0.1,
                "top_p": 0.9
            })
        else:
            yield "Error: Unsupported model family for auto-formatting."
            return

        try:
            response = self.client.invoke_model_with_response_stream(
                modelId=self.model,
                body=body
            )

            stream = response.get('body')
            if stream:
                for event in stream:
                    chunk = event.get('chunk')
                    if chunk:
                        chunk_json = json.loads(chunk.get('bytes').decode())
                        text = ""
                        if "claude" in self.model:
                            if chunk_json.get('type') == 'content_block_delta':
                                text = chunk_json['delta'].get('text', '')
                        elif "llama" in self.model:
                            text = chunk_json.get('generation', '')

                        if text:
                            yield text

        except Exception as e:
            yield f"Error: {str(e)}"

    async def list_models(self) -> List[str]:
        try:
            # This is blocking
            response = self.bedrock.list_foundation_models()
            return [m['modelId'] for m in response.get('modelSummaries', [])]
        except Exception:
            return []

    async def validate_connection(self) -> bool:
        try:
            self.bedrock.list_foundation_models()
            return True
        except Exception:
            return False
