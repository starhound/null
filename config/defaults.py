"""Default configuration values."""

import os

# Theme defaults
DEFAULT_THEME = "null-dark"

# Shell defaults
DEFAULT_SHELL = os.environ.get("SHELL", "/bin/bash")

# AI provider defaults - no default provider, user must configure
DEFAULT_AI_PROVIDER = ""
DEFAULT_AI_MODEL = ""
DEFAULT_AI_ENDPOINT = ""
DEFAULT_AI_ACTIVE_PROMPT = "default"
DEFAULT_AGENT_MODE = False

# Context defaults
DEFAULT_CONTEXT_WINDOW = 4000
DEFAULT_MAX_TOKENS = 2048
DEFAULT_TEMPERATURE = 0.7
