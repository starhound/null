"""Default configuration values."""

import os

# Theme defaults
DEFAULT_THEME = "null-dark"

# Shell defaults
DEFAULT_SHELL = os.environ.get("SHELL", "/bin/bash")

# AI provider defaults
DEFAULT_AI_PROVIDER = "ollama"
DEFAULT_AI_MODEL = "llama3"
DEFAULT_AI_ENDPOINT = "http://localhost:11434"
DEFAULT_AI_ACTIVE_PROMPT = "default"
DEFAULT_AGENT_MODE = False

# Context defaults
DEFAULT_CONTEXT_WINDOW = 4000
DEFAULT_MAX_TOKENS = 2048
DEFAULT_TEMPERATURE = 0.7
