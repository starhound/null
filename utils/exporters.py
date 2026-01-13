"""Export formatters for various output formats.

This module provides exporters for converting session blocks to:
- HTML: Rich HTML with syntax highlighting and embedded CSS
- Org-mode: Emacs org-mode format for power users
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from models import BlockState

from models import BlockType


class BaseExporter(ABC):
    """Base class for export formatters."""

    def __init__(self, blocks: list[BlockState]):
        self.blocks = blocks

    @abstractmethod
    def export(self) -> str:
        """Export blocks to formatted string."""
        pass

    def _format_duration(self) -> str:
        """Format session duration as human-readable string."""
        if not self.blocks:
            return "0s"
        start = self.blocks[0].timestamp
        end = self.blocks[-1].timestamp
        seconds = (end - start).total_seconds()
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


class HTMLExporter(BaseExporter):
    """Export session to HTML with syntax highlighting.

    Features:
    - Embedded CSS (no external dependencies)
    - Syntax highlighting for code blocks using CSS classes
    - Dark theme matching Null Terminal aesthetic
    - Responsive layout
    - Collapsible sections for large outputs
    """

    def export(self) -> str:
        """Export blocks to HTML document."""
        lines = []

        lines.append("<!DOCTYPE html>")
        lines.append('<html lang="en">')
        lines.append("<head>")
        lines.append('<meta charset="UTF-8">')
        lines.append(
            '<meta name="viewport" content="width=device-width, initial-scale=1.0">'
        )
        lines.append("<title>Null Session Export</title>")
        lines.append("<style>")
        lines.append(self._get_css())
        lines.append("</style>")
        lines.append("</head>")
        lines.append("<body>")

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        lines.append('<div class="container">')
        lines.append('<header class="header">')
        lines.append("<h1>Null Session Export</h1>")
        lines.append(
            f'<p class="meta">Exported: {timestamp} | Blocks: {len(self.blocks)} | Duration: {self._format_duration()}</p>'
        )
        lines.append("</header>")

        lines.append('<main class="content">')
        for i, block in enumerate(self.blocks, 1):
            lines.extend(self._format_block(block, i))
        lines.append("</main>")

        lines.append('<footer class="footer">')
        lines.append("<p>Exported from Null Terminal</p>")
        lines.append("</footer>")
        lines.append("</div>")
        lines.append("</body>")
        lines.append("</html>")

        return "\n".join(lines)

    def _format_block(self, block: BlockState, index: int) -> list[str]:
        """Format a single block as HTML."""
        lines = []
        ts = block.timestamp.strftime("%H:%M:%S")
        block_class = f"block block-{block.type.value}"

        lines.append(f'<article class="{block_class}">')

        if block.type == BlockType.COMMAND:
            lines.append(
                f'<header class="block-header"><span class="block-type">Command</span><span class="timestamp">{ts}</span></header>'
            )
            lines.append('<div class="block-content">')
            lines.append('<pre class="code code-bash"><code>')
            lines.append(
                f'<span class="prompt">$</span> {self._escape_html(block.content_input)}'
            )
            lines.append("</code></pre>")

            if block.content_output:
                lines.append('<div class="output">')
                lines.append("<h4>Output</h4>")
                lines.append('<pre class="code"><code>')
                lines.append(self._escape_html(block.content_output.rstrip()))
                lines.append("</code></pre>")
                lines.append("</div>")

            if block.exit_code is not None and block.exit_code != 0:
                lines.append(
                    f'<p class="exit-code error">Exit code: {block.exit_code}</p>'
                )

            lines.append("</div>")

        elif block.type == BlockType.AI_RESPONSE:
            lines.append(
                f'<header class="block-header"><span class="block-type">AI Chat</span><span class="timestamp">{ts}</span></header>'
            )
            lines.append('<div class="block-content">')
            lines.append(
                f'<div class="user-message"><strong>User:</strong> {self._escape_html(block.content_input)}</div>'
            )

            if block.content_output:
                lines.append('<div class="assistant-message">')
                lines.append("<strong>Assistant:</strong>")
                lines.append(
                    f'<div class="response">{self._format_markdown_basic(block.content_output)}</div>'
                )
                lines.append("</div>")

            if block.content_exec_output:
                lines.append('<div class="executed">')
                lines.append("<h4>Executed</h4>")
                lines.append('<pre class="code"><code>')
                lines.append(self._escape_html(block.content_exec_output.rstrip()))
                lines.append("</code></pre>")
                lines.append("</div>")

            if block.metadata:
                meta_parts = []
                if "model" in block.metadata:
                    meta_parts.append(f"Model: {block.metadata['model']}")
                if "tokens" in block.metadata:
                    meta_parts.append(f"Tokens: {block.metadata['tokens']}")
                if meta_parts:
                    lines.append(f'<p class="metadata">{" | ".join(meta_parts)}</p>')

            lines.append("</div>")

        elif block.type == BlockType.AGENT_RESPONSE:
            lines.append(
                f'<header class="block-header"><span class="block-type">Agent</span><span class="timestamp">{ts}</span></header>'
            )
            lines.append('<div class="block-content">')
            lines.append(
                f'<div class="user-message"><strong>Task:</strong> {self._escape_html(block.content_input)}</div>'
            )

            if block.iterations:
                lines.append('<div class="iterations">')
                for iteration in block.iterations:
                    lines.append('<div class="iteration">')
                    lines.append(f"<h4>Iteration {iteration.iteration_number}</h4>")

                    if iteration.thinking:
                        lines.append('<div class="thinking">')
                        lines.append("<strong>Thinking:</strong>")
                        lines.append(
                            f"<p>{self._escape_html(iteration.thinking[:500])}</p>"
                        )
                        if len(iteration.thinking) > 500:
                            lines.append(
                                '<span class="truncated">... (truncated)</span>'
                            )
                        lines.append("</div>")

                    for tc in iteration.tool_calls:
                        lines.append('<div class="tool-call">')
                        lines.append(
                            f'<span class="tool-name">{self._escape_html(tc.tool_name)}</span>'
                        )
                        lines.append(
                            f'<span class="tool-status status-{tc.status}">{tc.status}</span>'
                        )
                        if tc.arguments:
                            lines.append('<pre class="code code-json"><code>')
                            lines.append(self._escape_html(tc.arguments[:300]))
                            lines.append("</code></pre>")
                        if tc.output:
                            lines.append('<div class="tool-output">')
                            lines.append('<pre class="code"><code>')
                            lines.append(self._escape_html(tc.output[:500]))
                            lines.append("</code></pre>")
                            lines.append("</div>")
                        lines.append("</div>")

                    lines.append("</div>")
                lines.append("</div>")

            if block.content_output:
                lines.append('<div class="final-response">')
                lines.append("<h4>Final Response</h4>")
                lines.append(
                    f'<div class="response">{self._format_markdown_basic(block.content_output)}</div>'
                )
                lines.append("</div>")

            if block.metadata:
                meta_parts = []
                if "model" in block.metadata:
                    meta_parts.append(f"Model: {block.metadata['model']}")
                if "tokens" in block.metadata:
                    meta_parts.append(f"Tokens: {block.metadata['tokens']}")
                if meta_parts:
                    lines.append(f'<p class="metadata">{" | ".join(meta_parts)}</p>')

            lines.append("</div>")

        elif block.type == BlockType.SYSTEM_MSG:
            lines.append(
                f'<header class="block-header"><span class="block-type">System</span><span class="timestamp">{ts}</span></header>'
            )
            lines.append('<div class="block-content">')
            lines.append(
                f'<p class="system-message">{self._escape_html(block.content_input)}</p>'
            )
            lines.append("</div>")

        elif block.type == BlockType.TOOL_CALL:
            lines.append(
                f'<header class="block-header"><span class="block-type">Tool</span><span class="timestamp">{ts}</span></header>'
            )
            lines.append('<div class="block-content">')
            if block.metadata and "tool_name" in block.metadata:
                lines.append(
                    f"<p><strong>Tool:</strong> {self._escape_html(block.metadata['tool_name'])}</p>"
                )
                if "arguments" in block.metadata:
                    lines.append('<pre class="code code-json"><code>')
                    lines.append(self._escape_html(block.metadata["arguments"]))
                    lines.append("</code></pre>")
            if block.content_output:
                lines.append('<pre class="code"><code>')
                lines.append(self._escape_html(block.content_output.rstrip()))
                lines.append("</code></pre>")
            if block.exit_code is not None:
                status = "success" if block.exit_code == 0 else "error"
                lines.append(f'<p class="status status-{status}">Status: {status}</p>')
            lines.append("</div>")

        lines.append("</article>")
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

    def _format_markdown_basic(self, text: str) -> str:
        """Basic markdown to HTML conversion for inline content."""
        import re

        text = self._escape_html(text)
        text = re.sub(
            r"```(\w*)\n(.*?)```",
            r'<pre class="code code-\1"><code>\2</code></pre>',
            text,
            flags=re.DOTALL,
        )
        text = re.sub(r"`([^`]+)`", r"<code>\1</code>", text)
        text = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", text)
        text = re.sub(r"\*([^*]+)\*", r"<em>\1</em>", text)
        text = text.replace("\n", "<br>\n")
        return text

    def _get_css(self) -> str:
        """Get embedded CSS styles."""
        return """
:root {
    --bg-primary: #0d0d0d;
    --bg-secondary: #1a1a1a;
    --bg-tertiary: #2a2a2a;
    --text-primary: #e0e0e0;
    --text-secondary: #a0a0a0;
    --accent-blue: #00d4ff;
    --accent-green: #00ff88;
    --accent-orange: #ff9500;
    --accent-red: #ff4444;
    --accent-purple: #b366ff;
    --border-color: #333;
}

* {
    box-sizing: border-box;
    margin: 0;
    padding: 0;
}

body {
    font-family: 'SF Mono', 'Fira Code', 'Consolas', monospace;
    background: var(--bg-primary);
    color: var(--text-primary);
    line-height: 1.6;
    font-size: 14px;
}

.container {
    max-width: 1000px;
    margin: 0 auto;
    padding: 20px;
}

.header {
    border-bottom: 2px solid var(--accent-blue);
    padding-bottom: 20px;
    margin-bottom: 30px;
}

.header h1 {
    color: var(--accent-blue);
    font-size: 1.8em;
    font-weight: 600;
}

.header .meta {
    color: var(--text-secondary);
    margin-top: 8px;
}

.content {
    display: flex;
    flex-direction: column;
    gap: 20px;
}

.block {
    background: var(--bg-secondary);
    border-radius: 8px;
    border-left: 4px solid var(--border-color);
    overflow: hidden;
}

.block-command { border-left-color: var(--accent-green); }
.block-ai { border-left-color: var(--accent-blue); }
.block-agent { border-left-color: var(--accent-orange); }
.block-system { border-left-color: var(--text-secondary); }
.block-tool_call { border-left-color: var(--accent-purple); }

.block-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 12px 16px;
    background: var(--bg-tertiary);
    border-bottom: 1px solid var(--border-color);
}

.block-type {
    font-weight: 600;
    text-transform: uppercase;
    font-size: 0.75em;
    letter-spacing: 0.5px;
}

.block-command .block-type { color: var(--accent-green); }
.block-ai .block-type { color: var(--accent-blue); }
.block-agent .block-type { color: var(--accent-orange); }
.block-system .block-type { color: var(--text-secondary); }
.block-tool_call .block-type { color: var(--accent-purple); }

.timestamp {
    color: var(--text-secondary);
    font-size: 0.85em;
}

.block-content {
    padding: 16px;
}

.code {
    background: var(--bg-primary);
    border: 1px solid var(--border-color);
    border-radius: 4px;
    padding: 12px;
    overflow-x: auto;
    margin: 8px 0;
}

.code code {
    font-family: inherit;
    color: var(--text-primary);
}

.prompt {
    color: var(--accent-green);
    margin-right: 8px;
}

.output h4, .executed h4, .iterations h4, .final-response h4 {
    color: var(--text-secondary);
    font-size: 0.85em;
    margin: 16px 0 8px 0;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}

.user-message {
    margin-bottom: 12px;
    padding: 10px;
    background: var(--bg-tertiary);
    border-radius: 4px;
}

.assistant-message, .response {
    color: var(--text-primary);
}

.exit-code.error {
    color: var(--accent-red);
    font-style: italic;
    margin-top: 8px;
}

.metadata {
    color: var(--text-secondary);
    font-size: 0.85em;
    margin-top: 12px;
    padding-top: 12px;
    border-top: 1px solid var(--border-color);
}

.iteration {
    border: 1px solid var(--border-color);
    border-radius: 4px;
    padding: 12px;
    margin: 8px 0;
    background: var(--bg-tertiary);
}

.thinking {
    background: var(--bg-primary);
    padding: 10px;
    border-radius: 4px;
    margin: 8px 0;
    font-style: italic;
    color: var(--text-secondary);
}

.tool-call {
    border-left: 2px solid var(--accent-purple);
    padding-left: 12px;
    margin: 8px 0;
}

.tool-name {
    color: var(--accent-purple);
    font-weight: 600;
}

.tool-status {
    margin-left: 8px;
    padding: 2px 6px;
    border-radius: 3px;
    font-size: 0.75em;
    text-transform: uppercase;
}

.status-success { background: var(--accent-green); color: var(--bg-primary); }
.status-error { background: var(--accent-red); color: var(--bg-primary); }
.status-pending { background: var(--text-secondary); color: var(--bg-primary); }
.status-running { background: var(--accent-orange); color: var(--bg-primary); }

.truncated {
    color: var(--text-secondary);
    font-style: italic;
}

.footer {
    margin-top: 40px;
    padding-top: 20px;
    border-top: 1px solid var(--border-color);
    text-align: center;
    color: var(--text-secondary);
}

@media (max-width: 768px) {
    .container {
        padding: 10px;
    }

    .block-content {
        padding: 12px;
    }
}
"""


class OrgModeExporter(BaseExporter):
    """Export session to Emacs org-mode format.

    Features:
    - Proper org-mode heading hierarchy
    - Source blocks with language tags
    - Properties for metadata
    - TODO items for pending/failed operations
    - Timestamps in org format
    """

    def export(self) -> str:
        """Export blocks to org-mode document."""
        lines = []

        timestamp = datetime.now().strftime("%Y-%m-%d %a %H:%M")
        lines.append("#+TITLE: Null Session Export")
        lines.append(f"#+DATE: <{timestamp}>")
        lines.append("#+AUTHOR: Null Terminal")
        lines.append("#+OPTIONS: toc:2 num:nil")
        lines.append("#+STARTUP: showall")
        lines.append("")

        lines.append("* Session Info")
        lines.append(":PROPERTIES:")
        lines.append(f":BLOCKS: {len(self.blocks)}")
        lines.append(f":DURATION: {self._format_duration()}")
        lines.append(f":EXPORTED: {timestamp}")
        lines.append(":END:")
        lines.append("")

        lines.append("* Session Content")
        lines.append("")

        for i, block in enumerate(self.blocks, 1):
            lines.extend(self._format_block(block, i))
            lines.append("")

        lines.append("* Export Info")
        lines.append(
            "Exported from Null Terminal - https://github.com/starhound/null-terminal"
        )

        return "\n".join(lines)

    def _format_block(self, block: BlockState, index: int) -> list[str]:
        """Format a single block as org-mode content."""
        lines = []
        ts = block.timestamp.strftime("%Y-%m-%d %a %H:%M")
        org_ts = f"<{ts}>"

        if block.type == BlockType.COMMAND:
            status = (
                "DONE" if block.exit_code == 0 else "FAILED" if block.exit_code else ""
            )
            lines.append(
                f"** {status} Command: {self._truncate(block.content_input, 50)}"
            )
            lines.append(f"   {org_ts}")
            lines.append("")
            lines.append("#+begin_src bash")
            lines.append(f"$ {block.content_input}")
            lines.append("#+end_src")

            if block.content_output:
                lines.append("")
                lines.append("*** Output")
                lines.append("#+begin_example")
                lines.append(block.content_output.rstrip())
                lines.append("#+end_example")

            if block.exit_code is not None and block.exit_code != 0:
                lines.append("")
                lines.append(f"Exit code: {block.exit_code}")

        elif block.type == BlockType.AI_RESPONSE:
            lines.append("** AI Chat")
            lines.append(f"   {org_ts}")
            lines.append(":PROPERTIES:")
            if block.metadata:
                if "model" in block.metadata:
                    lines.append(f":MODEL: {block.metadata['model']}")
                if "tokens" in block.metadata:
                    lines.append(f":TOKENS: {block.metadata['tokens']}")
            lines.append(":END:")
            lines.append("")

            lines.append("*** User")
            lines.append(block.content_input)
            lines.append("")

            if block.content_output:
                lines.append("*** Assistant")
                lines.append(block.content_output.rstrip())

            if block.content_exec_output:
                lines.append("")
                lines.append("*** Executed")
                lines.append("#+begin_example")
                lines.append(block.content_exec_output.rstrip())
                lines.append("#+end_example")

        elif block.type == BlockType.AGENT_RESPONSE:
            lines.append("** Agent Session")
            lines.append(f"   {org_ts}")
            lines.append(":PROPERTIES:")
            lines.append(f":ITERATIONS: {len(block.iterations)}")
            lines.append(f":TOOL_CALLS: {len(block.tool_calls)}")
            if block.metadata:
                if "model" in block.metadata:
                    lines.append(f":MODEL: {block.metadata['model']}")
                if "tokens" in block.metadata:
                    lines.append(f":TOKENS: {block.metadata['tokens']}")
            lines.append(":END:")
            lines.append("")

            lines.append("*** Task")
            lines.append(block.content_input)
            lines.append("")

            if block.iterations:
                lines.append("*** Iterations")
                for iteration in block.iterations:
                    lines.append(f"**** Iteration {iteration.iteration_number}")

                    if iteration.thinking:
                        lines.append("***** Thinking")
                        lines.append(iteration.thinking.rstrip())
                        lines.append("")

                    for tc in iteration.tool_calls:
                        status_kw = (
                            "DONE"
                            if tc.status == "success"
                            else "FAILED"
                            if tc.status == "error"
                            else "TODO"
                        )
                        lines.append(f"***** {status_kw} Tool: {tc.tool_name}")
                        if tc.arguments:
                            lines.append("#+begin_src json")
                            lines.append(tc.arguments)
                            lines.append("#+end_src")
                        if tc.output:
                            lines.append("****** Result")
                            lines.append("#+begin_example")
                            lines.append(tc.output[:1000].rstrip())
                            lines.append("#+end_example")
                        lines.append("")

            if block.content_output:
                lines.append("*** Final Response")
                lines.append(block.content_output.rstrip())

        elif block.type == BlockType.SYSTEM_MSG:
            lines.append("** System Message")
            lines.append(f"   {org_ts}")
            lines.append("")
            lines.append(block.content_input)

        elif block.type == BlockType.TOOL_CALL:
            status_kw = (
                "DONE"
                if block.exit_code == 0
                else "FAILED"
                if block.exit_code
                else "TODO"
            )
            tool_name = (
                block.metadata.get("tool_name", "Unknown")
                if block.metadata
                else "Unknown"
            )
            lines.append(f"** {status_kw} Tool: {tool_name}")
            lines.append(f"   {org_ts}")
            lines.append("")

            if block.metadata and "arguments" in block.metadata:
                lines.append("*** Arguments")
                lines.append("#+begin_src json")
                lines.append(block.metadata["arguments"])
                lines.append("#+end_src")

            if block.content_output:
                lines.append("*** Output")
                lines.append("#+begin_example")
                lines.append(block.content_output.rstrip())
                lines.append("#+end_example")

        return lines

    def _truncate(self, text: str, max_len: int) -> str:
        """Truncate text for heading display."""
        text = text.replace("\n", " ").strip()
        if len(text) > max_len:
            return text[: max_len - 3] + "..."
        return text


def export_to_html(blocks: list[BlockState]) -> str:
    """Export blocks to HTML string."""
    exporter = HTMLExporter(blocks)
    return exporter.export()


def export_to_org(blocks: list[BlockState]) -> str:
    """Export blocks to org-mode string."""
    exporter = OrgModeExporter(blocks)
    return exporter.export()
