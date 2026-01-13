"""Prompt management for Null terminal."""

from .engine import (
    TemplateEngine,
    TemplateVariable,
    get_template_engine,
    reload_template_engine,
)
from .manager import PromptManager, get_prompt_manager
from .templates import BUILTIN_PROMPTS

__all__ = [
    "BUILTIN_PROMPTS",
    "PromptManager",
    "TemplateEngine",
    "TemplateVariable",
    "get_prompt_manager",
    "get_template_engine",
    "reload_template_engine",
]
