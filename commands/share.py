"""Session sharing command: /share."""

from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app import NullApp

from models import BlockState, BlockType

from .base import CommandMixin


class ShareFormatter:
    """Formats session data for sharing in various formats."""

    def __init__(self, blocks: list[BlockState], anonymize: bool = False):
        self.blocks = blocks
        self.anonymize = anonymize

    def to_json(self) -> str:
        """Export session to JSON format."""
        data = {
            "exported_at": datetime.now().isoformat(),
            "version": "1.0",
            "anonymized": self.anonymize,
            "metadata": {
                "block_count": len(self.blocks),
                "duration_seconds": self._calculate_duration(),
                "has_agent_sessions": any(
                    b.type == BlockType.AGENT_RESPONSE for b in self.blocks
                ),
            },
            "blocks": [self._serialize_block(b) for b in self.blocks],
        }
        return json.dumps(data, indent=2)

    def to_markdown(self) -> str:
        """Export session to Markdown format."""
        lines = []

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        lines.append(f"# Null Session Share - {timestamp}")
        lines.append("")

        lines.append("## Session Metadata")
        lines.append(f"- **Blocks:** {len(self.blocks)}")
        lines.append(f"- **Duration:** {self._format_duration()}")
        lines.append(f"- **Anonymized:** {self.anonymize}")
        lines.append("")

        for i, block in enumerate(self.blocks, 1):
            lines.extend(self._format_block_markdown(block, i))

        return "\n".join(lines)

    def to_html(self) -> str:
        """Export session to HTML format."""
        lines = []

        lines.append("<!DOCTYPE html>")
        lines.append("<html>")
        lines.append("<head>")
        lines.append("<meta charset='utf-8'>")
        lines.append("<title>Null Session Share</title>")
        lines.append("<style>")
        lines.append(self._get_html_styles())
        lines.append("</style>")
        lines.append("</head>")
        lines.append("<body>")

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        lines.append(f"<h1>Null Session Share - {timestamp}</h1>")

        lines.append("<div class='metadata'>")
        lines.append(f"<p><strong>Blocks:</strong> {len(self.blocks)}</p>")
        lines.append(f"<p><strong>Duration:</strong> {self._format_duration()}</p>")
        lines.append(f"<p><strong>Anonymized:</strong> {self.anonymize}</p>")
        lines.append("</div>")

        for i, block in enumerate(self.blocks, 1):
            lines.extend(self._format_block_html(block, i))

        lines.append("</body>")
        lines.append("</html>")

        return "\n".join(lines)

    def _serialize_block(self, block: BlockState) -> dict:
        """Serialize a block to dictionary, optionally anonymizing."""
        data = block.to_dict()

        if self.anonymize:
            data = self._anonymize_block_data(data)

        return data

    def _anonymize_block_data(self, data: dict) -> dict:
        """Anonymize sensitive data in block."""
        for field in [
            "content_input",
            "content_output",
            "content_thinking",
            "content_exec_output",
        ]:
            data[field] = self._anonymize_paths(data.get(field, ""))
            data[field] = re.sub(
                r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}",
                "[EMAIL]",
                data[field],
            )
            data[field] = re.sub(
                r"\b(?:\d{1,3}\.){3}\d{1,3}\b", "[IP_ADDRESS]", data[field]
            )
            data[field] = re.sub(r"https?://[^\s]+", "[URL]", data[field])

        return data

    def _anonymize_paths(self, text: str) -> str:
        """Replace absolute paths with relative or anonymized versions."""
        home = str(Path.home())
        text = text.replace(home, "~")
        text = re.sub(r"/home/[^/\s]+", "/home/[USER]", text)
        text = re.sub(r"/Users/[^/\s]+", "/Users/[USER]", text)
        return text

    def _format_block_markdown(self, block: BlockState, index: int) -> list[str]:
        """Format a single block as Markdown."""
        lines = []
        ts = block.timestamp.strftime("%H:%M:%S")

        if block.type == BlockType.COMMAND:
            lines.append(f"## {index}. Command [{ts}]")
            lines.append("")
            lines.append("```bash")
            lines.append(f"$ {block.content_input}")
            lines.append("```")

            if block.content_output:
                lines.append("")
                lines.append("**Output:**")
                lines.append("```")
                lines.append(block.content_output.rstrip())
                lines.append("```")

            if block.exit_code is not None and block.exit_code != 0:
                lines.append(f"*Exit code: {block.exit_code}*")

        elif block.type == BlockType.AI_RESPONSE:
            lines.append(f"## {index}. AI Conversation [{ts}]")
            lines.append("")
            lines.append(f"**User:** {block.content_input}")
            lines.append("")

            if block.content_output:
                lines.append("**Assistant:**")
                lines.append("")
                lines.append(block.content_output.rstrip())

            if block.content_exec_output:
                lines.append("")
                lines.append("**Executed:**")
                lines.append(block.content_exec_output.rstrip())

            if block.metadata:
                meta_parts = []
                if "model" in block.metadata:
                    meta_parts.append(f"Model: {block.metadata['model']}")
                if "tokens" in block.metadata:
                    meta_parts.append(f"Tokens: {block.metadata['tokens']}")
                if meta_parts:
                    lines.append("")
                    lines.append(f"*{' | '.join(meta_parts)}*")

        elif block.type == BlockType.AGENT_RESPONSE:
            lines.append(f"## {index}. Agent Session [{ts}]")
            lines.append("")
            lines.append(f"**Task:** {block.content_input}")
            lines.append("")

            if block.iterations:
                lines.append(f"**Iterations:** {len(block.iterations)}")
                lines.append(f"**Tool Calls:** {len(block.tool_calls)}")
                lines.append("")

                for iteration in block.iterations[:3]:
                    lines.append(f"### Iteration {iteration.iteration_number}")

                    if iteration.thinking:
                        lines.append("")
                        lines.append("**Thinking:**")
                        lines.append(iteration.thinking[:200].rstrip())
                        if len(iteration.thinking) > 200:
                            lines.append("...")

                    for tc in iteration.tool_calls:
                        lines.append("")
                        lines.append(f"**Tool:** `{tc.tool_name}`")
                        if tc.status:
                            lines.append(f"**Status:** {tc.status}")

                if len(block.iterations) > 3:
                    lines.append(f"... and {len(block.iterations) - 3} more iterations")

        elif block.type == BlockType.SYSTEM_MSG:
            lines.append(f"## {index}. System Message [{ts}]")
            lines.append("")
            lines.append(block.content_input)

        lines.append("")
        return lines

    def _format_block_html(self, block: BlockState, index: int) -> list[str]:
        """Format a single block as HTML."""
        lines = []
        ts = block.timestamp.strftime("%H:%M:%S")

        lines.append(f"<div class='block block-{block.type.value}'>")
        lines.append(f"<h2>{index}. {block.type.value.upper()} [{ts}]</h2>")

        if block.type == BlockType.COMMAND:
            lines.append("<div class='command'>")
            lines.append("<pre><code class='language-bash'>")
            lines.append(f"$ {self._escape_html(block.content_input)}")
            lines.append("</code></pre>")

            if block.content_output:
                lines.append("<div class='output'>")
                lines.append("<strong>Output:</strong>")
                lines.append("<pre><code>")
                lines.append(self._escape_html(block.content_output.rstrip()))
                lines.append("</code></pre>")
                lines.append("</div>")

            if block.exit_code is not None and block.exit_code != 0:
                lines.append(f"<p class='exit-code'>Exit code: {block.exit_code}</p>")

            lines.append("</div>")

        elif block.type == BlockType.AI_RESPONSE:
            lines.append("<div class='ai-response'>")
            lines.append(
                f"<p><strong>User:</strong> {self._escape_html(block.content_input)}</p>"
            )

            if block.content_output:
                lines.append("<div class='assistant-response'>")
                lines.append("<strong>Assistant:</strong>")
                lines.append(
                    f"<p>{self._escape_html(block.content_output.rstrip())}</p>"
                )
                lines.append("</div>")

            if block.metadata:
                meta_parts = []
                if "model" in block.metadata:
                    meta_parts.append(f"Model: {block.metadata['model']}")
                if "tokens" in block.metadata:
                    meta_parts.append(f"Tokens: {block.metadata['tokens']}")
                if meta_parts:
                    lines.append(f"<p class='metadata'>{' | '.join(meta_parts)}</p>")

            lines.append("</div>")

        elif block.type == BlockType.AGENT_RESPONSE:
            lines.append("<div class='agent-response'>")
            lines.append(
                f"<p><strong>Task:</strong> {self._escape_html(block.content_input)}</p>"
            )

            if block.iterations:
                lines.append(
                    f"<p><strong>Iterations:</strong> {len(block.iterations)}</p>"
                )
                lines.append(
                    f"<p><strong>Tool Calls:</strong> {len(block.tool_calls)}</p>"
                )

            lines.append("</div>")

        lines.append("</div>")
        return lines

    def _escape_html(self, text: str) -> str:
        """Escape HTML special characters."""
        return (
            text.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
            .replace("'", "&#39;")
        )

    def _get_html_styles(self) -> str:
        """Get CSS styles for HTML export."""
        return """
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 900px;
            margin: 0 auto;
            padding: 20px;
            background: #f5f5f5;
        }
        h1 {
            color: #222;
            border-bottom: 3px solid #007bff;
            padding-bottom: 10px;
        }
        h2 {
            color: #444;
            margin-top: 30px;
        }
        .metadata {
            background: #e8f4f8;
            padding: 15px;
            border-radius: 5px;
            margin-bottom: 20px;
        }
        .block {
            background: white;
            padding: 15px;
            margin: 15px 0;
            border-left: 4px solid #007bff;
            border-radius: 3px;
        }
        .block-command {
            border-left-color: #28a745;
        }
        .block-ai {
            border-left-color: #007bff;
        }
        .block-agent {
            border-left-color: #ff9800;
        }
        .block-system_msg {
            border-left-color: #6c757d;
        }
        pre {
            background: #f4f4f4;
            padding: 10px;
            border-radius: 3px;
            overflow-x: auto;
        }
        code {
            font-family: 'Courier New', monospace;
            font-size: 0.9em;
        }
        .output {
            margin-top: 10px;
        }
        .exit-code {
            color: #d32f2f;
            font-style: italic;
        }
        .ai-response {
            background: #f0f7ff;
            padding: 10px;
            border-radius: 3px;
        }
        .assistant-response {
            margin-top: 10px;
            padding: 10px;
            background: white;
            border-radius: 3px;
        }
        .metadata {
            color: #666;
            font-size: 0.9em;
        }
        """

    def _calculate_duration(self) -> float:
        """Calculate total session duration in seconds."""
        if not self.blocks:
            return 0.0
        start = self.blocks[0].timestamp
        end = self.blocks[-1].timestamp
        return (end - start).total_seconds()

    def _format_duration(self) -> str:
        """Format duration as human-readable string."""
        seconds = self._calculate_duration()
        if seconds < 60:
            return f"{int(seconds)}s"
        elif seconds < 3600:
            minutes = int(seconds / 60)
            secs = int(seconds % 60)
            return f"{minutes}m {secs}s"
        else:
            hours = int(seconds / 3600)
            minutes = int((seconds % 3600) / 60)
            return f"{hours}h {minutes}m"


class ShareCommands(CommandMixin):
    """Session sharing commands."""

    def __init__(self, app: NullApp):
        self.app = app

    async def cmd_share(self, args: list[str]):
        """Share current session in various formats.

        Usage:
            /share                          # Share to clipboard (markdown)
            /share --format json            # Share as JSON
            /share --format markdown        # Share as Markdown
            /share --format html            # Share as HTML
            /share --output /path/to/file   # Save to file
            /share --anonymize              # Anonymize sensitive data
            /share --include-context        # Include file context (future)
        """
        if not self.app.blocks:
            self.notify("No session to share", severity="warning")
            return

        format_type = "markdown"
        output_path = None
        anonymize = False

        i = 0
        while i < len(args):
            arg = args[i]

            if arg == "--format" and i + 1 < len(args):
                format_type = args[i + 1].lower()
                if format_type not in ("json", "markdown", "md", "html"):
                    self.notify(
                        f"Invalid format: {format_type}. Use: json, markdown, html",
                        severity="error",
                    )
                    return
                if format_type == "md":
                    format_type = "markdown"
                i += 2

            elif arg == "--output" and i + 1 < len(args):
                output_path = args[i + 1]
                i += 2

            elif arg == "--anonymize":
                anonymize = True
                i += 1

            elif arg == "--include-context":
                i += 1

            else:
                self.notify(f"Unknown option: {arg}", severity="warning")
                i += 1

        formatter = ShareFormatter(self.app.blocks, anonymize=anonymize)

        try:
            if format_type == "json":
                content = formatter.to_json()
                file_ext = "json"
            elif format_type == "markdown":
                content = formatter.to_markdown()
                file_ext = "md"
            elif format_type == "html":
                content = formatter.to_html()
                file_ext = "html"
            else:
                self.notify(f"Unsupported format: {format_type}", severity="error")
                return
        except Exception as e:
            self.notify(f"Error generating share: {e}", severity="error")
            return

        if output_path:
            try:
                path = Path(output_path)
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(content, encoding="utf-8")
                self.notify(f"Session shared to {path}")
            except Exception as e:
                self.notify(f"Error writing file: {e}", severity="error")
        else:
            try:
                import subprocess

                process = subprocess.Popen(
                    ["xclip", "-selection", "clipboard"],
                    stdin=subprocess.PIPE,
                    text=True,
                )
                process.communicate(input=content)

                if process.returncode == 0:
                    block_count = len(self.app.blocks)
                    self.notify(
                        f"Session shared to clipboard ({block_count} blocks, {format_type})"
                    )
                else:
                    await self.show_output(f"/share {format_type}", content)
            except FileNotFoundError:
                await self.show_output(f"/share {format_type}", content)
            except Exception as e:
                self.notify(f"Error copying to clipboard: {e}", severity="error")
