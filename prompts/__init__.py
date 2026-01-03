"""Prompt management for Null terminal."""

from .manager import PromptManager, get_prompt_manager
from .templates import BUILTIN_PROMPTS

__all__ = ["BUILTIN_PROMPTS", "PromptManager", "get_prompt_manager"]
