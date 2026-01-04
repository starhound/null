"""Built-in prompt templates for Null terminal.

Loads prompts from static/ directory with fallback to inline constants.
"""

from pathlib import Path

STATIC_DIR = Path(__file__).parent / "static"

# Fallback prompts (used if static files are missing)
_FALLBACK_DEFAULT = """You are an AI assistant in a terminal. Be concise.

## CRITICAL: Tool Behavior
- Call ONE tool, then STOP. Do not call multiple tools.
- After a tool returns results, do NOT call more tools unless explicitly asked.
- Do NOT explain what you're doing. Just do it.
- Do NOT provide commentary after tool results.
- The tool result IS the answer. Don't elaborate.

## Response Style
- No preambles ("I'll help you", "Let me", "Sure!")
- No summaries after actions
- Maximum 2-3 sentences if text response needed
- Use code blocks for commands/code only"""

_FALLBACK_CONCISE = """You are a terse AI assistant in a terminal.

Rules:
- Maximum 3 sentences of explanation
- Always use code blocks for commands/code
- No pleasantries or filler words
- Just give the answer"""

_FALLBACK_AGENT = """You are an AI agent that executes commands in the terminal.

## Core Responsibilities
1. **Analyze**: capabilities and constraints before acting
2. **Execute**: use tools to perform actions (one at a time)
3. **Observe**: check tool results carefully
4. **Iterate**: refine commands based on feedback
5. **Report**: provide a final clear answer

## Final Output
- You MUST provide a final answer when the task is complete.
- Start your final answer with "## Result" or "## Answer".
- Summarize what was done and the outcome."""

_FALLBACK_CODE = """You are a programming assistant in a terminal environment.

## Focus Areas
- Code review and suggestions
- Debugging help
- Best practices and patterns
- Documentation and explanation

Always use proper markdown code blocks with language identifiers."""

_FALLBACK_DEVOPS = """You are a DevOps and system administration assistant.

## Expertise
- Linux/Unix system administration
- Docker, Kubernetes, containers
- CI/CD pipelines
- Cloud infrastructure (AWS, GCP, Azure)

Always use ```bash for commands and explain any destructive operations."""

# Fallback registry
_FALLBACKS = {
    "default": _FALLBACK_DEFAULT,
    "concise": _FALLBACK_CONCISE,
    "agent": _FALLBACK_AGENT,
    "code": _FALLBACK_CODE,
    "devops": _FALLBACK_DEVOPS,
}

# Prompt metadata
_PROMPT_META = {
    "default": {
        "name": "Default",
        "description": "Balanced assistant for terminal use",
    },
    "concise": {
        "name": "Concise",
        "description": "Minimal, terse responses",
    },
    "agent": {
        "name": "Agent",
        "description": "Autonomous task execution mode",
    },
    "code": {
        "name": "Code Helper",
        "description": "Programming and code review focus",
    },
    "devops": {
        "name": "DevOps",
        "description": "System admin and infrastructure",
    },
}


def _load_prompt_file(name: str) -> str | None:
    """Load a prompt from static directory.

    Args:
        name: The prompt name (without extension).

    Returns:
        The prompt content, or None if file doesn't exist.
    """
    filepath = STATIC_DIR / f"{name}.md"
    if filepath.exists():
        try:
            return filepath.read_text(encoding="utf-8")
        except Exception:
            pass
    return None


def _load_builtin_prompts() -> dict:
    """Load all built-in prompts from static directory with fallbacks.

    Returns:
        Dictionary mapping prompt keys to prompt data (name, description, content).
    """
    prompts = {}

    for key, meta in _PROMPT_META.items():
        # Try loading from file first
        content = _load_prompt_file(key)

        # Fall back to inline constant
        if content is None:
            content = _FALLBACKS.get(key, "")

        prompts[key] = {
            "name": meta["name"],
            "description": meta["description"],
            "content": content,
        }

    return prompts


# Load on module import (cached)
BUILTIN_PROMPTS = _load_builtin_prompts()

# Convenience accessors for backward compatibility
DEFAULT_PROMPT = BUILTIN_PROMPTS.get("default", {}).get("content", "")
CONCISE_PROMPT = BUILTIN_PROMPTS.get("concise", {}).get("content", "")
AGENT_PROMPT = BUILTIN_PROMPTS.get("agent", {}).get("content", "")
CODE_PROMPT = BUILTIN_PROMPTS.get("code", {}).get("content", "")
DEVOPS_PROMPT = BUILTIN_PROMPTS.get("devops", {}).get("content", "")
