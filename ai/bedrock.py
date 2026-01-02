from typing import AsyncGenerator, List, Optional
import boto3
import json
import asyncio
from .base import LLMProvider

class BedrockProvider(LLMProvider):
    def __init__(self, region_name: str, model: str = "anthropic.claude-v2"):
        # Boto3 client is synchronous usually, need to tread carefully with async gen
        # We might need to run blocking calls in a thread or use aiobotocore is better,
        # but to keep dependencies low(er), we'll do run_in_executor for standard boto3 if needed,
        # OR just use standard boto3 and yield (blocking the loop slightly, bad practice but fine for MVP)
        # Actuallly, for streaming response, boto3 returns a stream we can iterate.
        self.client = boto3.client("bedrock-runtime", region_name=region_name)
        self.bedrock = boto3.client("bedrock", region_name=region_name)
        self.model = model

    async def generate(self, prompt: str, context: str, system_prompt: Optional[str] = None) -> AsyncGenerator[str, None]:
        # Construct payload based on model family (Claude vs generic)
        # MVP: Support Claude (Messages API) and Llama
        
        if not system_prompt:
            system_prompt = "You are a helpful AI assistant."

        body = {}
        if "claude" in self.model:
            # Anthropic Claude 3 / Messages format
             body = json.dumps({
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 1024,
                "system": system_prompt,
                "messages": [
                    {
                        "role": "user",
                        "content": f"{context}\n\nUser: {prompt}\n\nAssistant:"
                    }
                ]
            })
        elif "llama" in self.model:
             body = json.dumps({
                "prompt": f"[INST] {context}\n\n{prompt} [/INST]",
                "max_gen_len": 200,
                "temperature": 0.1,
                "top_p": 0.9
            })
        else:
            yield "Error: Unsupported model family for auto-formatting."
            return

        try:
            # This IO is blocking in standard boto3. 
            # Ideally we wrap this in asyncio.to_thread but the stream object returned 
            # needs to be iterated.
            response = self.client.invoke_model_with_response_stream(
                modelId=self.model,
                body=body
            )
            
            stream = response.get('body')
            if stream:
                for event in stream:
                    # BLOCKING iteration
                    chunk = event.get('chunk')
                    if chunk:
                        chunk_json = json.loads(chunk.get('bytes').decode())
                        # Extract text based on model
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
