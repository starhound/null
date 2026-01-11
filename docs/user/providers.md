# AI Providers

Null Terminal is designed to be provider-agnostic, supporting over 20+ local and cloud AI backends. Whether you prefer the privacy of local models or the power of state-of-the-art cloud LLMs, Null has you covered.

---

## Quick Configuration

You can manage your AI providers using the following slash commands:

| Command | Action |
|---------|--------|
| `/providers` | Open the interactive provider management screen (also `F4`) |
| `/provider <name>` | Quickly switch to a specific provider |
| `/model` | Open the model selection UI (also `F2`) |
| `/model <provider> <model>` | Set a specific provider and model |
| `/settings` | Global settings including default provider (also `F3`) |

---

## Local Providers

Local providers allow you to run models on your own hardware, ensuring complete privacy and zero API costs.

=== "Ollama"
    **The easiest way to run local models.**
    
    *   **Endpoint:** `http://localhost:11434` (default)
    *   **API Key:** Not required
    
    **Setup:**
    1.  Install [Ollama](https://ollama.ai).
    2.  Pull a model from the terminal: `ollama pull llama3.2`
    3.  In Null Terminal, run `/provider ollama`.
    
    **Popular Models:** `llama3.2`, `mistral`, `deepseek-coder`, `qwen2.5-coder`.

=== "LM Studio"
    **A powerful GUI for discovering and running local LLMs.**
    
    *   **Endpoint:** `http://localhost:1234/v1` (default)
    *   **API Key:** Not required
    
    **Setup:**
    1.  Install [LM Studio](https://lmstudio.ai).
    2.  Download a model and start the **Local Server**.
    3.  Ensure the server is running on port 1234.
    4.  In Null Terminal, run `/provider lm_studio`.

=== "Llama.cpp"
    **Direct integration with the `llama.cpp` server.**
    
    *   **Endpoint:** `http://localhost:8000/v1` (default)
    *   **API Key:** Not required
    
    **Setup:**
    1.  Start your `llama.cpp` server with the `--api` flag.
    2.  In Null Terminal, run `/provider llama_cpp`.

=== "vLLM"
    **High-throughput serving for local or self-hosted GPU clusters.**
    
    *   **Endpoint:** `http://localhost:8000/v1` (default)
    *   **API Key:** Not required
    
    **Setup:**
    1.  Deploy your vLLM server.
    2.  In Null Terminal, run `/provider vllm` and set your endpoint.

---

## Major Cloud Providers

Cloud providers offer access to the most capable models (GPT-4o, Claude 3.5 Sonnet, Gemini 1.5 Pro) with native tool-calling support.

=== "OpenAI"
    **Industry-standard models with robust tool-calling.**
    
    *   **API Key:** Required (`sk-...`)
    *   **Get Key:** [platform.openai.com](https://platform.openai.com/)
    
    **Setup:**
    1.  Enter your API key in `/providers`.
    2.  Select models like `gpt-4o`, `gpt-4o-mini`, or the reasoning models `o1`.

=== "Anthropic"
    **Claude models known for high-quality coding and reasoning.**
    
    *   **API Key:** Required (`sk-ant-...`)
    *   **Get Key:** [console.anthropic.com](https://console.anthropic.com/)
    
    **Setup:**
    1.  Enter your API key in `/providers`.
    2.  Recommended models: `claude-3-5-sonnet-20241022`, `claude-3-opus`.

=== "Google (AI Studio)"
    **Gemini models with massive context windows (up to 2M tokens).**
    
    *   **API Key:** Required
    *   **Get Key:** [aistudio.google.com](https://aistudio.google.com/)
    
    **Setup:**
    1.  Create a free API key in AI Studio.
    2.  In Null Terminal, run `/provider google`.
    3.  Models: `gemini-2.0-flash`, `gemini-1.5-pro`.

=== "Google Vertex AI"
    **Enterprise Google Cloud Platform (GCP) integration.**
    
    *   **Project ID:** Required
    *   **Location:** `us-central1` (default)
    *   **Auth:** Uses `gcloud auth application-default login`
    
    **Setup:**
    1.  Enable Vertex AI API in your GCP project.
    2.  Install `gcloud` CLI and authenticate.
    3.  In Null Terminal, run `/provider google_vertex`.
    4.  Configure your **Project ID** and **Location**.

=== "Azure OpenAI"
    **Enterprise-grade OpenAI hosting on Microsoft Azure.**
    
    *   **Endpoint:** `https://<resource>.openai.azure.com`
    *   **API Key:** Required
    *   **API Version:** `2024-02-01` (default)
    
    **Setup:**
    1.  Create an Azure OpenAI resource and deploy a model.
    2.  Configure the **Endpoint**, **API Key**, and **Deployment Name** (as the model name).

=== "AWS Bedrock"
    **Access models from Anthropic, Meta, and Amazon via AWS.**
    
    *   **Region:** `us-east-1` (default)
    *   **Credentials:** Uses your `~/.aws/credentials` or environment variables.
    
    **Setup:**
    1.  Enable model access in the AWS Console.
    2.  In Null Terminal, run `/provider bedrock`.
    3.  Model IDs follow AWS format: `anthropic.claude-3-5-sonnet-20241022-v2:0`.

---

## OpenAI-Compatible & Hosted Open Models

These providers offer fast, cost-effective inference for open-weights models like Llama 3, Mixtral, and DeepSeek.

=== "Groq"
    **Ultra-fast inference using LPU technology.**
    
    *   **API Key:** Required
    *   **Get Key:** [console.groq.com](https://console.groq.com/)
    *   **Models:** `llama-3.3-70b-versatile`, `mixtral-8x7b-32768`.

=== "DeepSeek"
    **High-performance, low-cost models from DeepSeek.**
    
    *   **API Key:** Required
    *   **Get Key:** [platform.deepseek.com](https://platform.deepseek.com/)
    *   **Models:** `deepseek-chat`, `deepseek-coder`, `deepseek-reasoner`.

=== "Mistral AI"
    **Native hosting for Mistral, Mixtral, and Codestral.**
    
    *   **API Key:** Required
    *   **Get Key:** [console.mistral.ai](https://console.mistral.ai/)
    *   **Models:** `mistral-large-latest`, `codestral-latest`.

=== "OpenRouter"
    **A unified interface for almost every LLM available.**
    
    *   **API Key:** Required
    *   **Get Key:** [openrouter.ai](https://openrouter.ai/)
    *   **Feature:** Access hundreds of models through a single API key.

=== "Together AI"
    **Fast inference for a wide variety of open models.**
    
    *   **API Key:** Required
    *   **Get Key:** [together.ai](https://www.together.ai/)

=== "NVIDIA NIM"
    **NVIDIA's optimized inference microservices.**
    
    *   **API Key:** Required
    *   **Get Key:** [build.nvidia.com](https://build.nvidia.com/)
    *   **Models:** `meta/llama-3.1-405b-instruct`, `nvidia/nemotron-4-340b-instruct`.

=== "Other Providers"
    Null Terminal also supports:
    *   **xAI (Grok):** Grok-2 and Grok-beta.
    *   **Perplexity:** Sonar models with web search capabilities.
    *   **Fireworks AI:** Fast open model inference.
    *   **Cloudflare Workers AI:** Run models on Cloudflare's edge.
    *   **Cerebras / SambaNova:** Specialized hardware for extreme speed.
    *   **HuggingFace:** Access models via Inference API (TGI/v1).
    *   **Anyscale / Lepton:** Scalable serverless AI inference.

---

## Custom HTTP

If you have a self-hosted API or a provider not listed above that follows the OpenAI API format (e.g., LiteLLM, vLLM, Ollama with OpenAI shim), you can use the **Custom HTTP** provider.

*   **Endpoint:** Your custom URL (e.g., `http://192.168.1.50:8000/v1`)
*   **API Key:** Optional
*   **Model:** Your model identifier

---

## API Key Security

Null Terminal takes the security of your credentials seriously:

- **Encryption:** All API keys are encrypted using **Fernet symmetric encryption** before being stored.
- **Storage:** Encrypted keys are stored in a local SQLite database (`~/.null/null.db`).
- **Key Management:** The encryption key is stored securely in your OS keyring (via `keyring` library). If a keyring is unavailable, it falls back to a hidden file with restricted permissions.
- **Privacy:** API keys are never logged to the console or included in session exports.

---

## Model Selection & Context

When switching models, Null Terminal automatically adjusts to the model's specific capabilities:

1.  **Context Window:** Null tracks the context limit (e.g., 128K for GPT-4o, 200K for Claude 3.5). Use `/context` to see current usage.
2.  **Tool Support:** Not all models support tool-calling (Agent Mode). Local models often require specific prompting for tools, while cloud models have native support.
3.  **Reasoning:** Models like `deepseek-reasoner` or `o1` will display their "Thinking" process in a dedicated expandable block in the TUI.

---

## Pricing Reference (Estimated)

*Pricing per 1M tokens in USD. Updated January 2025.*

| Provider | Model | Input | Output | Context |
|----------|-------|-------|--------|---------|
| **OpenAI** | `gpt-4o` | $2.50 | $10.00 | 128K |
| | `gpt-4o-mini` | $0.15 | $0.60 | 128K |
| | `o1` | $15.00 | $60.00 | 200K |
| **Anthropic** | `claude-3-5-sonnet` | $3.00 | $15.00 | 200K |
| | `claude-3-5-haiku` | $0.80 | $4.00 | 200K |
| **Google** | `gemini-1.5-pro` | $1.25 | $5.00 | 2M |
| | `gemini-1.5-flash` | $0.075 | $0.30 | 1M |
| **DeepSeek** | `deepseek-chat` | $0.14 | $0.28 | 64K |
| | `deepseek-reasoner` | $0.55 | $2.19 | 64K |
| **Groq** | `llama-3.3-70b` | $0.59 | $0.79 | 128K |
| **Mistral** | `mistral-large` | $2.00 | $6.00 | 128K |
| **Cohere** | `command-r-plus` | $2.50 | $10.00 | 128K |
| **Local** | All models | **$0.00** | **$0.00** | Varies |
