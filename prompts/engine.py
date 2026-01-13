"""Template engine for prompt variable substitution and conditionals.

Supports:
- Variables: {{variable_name}}
- Conditionals: {{#if condition}}...{{/if}}, {{#unless condition}}...{{/unless}}
- Else blocks: {{#if condition}}...{{else}}...{{/if}}
- Nested conditionals
- Custom variables via config
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Callable


@dataclass
class TemplateVariable:
    """Definition of a template variable."""

    name: str
    description: str
    example: str
    category: str = "general"
    resolver: Callable[[], str] | None = None

    def resolve(self, context: dict[str, Any]) -> str:
        """Resolve the variable value."""
        # Check context first (allows overrides)
        if self.name in context:
            value = context[self.name]
            return str(value) if value is not None else ""

        # Use custom resolver if provided
        if self.resolver:
            try:
                return self.resolver()
            except Exception:
                return ""

        return ""


# Built-in variable resolvers
def _resolve_date() -> str:
    return datetime.now().strftime("%Y-%m-%d")


def _resolve_time() -> str:
    return datetime.now().strftime("%H:%M:%S")


def _resolve_datetime() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _resolve_cwd() -> str:
    return os.getcwd()


def _resolve_home() -> str:
    return str(Path.home())


def _resolve_user() -> str:
    return os.environ.get("USER", os.environ.get("USERNAME", "user"))


def _resolve_hostname() -> str:
    import socket

    return socket.gethostname()


def _resolve_os() -> str:
    import platform

    return platform.system()


def _resolve_shell() -> str:
    return os.environ.get("SHELL", "/bin/bash")


# Built-in variable definitions
BUILTIN_VARIABLES: dict[str, TemplateVariable] = {
    # Context variables (set at runtime)
    "model": TemplateVariable(
        name="model",
        description="Currently active AI model",
        example="gpt-4o",
        category="ai",
    ),
    "provider": TemplateVariable(
        name="provider",
        description="Currently active AI provider",
        example="openai",
        category="ai",
    ),
    "agent_mode": TemplateVariable(
        name="agent_mode",
        description="Whether agent mode is enabled (true/false)",
        example="true",
        category="ai",
    ),
    "prompt_name": TemplateVariable(
        name="prompt_name",
        description="Name of the active system prompt",
        example="default",
        category="ai",
    ),
    # Date/time variables (dynamic resolvers)
    "date": TemplateVariable(
        name="date",
        description="Current date (YYYY-MM-DD)",
        example="2026-01-13",
        category="datetime",
        resolver=_resolve_date,
    ),
    "time": TemplateVariable(
        name="time",
        description="Current time (HH:MM:SS)",
        example="14:30:00",
        category="datetime",
        resolver=_resolve_time,
    ),
    "datetime": TemplateVariable(
        name="datetime",
        description="Current date and time",
        example="2026-01-13 14:30:00",
        category="datetime",
        resolver=_resolve_datetime,
    ),
    # Environment variables
    "cwd": TemplateVariable(
        name="cwd",
        description="Current working directory",
        example="/home/user/projects",
        category="environment",
        resolver=_resolve_cwd,
    ),
    "home": TemplateVariable(
        name="home",
        description="User's home directory",
        example="/home/user",
        category="environment",
        resolver=_resolve_home,
    ),
    "user": TemplateVariable(
        name="user",
        description="Current username",
        example="starhound",
        category="environment",
        resolver=_resolve_user,
    ),
    "hostname": TemplateVariable(
        name="hostname",
        description="System hostname",
        example="null-terminal",
        category="environment",
        resolver=_resolve_hostname,
    ),
    "os": TemplateVariable(
        name="os",
        description="Operating system name",
        example="Linux",
        category="environment",
        resolver=_resolve_os,
    ),
    "shell": TemplateVariable(
        name="shell",
        description="User's default shell",
        example="/bin/zsh",
        category="environment",
        resolver=_resolve_shell,
    ),
}


@dataclass
class TemplateEngine:
    """Engine for processing template variables and conditionals.

    Usage:
        engine = TemplateEngine()
        result = engine.render(template, context={"model": "gpt-4o", "agent_mode": True})

    Template syntax:
        Variables:    {{variable_name}}
        Conditionals: {{#if variable}}content{{/if}}
                      {{#if variable}}content{{else}}fallback{{/if}}
                      {{#unless variable}}content{{/unless}}
    """

    custom_variables: dict[str, TemplateVariable] = field(default_factory=dict)

    _VAR_PATTERN: re.Pattern = field(
        default_factory=lambda: re.compile(
            r"\{\{\s*(?!(?:else|#if|#unless|/if|/unless)\s*\}\})([a-zA-Z_][a-zA-Z0-9_]*)\s*\}\}"
        ),
        repr=False,
    )
    _OPEN_PATTERN: re.Pattern = field(
        default_factory=lambda: re.compile(
            r"\{\{#(if|unless)\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\}\}"
        ),
        repr=False,
    )

    def get_all_variables(self) -> dict[str, TemplateVariable]:
        """Get all available variables (built-in + custom)."""
        variables = dict(BUILTIN_VARIABLES)
        variables.update(self.custom_variables)
        return variables

    def add_custom_variable(
        self,
        name: str,
        description: str,
        example: str = "",
        category: str = "custom",
        resolver: Callable[[], str] | None = None,
    ) -> None:
        """Add a custom variable definition."""
        self.custom_variables[name] = TemplateVariable(
            name=name,
            description=description,
            example=example,
            category=category,
            resolver=resolver,
        )

    def remove_custom_variable(self, name: str) -> bool:
        """Remove a custom variable. Returns True if removed."""
        if name in self.custom_variables:
            del self.custom_variables[name]
            return True
        return False

    def _is_truthy(self, value: Any) -> bool:
        """Check if a value is truthy for conditionals."""
        if value is None:
            return False
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.lower() not in ("", "false", "0", "no", "off", "none")
        if isinstance(value, (int, float)):
            return value != 0
        return bool(value)

    def _resolve_variable(self, name: str, context: dict[str, Any]) -> str:
        """Resolve a single variable."""
        all_vars = self.get_all_variables()

        if name in all_vars:
            return all_vars[name].resolve(context)

        # Check context for undefined variables
        if name in context:
            value = context[name]
            return str(value) if value is not None else ""

        # Return empty for undefined
        return ""

    def _find_matching_close(
        self, template: str, start: int, block_type: str
    ) -> int | None:
        """Find the matching closing tag for a conditional block, handling nesting."""
        depth = 1
        pos = start
        open_pattern = re.compile(r"\{\{#(if|unless)\s+[a-zA-Z_][a-zA-Z0-9_]*\s*\}\}")
        close_pattern = re.compile(r"\{\{/(if|unless)\}\}")

        while pos < len(template) and depth > 0:
            open_match = open_pattern.search(template, pos)
            close_match = close_pattern.search(template, pos)

            if close_match is None:
                return None

            if open_match and open_match.start() < close_match.start():
                depth += 1
                pos = open_match.end()
            else:
                depth -= 1
                if depth == 0:
                    if close_match.group(1) != block_type:
                        return None
                    return close_match.start()
                pos = close_match.end()

        return None

    def _process_conditionals(self, template: str, context: dict[str, Any]) -> str:
        """Process conditional blocks with proper nesting support."""
        result = template
        max_iterations = 50

        for _ in range(max_iterations):
            match = self._OPEN_PATTERN.search(result)
            if not match:
                break

            block_type = match.group(1)
            var_name = match.group(2)
            content_start = match.end()

            close_pos = self._find_matching_close(result, content_start, block_type)
            if close_pos is None:
                break

            close_tag = f"{{{{/{block_type}}}}}"
            close_end = close_pos + len(close_tag)

            block_content = result[content_start:close_pos]

            else_pattern = re.compile(r"\{\{else\}\}")
            else_match = None
            search_pos = 0
            depth = 0
            open_p = re.compile(r"\{\{#(if|unless)\s+[a-zA-Z_][a-zA-Z0-9_]*\s*\}\}")
            close_p = re.compile(r"\{\{/(if|unless)\}\}")

            while search_pos < len(block_content):
                o = open_p.search(block_content, search_pos)
                c = close_p.search(block_content, search_pos)
                e = else_pattern.search(block_content, search_pos)

                next_pos = len(block_content)
                next_type = None

                if o and o.start() < next_pos:
                    next_pos, next_type = o.start(), "open"
                if c and c.start() < next_pos:
                    next_pos, next_type = c.start(), "close"
                if e and e.start() < next_pos and depth == 0:
                    else_match = e
                    break

                if next_type == "open":
                    depth += 1
                    search_pos = o.end()
                elif next_type == "close":
                    depth -= 1
                    search_pos = c.end()
                else:
                    break

            if else_match:
                true_content = block_content[: else_match.start()]
                false_content = block_content[else_match.end() :]
            else:
                true_content = block_content
                false_content = ""

            all_vars = self.get_all_variables()
            if var_name in context:
                value = context[var_name]
            elif var_name in all_vars and all_vars[var_name].resolver:
                try:
                    value = all_vars[var_name].resolver()
                except Exception:
                    value = None
            else:
                value = context.get(var_name)

            is_truthy = self._is_truthy(value)
            if block_type == "unless":
                is_truthy = not is_truthy

            chosen_content = true_content if is_truthy else false_content
            result = result[: match.start()] + chosen_content + result[close_end:]

        return result

    def _process_variables(self, template: str, context: dict[str, Any]) -> str:
        """Process variable substitutions."""

        def replace_variable(match: re.Match) -> str:
            var_name = match.group(1)
            return self._resolve_variable(var_name, context)

        return self._VAR_PATTERN.sub(replace_variable, template)

    def render(self, template: str, context: dict[str, Any] | None = None) -> str:
        """Render a template with variable substitution and conditionals.

        Args:
            template: The template string with {{variables}} and conditionals.
            context: Dictionary of variable values to use for substitution.

        Returns:
            The rendered template with all variables and conditionals resolved.
        """
        if context is None:
            context = {}

        # Process conditionals first (they may contain variables)
        result = self._process_conditionals(template, context)

        # Then process variable substitutions
        result = self._process_variables(result, context)

        return result

    def preview(self, template: str, context: dict[str, Any] | None = None) -> str:
        """Preview a template with sample values for undefined variables.

        This is useful for showing users what a template will look like
        without requiring all context values to be set.
        """
        if context is None:
            context = {}

        # Build preview context with example values for missing variables
        preview_context = dict(context)
        all_vars = self.get_all_variables()

        for name, var_def in all_vars.items():
            if name not in preview_context:
                # Use example value for preview
                preview_context[name] = var_def.example or f"<{name}>"

        return self.render(template, preview_context)

    def extract_variables(self, template: str) -> set[str]:
        """Extract all variable names used in a template."""
        variables: set[str] = set()

        for match in self._VAR_PATTERN.finditer(template):
            variables.add(match.group(1))

        for match in self._OPEN_PATTERN.finditer(template):
            variables.add(match.group(2))

        return variables

    def validate_template(self, template: str) -> list[str]:
        """Validate a template and return a list of warnings/errors."""
        errors: list[str] = []

        # Check for unclosed conditionals
        if_opens = len(re.findall(r"\{\{#if\s+", template))
        if_closes = len(re.findall(r"\{\{/if\}\}", template))
        unless_opens = len(re.findall(r"\{\{#unless\s+", template))
        unless_closes = len(re.findall(r"\{\{/unless\}\}", template))

        if if_opens != if_closes:
            errors.append(
                f"Mismatched {{{{#if}}}} blocks: {if_opens} opens, {if_closes} closes"
            )
        if unless_opens != unless_closes:
            errors.append(
                f"Mismatched {{{{#unless}}}} blocks: {unless_opens} opens, {unless_closes} closes"
            )

        # Check for unknown variables
        all_vars = self.get_all_variables()
        used_vars = self.extract_variables(template)
        unknown_vars = used_vars - set(all_vars.keys())

        if unknown_vars:
            errors.append(f"Unknown variables: {', '.join(sorted(unknown_vars))}")

        return errors

    def get_variable_reference(self) -> str:
        """Generate a formatted reference of all available variables."""
        all_vars = self.get_all_variables()

        # Group by category
        categories: dict[str, list[TemplateVariable]] = {}
        for var in all_vars.values():
            if var.category not in categories:
                categories[var.category] = []
            categories[var.category].append(var)

        # Build reference text
        lines = ["# Template Variables Reference\n"]

        category_order = ["ai", "datetime", "environment", "custom"]
        category_titles = {
            "ai": "AI Context",
            "datetime": "Date & Time",
            "environment": "Environment",
            "custom": "Custom Variables",
        }

        for cat in category_order:
            if cat not in categories:
                continue

            lines.append(f"\n## {category_titles.get(cat, cat.title())}\n")
            for var in sorted(categories[cat], key=lambda v: v.name):
                lines.append(f"**{{{{{var.name}}}}}**")
                lines.append(f"  {var.description}")
                if var.example:
                    lines.append(f"  Example: `{var.example}`\n")
                else:
                    lines.append("")

        lines.append("\n## Conditionals\n")
        lines.append("**{{#if variable}}...{{/if}}**")
        lines.append("  Show content if variable is truthy\n")
        lines.append("**{{#if variable}}...{{else}}...{{/if}}**")
        lines.append("  Show content if truthy, else show fallback\n")
        lines.append("**{{#unless variable}}...{{/unless}}**")
        lines.append("  Show content if variable is falsy\n")

        return "\n".join(lines)


_engine: TemplateEngine | None = None


def get_template_engine() -> TemplateEngine:
    """Get the global template engine instance."""
    global _engine
    if _engine is None:
        _engine = TemplateEngine()
        _load_custom_variables(_engine)
    return _engine


def _load_custom_variables(engine: TemplateEngine) -> None:
    """Load custom variables from user config."""
    try:
        from config.settings import get_settings

        settings = get_settings()
        custom_vars = settings.ai.custom_template_variables
        if custom_vars:
            for name, value in custom_vars.items():
                engine.add_custom_variable(
                    name=name,
                    description=f"Custom variable: {name}",
                    example=value,
                    category="custom",
                    resolver=lambda v=value: v,
                )
    except Exception:
        pass


def reload_template_engine() -> TemplateEngine:
    """Reload the template engine with fresh custom variables."""
    global _engine
    _engine = TemplateEngine()
    _load_custom_variables(_engine)
    return _engine
