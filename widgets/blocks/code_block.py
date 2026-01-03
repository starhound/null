"""Widget for rendering code blocks with Run/Copy/Save actions."""

import asyncio
import os
import re
import subprocess
import tempfile

from textual import on
from textual.app import ComposeResult
from textual.containers import Container, Horizontal
from textual.events import Click
from textual.message import Message
from textual.widgets import Label, Static

try:
    import pyperclip
except ImportError:
    pyperclip = None


class CodeBlockWidget(Static):
    """A code block with Run/Copy/Save action buttons."""

    class RunCodeRequested(Message):
        """Sent when user clicks run button."""

        def __init__(self, code: str, language: str):
            self.code = code
            self.language = language
            super().__init__()

    class SaveCodeRequested(Message):
        """Sent when user clicks save button."""

        def __init__(self, code: str, language: str):
            self.code = code
            self.language = language
            super().__init__()

    # Map of language aliases to canonical names
    LANGUAGE_ALIASES = {
        "py": "python",
        "python3": "python",
        "sh": "bash",
        "shell": "bash",
        "zsh": "bash",
        "js": "javascript",
        "ts": "typescript",
        "rb": "ruby",
    }

    # Languages that can be executed
    EXECUTABLE_LANGUAGES = {"bash", "python", "sh", "shell", "zsh", "py", "python3"}

    def __init__(self, code: str, language: str = ""):
        super().__init__()
        self.code = code
        self.language = language.lower().strip() if language else ""
        self._canonical_language = self.LANGUAGE_ALIASES.get(
            self.language, self.language
        )

    def compose(self) -> ComposeResult:
        """Compose the code block with header and content."""
        # Header with language label and action buttons
        with Container(classes="code-block-container"):
            with Horizontal(classes="code-block-header"):
                lang_display = self._canonical_language or "code"
                yield Label(lang_display, classes="code-lang-label")
                yield Label("", classes="code-header-spacer")

                # Action buttons (using classes instead of IDs for multiple code blocks)
                if self._is_executable():
                    yield Static(
                        "run", classes="code-action code-action-run code-run-btn"
                    )
                yield Static(
                    "copy", classes="code-action code-action-copy code-copy-btn"
                )
                yield Static(
                    "save", classes="code-action code-action-save code-save-btn"
                )

            # Code content with syntax highlighting
            with Container(classes="code-block-content"):
                from rich.syntax import Syntax

                syntax = Syntax(
                    self.code,
                    self._canonical_language or "text",
                    theme="monokai",
                    line_numbers=False,
                    word_wrap=True,
                )
                yield Static(syntax, classes="code-syntax")

    def _is_executable(self) -> bool:
        """Check if this code block's language is executable."""
        return (
            self.language in self.EXECUTABLE_LANGUAGES
            or self._canonical_language in self.EXECUTABLE_LANGUAGES
        )

    @on(Click, ".code-run-btn")
    def on_run_clicked(self, event: Click):
        """Handle run button click."""
        event.stop()
        self.post_message(self.RunCodeRequested(self.code, self._canonical_language))

    @on(Click, ".code-copy-btn")
    def on_copy_clicked(self, event: Click):
        """Handle copy button click."""
        event.stop()
        self._copy_to_clipboard()

    @on(Click, ".code-save-btn")
    def on_save_clicked(self, event: Click):
        """Handle save button click."""
        event.stop()
        self.post_message(self.SaveCodeRequested(self.code, self._canonical_language))

    def _copy_to_clipboard(self):
        """Copy code to clipboard."""
        try:
            if pyperclip:
                pyperclip.copy(self.code)
                self.notify("Copied to clipboard")
            else:
                # Fallback: try using subprocess for Linux
                import sys

                if sys.platform == "linux":
                    try:
                        subprocess.run(
                            ["xclip", "-selection", "clipboard"],
                            input=self.code.encode(),
                            check=True,
                        )
                        self.notify("Copied to clipboard")
                        return
                    except (subprocess.CalledProcessError, FileNotFoundError):
                        pass
                self.notify(
                    "Install pyperclip: pip install pyperclip", severity="warning"
                )
        except Exception as e:
            self.notify(f"Copy failed: {e}", severity="error")


def extract_code_blocks(markdown_text: str) -> list[tuple[str, str, int, int]]:
    """
    Extract code blocks from markdown text.

    Returns list of tuples: (code, language, start_pos, end_pos)
    """
    # Pattern to match fenced code blocks
    pattern = r"```(\w*)\n(.*?)```"
    blocks = []

    for match in re.finditer(pattern, markdown_text, re.DOTALL):
        language = match.group(1)
        code = match.group(2).rstrip("\n")
        blocks.append((code, language, match.start(), match.end()))

    return blocks


def get_file_extension(language: str) -> str:
    """Get appropriate file extension for a language."""
    extensions = {
        "python": ".py",
        "bash": ".sh",
        "shell": ".sh",
        "javascript": ".js",
        "typescript": ".ts",
        "ruby": ".rb",
        "go": ".go",
        "rust": ".rs",
        "java": ".java",
        "c": ".c",
        "cpp": ".cpp",
        "cxx": ".cpp",
        "c++": ".cpp",
        "css": ".css",
        "html": ".html",
        "json": ".json",
        "yaml": ".yaml",
        "yml": ".yaml",
        "toml": ".toml",
        "sql": ".sql",
        "markdown": ".md",
        "md": ".md",
    }
    return extensions.get(language.lower(), ".txt")


async def execute_code(code: str, language: str) -> tuple[str, int]:
    """
    Execute code and return (output, exit_code).

    Supports bash and python.
    """
    if language in ("bash", "sh", "shell", "zsh"):
        return await _execute_bash(code)
    elif language in ("python", "py", "python3"):
        return await _execute_python(code)
    else:
        return f"Execution not supported for language: {language}", 1


async def _execute_bash(code: str) -> tuple[str, int]:
    """Execute bash code."""
    try:
        process = await asyncio.create_subprocess_shell(
            code,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
            shell=True,
        )
        stdout, _ = await process.communicate()
        output = stdout.decode("utf-8", errors="replace")
        return output, process.returncode or 0
    except Exception as e:
        return f"Execution error: {e}", 1


async def _execute_python(code: str) -> tuple[str, int]:
    """Execute python code."""
    try:
        # Write code to temporary file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(code)
            temp_path = f.name

        try:
            process = await asyncio.create_subprocess_exec(
                "python3",
                temp_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
            )
            stdout, _ = await process.communicate()
            output = stdout.decode("utf-8", errors="replace")
            return output, process.returncode or 0
        finally:
            # Clean up temp file
            try:
                os.unlink(temp_path)
            except Exception:
                pass
    except Exception as e:
        return f"Execution error: {e}", 1
