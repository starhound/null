# PROJECT KNOWLEDGE BASE: AI SUBSYSTEM

**Generated:** 2026-01-05
**Context:** Provider Abstraction, Async Streaming, Tool Calling, Thinking Strategies

## OVERVIEW
Unified AI integration layer providing a consistent interface for local and cloud LLMs via a provider abstraction pattern.

## STRUCTURE
```
ai/
├── base.py            # Core ABC (LLMProvider), Message, and StreamChunk types
├── factory.py         # AIFactory for provider instantiation and metadata
├── manager.py         # AIManager for multi-provider lifecycle and parallel listing
├── thinking.py        # ThinkingStrategy system for reasoning extraction
├── openai_compat.py   # Generic OpenAI-compatible API adapter (Base for many)
├── anthropic.py       # Anthropic Claude native SDK implementation
├── ollama.py          # Local Ollama API integration
└── [others].py        # Google Vertex, Azure, Bedrock, Cohere, etc.
```

## WHERE TO LOOK
| Component | File | Role |
|-----------|------|------|
| **LLM Interface** | `base.py` | `LLMProvider` abstract methods (`generate`, `list_models`) |
| **Instantiation** | `factory.py` | `AIFactory.get_provider` maps config to classes |
| **Model Fetching**| `manager.py` | `list_all_models` handles parallel async provider calls |
| **Reasoning**    | `thinking.py` | `ThinkingStrategy` for parsing `<think>` or JSON reasoning |
| **Pricing**      | `base.py` | `MODEL_PRICING` and `calculate_cost` logic |

## CONVENTIONS
*   **Async First**: All generation MUST use `AsyncGenerator[StreamChunk, None]`.
*   **Provider Pattern**: Every AI backend must inherit from `LLMProvider`.
*   **Unified Message Format**: Uses OpenAI-style `role`, `content`, `tool_calls` structure.
*   **Tool Calling**: Implement `generate_with_tools` for providers that support native function calling.
*   **Thinking Extraction**: Use `get_thinking_strategy` to handle model-specific reasoning (XML, JSON, or Native).
*   **Model Info**: Context windows and pricing are maintained in `base.py`.

## ANTI-PATTERNS
*   **No Synchronous Clients**: Never use `requests` or blocking SDKs; use `httpx.AsyncClient`.
*   **No Direct Config Access**: Providers receive specific settings via `__init__`, not by reading global `Config`.
*   **No Raw Parsing**: Prefer `StreamChunk` over raw string yields to preserve tool calls and usage data.
*   **No Hardcoded Models**: Register new models in `KNOWN_MODEL_CONTEXTS` and `MODEL_PRICING` in `base.py`.
*   **No Blocking in Factory**: Provider initialization should be lightweight; keep network checks in `validate_connection`.
