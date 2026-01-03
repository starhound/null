import os

from storage import StorageManager

# Keys that should be encrypted
SENSITIVE_KEYS = {
    "ai.openai.api_key",
    "ai.azure.api_key",
    "ai.xai.api_key",
    "ai.bedrock.secret_key",
    "ai.lm_studio.api_key",
}


class Config:
    @staticmethod
    def _get_storage():
        return StorageManager()

    @staticmethod
    def load_all():
        # Helper to load common config into a dict for easy access
        sm = Config._get_storage()
        provider = sm.get_config("ai.provider", "ollama")
        agent_mode_str = sm.get_config("ai.agent_mode", "false")
        agent_mode = agent_mode_str.lower() in ("true", "1", "yes")

        return {
            "theme": sm.get_config("theme", "null-dark"),
            "shell": sm.get_config("shell", os.environ.get("SHELL", "bash")),
            "ai": {
                "provider": provider,
                # Dynamic load based on active provider
                "model": sm.get_config(f"ai.{provider}.model", "llama3"),
                "endpoint": sm.get_config(
                    f"ai.{provider}.endpoint", "http://localhost:11434"
                ),
                "api_key": sm.get_config(f"ai.{provider}.api_key", ""),
                "region": sm.get_config(f"ai.{provider}.region", ""),
                "agent_mode": agent_mode,
                "active_prompt": sm.get_config("ai.active_prompt", "default"),
                "prompts": {
                    "default": """You are an autonomous AI agent running in a Linux terminal. 
You have access to a tool to execute shell commands. use it to answer the user's request.
To execute a command, you MUST output a markdown code block with the language 'bash' or 'sh'.
Example:
```bash
ls -la
```
""",
                    "pirate": "You are a salty pirate styling your answers with nautical slang. You are helpful but gritty.",
                    "concise": "You are a minimal command-line tool. Output only the requested command or brief explanation.",
                    "agent": """You are an autonomous AI agent running in a Linux terminal. 
You have access to a tool to execute shell commands. use it to answer the user's request.

To execute a command, you MUST output a markdown code block with the language 'bash' or 'sh'.
Example:
```bash
ls -la
```

The system will execute the code block and provide you with the output. 
Use this to explore the system, check files, and perform tasks. 
Do not assume standard output; check it by running commands.
""",
                },
            },
        }

    @staticmethod
    def get(key: str, default=None):
        sm = Config._get_storage()
        return sm.get_config(key, default)

    @staticmethod
    def set(key: str, value: str):
        sm = Config._get_storage()
        is_sensitive = key in SENSITIVE_KEYS
        sm.set_config(key, value, is_sensitive=is_sensitive)

    @staticmethod
    def update_key(key_path: list[str], value):
        """Update a specific config key. key_path e.g. ['ai', 'model'] -> key='ai.model'"""
        key_str = ".".join(key_path)
        Config.set(key_str, value)
