from textual.app import ComposeResult
from textual.message import Message
from textual.reactive import reactive
from textual.widgets import Label, Static


class ClickableSection(Static):
    """A clickable status bar section that emits click events."""

    DEFAULT_CSS = """
    ClickableSection {
        width: auto;
        height: 1;
        padding: 0 1;
    }

    ClickableSection:hover {
        background: $surface-lighten-1;
    }

    ClickableSection.clickable {
        text-style: none;
    }

    ClickableSection.clickable:hover {
        text-style: underline;
    }
    """

    class Clicked(Message):
        """Posted when a section is clicked."""

        def __init__(self, section_id: str) -> None:
            self.section_id = section_id
            super().__init__()

    def __init__(
        self,
        content: str = "",
        *,
        section_id: str = "",
        clickable: bool = True,
        name: str | None = None,
        id: str | None = None,
        classes: str | None = None,
    ) -> None:
        super().__init__(content, name=name, id=id, classes=classes)
        self.section_id = section_id or (id or "")
        self._clickable = clickable
        if clickable:
            self.add_class("clickable")

    def on_click(self) -> None:
        """Handle click events."""
        if self._clickable:
            self.post_message(self.Clicked(self.section_id))


class StatusBar(Static):
    """Status bar showing mode, context size, provider status, and token usage."""

    DEFAULT_CSS = """
    StatusBar {
        dock: bottom;
        width: 100%;
        height: 1;
        background: $surface;
        color: $text-muted;
        layout: horizontal;
    }
    """

    def _safe_log_warning(self, message: str) -> None:
        try:
            self.log.warning(message)
        except Exception:
            pass

    mode = reactive("CLI")
    agent_mode = reactive(False)
    context_chars = reactive(0)
    context_limit = reactive(4000)
    provider_name = reactive("")
    provider_status = reactive("unknown")
    provider_latency = reactive("")
    mcp_count = reactive(0)
    process_count = reactive(0)
    is_recording = reactive(False)
    git_branch = reactive("")
    git_dirty = reactive(False)
    # Token usage tracking
    session_input_tokens = reactive(0)
    session_output_tokens = reactive(0)
    session_cost = reactive(0.0)
    # Streaming token tracking (real-time updates during generation)
    streaming_output_chars = reactive(0)
    is_streaming = reactive(False)
    # New indicators
    network_status = reactive("unknown")  # "online", "offline", "unknown"
    memory_percent = reactive(0.0)
    cpu_percent = reactive(0.0)
    keyboard_mode = reactive("")  # "INSERT", "NORMAL", "" (empty if not vim mode)
    vim_mode_enabled = reactive(False)

    def compose(self) -> ComposeResult:
        # Mode indicator (click to toggle CLI/AI)
        yield ClickableSection(
            "", section_id="mode", id="mode-indicator", classes="status-section"
        )
        yield Label("|", classes="status-sep")

        # Keyboard mode indicator (vim mode)
        yield ClickableSection(
            "", section_id="keyboard", id="keyboard-indicator", classes="status-section"
        )
        yield Label("|", id="keyboard-sep", classes="status-sep")

        # Git branch indicator (click to switch branch)
        yield ClickableSection(
            "", section_id="git", id="git-indicator", classes="status-section"
        )
        yield Label("|", id="git-sep", classes="status-sep")

        # Provider indicator (click to change provider)
        yield ClickableSection(
            "", section_id="provider", id="provider-indicator", classes="status-section"
        )
        yield Label("|", classes="status-sep")

        # MCP indicator (click to manage MCP)
        yield ClickableSection(
            "", section_id="mcp", id="mcp-indicator", classes="status-section"
        )
        yield Label("|", classes="status-sep")

        # Process indicator (click to view processes)
        yield ClickableSection(
            "", section_id="process", id="process-indicator", classes="status-section"
        )
        yield Label("|", classes="status-sep")

        # Recording indicator (click to toggle)
        yield ClickableSection(
            "", section_id="voice", id="voice-indicator", classes="status-section"
        )

        # Spacer to push right-side indicators
        yield Label("", classes="spacer")

        # Network status indicator (click to refresh)
        yield ClickableSection(
            "", section_id="network", id="network-indicator", classes="status-section"
        )
        yield Label("|", id="network-sep", classes="status-sep")

        # System stats indicator (click for details)
        yield ClickableSection(
            "", section_id="system", id="system-indicator", classes="status-section"
        )
        yield Label("|", id="system-sep", classes="status-sep")

        # Token usage indicator (click to reset/view details)
        yield ClickableSection(
            "", section_id="token", id="token-indicator", classes="status-section"
        )
        yield Label("|", id="token-sep", classes="status-sep")

        # Context indicator (click to view context)
        yield ClickableSection(
            "ctx: ~0 / 1k",
            section_id="context",
            id="context-indicator",
            classes="status-section context-low",
        )

    def on_mount(self):
        """Initialize display."""
        self._update_mode_display()
        self._update_keyboard_display()
        self._update_git_display()
        self._update_context_display()
        self._update_provider_display()
        self._update_token_display()
        self._update_process_display()
        self._update_network_display()
        self._update_system_display()

    def watch_mode(self, mode: str):
        self._update_mode_display()

    def watch_agent_mode(self, enabled: bool):
        self._update_mode_display()

    def watch_context_chars(self, chars: int):
        self._update_context_display()

    def watch_context_limit(self, limit: int):
        self._update_context_display()

    def watch_provider_status(self, status: str):
        self._update_provider_display()

    def watch_provider_name(self, name: str):
        self._update_provider_display()

    def watch_provider_latency(self, latency: str):
        self._update_provider_display()

    def watch_mcp_count(self, count: int):
        self._update_mcp_display()

    def watch_process_count(self, count: int):
        self._update_process_display()

    def watch_is_recording(self, recording: bool):
        self._update_voice_display()

    def watch_git_branch(self, branch: str):
        self._update_git_display()

    def watch_git_dirty(self, dirty: bool):
        self._update_git_display()

    def watch_session_input_tokens(self, tokens: int):
        self._update_token_display()

    def watch_session_output_tokens(self, tokens: int):
        self._update_token_display()

    def watch_session_cost(self, cost: float):
        self._update_token_display()

    def watch_streaming_output_chars(self, chars: int):
        self._update_token_display()

    def watch_is_streaming(self, streaming: bool):
        self._update_token_display()

    def watch_network_status(self, status: str):
        self._update_network_display()

    def watch_memory_percent(self, percent: float):
        self._update_system_display()

    def watch_cpu_percent(self, percent: float):
        self._update_system_display()

    def watch_keyboard_mode(self, mode: str):
        self._update_keyboard_display()

    def watch_vim_mode_enabled(self, enabled: bool):
        self._update_keyboard_display()

    def _update_keyboard_display(self):
        """Update keyboard mode indicator (vim mode)."""
        try:
            indicator = self.query_one("#keyboard-indicator", ClickableSection)
            sep = self.query_one("#keyboard-sep", Label)
            indicator.remove_class("vim-insert", "vim-normal", "vim-visual")

            if not self.vim_mode_enabled or not self.keyboard_mode:
                indicator.update("")
                indicator.display = False
                sep.display = False
                return

            indicator.display = True
            sep.display = True

            mode_upper = self.keyboard_mode.upper()
            if mode_upper == "INSERT":
                indicator.update("󰌌 INS")
                indicator.add_class("vim-insert")
            elif mode_upper == "NORMAL":
                indicator.update("󰌌 NOR")
                indicator.add_class("vim-normal")
            elif mode_upper == "VISUAL":
                indicator.update("󰌌 VIS")
                indicator.add_class("vim-visual")
            else:
                indicator.update(f"󰌌 {mode_upper[:3]}")
        except Exception as e:
            self._safe_log_warning(f"Status update failed: {e}")

    def _update_network_display(self):
        """Update network status indicator."""
        try:
            indicator = self.query_one("#network-indicator", ClickableSection)
            sep = self.query_one("#network-sep", Label)
            indicator.remove_class(
                "network-online", "network-offline", "network-unknown"
            )

            if self.network_status == "online":
                indicator.update("󰖩 ")
                indicator.add_class("network-online")
                indicator.display = True
                sep.display = True
            elif self.network_status == "offline":
                indicator.update("󰖪 ")
                indicator.add_class("network-offline")
                indicator.display = True
                sep.display = True
            else:
                # Hide when unknown
                indicator.update("")
                indicator.display = False
                sep.display = False
        except Exception as e:
            self._safe_log_warning(f"Status update failed: {e}")

    def _update_system_display(self):
        """Update memory/CPU usage indicator."""
        try:
            indicator = self.query_one("#system-indicator", ClickableSection)
            sep = self.query_one("#system-sep", Label)
            indicator.remove_class("system-low", "system-medium", "system-high")

            # Only show if we have data
            if self.memory_percent == 0 and self.cpu_percent == 0:
                indicator.update("")
                indicator.display = False
                sep.display = False
                return

            indicator.display = True
            sep.display = True

            # Format: CPU/MEM
            cpu_str = f"{self.cpu_percent:.0f}"
            mem_str = f"{self.memory_percent:.0f}"
            indicator.update(f"󰍛 {cpu_str}%/{mem_str}%")

            # Color based on highest usage
            max_usage = max(self.cpu_percent, self.memory_percent)
            if max_usage < 50:
                indicator.add_class("system-low")
            elif max_usage < 80:
                indicator.add_class("system-medium")
            else:
                indicator.add_class("system-high")
        except Exception as e:
            self._safe_log_warning(f"Status update failed: {e}")

    def _update_mcp_display(self):
        try:
            indicator = self.query_one("#mcp-indicator", ClickableSection)
            indicator.remove_class("mcp-active", "mcp-inactive")

            if self.mcp_count > 0:
                indicator.update(f"󱔗 MCP: {self.mcp_count}")
                indicator.add_class("mcp-active")
            else:
                indicator.update("󱔗 MCP: 0")
                indicator.add_class("mcp-inactive")
        except Exception as e:
            self._safe_log_warning(f"Status update failed: {e}")

    def _update_process_display(self):
        try:
            indicator = self.query_one("#process-indicator", ClickableSection)
            indicator.remove_class("process-active", "process-inactive")

            if self.process_count > 0:
                indicator.update(f"󰄬 PROC: {self.process_count}")
                indicator.add_class("process-active")
            else:
                indicator.update("󰅖 PROC: 0")
                indicator.add_class("process-inactive")
        except Exception as e:
            self._safe_log_warning(f"Status update failed: {e}")

    def _update_voice_display(self):
        try:
            indicator = self.query_one("#voice-indicator", ClickableSection)
            indicator.remove_class("voice-active", "voice-inactive")

            if self.is_recording:
                indicator.update("● REC")
                indicator.add_class("voice-active")
            else:
                indicator.update("")
                indicator.add_class("voice-inactive")
        except Exception as e:
            self._safe_log_warning(f"Status update failed: {e}")

    def _update_git_display(self):
        try:
            indicator = self.query_one("#git-indicator", ClickableSection)
            sep = self.query_one("#git-sep", Label)
            indicator.remove_class("git-dirty", "git-clean")

            if not self.git_branch:
                indicator.update("")
                indicator.display = False
                sep.display = False
                return

            indicator.display = True
            sep.display = True
            icon = "±" if self.git_dirty else ""
            text = f"{icon} {self.git_branch}"
            indicator.update(text)

            if self.git_dirty:
                indicator.add_class("git-dirty")
            else:
                indicator.add_class("git-clean")
        except Exception as e:
            self._safe_log_warning(f"Status update failed: {e}")

    def _update_mode_display(self):
        try:
            indicator = self.query_one("#mode-indicator", ClickableSection)
            indicator.remove_class("mode-cli", "mode-ai", "mode-agent")

            if self.mode == "CLI":
                indicator.update(" CLI")
                indicator.add_class("mode-cli")
            else:
                if self.agent_mode:
                    indicator.update("⚙ AGENT")
                    indicator.add_class("mode-agent")
                else:
                    indicator.update("◆ AI")
                    indicator.add_class("mode-ai")
        except Exception as e:
            self._safe_log_warning(f"Status update failed: {e}")

    def _update_context_display(self):
        try:
            indicator = self.query_one("#context-indicator", ClickableSection)
            indicator.remove_class("context-low", "context-medium", "context-high")

            pct = (
                (self.context_chars / self.context_limit * 100)
                if self.context_limit > 0
                else 0
            )
            tokens = self.context_chars // 4
            limit_tokens = self.context_limit // 4

            # Format limit nicely (e.g., 32000 -> 32k)
            if limit_tokens >= 1000:
                limit_str = f"{limit_tokens // 1000}k"
            else:
                limit_str = str(limit_tokens)

            # Always show context usage
            indicator.update(f"󰈙 ctx: ~{tokens:,} / {limit_str}")

            if pct < 50:
                indicator.add_class("context-low")
            elif pct < 80:
                indicator.add_class("context-medium")
            else:
                indicator.add_class("context-high")
        except Exception as e:
            self._safe_log_warning(f"Status update failed: {e}")

    def _update_provider_display(self):
        try:
            indicator = self.query_one("#provider-indicator", ClickableSection)
            indicator.remove_class(
                "provider-connected",
                "provider-disconnected",
                "provider-checking",
                "provider-slow",
                "provider-fast",
            )

            name = self.provider_name or ""
            if not name:
                indicator.update("")
                return

            latency_str = f" {self.provider_latency}" if self.provider_latency else ""

            if self.provider_status == "connected":
                indicator.update(f"{name} 󰄬{latency_str}")
                indicator.add_class("provider-connected")
                if self.provider_latency:
                    try:
                        ms = int(
                            self.provider_latency.replace("ms", "").replace("s", "000")
                        )
                        if ms < 500:
                            indicator.add_class("provider-fast")
                        elif ms > 2000:
                            indicator.add_class("provider-slow")
                    except ValueError:
                        pass
            elif self.provider_status == "disconnected":
                indicator.update(f"{name} 󰅖")
                indicator.add_class("provider-disconnected")
            elif self.provider_status == "error":
                indicator.update(f"{name} ✗")
                indicator.add_class("provider-disconnected")
            else:
                indicator.update(name)
                indicator.add_class("provider-checking")
        except Exception as e:
            self._safe_log_warning(f"Status update failed: {e}")

    def _update_token_display(self):
        try:
            indicator = self.query_one("#token-indicator", ClickableSection)
            sep = self.query_one("#token-sep", Label)

            total_tokens = self.session_input_tokens + self.session_output_tokens
            streaming_tokens = self.streaming_output_chars // 4

            if total_tokens == 0 and not self.is_streaming:
                indicator.update("")
                sep.display = False
                return

            sep.display = True

            if self.is_streaming:
                display_tokens = total_tokens + streaming_tokens
                if display_tokens >= 1_000_000:
                    token_str = f"~{display_tokens / 1_000_000:.1f}M"
                elif display_tokens >= 1000:
                    token_str = f"~{display_tokens / 1000:.1f}k"
                else:
                    token_str = f"~{display_tokens}"
                indicator.update(f"󱓞 tok: {token_str} ...")
            else:
                if total_tokens >= 1_000_000:
                    token_str = f"{total_tokens / 1_000_000:.1f}M"
                elif total_tokens >= 1000:
                    token_str = f"{total_tokens / 1000:.1f}k"
                else:
                    token_str = str(total_tokens)

                if self.session_cost >= 0.01:
                    cost_str = f"${self.session_cost:.2f}"
                elif self.session_cost > 0:
                    cost_str = f"${self.session_cost:.4f}"
                else:
                    cost_str = "$0"

                indicator.update(f"󱓞 tok: {token_str} / {cost_str}")

        except Exception as e:
            self._safe_log_warning(f"Status update failed: {e}")

    def set_mode(self, mode: str):
        """Set current mode (CLI or AI)."""
        self.mode = mode

    def set_agent_mode(self, enabled: bool):
        """Set agent mode status."""
        self.agent_mode = enabled

    def set_context(self, chars: int, limit: int = 4000):
        """Set current context size."""
        self.context_chars = chars
        self.context_limit = limit

    def set_provider(self, name: str, status: str = "unknown", latency: str = ""):
        """Set provider name, status, and latency."""
        self.provider_name = name
        self.provider_status = status
        self.provider_latency = latency

    def set_mcp_status(self, count: int):
        """Set number of active MCP servers."""
        self.mcp_count = count

    def set_process_count(self, count: int):
        """Set number of active processes."""
        self.process_count = count

    def set_recording(self, recording: bool):
        self.is_recording = recording

    def set_git_status(self, branch: str, is_dirty: bool):
        self.git_branch = branch
        self.git_dirty = is_dirty

    def add_token_usage(self, input_tokens: int, output_tokens: int, cost: float):
        """Add token usage from a completed request."""
        self.session_input_tokens += input_tokens
        self.session_output_tokens += output_tokens
        self.session_cost += cost

    def reset_token_usage(self):
        self.session_input_tokens = 0
        self.session_output_tokens = 0
        self.session_cost = 0.0
        self.streaming_output_chars = 0
        self.is_streaming = False

    def start_streaming(self):
        self.streaming_output_chars = 0
        self.is_streaming = True

    def update_streaming_tokens(self, output_chars: int):
        self.streaming_output_chars = output_chars

    def stop_streaming(self):
        self.is_streaming = False
        self.streaming_output_chars = 0

    def set_network_status(self, status: str):
        """Set network status (online, offline, unknown)."""
        self.network_status = status

    def set_system_stats(self, cpu_percent: float, memory_percent: float):
        """Set CPU and memory usage percentages."""
        self.cpu_percent = cpu_percent
        self.memory_percent = memory_percent

    def set_keyboard_mode(self, mode: str):
        """Set keyboard mode (INSERT, NORMAL, VISUAL, etc.)."""
        self.keyboard_mode = mode

    def set_vim_mode(self, enabled: bool):
        """Enable/disable vim mode indicator."""
        self.vim_mode_enabled = enabled
