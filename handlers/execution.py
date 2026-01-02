"""Execution handlers for AI and CLI commands."""

from __future__ import annotations
import asyncio
import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app import NullApp

from models import BlockState
from widgets import BaseBlockWidget


class ExecutionHandler:
    """Handles AI and CLI command execution."""

    def __init__(self, app: "NullApp"):
        self.app = app

    async def execute_ai(self, prompt: str, block_state: BlockState, widget: BaseBlockWidget):
        """Execute AI generation with streaming response."""
        try:
            from context import ContextManager
            from prompts import get_prompt_manager

            # Get system prompt from prompt manager
            active_key = self.app.config.get("ai", {}).get("active_prompt", "default")
            provider = self.app.config.get("ai", {}).get("provider", "")
            prompt_manager = get_prompt_manager()
            system_prompt = prompt_manager.get_prompt_content(active_key, provider)

            # Gather context (exclude current block)
            context_str = ContextManager.get_context(self.app.blocks[:-1])

            # Store metadata
            block_state.metadata = {
                "model": f"{self.app.config['ai']['provider']}/{self.app.config['ai']['model']}",
                "context": f"{len(context_str)} chars",
                "persona": active_key
            }
            if widget:
                widget.update_metadata()

            full_response = ""

            # Streaming generation
            async for chunk in self.app.ai_provider.generate(prompt, context_str, system_prompt=system_prompt):
                # Check for cancellation
                if self.app._ai_cancelled:
                    full_response += "\n\n[Cancelled]"
                    block_state.content_output = full_response
                    widget.update_output(full_response)
                    break

                full_response += chunk
                block_state.content_output = full_response
                widget.update_output(full_response)

            block_state.is_running = False
            self.app._active_worker = None

            # Update metadata with token estimate
            response_tokens = len(full_response) // 4
            context_tokens = len(context_str) // 4
            block_state.metadata["tokens"] = f"~{response_tokens} out / ~{context_tokens} ctx"
            widget.update_metadata()

            widget.set_loading(False)

            # Auto-save session
            self.app._auto_save()

            # Check for agent command in response
            command_to_run = self._extract_command(full_response)
            if command_to_run:
                self.app.notify(f"Agent requested execution: {command_to_run}")
                self.app.call_later(self.run_agent_command, command_to_run, block_state, widget)

        except asyncio.CancelledError:
            block_state.content_output += "\n\n[Cancelled]"
            block_state.is_running = False
            widget.update_output(block_state.content_output)
            widget.set_loading(False)
            self.app._active_worker = None
        except Exception as e:
            block_state.content_output = f"AI Error: {str(e)}"
            block_state.is_running = False
            widget.update_output(f"Error: {str(e)}")
            self.app._active_worker = None

    def _extract_command(self, response: str) -> str | None:
        """Extract executable command from AI response."""
        # Look for markdown code blocks with bash/sh
        code_block_match = re.search(
            r"```\s*(bash|sh|console|shell)\s+\n?(.*?)```",
            response,
            re.DOTALL
        )

        if code_block_match:
            return code_block_match.group(2).strip()

        # Fallback to [COMMAND] tags
        tag_match = re.search(r"\[COMMAND\](.*?)\[/COMMAND\]", response, re.DOTALL)
        if tag_match:
            return tag_match.group(1).strip()

        return None

    def run_agent_command(self, command: str, ai_block: BlockState, ai_widget: BaseBlockWidget):
        """Execute a command requested by the AI agent."""

        async def run_inline():
            try:
                output_buffer = []

                def callback(line):
                    output_buffer.append(line)
                    current_text = "".join(output_buffer)
                    ai_block.content_exec_output = f"\n```text\n{current_text}\n```\n"
                    ai_widget.update_output("")

                # Execute command
                rc = await self.app.executor.run_command_and_get_rc(command, callback)

                output_text = "".join(output_buffer)
                if not output_text.strip():
                    output_text = "(Command execution completed with no output)"

                # Format output
                result_md = f"\n```text\n{output_text}\n```\n"
                if rc != 0:
                    result_md += f"\n*Exit Code: {rc}*\n"

                ai_block.content_exec_output = result_md
                ai_widget.update_output("")

            except Exception as e:
                err_msg = f"\n**Error Running Command:** {str(e)}\n"
                ai_block.content_exec_output = err_msg
                ai_widget.update_output("")
                self.app.notify(f"Agent Execution Error: {e}", severity="error")
            finally:
                ai_widget.set_loading(False)
                ai_block.is_running = False

        self.app.run_worker(run_inline())

    async def execute_cli(self, block: BlockState, widget: BaseBlockWidget):
        """Execute a CLI command and stream output."""

        def update_callback(line: str):
            block.content_output += line
            widget.update_output()

        exit_code = await self.app.executor.run_command_and_get_rc(
            block.content_input,
            update_callback
        )

        widget.set_exit_code(exit_code)
        self.app._auto_save()

    async def execute_cli_append(self, cmd: str, block: BlockState, widget: BaseBlockWidget):
        """Execute a command and append output to existing CLI block."""

        def update_callback(line: str):
            block.content_output += line
            widget.update_output()

        exit_code = await self.app.executor.run_command_and_get_rc(cmd, update_callback)

        if exit_code != 0:
            block.content_output += f"[exit: {exit_code}]\n"
            widget.update_output()

        self.app._auto_save()

    async def regenerate_ai(self, block: BlockState, widget: BaseBlockWidget):
        """Regenerate an AI response block."""
        if not self.app.ai_provider:
            self.app.notify("AI Provider not configured", severity="error")
            return

        # Clear output and reset state
        block.content_output = ""
        block.content_exec_output = ""
        block.is_running = True
        block.exit_code = None

        # Reset widget display
        widget.set_loading(True)
        if hasattr(widget, 'thinking_widget') and widget.thinking_widget:
            widget.thinking_widget.thinking_text = ""
            widget.thinking_widget.start_loading()
        if hasattr(widget, 'exec_widget') and widget.exec_widget:
            widget.exec_widget.exec_output = ""

        widget.update_metadata()

        # Run AI worker
        self.app._ai_cancelled = False
        self.app._active_worker = self.app.run_worker(
            self.execute_ai(block.content_input, block, widget)
        )
