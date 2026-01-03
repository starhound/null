# AI Providers

Null Terminal supports 20+ AI providers. Configure them via `/providers` or `/provider <name>`.

## Local Providers

### Ollama

Local AI models via Ollama.

```
Endpoint: http://localhost:11434 (default)
API Key: Not required
```

**Setup:**
1. Install Ollama: https://ollama.ai
2. Pull a model: `ollama pull llama3.2`
3. In Null Terminal: `/provider ollama`

**Popular Models:**
- `llama3.2` - Meta's latest Llama
- `mistral` - Mistral 7B
- `codellama` - Code-focused Llama
- `deepseek-coder` - DeepSeek Coder

### LM Studio

Local models via LM Studio's OpenAI-compatible API.

```
Endpoint: http://localhost:1234/v1 (default)
API Key: Not required
```

**Setup:**
1. Install LM Studio: https://lmstudio.ai
2. Load a model and start the server
3. In Null Terminal: `/provider lm_studio`

## Cloud Providers

### OpenAI

```
Endpoint: https://api.openai.com/v1 (default)
API Key: Required (sk-...)
```

**Models:**
- `gpt-4o` - Latest GPT-4 Omni
- `gpt-4-turbo` - GPT-4 Turbo
- `gpt-3.5-turbo` - Fast and affordable

### Anthropic

```
Endpoint: https://api.anthropic.com (default)
API Key: Required (sk-ant-...)
```

**Models:**
- `claude-sonnet-4-20250514` - Claude Sonnet 4
- `claude-3-5-sonnet-20241022` - Claude 3.5 Sonnet
- `claude-3-opus-20240229` - Claude 3 Opus

### Google (Vertex AI)

```
Project ID: Required
Region: us-central1 (default)
```

**Setup:**
1. Enable Vertex AI API in Google Cloud
2. Set up authentication: `gcloud auth application-default login`
3. Configure project ID in Null Terminal

**Models:**
- `gemini-2.0-flash` - Gemini 2.0 Flash
- `gemini-1.5-pro` - Gemini 1.5 Pro

### Azure OpenAI

```
Endpoint: https://<resource>.openai.azure.com
API Key: Required
API Version: 2024-02-15-preview (default)
```

**Setup:**
1. Create Azure OpenAI resource
2. Deploy a model
3. Configure endpoint and key

### AWS Bedrock

```
Region: us-east-1 (default)
```

**Setup:**
1. Enable Bedrock in AWS Console
2. Request model access
3. Configure AWS credentials (`~/.aws/credentials`)

**Models:**
- `anthropic.claude-3-5-sonnet-20241022-v2:0`
- `amazon.titan-text-express-v1`

### Cohere

```
Endpoint: https://api.cohere.ai (default)
API Key: Required
```

**Models:**
- `command-r-plus` - Most capable
- `command-r` - Fast and efficient

## OpenAI-Compatible Providers

These use the same API format as OpenAI:

### Groq

```
Endpoint: https://api.groq.com/openai/v1
API Key: Required
```

**Models:** `llama-3.3-70b-versatile`, `mixtral-8x7b-32768`

### Mistral

```
Endpoint: https://api.mistral.ai/v1
API Key: Required
```

**Models:** `mistral-large-latest`, `codestral-latest`

### Together AI

```
Endpoint: https://api.together.xyz/v1
API Key: Required
```

**Models:** `meta-llama/Llama-3.2-90B-Vision-Instruct-Turbo`

### xAI (Grok)

```
Endpoint: https://api.x.ai/v1
API Key: Required
```

**Models:** `grok-beta`

### OpenRouter

```
Endpoint: https://openrouter.ai/api/v1
API Key: Required
```

Unified API for many providers. See https://openrouter.ai/models

### DeepSeek

```
Endpoint: https://api.deepseek.com/v1
API Key: Required
```

**Models:** `deepseek-chat`, `deepseek-coder`

### Perplexity

```
Endpoint: https://api.perplexity.ai
API Key: Required
```

**Models:** `llama-3.1-sonar-large-128k-online`

### Fireworks AI

```
Endpoint: https://api.fireworks.ai/inference/v1
API Key: Required
```

### NVIDIA NIM

```
Endpoint: https://integrate.api.nvidia.com/v1
API Key: Required
```

### Cloudflare Workers AI

```
Endpoint: https://api.cloudflare.com/client/v4/accounts/<id>/ai/v1
API Key: Required
Account ID: Required
```

### Custom HTTP

Any OpenAI-compatible endpoint:

```
Endpoint: Your custom URL
API Key: Optional
```

## Quick Setup

1. **Open providers screen:** `/providers`
2. **Select a provider** from the list
3. **Enter credentials** (API key, endpoint, etc.)
4. **Test connection** - validates configuration
5. **Select a model:** `/model`

## Switching Providers

```bash
# Switch to a different provider
/provider anthropic

# Set a specific model
/model anthropic claude-3-5-sonnet-20241022

# Or use the model selector
/model  # Opens selection UI
```

## API Key Security

- API keys are encrypted with Fernet encryption
- Stored in SQLite database (`~/.null/null.db`)
- Encryption key in OS keyring or `~/.null/.key`
- Keys never logged or displayed in plain text
