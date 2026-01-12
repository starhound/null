from __future__ import annotations

import asyncio
import os
import logging
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from ai.base import LLMProvider


@dataclass
class Suggestion:
    command: str
    description: str
    source: Literal["history", "context", "ai"]
    score: float = 0.0
    icon: str = ""

    def __post_init__(self):
        if not self.icon:
            self.icon = {"history": "⏱", "context": "📁", "ai": "✨"}.get(
                self.source, ""
            )


@dataclass
class ContextState:
    cwd: str = ""
    git_branch: str = ""
    git_dirty: bool = False
    recent_commands: list[str] = field(default_factory=list)
    recent_errors: list[str] = field(default_factory=list)
    directory_contents: list[str] = field(default_factory=list)


class HistoryProvider:
    def __init__(self):
        self._history: list[str] = []

    def add_command(self, command: str):
        if command and command not in self._history:
            self._history.insert(0, command)
            self._history = self._history[:500]

    def suggest(self, prefix: str, limit: int = 5) -> list[Suggestion]:
        suggestions = []
        prefix_lower = prefix.lower()

        frequency: dict[str, int] = {}
        for cmd in self._history:
            if cmd not in frequency:
                frequency[cmd] = 0
            frequency[cmd] += 1

        matches = []
        for cmd in self._history:
            if cmd.lower().startswith(prefix_lower):
                recency = 1.0 - (self._history.index(cmd) / len(self._history))
                freq_score = min(frequency[cmd] / 10, 1.0)
                score = (recency * 0.6) + (freq_score * 0.4)
                matches.append((cmd, score))

        matches.sort(key=lambda x: x[1], reverse=True)

        for cmd, score in matches[:limit]:
            suggestions.append(
                Suggestion(
                    command=cmd,
                    description="From history",
                    source="history",
                    score=score,
                )
            )

        return suggestions


class ContextProvider:
    def suggest(
        self, prefix: str, context: ContextState, limit: int = 5
    ) -> list[Suggestion]:
        suggestions = []

        if context.git_dirty and prefix.lower().startswith("git"):
            suggestions.append(
                Suggestion(
                    command="git status",
                    description="View uncommitted changes",
                    source="context",
                    score=0.9,
                )
            )
            suggestions.append(
                Suggestion(
                    command="git diff",
                    description="View file changes",
                    source="context",
                    score=0.85,
                )
            )
            suggestions.append(
                Suggestion(
                    command="git add .",
                    description="Stage all changes",
                    source="context",
                    score=0.8,
                )
            )

        for filename in context.directory_contents[:10]:
            if filename.endswith(".py"):
                if prefix.lower().startswith("python") or prefix.lower().startswith(
                    "py"
                ):
                    suggestions.append(
                        Suggestion(
                            command=f"python {filename}",
                            description=f"Run {filename}",
                            source="context",
                            score=0.7,
                        )
                    )
            elif filename.endswith(".js") or filename.endswith(".ts"):
                if prefix.lower().startswith("node"):
                    suggestions.append(
                        Suggestion(
                            command=f"node {filename}",
                            description=f"Run {filename}",
                            source="context",
                            score=0.7,
                        )
                    )

        if "package.json" in context.directory_contents:
            if prefix.lower().startswith("npm"):
                for cmd in ["npm install", "npm run", "npm test", "npm start"]:
                    if cmd.startswith(prefix.lower()):
                        suggestions.append(
                            Suggestion(
                                command=cmd,
                                description="npm command",
                                source="context",
                                score=0.75,
                            )
                        )

        if context.recent_errors:
            last_error = context.recent_errors[-1]
            if "ModuleNotFoundError" in last_error or "ImportError" in last_error:
                suggestions.append(
                    Suggestion(
                        command="pip install",
                        description="Install missing module",
                        source="context",
                        score=0.9,
                    )
                )

        return suggestions[:limit]


class AISuggestionProvider:
    async def suggest(
        self,
        input_text: str,
        context: ContextState,
        provider: LLMProvider,
        limit: int = 3,
    ) -> list[Suggestion]:
        context_parts = []
        if context.cwd:
            context_parts.append(f"Current directory: {context.cwd}")
        if context.git_branch:
            context_parts.append(f"Git branch: {context.git_branch}")
        if context.recent_commands:
            context_parts.append(
                f"Recent commands: {', '.join(context.recent_commands[-5:])}"
            )

        prompt = f"""Suggest shell commands to complete this input.

Context:
{chr(10).join(context_parts)}

Input: {input_text}

Suggest up to {limit} commands. Output one per line, format: COMMAND | DESCRIPTION
Only output commands, no explanations."""

        response = ""
        async for chunk in provider.generate(prompt, []):  # type: ignore[attr-defined]
            response += chunk

        suggestions = []
        for line in response.strip().split("\n"):
            line = line.strip()
            if not line or line.startswith("#"):
                continue

            if "|" in line:
                parts = line.split("|", 1)
                cmd = parts[0].strip().strip("`").strip()
                desc = parts[1].strip() if len(parts) > 1 else ""
            else:
                cmd = line.strip().strip("`").strip()
                desc = "AI suggestion"

            if cmd and cmd != input_text:
                suggestions.append(
                    Suggestion(
                        command=cmd,
                        description=desc,
                        source="ai",
                        score=0.7 - (len(suggestions) * 0.1),
                    )
                )

            if len(suggestions) >= limit:
                break

        return suggestions


class SuggestionEngine:
    def __init__(self):
        self.history_provider = HistoryProvider()
        self.context_provider = ContextProvider()
        self.ai_provider = AISuggestionProvider()
        self.enabled_sources: list[str] = ["history", "context", "ai"]

    def add_to_history(self, command: str):
        self.history_provider.add_command(command)

    async def get_context(self) -> ContextState:
        context = ContextState()

        try:
            context.cwd = os.getcwd()
        except Exception as e:
            logger.debug(f"Failed to get CWD: {e}")

        try:
            context.directory_contents = os.listdir(".")
        except Exception as e:
            logger.debug(f"Failed to list directory: {e}")

        try:
            context.directory_contents = os.listdir(".")
        except Exception as e:
            logger.debug(f"Failed to list directory: {e}")

        try:
            proc = await asyncio.create_subprocess_exec(
                "git",
                "rev-parse",
                "--abbrev-ref",
                "HEAD",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=2)
            if proc.returncode == 0:
                context.git_branch = stdout.decode().strip()

                status_proc = await asyncio.create_subprocess_exec(
                    "git",
                    "status",
                    "--porcelain",
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                stdout, _ = await asyncio.wait_for(status_proc.communicate(), timeout=2)
                context.git_dirty = bool(stdout.strip())
        except (FileNotFoundError, asyncio.TimeoutError):
            pass
        except Exception as e:
            logger.debug(f"Git status check failed: {e}")

        return context

    async def suggest(
        self,
        input_text: str,
        ai_provider: LLMProvider | None = None,
        max_suggestions: int = 5,
    ) -> list[Suggestion]:
        if not input_text or len(input_text) < 2:
            return []

        all_suggestions: list[Suggestion] = []
        context = await self.get_context()

        if "history" in self.enabled_sources:
            all_suggestions.extend(self.history_provider.suggest(input_text, limit=3))

        if "context" in self.enabled_sources:
            all_suggestions.extend(
                self.context_provider.suggest(input_text, context, limit=3)
            )

        if "ai" in self.enabled_sources and ai_provider:
            try:
                ai_suggestions = await self.ai_provider.suggest(
                    input_text, context, ai_provider, limit=2
                )
                all_suggestions.extend(ai_suggestions)
            except Exception as e:
                logger.warning(f"AI suggestion failed: {e}")

        seen = set()
        unique: list[Suggestion] = []
        for s in all_suggestions:
            if s.command not in seen:
                seen.add(s.command)
                unique.append(s)

        unique.sort(key=lambda x: x.score, reverse=True)

        return unique[:max_suggestions]
