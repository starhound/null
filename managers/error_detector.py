from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ai.base import LLMProvider


class ErrorType(Enum):
    PYTHON_SYNTAX = "python_syntax"
    PYTHON_RUNTIME = "python_runtime"
    PYTHON_IMPORT = "python_import"
    PYTHON_TYPE = "python_type"
    TYPESCRIPT = "typescript"
    ESLINT = "eslint"
    PYTEST = "pytest"
    RUFF = "ruff"
    SHELL = "shell"
    PERMISSION = "permission"
    NOT_FOUND = "not_found"
    UNKNOWN = "unknown"


@dataclass
class DetectedError:
    error_type: ErrorType
    message: str
    file: str | None = None
    line: int | None = None
    column: int | None = None
    full_output: str = ""
    severity: str = "error"
    suggestion: str | None = None
    timestamp: datetime = field(default_factory=datetime.now)

    @property
    def location(self) -> str:
        if self.file and self.line:
            return f"{self.file}:{self.line}"
        elif self.file:
            return self.file
        return "unknown"


@dataclass
class CorrectionAttempt:
    error: DetectedError
    fix_description: str
    files_modified: list[str] = field(default_factory=list)
    success: bool = False
    verification_output: str = ""
    duration: float = 0.0


ERROR_PATTERNS: dict[str, tuple[str, ErrorType]] = {
    "python_syntax": (
        r"(?:SyntaxError|IndentationError):\s*(.+?)(?:\s*\()?(?:(.+?),\s*line\s*(\d+))?",
        ErrorType.PYTHON_SYNTAX,
    ),
    "python_traceback": (
        r'File "(.+?)", line (\d+).*\n\s+.*\n(\w+Error):\s*(.+)',
        ErrorType.PYTHON_RUNTIME,
    ),
    "python_type": (
        r"TypeError:\s*(.+)",
        ErrorType.PYTHON_TYPE,
    ),
    "python_import": (
        r"(?:ModuleNotFoundError|ImportError):\s*(?:No module named\s*)?['\"]?(.+?)['\"]?$",
        ErrorType.PYTHON_IMPORT,
    ),
    "typescript": (
        r"(.+?)\((\d+),(\d+)\):\s*error\s*TS(\d+):\s*(.+)",
        ErrorType.TYPESCRIPT,
    ),
    "eslint": (
        r"(\d+):(\d+)\s+(error|warning)\s+(.+?)\s+(\S+)$",
        ErrorType.ESLINT,
    ),
    "pytest": (
        r"FAILED\s+(.+?)::(.+?)\s+-\s+(.+)",
        ErrorType.PYTEST,
    ),
    "ruff": (
        r"(.+?):(\d+):(\d+):\s*(\w+)\s+(.+)",
        ErrorType.RUFF,
    ),
    "shell_not_found": (
        r"(?:bash:|zsh:|sh:)?\s*(.+?):\s*(?:command\s+)?not\s+found",
        ErrorType.NOT_FOUND,
    ),
    "permission_denied": (
        r"(?:Permission denied|EACCES).*?([\/\w.-]+)?",
        ErrorType.PERMISSION,
    ),
}

VERIFICATION_COMMANDS: dict[str, list[str]] = {
    "python": ["python -m py_compile {file}", "ruff check {file} --output-format=text"],
    "typescript": ["tsc --noEmit {file}"],
    "javascript": ["eslint {file}"],
    "rust": ["cargo check"],
}


class ErrorDetector:
    def __init__(self):
        self.error_history: list[DetectedError] = []
        self.correction_history: list[CorrectionAttempt] = []

    def detect(self, output: str) -> list[DetectedError]:
        errors: list[DetectedError] = []

        for pattern_name, (pattern, error_type) in ERROR_PATTERNS.items():
            for match in re.finditer(pattern, output, re.MULTILINE | re.IGNORECASE):
                error = self._parse_match(pattern_name, match, error_type, output)
                if error:
                    errors.append(error)

        for error in errors:
            if error not in self.error_history:
                self.error_history.append(error)

        return errors

    def _parse_match(
        self,
        pattern_name: str,
        match: re.Match,
        error_type: ErrorType,
        full_output: str,
    ) -> DetectedError | None:
        groups = match.groups()

        if pattern_name == "python_syntax":
            return DetectedError(
                error_type=error_type,
                message=groups[0] if groups else match.group(0),
                file=groups[1] if len(groups) > 1 else None,
                line=int(groups[2]) if len(groups) > 2 and groups[2] else None,
                full_output=full_output,
            )

        elif pattern_name == "python_traceback":
            return DetectedError(
                error_type=error_type,
                message=f"{groups[2]}: {groups[3]}"
                if len(groups) > 3
                else match.group(0),
                file=groups[0] if groups else None,
                line=int(groups[1]) if len(groups) > 1 and groups[1] else None,
                full_output=full_output,
            )

        elif pattern_name in ("python_type", "python_import"):
            return DetectedError(
                error_type=error_type,
                message=groups[0] if groups else match.group(0),
                full_output=full_output,
            )

        elif pattern_name == "typescript":
            return DetectedError(
                error_type=error_type,
                message=groups[4] if len(groups) > 4 else match.group(0),
                file=groups[0] if groups else None,
                line=int(groups[1]) if len(groups) > 1 and groups[1] else None,
                column=int(groups[2]) if len(groups) > 2 and groups[2] else None,
                full_output=full_output,
            )

        elif pattern_name == "eslint":
            return DetectedError(
                error_type=error_type,
                message=groups[3] if len(groups) > 3 else match.group(0),
                line=int(groups[0]) if groups and groups[0] else None,
                column=int(groups[1]) if len(groups) > 1 and groups[1] else None,
                severity=groups[2] if len(groups) > 2 else "error",
                full_output=full_output,
            )

        elif pattern_name == "pytest":
            return DetectedError(
                error_type=error_type,
                message=groups[2] if len(groups) > 2 else match.group(0),
                file=groups[0] if groups else None,
                full_output=full_output,
            )

        elif pattern_name == "ruff":
            return DetectedError(
                error_type=error_type,
                message=groups[4] if len(groups) > 4 else match.group(0),
                file=groups[0] if groups else None,
                line=int(groups[1]) if len(groups) > 1 and groups[1] else None,
                column=int(groups[2]) if len(groups) > 2 and groups[2] else None,
                full_output=full_output,
            )

        elif pattern_name in ("shell_not_found", "permission_denied"):
            return DetectedError(
                error_type=error_type,
                message=match.group(0),
                file=groups[0] if groups else None,
                full_output=full_output,
            )

        return DetectedError(
            error_type=error_type,
            message=match.group(0),
            full_output=full_output,
        )

    def get_last_error(self) -> DetectedError | None:
        return self.error_history[-1] if self.error_history else None

    def clear_history(self):
        self.error_history.clear()
        self.correction_history.clear()


FIX_GENERATION_PROMPT = """Analyze this error and provide a fix.

Error Type: {error_type}
Message: {message}
{location_info}

Output Context:
```
{output}
```

{file_content}

Provide a concise fix. If it requires modifying code, output the corrected code.
Focus only on fixing the specific error, do not refactor unrelated code.
"""


class AutoCorrectionLoop:
    def __init__(self, max_iterations: int = 5):
        self.max_iterations = max_iterations
        self.detector = ErrorDetector()
        self.is_running = False
        self.current_iteration = 0

    async def generate_fix(
        self, error: DetectedError, provider: LLMProvider, file_content: str = ""
    ) -> str:
        location_info = ""
        if error.file:
            location_info = f"File: {error.file}"
            if error.line:
                location_info += f", Line: {error.line}"

        prompt = FIX_GENERATION_PROMPT.format(
            error_type=error.error_type.value,
            message=error.message,
            location_info=location_info,
            output=error.full_output[:2000],
            file_content=f"Current file content:\n```\n{file_content[:3000]}\n```"
            if file_content
            else "",
        )

        response = ""
        async for chunk in provider.generate(  # type: ignore[attr-defined]
            prompt,
            [],
            system_prompt="You are an expert debugger. Provide minimal, targeted fixes.",
        ):
            response += chunk

        return response.strip()

    async def verify_fix(self, error: DetectedError) -> tuple[bool, str]:
        if not error.file:
            return True, "No file to verify"

        import asyncio
        import os

        ext = os.path.splitext(error.file)[1].lower()
        lang_map = {
            ".py": "python",
            ".ts": "typescript",
            ".tsx": "typescript",
            ".js": "javascript",
            ".jsx": "javascript",
            ".rs": "rust",
        }
        lang = lang_map.get(ext)

        if not lang or lang not in VERIFICATION_COMMANDS:
            return True, "No verification command for this file type"

        for cmd_template in VERIFICATION_COMMANDS[lang]:
            cmd = cmd_template.format(file=error.file)
            try:
                process = await asyncio.create_subprocess_shell(
                    cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.STDOUT,
                )
                stdout, _ = await asyncio.wait_for(process.communicate(), timeout=30.0)
                output = stdout.decode("utf-8", errors="replace")

                if process.returncode != 0:
                    return False, output

            except Exception as e:
                return False, str(e)

        return True, "Verification passed"

    def stop(self):
        self.is_running = False
