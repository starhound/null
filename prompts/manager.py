"""Prompt manager for loading and managing prompts."""

import json
from pathlib import Path

from .templates import BUILTIN_PROMPTS


class PromptManager:
    """Manages built-in and user-defined prompts."""

    def __init__(self):
        self.prompts_dir = Path.home() / ".null" / "prompts"
        self._user_prompts: dict = {}
        self._ensure_prompts_dir()
        self._load_user_prompts()

    def _ensure_prompts_dir(self):
        """Create prompts directory and example files if needed."""
        if not self.prompts_dir.exists():
            self.prompts_dir.mkdir(parents=True, exist_ok=True)
            self._create_example_prompts()

    def _create_example_prompts(self):
        """Create example prompt files for users."""
        # Example markdown prompt
        example_md = self.prompts_dir / "example.md.example"
        example_md.write_text("""# Custom Prompt Example

You are a helpful assistant specialized in [your domain].

## Guidelines
- Your custom rules here
- Format preferences
- Domain-specific knowledge

## Response Format
Describe how you want responses formatted.

---
To use this prompt:
1. Remove the .example extension
2. Edit the content above
3. Select it with /prompts command
""")

        # Example JSON prompt with metadata
        example_json = self.prompts_dir / "example.json.example"
        example_json.write_text(
            json.dumps(
                {
                    "name": "My Custom Prompt",
                    "description": "A custom prompt for specific tasks",
                    "content": "You are a helpful assistant...",
                    "provider_overrides": {
                        "ollama": {
                            "temperature": 0.7,
                            "content_suffix": "\nRespond in a conversational tone.",
                        },
                        "openai": {"temperature": 0.5},
                    },
                },
                indent=2,
            )
        )

    def _load_user_prompts(self):
        """Load prompts from ~/.null/prompts/"""
        self._user_prompts = {}

        if not self.prompts_dir.exists():
            return

        # Load .md files
        for md_file in self.prompts_dir.glob("*.md"):
            if md_file.name.endswith(".example"):
                continue
            try:
                content = md_file.read_text()
                name = md_file.stem
                self._user_prompts[name] = {
                    "name": name.replace("-", " ").replace("_", " ").title(),
                    "description": f"Custom prompt from {md_file.name}",
                    "content": content,
                    "source": str(md_file),
                }
            except Exception:
                pass

        # Load .txt files
        for txt_file in self.prompts_dir.glob("*.txt"):
            if txt_file.name.endswith(".example"):
                continue
            try:
                content = txt_file.read_text()
                name = txt_file.stem
                self._user_prompts[name] = {
                    "name": name.replace("-", " ").replace("_", " ").title(),
                    "description": f"Custom prompt from {txt_file.name}",
                    "content": content,
                    "source": str(txt_file),
                }
            except Exception:
                pass

        # Load .json files (with metadata)
        for json_file in self.prompts_dir.glob("*.json"):
            if json_file.name.endswith(".example"):
                continue
            try:
                data = json.loads(json_file.read_text())
                name = json_file.stem
                self._user_prompts[name] = {
                    "name": data.get("name", name),
                    "description": data.get("description", "Custom prompt"),
                    "content": data.get("content", ""),
                    "source": str(json_file),
                    "provider_overrides": data.get("provider_overrides", {}),
                }
            except Exception:
                pass

    def reload(self):
        """Reload user prompts from disk."""
        self._load_user_prompts()

    def get_all_prompts(self) -> dict:
        """Get all available prompts (built-in + user)."""
        prompts = dict(BUILTIN_PROMPTS)
        prompts.update(self._user_prompts)
        return prompts

    def get_prompt(self, key: str) -> dict | None:
        """Get a specific prompt by key."""
        if key in BUILTIN_PROMPTS:
            return BUILTIN_PROMPTS[key]
        return self._user_prompts.get(key)

    def get_prompt_content(self, key: str, provider: str | None = None) -> str:
        """Get prompt content, with optional provider-specific overrides."""
        prompt = self.get_prompt(key)
        if not prompt:
            # Fallback to default
            prompt = BUILTIN_PROMPTS["default"]

        content = prompt.get("content", "")

        # Apply provider overrides if available
        if provider and "provider_overrides" in prompt:
            provider_overrides = prompt["provider_overrides"]
            if isinstance(provider_overrides, dict):
                overrides = provider_overrides.get(provider, {})
                if isinstance(overrides, dict):
                    if "content_suffix" in overrides:
                        content += overrides["content_suffix"]
                    if "content_prefix" in overrides:
                        content = overrides["content_prefix"] + content
                    if "content" in overrides:
                        content = overrides["content"]

        return content

    def list_prompts(self) -> list[tuple[str, str, str, bool]]:
        """List all prompts: (key, name, description, is_user)"""
        result = []

        # Built-in first
        for key, data in BUILTIN_PROMPTS.items():
            result.append((key, data["name"], data["description"], False))

        # Then user prompts
        for key, data in self._user_prompts.items():
            result.append((key, data["name"], data["description"], True))

        return result

    def save_prompt(self, key: str, name: str, description: str, content: str) -> Path:
        """Save a new user prompt."""
        data = {
            "name": name,
            "description": description,
            "content": content,
        }

        filepath = self.prompts_dir / f"{key}.json"
        filepath.write_text(json.dumps(data, indent=2))

        # Reload to pick up the new prompt
        self._load_user_prompts()

        return filepath

    def delete_prompt(self, key: str) -> bool:
        """Delete a user prompt. Returns True if deleted."""
        if key in BUILTIN_PROMPTS:
            return False  # Can't delete built-in

        prompt = self._user_prompts.get(key)
        if not prompt:
            return False

        source = prompt.get("source")
        if source:
            try:
                Path(source).unlink()
                del self._user_prompts[key]
                return True
            except Exception:
                pass

        return False


# Global instance
_manager: PromptManager | None = None


def get_prompt_manager() -> PromptManager:
    """Get the global prompt manager instance."""
    global _manager
    if _manager is None:
        _manager = PromptManager()
    return _manager
