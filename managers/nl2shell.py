from __future__ import annotations

import asyncio
import os
import shutil
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ai.base import LLMProvider


@dataclass
class ShellContext:
    cwd: str = ""
    git_branch: str = ""
    os_info: str = ""
    recent_commands: list[str] = field(default_factory=list)
    environment: dict[str, str] = field(default_factory=dict)
    available_tools: list[str] = field(default_factory=list)


@dataclass
class CommandSuggestion:
    command: str
    explanation: str
    confidence: float = 0.8
    alternatives: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    requires_sudo: bool = False


NL_TRANSLATE_PROMPT = """Translate this natural language request into a shell command.

Context:
- Current directory: {cwd}
- OS: {os_info}
{git_info}
{recent_info}

Request: {request}

Respond in this exact format:
COMMAND: <the shell command>
EXPLANATION: <brief explanation of what it does>
ALTERNATIVES: <comma-separated alternative commands, or "none">
WARNINGS: <any warnings about destructive operations, or "none">
REQUIRES_SUDO: <yes or no>
CONFIDENCE: <0.0 to 1.0>
"""

EXPLAIN_COMMAND_PROMPT = """Explain this shell command in detail.

Command: {command}

Provide a clear explanation of:
1. What the command does
2. Each flag/option used
3. Any side effects or risks

Format your response as a clear explanation, not code.
"""


COMMON_NL_PATTERNS: dict[str, str] = {
    "find large files": "find . -type f -size +{size}M -exec ls -lh {{}} \\;",
    "find files larger than": "find . -type f -size +{size}M -exec ls -lh {{}} \\;",
    "search for text": "grep -rn '{text}' .",
    "find text in files": "grep -rn '{text}' .",
    "disk usage": "du -sh *",
    "folder size": "du -sh {folder}",
    "process list": "ps aux | grep {process}",
    "running processes": "ps aux",
    "kill process": "pkill {process}",
    "git undo": "git checkout -- .",
    "git undo file": "git checkout -- {file}",
    "compress folder": "tar -czvf {name}.tar.gz {folder}",
    "extract tar": "tar -xzvf {file}",
    "list ports": "netstat -tuln",
    "listening ports": "ss -tuln",
    "memory usage": "free -h",
    "cpu info": "lscpu",
    "system info": "uname -a",
    "current user": "whoami",
    "environment variables": "env",
    "file permissions": "ls -la {file}",
    "make executable": "chmod +x {file}",
    "change owner": "chown {user}:{group} {file}",
    "count lines": "wc -l {file}",
    "tail logs": "tail -f {file}",
    "watch file": "tail -f {file}",
    "download file": "curl -O {url}",
    "wget download": "wget {url}",
    "ssh connect": "ssh {user}@{host}",
    "copy files": "cp -r {source} {dest}",
    "move files": "mv {source} {dest}",
    "delete folder": "rm -rf {folder}",
    "create folder": "mkdir -p {folder}",
    "python version": "python --version",
    "node version": "node --version",
    "install package": "pip install {package}",
    "npm install": "npm install {package}",
}


class NL2Shell:
    def __init__(self):
        self._common_tools = [
            "git",
            "npm",
            "node",
            "python",
            "pip",
            "docker",
            "kubectl",
            "curl",
            "wget",
            "tar",
            "grep",
            "find",
            "awk",
            "sed",
        ]

    async def get_context(self) -> ShellContext:
        context = ShellContext()

        try:
            context.cwd = await asyncio.to_thread(os.getcwd)
        except Exception:
            context.cwd = "unknown"

        try:
            import platform

            context.os_info = f"{platform.system()} {platform.release()}"
        except Exception:
            context.os_info = "unknown"

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
        except (TimeoutError, FileNotFoundError):
            pass
        except Exception:
            pass

        def check_tools():
            return [t for t in self._common_tools if shutil.which(t)]

        context.available_tools = await asyncio.to_thread(check_tools)

        return context

    async def translate(
        self,
        natural_language: str,
        provider: LLMProvider,
    ) -> CommandSuggestion:
        context = await self.get_context()

        quick_match = self._try_pattern_match(natural_language.lower())
        if quick_match:
            return quick_match

        git_info = f"- Git branch: {context.git_branch}" if context.git_branch else ""
        recent_info = ""
        if context.recent_commands:
            recent_info = (
                f"- Recent commands: {', '.join(context.recent_commands[-3:])}"
            )

        prompt = NL_TRANSLATE_PROMPT.format(
            cwd=context.cwd,
            os_info=context.os_info,
            git_info=git_info,
            recent_info=recent_info,
            request=natural_language,
        )

        response = ""
        async for chunk in provider.generate(prompt, []):  # type: ignore[attr-defined]
            response += chunk

        return self._parse_response(response)

    def _try_pattern_match(self, text: str) -> CommandSuggestion | None:
        for pattern, template in COMMON_NL_PATTERNS.items():
            if pattern in text:
                command = template

                if "{size}" in command:
                    import re

                    size_match = re.search(r"(\d+)\s*(?:mb|m|megabytes?)?", text, re.I)
                    size = size_match.group(1) if size_match else "100"
                    command = command.replace("{size}", size)

                if any(
                    p in command
                    for p in ["{text}", "{file}", "{folder}", "{url}", "{package}"]
                ):
                    return None

                return CommandSuggestion(
                    command=command,
                    explanation=f"Pattern match for: {pattern}",
                    confidence=0.95,
                )

        return None

    def _parse_response(self, response: str) -> CommandSuggestion:
        lines = response.strip().split("\n")

        command = ""
        explanation = ""
        alternatives: list[str] = []
        warnings: list[str] = []
        requires_sudo = False
        confidence = 0.8

        for line in lines:
            line = line.strip()
            upper = line.upper()

            if upper.startswith("COMMAND:"):
                command = line.split(":", 1)[1].strip().strip("`")
            elif upper.startswith("EXPLANATION:"):
                explanation = line.split(":", 1)[1].strip()
            elif upper.startswith("ALTERNATIVES:"):
                alt_text = line.split(":", 1)[1].strip()
                if alt_text.lower() != "none":
                    alternatives = [a.strip() for a in alt_text.split(",") if a.strip()]
            elif upper.startswith("WARNINGS:"):
                warn_text = line.split(":", 1)[1].strip()
                if warn_text.lower() != "none":
                    warnings = [warn_text]
            elif upper.startswith("REQUIRES_SUDO:"):
                sudo_text = line.split(":", 1)[1].strip().lower()
                requires_sudo = sudo_text in ("yes", "true", "1")
            elif upper.startswith("CONFIDENCE:"):
                try:
                    confidence = float(line.split(":", 1)[1].strip())
                except ValueError:
                    pass

        if not command:
            for line in lines:
                line = line.strip()
                if line.startswith("$"):
                    command = line[1:].strip()
                    break
                elif line.startswith("`") and line.endswith("`"):
                    command = line.strip("`")
                    break

        if not command:
            command = response.strip().split("\n")[0].strip("`")

        return CommandSuggestion(
            command=command,
            explanation=explanation or "AI-generated command",
            confidence=confidence,
            alternatives=alternatives,
            warnings=warnings,
            requires_sudo=requires_sudo,
        )

    async def explain(self, command: str, provider: LLMProvider) -> str:
        prompt = EXPLAIN_COMMAND_PROMPT.format(command=command)

        response = ""
        async for chunk in provider.generate(prompt, []):  # type: ignore[attr-defined]
            response += chunk

        return response.strip()
