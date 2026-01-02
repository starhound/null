from textual.app import ComposeResult
from textual.widgets import Static, Label
from textual.reactive import reactive


class StatusBar(Static):
    """Status bar showing mode, context size, provider status, and token usage."""

    mode = reactive("CLI")
    agent_mode = reactive(False)
    context_chars = reactive(0)
    context_limit = reactive(4000)
    provider_name = reactive("")
    provider_status = reactive("unknown")
    mcp_count = reactive(0)
    # Token usage tracking
    session_input_tokens = reactive(0)
    session_output_tokens = reactive(0)
    session_cost = reactive(0.0)

    def compose(self) -> ComposeResult:
        yield Label("", id="mode-indicator", classes="status-section")
        yield Label("|", classes="status-sep")
        yield Label("", id="provider-indicator", classes="status-section")
        yield Label("|", classes="status-sep")
        yield Label("", id="mcp-indicator", classes="status-section")
        yield Label("", classes="spacer")
        # Token usage indicator
        yield Label("", id="token-indicator", classes="status-section")
        yield Label("|", id="token-sep", classes="status-sep")
        # Context indicator
        yield Label("ctx: ~0 / 1k", id="context-indicator", classes="status-section context-low")

    def on_mount(self):
        """Initialize display."""
        self._update_mode_display()
        self._update_context_display()
        self._update_provider_display()
        self._update_token_display()

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

    def watch_mcp_count(self, count: int):
        self._update_mcp_display()

    def watch_session_input_tokens(self, tokens: int):
        self._update_token_display()

    def watch_session_output_tokens(self, tokens: int):
        self._update_token_display()

    def watch_session_cost(self, cost: float):
        self._update_token_display()

    def _update_mcp_display(self):
        try:
            indicator = self.query_one("#mcp-indicator", Label)
            indicator.remove_class("mcp-active", "mcp-inactive")
            
            if self.mcp_count > 0:
                indicator.update(f"MCP: {self.mcp_count}")
                indicator.add_class("mcp-active")
            else:
                indicator.update("MCP: 0")
                indicator.add_class("mcp-inactive")
        except Exception:
            pass

    def _update_mode_display(self):
        try:
            indicator = self.query_one("#mode-indicator", Label)
            indicator.remove_class("mode-cli", "mode-ai", "mode-agent")

            if self.mode == "CLI":
                indicator.update("❯ CLI")
                indicator.add_class("mode-cli")
            else:
                if self.agent_mode:
                    indicator.update("◆ AGENT")
                    indicator.add_class("mode-agent")
                else:
                    indicator.update("◆ AI")
                    indicator.add_class("mode-ai")
        except Exception:
            pass

    def _update_context_display(self):
        try:
            indicator = self.query_one("#context-indicator", Label)
            indicator.remove_class("context-low", "context-medium", "context-high")

            pct = (self.context_chars / self.context_limit * 100) if self.context_limit > 0 else 0
            tokens = self.context_chars // 4
            limit_tokens = self.context_limit // 4

            # Format limit nicely (e.g., 32000 -> 32k)
            if limit_tokens >= 1000:
                limit_str = f"{limit_tokens // 1000}k"
            else:
                limit_str = str(limit_tokens)

            # Always show context usage
            indicator.update(f"ctx: ~{tokens:,} / {limit_str}")

            if pct < 50:
                indicator.add_class("context-low")
            elif pct < 80:
                indicator.add_class("context-medium")
            else:
                indicator.add_class("context-high")
        except Exception as e:
            # Debug: show error
            pass

    def _update_provider_display(self):
        try:
            indicator = self.query_one("#provider-indicator", Label)
            indicator.remove_class("provider-connected", "provider-disconnected", "provider-checking")

            name = self.provider_name or ""
            if not name:
                indicator.update("")
                return

            if self.provider_status == "connected":
                indicator.update(f"{name} ●")
                indicator.add_class("provider-connected")
            elif self.provider_status == "disconnected":
                indicator.update(f"{name} ○")
                indicator.add_class("provider-disconnected")
            else:
                indicator.update(name)
                indicator.add_class("provider-checking")
        except Exception:
            pass

    def _update_token_display(self):
        """Update the token usage and cost display."""
        try:
            indicator = self.query_one("#token-indicator", Label)
            sep = self.query_one("#token-sep", Label)

            total_tokens = self.session_input_tokens + self.session_output_tokens

            if total_tokens == 0:
                # Hide token display when no tokens used
                indicator.update("")
                sep.display = False
                return

            sep.display = True

            # Format token count (e.g., 1.2k, 15k, 1.5M)
            if total_tokens >= 1_000_000:
                token_str = f"{total_tokens / 1_000_000:.1f}M"
            elif total_tokens >= 1000:
                token_str = f"{total_tokens / 1000:.1f}k"
            else:
                token_str = str(total_tokens)

            # Format cost
            if self.session_cost >= 1.0:
                cost_str = f"${self.session_cost:.2f}"
            elif self.session_cost >= 0.01:
                cost_str = f"${self.session_cost:.2f}"
            elif self.session_cost > 0:
                cost_str = f"${self.session_cost:.4f}"
            else:
                cost_str = "$0"

            # Display format: "Tokens: 1.2k / $0.02"
            indicator.update(f"tok: {token_str} / {cost_str}")

        except Exception:
            pass

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

    def set_provider(self, name: str, status: str = "unknown"):
        """Set provider name and status."""
        self.provider_name = name
        self.provider_status = status

    def set_mcp_status(self, count: int):
        """Set number of active MCP servers."""
        self.mcp_count = count

    def add_token_usage(self, input_tokens: int, output_tokens: int, cost: float):
        """Add token usage from a completed request."""
        self.session_input_tokens += input_tokens
        self.session_output_tokens += output_tokens
        self.session_cost += cost

    def reset_token_usage(self):
        """Reset session token usage (e.g., on clear)."""
        self.session_input_tokens = 0
        self.session_output_tokens = 0
        self.session_cost = 0.0
