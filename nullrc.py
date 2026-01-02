"""Project-local .nullrc configuration support."""

import json
import os
from pathlib import Path
from typing import Any, Optional
from dataclasses import dataclass, field, asdict


@dataclass
class ProjectConfig:
    """Project-specific configuration from .nullrc."""

    # AI settings
    provider: Optional[str] = None
    model: Optional[str] = None
    system_prompt: Optional[str] = None
    temperature: Optional[float] = None

    # Shell settings
    shell: Optional[str] = None
    env: dict = field(default_factory=dict)

    # Project context
    context_files: list = field(default_factory=list)  # Files to include in AI context
    ignore_patterns: list = field(default_factory=list)  # Files to ignore

    # Command aliases
    aliases: dict = field(default_factory=dict)  # e.g., {"build": "npm run build"}

    # Startup commands
    on_start: list = field(default_factory=list)  # Commands to run on project load

    def to_dict(self) -> dict:
        """Convert to dictionary, filtering None values."""
        result = {}
        for key, value in asdict(self).items():
            if value is not None and value != [] and value != {}:
                result[key] = value
        return result

    @classmethod
    def from_dict(cls, data: dict) -> "ProjectConfig":
        """Create ProjectConfig from dictionary."""
        config = cls()
        for key, value in data.items():
            if hasattr(config, key):
                setattr(config, key, value)
        return config


class NullrcManager:
    """Manages .nullrc files in project directories."""

    NULLRC_NAMES = [".nullrc", ".nullrc.json", "nullrc.json"]

    def __init__(self):
        self._cache: dict[str, ProjectConfig] = {}
        self._file_cache: dict[str, Path] = {}

    def find_nullrc(self, start_path: Optional[Path] = None) -> Optional[Path]:
        """Find .nullrc file by walking up from start_path or cwd."""
        if start_path is None:
            start_path = Path.cwd()

        current = start_path.resolve()
        home = Path.home()

        while current != current.parent:
            for name in self.NULLRC_NAMES:
                nullrc_path = current / name
                if nullrc_path.exists():
                    return nullrc_path

            # Don't search above home directory
            if current == home:
                break
            current = current.parent

        return None

    def load(self, start_path: Optional[Path] = None) -> Optional[ProjectConfig]:
        """Load .nullrc from current directory or parents."""
        nullrc_path = self.find_nullrc(start_path)

        if nullrc_path is None:
            return None

        # Check cache
        cache_key = str(nullrc_path)
        if cache_key in self._cache:
            return self._cache[cache_key]

        try:
            content = nullrc_path.read_text(encoding="utf-8")
            data = json.loads(content)
            config = ProjectConfig.from_dict(data)

            self._cache[cache_key] = config
            self._file_cache[cache_key] = nullrc_path

            return config
        except Exception:
            return None

    def get_project_root(self, start_path: Optional[Path] = None) -> Optional[Path]:
        """Get the project root (directory containing .nullrc)."""
        nullrc_path = self.find_nullrc(start_path)
        if nullrc_path:
            return nullrc_path.parent
        return None

    def create_default(self, path: Optional[Path] = None) -> Path:
        """Create a default .nullrc in the specified directory."""
        if path is None:
            path = Path.cwd()

        nullrc_path = path / ".nullrc"

        default_config = {
            "provider": None,
            "model": None,
            "system_prompt": "You are a helpful assistant working on this project.",
            "context_files": ["README.md", "package.json", "pyproject.toml"],
            "ignore_patterns": ["node_modules", ".git", "__pycache__", "*.pyc"],
            "aliases": {
                "test": "npm test",
                "build": "npm run build",
                "lint": "npm run lint"
            },
            "env": {},
            "on_start": []
        }

        nullrc_path.write_text(
            json.dumps(default_config, indent=2),
            encoding="utf-8"
        )

        return nullrc_path

    def apply_to_config(self, base_config: dict, project_config: ProjectConfig) -> dict:
        """Apply project config overrides to base config."""
        config = base_config.copy()

        if project_config.provider:
            config.setdefault("ai", {})["provider"] = project_config.provider

        if project_config.model:
            config.setdefault("ai", {})["model"] = project_config.model

        if project_config.shell:
            config["shell"] = project_config.shell

        if project_config.temperature is not None:
            config.setdefault("ai", {})["temperature"] = project_config.temperature

        return config

    def get_context_files(self, project_config: ProjectConfig) -> list[Path]:
        """Get list of context files that exist in the project."""
        project_root = self.get_project_root()
        if not project_root:
            return []

        files = []
        for pattern in project_config.context_files:
            if "*" in pattern:
                # Glob pattern
                files.extend(project_root.glob(pattern))
            else:
                # Direct file
                file_path = project_root / pattern
                if file_path.exists():
                    files.append(file_path)

        return files

    def reload(self):
        """Clear cache and reload."""
        self._cache.clear()
        self._file_cache.clear()


# Singleton instance
_nullrc_manager: Optional[NullrcManager] = None


def get_nullrc_manager() -> NullrcManager:
    """Get the singleton NullrcManager instance."""
    global _nullrc_manager
    if _nullrc_manager is None:
        _nullrc_manager = NullrcManager()
    return _nullrc_manager


def get_project_config() -> Optional[ProjectConfig]:
    """Get project configuration for current directory."""
    return get_nullrc_manager().load()
