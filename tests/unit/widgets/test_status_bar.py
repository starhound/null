"""Tests for widgets/status_bar.py - StatusBar widget."""

from unittest.mock import MagicMock, patch

import pytest
from textual.widgets import Label, Static

from widgets.status_bar import ClickableSection, StatusBar


class TestClickableSection:
    """Test ClickableSection widget."""

    def test_default_init(self):
        """Default initialization should be clickable."""
        section = ClickableSection("test")
        assert section._clickable is True
        assert "clickable" in section.classes

    def test_init_with_section_id(self):
        """Section ID should be set from parameter."""
        section = ClickableSection("test", section_id="my-section")
        assert section.section_id == "my-section"

    def test_init_section_id_from_widget_id(self):
        """Section ID should fallback to widget id."""
        section = ClickableSection("test", id="widget-id")
        assert section.section_id == "widget-id"

    def test_init_not_clickable(self):
        """Non-clickable section should not have clickable class."""
        section = ClickableSection("test", clickable=False)
        assert section._clickable is False
        assert "clickable" not in section.classes

    def test_on_click_posts_message(self):
        """Clicking should post Clicked message."""
        section = ClickableSection("test", section_id="test-section")
        with patch.object(section, "post_message") as mock_post:
            section.on_click()
            mock_post.assert_called_once()
            message = mock_post.call_args[0][0]
            assert isinstance(message, ClickableSection.Clicked)
            assert message.section_id == "test-section"

    def test_on_click_not_clickable(self):
        """Non-clickable section should not post message on click."""
        section = ClickableSection("test", clickable=False)
        with patch.object(section, "post_message") as mock_post:
            section.on_click()
            mock_post.assert_not_called()


class TestStatusBarInit:
    """Test StatusBar initialization."""

    def test_default_mode(self):
        """Default mode should be 'CLI'."""
        bar = StatusBar()
        assert bar.mode == "CLI"

    def test_default_agent_mode(self):
        """Default agent_mode should be False."""
        bar = StatusBar()
        assert bar.agent_mode is False

    def test_default_context_chars(self):
        """Default context_chars should be 0."""
        bar = StatusBar()
        assert bar.context_chars == 0

    def test_default_context_limit(self):
        """Default context_limit should be 4000."""
        bar = StatusBar()
        assert bar.context_limit == 4000

    def test_default_provider_name(self):
        """Default provider_name should be empty string."""
        bar = StatusBar()
        assert bar.provider_name == ""

    def test_default_provider_status(self):
        """Default provider_status should be 'unknown'."""
        bar = StatusBar()
        assert bar.provider_status == "unknown"

    def test_default_mcp_count(self):
        """Default mcp_count should be 0."""
        bar = StatusBar()
        assert bar.mcp_count == 0

    def test_default_process_count(self):
        """Default process_count should be 0."""
        bar = StatusBar()
        assert bar.process_count == 0

    def test_default_git_branch(self):
        """Default git_branch should be empty string."""
        bar = StatusBar()
        assert bar.git_branch == ""

    def test_default_git_dirty(self):
        """Default git_dirty should be False."""
        bar = StatusBar()
        assert bar.git_dirty is False

    def test_default_session_input_tokens(self):
        """Default session_input_tokens should be 0."""
        bar = StatusBar()
        assert bar.session_input_tokens == 0

    def test_default_session_output_tokens(self):
        """Default session_output_tokens should be 0."""
        bar = StatusBar()
        assert bar.session_output_tokens == 0

    def test_default_session_cost(self):
        """Default session_cost should be 0.0."""
        bar = StatusBar()
        assert bar.session_cost == 0.0

    def test_custom_id(self):
        """Custom ID should be passed to parent."""
        bar = StatusBar(id="my-status-bar")
        assert bar.id == "my-status-bar"

    def test_custom_name(self):
        """Custom name should be passed to parent."""
        bar = StatusBar(name="test-bar")
        assert bar.name == "test-bar"

    def test_custom_classes(self):
        """Custom classes should be passed to parent."""
        bar = StatusBar(classes="custom-class")
        assert "custom-class" in bar.classes


class TestStatusBarCompose:
    """Test compose method yields correct widgets."""

    def test_compose_yields_widgets(self):
        """Compose should yield widgets."""
        bar = StatusBar()
        children = list(bar.compose())

        # Should have more widgets now (added network, system, keyboard indicators)
        assert len(children) == 23
        # Mix of ClickableSection and Label
        assert all(isinstance(child, (ClickableSection, Label)) for child in children)

    def test_compose_mode_indicator(self):
        """Mode indicator should have correct id."""
        bar = StatusBar()
        children = list(bar.compose())

        mode_indicator = children[0]
        assert mode_indicator.id == "mode-indicator"
        assert "status-section" in mode_indicator.classes
        assert isinstance(mode_indicator, ClickableSection)

    def test_compose_keyboard_indicator(self):
        """Keyboard indicator should have correct id."""
        bar = StatusBar()
        children = list(bar.compose())

        keyboard_indicator = children[2]
        assert keyboard_indicator.id == "keyboard-indicator"
        assert "status-section" in keyboard_indicator.classes
        assert isinstance(keyboard_indicator, ClickableSection)

    def test_compose_git_indicator(self):
        """Git indicator should have correct id."""
        bar = StatusBar()
        children = list(bar.compose())

        git_indicator = children[4]
        assert git_indicator.id == "git-indicator"
        assert "status-section" in git_indicator.classes
        assert isinstance(git_indicator, ClickableSection)

    def test_compose_provider_indicator(self):
        """Provider indicator should have correct id."""
        bar = StatusBar()
        children = list(bar.compose())

        provider_indicator = children[6]
        assert provider_indicator.id == "provider-indicator"
        assert "status-section" in provider_indicator.classes

    def test_compose_mcp_indicator(self):
        """MCP indicator should have correct id."""
        bar = StatusBar()
        children = list(bar.compose())

        mcp_indicator = children[8]
        assert mcp_indicator.id == "mcp-indicator"
        assert "status-section" in mcp_indicator.classes

    def test_compose_process_indicator(self):
        """Process indicator should have correct id."""
        bar = StatusBar()
        children = list(bar.compose())

        process_indicator = children[10]
        assert process_indicator.id == "process-indicator"
        assert "status-section" in process_indicator.classes

    def test_compose_voice_indicator(self):
        """Voice indicator should have correct id."""
        bar = StatusBar()
        children = list(bar.compose())

        voice_indicator = children[12]
        assert voice_indicator.id == "voice-indicator"
        assert "status-section" in voice_indicator.classes

    def test_compose_spacer(self):
        """Spacer label should have spacer class."""
        bar = StatusBar()
        children = list(bar.compose())

        spacer = children[13]
        assert "spacer" in spacer.classes

    def test_compose_network_indicator(self):
        """Network indicator should have correct id."""
        bar = StatusBar()
        children = list(bar.compose())

        network_indicator = children[14]
        assert network_indicator.id == "network-indicator"
        assert "status-section" in network_indicator.classes

    def test_compose_system_indicator(self):
        """System indicator should have correct id."""
        bar = StatusBar()
        children = list(bar.compose())

        system_indicator = children[16]
        assert system_indicator.id == "system-indicator"
        assert "status-section" in system_indicator.classes

    def test_compose_token_indicator(self):
        """Token indicator should have correct id."""
        bar = StatusBar()
        children = list(bar.compose())

        token_indicator = children[18]
        assert token_indicator.id == "token-indicator"
        assert "status-section" in token_indicator.classes

    def test_compose_context_indicator(self):
        """Context indicator should have correct id and classes."""
        bar = StatusBar()
        children = list(bar.compose())

        context_indicator = children[22]
        assert context_indicator.id == "context-indicator"
        assert "status-section" in context_indicator.classes
        assert "context-low" in context_indicator.classes

    def test_compose_separators(self):
        """Separators should have status-sep class."""
        bar = StatusBar()
        children = list(bar.compose())

        separators = [children[1], children[5], children[7], children[9]]
        for sep in separators:
            assert "status-sep" in sep.classes

    def test_compose_token_separator(self):
        """Token separator should have correct id."""
        bar = StatusBar()
        children = list(bar.compose())
        token_sep = [c for c in children if hasattr(c, 'id') and c.id == "token-sep"]
        assert len(token_sep) == 1
        assert "status-sep" in token_sep[0].classes


class TestStatusBarSetMode:
    """Test set_mode method."""

    def test_set_mode_cli(self):
        """Setting mode to CLI."""
        bar = StatusBar()
        bar.set_mode("CLI")
        assert bar.mode == "CLI"

    def test_set_mode_ai(self):
        """Setting mode to AI."""
        bar = StatusBar()
        bar.set_mode("AI")
        assert bar.mode == "AI"

    def test_set_mode_updates_reactive(self):
        """set_mode should update the reactive property."""
        bar = StatusBar()
        bar.mode = "AI"
        bar.set_mode("CLI")
        assert bar.mode == "CLI"


class TestStatusBarSetAgentMode:
    """Test set_agent_mode method."""

    def test_set_agent_mode_enabled(self):
        """Setting agent_mode to True."""
        bar = StatusBar()
        bar.set_agent_mode(True)
        assert bar.agent_mode is True

    def test_set_agent_mode_disabled(self):
        """Setting agent_mode to False."""
        bar = StatusBar()
        bar.agent_mode = True
        bar.set_agent_mode(False)
        assert bar.agent_mode is False


class TestStatusBarSetContext:
    """Test set_context method."""

    def test_set_context_chars(self):
        """Setting context chars."""
        bar = StatusBar()
        bar.set_context(1000)
        assert bar.context_chars == 1000

    def test_set_context_default_limit(self):
        """Default limit when not specified."""
        bar = StatusBar()
        bar.set_context(500)
        assert bar.context_limit == 4000

    def test_set_context_custom_limit(self):
        """Setting custom context limit."""
        bar = StatusBar()
        bar.set_context(1000, limit=8000)
        assert bar.context_chars == 1000
        assert bar.context_limit == 8000

    def test_set_context_large_values(self):
        """Setting large context values."""
        bar = StatusBar()
        bar.set_context(128000, limit=200000)
        assert bar.context_chars == 128000
        assert bar.context_limit == 200000


class TestStatusBarSetProvider:
    """Test set_provider method."""

    def test_set_provider_name(self):
        """Setting provider name."""
        bar = StatusBar()
        bar.set_provider("Ollama")
        assert bar.provider_name == "Ollama"

    def test_set_provider_default_status(self):
        """Default status should be 'unknown'."""
        bar = StatusBar()
        bar.set_provider("OpenAI")
        assert bar.provider_status == "unknown"

    def test_set_provider_connected(self):
        """Setting provider as connected."""
        bar = StatusBar()
        bar.set_provider("Anthropic", status="connected")
        assert bar.provider_name == "Anthropic"
        assert bar.provider_status == "connected"

    def test_set_provider_disconnected(self):
        """Setting provider as disconnected."""
        bar = StatusBar()
        bar.set_provider("DeepSeek", status="disconnected")
        assert bar.provider_status == "disconnected"

    def test_set_provider_empty_name(self):
        """Setting empty provider name."""
        bar = StatusBar()
        bar.set_provider("")
        assert bar.provider_name == ""


class TestStatusBarSetMcpStatus:
    """Test set_mcp_status method."""

    def test_set_mcp_count_zero(self):
        """Setting MCP count to zero."""
        bar = StatusBar()
        bar.set_mcp_status(0)
        assert bar.mcp_count == 0

    def test_set_mcp_count_positive(self):
        """Setting positive MCP count."""
        bar = StatusBar()
        bar.set_mcp_status(3)
        assert bar.mcp_count == 3

    def test_set_mcp_count_large(self):
        """Setting large MCP count."""
        bar = StatusBar()
        bar.set_mcp_status(10)
        assert bar.mcp_count == 10


class TestStatusBarSetProcessCount:
    """Test set_process_count method."""

    def test_set_process_count_zero(self):
        """Setting process count to zero."""
        bar = StatusBar()
        bar.set_process_count(0)
        assert bar.process_count == 0

    def test_set_process_count_positive(self):
        """Setting positive process count."""
        bar = StatusBar()
        bar.set_process_count(5)
        assert bar.process_count == 5


class TestStatusBarSetGitStatus:
    """Test set_git_status method."""

    def test_set_git_clean(self):
        """Setting git status as clean."""
        bar = StatusBar()
        bar.set_git_status("main", is_dirty=False)
        assert bar.git_branch == "main"
        assert bar.git_dirty is False

    def test_set_git_dirty(self):
        """Setting git status as dirty."""
        bar = StatusBar()
        bar.set_git_status("feature/test", is_dirty=True)
        assert bar.git_branch == "feature/test"
        assert bar.git_dirty is True

    def test_set_git_empty_branch(self):
        """Setting empty git branch."""
        bar = StatusBar()
        bar.set_git_status("", is_dirty=False)
        assert bar.git_branch == ""


class TestStatusBarAddTokenUsage:
    """Test add_token_usage method."""

    def test_add_token_usage_first_call(self):
        """Adding tokens from first call."""
        bar = StatusBar()
        bar.add_token_usage(100, 50, 0.01)
        assert bar.session_input_tokens == 100
        assert bar.session_output_tokens == 50
        assert bar.session_cost == 0.01

    def test_add_token_usage_accumulates(self):
        """Token usage should accumulate."""
        bar = StatusBar()
        bar.add_token_usage(100, 50, 0.01)
        bar.add_token_usage(200, 100, 0.02)
        assert bar.session_input_tokens == 300
        assert bar.session_output_tokens == 150
        assert bar.session_cost == pytest.approx(0.03)

    def test_add_token_usage_zero(self):
        """Adding zero tokens."""
        bar = StatusBar()
        bar.add_token_usage(0, 0, 0.0)
        assert bar.session_input_tokens == 0
        assert bar.session_output_tokens == 0
        assert bar.session_cost == 0.0

    def test_add_token_usage_large_values(self):
        """Adding large token values."""
        bar = StatusBar()
        bar.add_token_usage(1000000, 500000, 15.50)
        assert bar.session_input_tokens == 1000000
        assert bar.session_output_tokens == 500000
        assert bar.session_cost == pytest.approx(15.50)


class TestStatusBarResetTokenUsage:
    """Test reset_token_usage method."""

    def test_reset_token_usage(self):
        """Resetting token usage should zero all values."""
        bar = StatusBar()
        bar.add_token_usage(1000, 500, 0.50)
        bar.reset_token_usage()
        assert bar.session_input_tokens == 0
        assert bar.session_output_tokens == 0
        assert bar.session_cost == 0.0

    def test_reset_token_usage_when_empty(self):
        """Resetting already empty token usage."""
        bar = StatusBar()
        bar.reset_token_usage()
        assert bar.session_input_tokens == 0
        assert bar.session_output_tokens == 0
        assert bar.session_cost == 0.0


class TestStatusBarWatchMode:
    """Test watch_mode reactive watcher."""

    def test_watch_mode_calls_update(self):
        """watch_mode should call _update_mode_display."""
        bar = StatusBar()
        with patch.object(bar, "_update_mode_display") as mock_update:
            bar.watch_mode("AI")
            mock_update.assert_called_once()

    def test_watch_mode_with_cli(self):
        """watch_mode should handle CLI mode."""
        bar = StatusBar()
        with patch.object(bar, "_update_mode_display") as mock_update:
            bar.watch_mode("CLI")
            mock_update.assert_called_once()


class TestStatusBarWatchAgentMode:
    """Test watch_agent_mode reactive watcher."""

    def test_watch_agent_mode_calls_update(self):
        """watch_agent_mode should call _update_mode_display."""
        bar = StatusBar()
        with patch.object(bar, "_update_mode_display") as mock_update:
            bar.watch_agent_mode(True)
            mock_update.assert_called_once()

    def test_watch_agent_mode_false(self):
        """watch_agent_mode should handle False value."""
        bar = StatusBar()
        with patch.object(bar, "_update_mode_display") as mock_update:
            bar.watch_agent_mode(False)
            mock_update.assert_called_once()


class TestStatusBarWatchContextChars:
    """Test watch_context_chars reactive watcher."""

    def test_watch_context_chars_calls_update(self):
        """watch_context_chars should call _update_context_display."""
        bar = StatusBar()
        with patch.object(bar, "_update_context_display") as mock_update:
            bar.watch_context_chars(1000)
            mock_update.assert_called_once()


class TestStatusBarWatchContextLimit:
    """Test watch_context_limit reactive watcher."""

    def test_watch_context_limit_calls_update(self):
        """watch_context_limit should call _update_context_display."""
        bar = StatusBar()
        with patch.object(bar, "_update_context_display") as mock_update:
            bar.watch_context_limit(8000)
            mock_update.assert_called_once()


class TestStatusBarWatchProviderStatus:
    """Test watch_provider_status reactive watcher."""

    def test_watch_provider_status_calls_update(self):
        """watch_provider_status should call _update_provider_display."""
        bar = StatusBar()
        with patch.object(bar, "_update_provider_display") as mock_update:
            bar.watch_provider_status("connected")
            mock_update.assert_called_once()


class TestStatusBarWatchProviderName:
    """Test watch_provider_name reactive watcher."""

    def test_watch_provider_name_calls_update(self):
        """watch_provider_name should call _update_provider_display."""
        bar = StatusBar()
        with patch.object(bar, "_update_provider_display") as mock_update:
            bar.watch_provider_name("Ollama")
            mock_update.assert_called_once()


class TestStatusBarWatchMcpCount:
    """Test watch_mcp_count reactive watcher."""

    def test_watch_mcp_count_calls_update(self):
        """watch_mcp_count should call _update_mcp_display."""
        bar = StatusBar()
        with patch.object(bar, "_update_mcp_display") as mock_update:
            bar.watch_mcp_count(3)
            mock_update.assert_called_once()


class TestStatusBarWatchProcessCount:
    """Test watch_process_count reactive watcher."""

    def test_watch_process_count_calls_update(self):
        """watch_process_count should call _update_process_display."""
        bar = StatusBar()
        with patch.object(bar, "_update_process_display") as mock_update:
            bar.watch_process_count(2)
            mock_update.assert_called_once()


class TestStatusBarWatchGitBranch:
    """Test watch_git_branch reactive watcher."""

    def test_watch_git_branch_calls_update(self):
        """watch_git_branch should call _update_git_display."""
        bar = StatusBar()
        with patch.object(bar, "_update_git_display") as mock_update:
            bar.watch_git_branch("main")
            mock_update.assert_called_once()


class TestStatusBarWatchGitDirty:
    """Test watch_git_dirty reactive watcher."""

    def test_watch_git_dirty_calls_update(self):
        """watch_git_dirty should call _update_git_display."""
        bar = StatusBar()
        with patch.object(bar, "_update_git_display") as mock_update:
            bar.watch_git_dirty(True)
            mock_update.assert_called_once()


class TestStatusBarWatchSessionInputTokens:
    """Test watch_session_input_tokens reactive watcher."""

    def test_watch_session_input_tokens_calls_update(self):
        """watch_session_input_tokens should call _update_token_display."""
        bar = StatusBar()
        with patch.object(bar, "_update_token_display") as mock_update:
            bar.watch_session_input_tokens(500)
            mock_update.assert_called_once()


class TestStatusBarWatchSessionOutputTokens:
    """Test watch_session_output_tokens reactive watcher."""

    def test_watch_session_output_tokens_calls_update(self):
        """watch_session_output_tokens should call _update_token_display."""
        bar = StatusBar()
        with patch.object(bar, "_update_token_display") as mock_update:
            bar.watch_session_output_tokens(200)
            mock_update.assert_called_once()


class TestStatusBarWatchSessionCost:
    """Test watch_session_cost reactive watcher."""

    def test_watch_session_cost_calls_update(self):
        """watch_session_cost should call _update_token_display."""
        bar = StatusBar()
        with patch.object(bar, "_update_token_display") as mock_update:
            bar.watch_session_cost(0.05)
            mock_update.assert_called_once()


class TestStatusBarOnMount:
    """Test on_mount lifecycle method."""

    def test_on_mount_calls_update_mode(self):
        """on_mount should call _update_mode_display."""
        bar = StatusBar()
        with (
            patch.object(bar, "_update_mode_display") as mock_mode,
            patch.object(bar, "_update_context_display"),
            patch.object(bar, "_update_provider_display"),
            patch.object(bar, "_update_token_display"),
            patch.object(bar, "_update_process_display"),
        ):
            bar.on_mount()
            mock_mode.assert_called_once()

    def test_on_mount_calls_update_context(self):
        """on_mount should call _update_context_display."""
        bar = StatusBar()
        with (
            patch.object(bar, "_update_mode_display"),
            patch.object(bar, "_update_context_display") as mock_ctx,
            patch.object(bar, "_update_provider_display"),
            patch.object(bar, "_update_token_display"),
            patch.object(bar, "_update_process_display"),
        ):
            bar.on_mount()
            mock_ctx.assert_called_once()

    def test_on_mount_calls_update_provider(self):
        """on_mount should call _update_provider_display."""
        bar = StatusBar()
        with (
            patch.object(bar, "_update_mode_display"),
            patch.object(bar, "_update_context_display"),
            patch.object(bar, "_update_provider_display") as mock_prov,
            patch.object(bar, "_update_token_display"),
            patch.object(bar, "_update_process_display"),
        ):
            bar.on_mount()
            mock_prov.assert_called_once()

    def test_on_mount_calls_update_token(self):
        """on_mount should call _update_token_display."""
        bar = StatusBar()
        with (
            patch.object(bar, "_update_mode_display"),
            patch.object(bar, "_update_context_display"),
            patch.object(bar, "_update_provider_display"),
            patch.object(bar, "_update_token_display") as mock_tok,
            patch.object(bar, "_update_process_display"),
        ):
            bar.on_mount()
            mock_tok.assert_called_once()

    def test_on_mount_calls_update_process(self):
        """on_mount should call _update_process_display."""
        bar = StatusBar()
        with (
            patch.object(bar, "_update_mode_display"),
            patch.object(bar, "_update_context_display"),
            patch.object(bar, "_update_provider_display"),
            patch.object(bar, "_update_token_display"),
            patch.object(bar, "_update_process_display") as mock_proc,
        ):
            bar.on_mount()
            mock_proc.assert_called_once()


class TestStatusBarUpdateModeDisplay:
    """Test _update_mode_display method."""

    def test_update_mode_display_no_widget_no_error(self):
        """Should not raise when widget not mounted."""
        bar = StatusBar()
        bar._update_mode_display()

    def test_update_mode_display_cli(self):
        """CLI mode should show CLI text and add mode-cli class."""
        bar = StatusBar()
        bar.mode = "CLI"

        mock_label = MagicMock(spec=Label)
        bar.query_one = MagicMock(return_value=mock_label)

        bar._update_mode_display()

        mock_label.remove_class.assert_called_with("mode-cli", "mode-ai", "mode-agent")
        mock_label.update.assert_called_once()
        call_arg = mock_label.update.call_args[0][0]
        assert "CLI" in call_arg
        mock_label.add_class.assert_called_with("mode-cli")

    def test_update_mode_display_ai(self):
        """AI mode should show AI text and add mode-ai class."""
        bar = StatusBar()
        bar.mode = "AI"
        bar.agent_mode = False

        mock_label = MagicMock(spec=Label)
        bar.query_one = MagicMock(return_value=mock_label)

        bar._update_mode_display()

        call_arg = mock_label.update.call_args[0][0]
        assert "AI" in call_arg
        mock_label.add_class.assert_called_with("mode-ai")

    def test_update_mode_display_agent(self):
        """Agent mode should show AGENT text and add mode-agent class."""
        bar = StatusBar()
        bar.mode = "AI"
        bar.agent_mode = True

        mock_label = MagicMock(spec=Label)
        bar.query_one = MagicMock(return_value=mock_label)

        bar._update_mode_display()

        call_arg = mock_label.update.call_args[0][0]
        assert "AGENT" in call_arg
        mock_label.add_class.assert_called_with("mode-agent")

    def test_update_mode_display_exception_handled(self):
        """Query exception should be silently caught."""
        bar = StatusBar()
        bar.query_one = MagicMock(side_effect=Exception("No widget"))
        bar._update_mode_display()


class TestStatusBarUpdateContextDisplay:
    """Test _update_context_display method."""

    def test_update_context_display_no_widget_no_error(self):
        """Should not raise when widget not mounted."""
        bar = StatusBar()
        bar._update_context_display()

    def test_update_context_display_low(self):
        """Low context should add context-low class."""
        bar = StatusBar()
        bar.context_chars = 1000
        bar.context_limit = 4000

        mock_label = MagicMock(spec=Label)
        bar.query_one = MagicMock(return_value=mock_label)

        bar._update_context_display()

        mock_label.remove_class.assert_called_with(
            "context-low", "context-medium", "context-high"
        )
        mock_label.add_class.assert_called_with("context-low")

    def test_update_context_display_medium(self):
        """Medium context (50-80%) should add context-medium class."""
        bar = StatusBar()
        bar.context_chars = 2400
        bar.context_limit = 4000

        mock_label = MagicMock(spec=Label)
        bar.query_one = MagicMock(return_value=mock_label)

        bar._update_context_display()

        mock_label.add_class.assert_called_with("context-medium")

    def test_update_context_display_high(self):
        """High context (>=80%) should add context-high class."""
        bar = StatusBar()
        bar.context_chars = 3500
        bar.context_limit = 4000

        mock_label = MagicMock(spec=Label)
        bar.query_one = MagicMock(return_value=mock_label)

        bar._update_context_display()

        mock_label.add_class.assert_called_with("context-high")

    def test_update_context_display_format_tokens(self):
        """Context should be displayed in tokens (chars / 4)."""
        bar = StatusBar()
        bar.context_chars = 4000
        bar.context_limit = 8000

        mock_label = MagicMock(spec=Label)
        bar.query_one = MagicMock(return_value=mock_label)

        bar._update_context_display()

        call_arg = mock_label.update.call_args[0][0]
        assert "1,000" in call_arg

    def test_update_context_display_format_limit_k(self):
        """Large limits should show k notation."""
        bar = StatusBar()
        bar.context_chars = 0
        bar.context_limit = 128000

        mock_label = MagicMock(spec=Label)
        bar.query_one = MagicMock(return_value=mock_label)

        bar._update_context_display()

        call_arg = mock_label.update.call_args[0][0]
        assert "32k" in call_arg

    def test_update_context_display_zero_limit(self):
        """Zero limit should not cause division by zero."""
        bar = StatusBar()
        bar.context_chars = 100
        bar.context_limit = 0

        mock_label = MagicMock(spec=Label)
        bar.query_one = MagicMock(return_value=mock_label)

        bar._update_context_display()

    def test_update_context_display_exception_handled(self):
        """Query exception should be silently caught."""
        bar = StatusBar()
        bar.query_one = MagicMock(side_effect=Exception("No widget"))
        bar._update_context_display()


class TestStatusBarUpdateProviderDisplay:
    """Test _update_provider_display method."""

    def test_update_provider_display_no_widget_no_error(self):
        """Should not raise when widget not mounted."""
        bar = StatusBar()
        bar._update_provider_display()

    def test_update_provider_display_empty_name(self):
        """Empty provider name should show empty text."""
        bar = StatusBar()
        bar.provider_name = ""

        mock_label = MagicMock(spec=Label)
        bar.query_one = MagicMock(return_value=mock_label)

        bar._update_provider_display()

        mock_label.update.assert_called_with("")

    def test_update_provider_display_connected(self):
        """Connected provider should show check icon and add class."""
        bar = StatusBar()
        bar.provider_name = "Ollama"
        bar.provider_status = "connected"

        mock_label = MagicMock(spec=Label)
        bar.query_one = MagicMock(return_value=mock_label)

        bar._update_provider_display()

        call_arg = mock_label.update.call_args[0][0]
        assert "Ollama" in call_arg
        assert "󰄬" in call_arg
        mock_label.add_class.assert_called_with("provider-connected")

    def test_update_provider_display_disconnected(self):
        """Disconnected provider should show X icon and add class."""
        bar = StatusBar()
        bar.provider_name = "OpenAI"
        bar.provider_status = "disconnected"

        mock_label = MagicMock(spec=Label)
        bar.query_one = MagicMock(return_value=mock_label)

        bar._update_provider_display()

        call_arg = mock_label.update.call_args[0][0]
        assert "OpenAI" in call_arg
        assert "󰅖" in call_arg
        mock_label.add_class.assert_called_with("provider-disconnected")

    def test_update_provider_display_unknown(self):
        """Unknown status should add provider-checking class."""
        bar = StatusBar()
        bar.provider_name = "Test"
        bar.provider_status = "unknown"

        mock_label = MagicMock(spec=Label)
        bar.query_one = MagicMock(return_value=mock_label)

        bar._update_provider_display()

        call_arg = mock_label.update.call_args[0][0]
        assert "Test" in call_arg
        mock_label.add_class.assert_called_with("provider-checking")

    def test_update_provider_display_exception_handled(self):
        """Query exception should be silently caught."""
        bar = StatusBar()
        bar.query_one = MagicMock(side_effect=Exception("No widget"))
        bar._update_provider_display()


class TestStatusBarUpdateMcpDisplay:
    """Test _update_mcp_display method."""

    def test_update_mcp_display_no_widget_no_error(self):
        """Should not raise when widget not mounted."""
        bar = StatusBar()
        bar._update_mcp_display()

    def test_update_mcp_display_zero(self):
        """Zero MCP count should show inactive."""
        bar = StatusBar()
        bar.mcp_count = 0

        mock_label = MagicMock(spec=Label)
        bar.query_one = MagicMock(return_value=mock_label)

        bar._update_mcp_display()

        call_arg = mock_label.update.call_args[0][0]
        assert "MCP: 0" in call_arg
        mock_label.add_class.assert_called_with("mcp-inactive")

    def test_update_mcp_display_positive(self):
        """Positive MCP count should show active."""
        bar = StatusBar()
        bar.mcp_count = 3

        mock_label = MagicMock(spec=Label)
        bar.query_one = MagicMock(return_value=mock_label)

        bar._update_mcp_display()

        call_arg = mock_label.update.call_args[0][0]
        assert "MCP: 3" in call_arg
        mock_label.add_class.assert_called_with("mcp-active")

    def test_update_mcp_display_exception_handled(self):
        """Query exception should be silently caught."""
        bar = StatusBar()
        bar.query_one = MagicMock(side_effect=Exception("No widget"))
        bar._update_mcp_display()


class TestStatusBarUpdateProcessDisplay:
    """Test _update_process_display method."""

    def test_update_process_display_no_widget_no_error(self):
        """Should not raise when widget not mounted."""
        bar = StatusBar()
        bar._update_process_display()

    def test_update_process_display_zero(self):
        """Zero process count should show inactive."""
        bar = StatusBar()
        bar.process_count = 0

        mock_label = MagicMock(spec=Label)
        bar.query_one = MagicMock(return_value=mock_label)

        bar._update_process_display()

        call_arg = mock_label.update.call_args[0][0]
        assert "PROC: 0" in call_arg
        mock_label.add_class.assert_called_with("process-inactive")

    def test_update_process_display_positive(self):
        """Positive process count should show active."""
        bar = StatusBar()
        bar.process_count = 2

        mock_label = MagicMock(spec=Label)
        bar.query_one = MagicMock(return_value=mock_label)

        bar._update_process_display()

        call_arg = mock_label.update.call_args[0][0]
        assert "PROC: 2" in call_arg
        mock_label.add_class.assert_called_with("process-active")

    def test_update_process_display_exception_handled(self):
        """Query exception should be silently caught."""
        bar = StatusBar()
        bar.query_one = MagicMock(side_effect=Exception("No widget"))
        bar._update_process_display()


class TestStatusBarUpdateGitDisplay:
    """Test _update_git_display method."""

    def test_update_git_display_no_widget_no_error(self):
        """Should not raise when widget not mounted."""
        bar = StatusBar()
        bar._update_git_display()

    def test_update_git_display_no_branch(self):
        """Empty branch should show empty text."""
        bar = StatusBar()
        bar.git_branch = ""

        mock_label = MagicMock(spec=Label)
        bar.query_one = MagicMock(return_value=mock_label)

        bar._update_git_display()

        mock_label.update.assert_called_with("")

    def test_update_git_display_clean(self):
        """Clean branch should show branch icon and add git-clean class."""
        bar = StatusBar()
        bar.git_branch = "main"
        bar.git_dirty = False

        mock_label = MagicMock(spec=Label)
        bar.query_one = MagicMock(return_value=mock_label)

        bar._update_git_display()

        call_arg = mock_label.update.call_args[0][0]
        assert "main" in call_arg
        assert "" in call_arg
        mock_label.add_class.assert_called_with("git-clean")

    def test_update_git_display_dirty(self):
        """Dirty branch should show dirty icon and add git-dirty class."""
        bar = StatusBar()
        bar.git_branch = "feature/test"
        bar.git_dirty = True

        mock_label = MagicMock(spec=Label)
        bar.query_one = MagicMock(return_value=mock_label)

        bar._update_git_display()

        call_arg = mock_label.update.call_args[0][0]
        assert "feature/test" in call_arg
        assert "±" in call_arg
        mock_label.add_class.assert_called_with("git-dirty")

    def test_update_git_display_exception_handled(self):
        """Query exception should be silently caught."""
        bar = StatusBar()
        bar.query_one = MagicMock(side_effect=Exception("No widget"))
        bar._update_git_display()


class TestStatusBarUpdateTokenDisplay:
    """Test _update_token_display method."""

    def test_update_token_display_no_widget_no_error(self):
        """Should not raise when widget not mounted."""
        bar = StatusBar()
        bar._update_token_display()

    def test_update_token_display_zero_tokens(self):
        """Zero tokens should hide the display."""
        bar = StatusBar()
        bar.session_input_tokens = 0
        bar.session_output_tokens = 0

        mock_indicator = MagicMock(spec=Label)
        mock_sep = MagicMock(spec=Label)

        def query_side_effect(selector, typ):
            if "token-indicator" in selector:
                return mock_indicator
            elif "token-sep" in selector:
                return mock_sep
            raise Exception("Unknown selector")

        bar.query_one = MagicMock(side_effect=query_side_effect)

        bar._update_token_display()

        mock_indicator.update.assert_called_with("")
        assert mock_sep.display is False

    def test_update_token_display_small_tokens(self):
        """Small token count should show raw number."""
        bar = StatusBar()
        bar.session_input_tokens = 500
        bar.session_output_tokens = 200
        bar.session_cost = 0.001

        mock_indicator = MagicMock(spec=Label)
        mock_sep = MagicMock(spec=Label)

        def query_side_effect(selector, typ):
            if "token-indicator" in selector:
                return mock_indicator
            elif "token-sep" in selector:
                return mock_sep
            raise Exception("Unknown selector")

        bar.query_one = MagicMock(side_effect=query_side_effect)

        bar._update_token_display()

        call_arg = mock_indicator.update.call_args[0][0]
        assert "700" in call_arg
        assert mock_sep.display is True

    def test_update_token_display_thousands(self):
        """Thousands of tokens should show k notation."""
        bar = StatusBar()
        bar.session_input_tokens = 5000
        bar.session_output_tokens = 2500
        bar.session_cost = 0.05

        mock_indicator = MagicMock(spec=Label)
        mock_sep = MagicMock(spec=Label)

        def query_side_effect(selector, typ):
            if "token-indicator" in selector:
                return mock_indicator
            elif "token-sep" in selector:
                return mock_sep
            raise Exception("Unknown selector")

        bar.query_one = MagicMock(side_effect=query_side_effect)

        bar._update_token_display()

        call_arg = mock_indicator.update.call_args[0][0]
        assert "7.5k" in call_arg

    def test_update_token_display_millions(self):
        """Millions of tokens should show M notation."""
        bar = StatusBar()
        bar.session_input_tokens = 1000000
        bar.session_output_tokens = 500000
        bar.session_cost = 15.00

        mock_indicator = MagicMock(spec=Label)
        mock_sep = MagicMock(spec=Label)

        def query_side_effect(selector, typ):
            if "token-indicator" in selector:
                return mock_indicator
            elif "token-sep" in selector:
                return mock_sep
            raise Exception("Unknown selector")

        bar.query_one = MagicMock(side_effect=query_side_effect)

        bar._update_token_display()

        call_arg = mock_indicator.update.call_args[0][0]
        assert "1.5M" in call_arg

    def test_update_token_display_cost_format_dollars(self):
        """Cost >= $1 should show 2 decimal places."""
        bar = StatusBar()
        bar.session_input_tokens = 100000
        bar.session_output_tokens = 50000
        bar.session_cost = 2.50

        mock_indicator = MagicMock(spec=Label)
        mock_sep = MagicMock(spec=Label)

        def query_side_effect(selector, typ):
            if "token-indicator" in selector:
                return mock_indicator
            elif "token-sep" in selector:
                return mock_sep
            raise Exception("Unknown selector")

        bar.query_one = MagicMock(side_effect=query_side_effect)

        bar._update_token_display()

        call_arg = mock_indicator.update.call_args[0][0]
        assert "$2.50" in call_arg

    def test_update_token_display_cost_format_cents(self):
        """Cost >= $0.01 should show 2 decimal places."""
        bar = StatusBar()
        bar.session_input_tokens = 1000
        bar.session_output_tokens = 500
        bar.session_cost = 0.05

        mock_indicator = MagicMock(spec=Label)
        mock_sep = MagicMock(spec=Label)

        def query_side_effect(selector, typ):
            if "token-indicator" in selector:
                return mock_indicator
            elif "token-sep" in selector:
                return mock_sep
            raise Exception("Unknown selector")

        bar.query_one = MagicMock(side_effect=query_side_effect)

        bar._update_token_display()

        call_arg = mock_indicator.update.call_args[0][0]
        assert "$0.05" in call_arg

    def test_update_token_display_cost_format_micro(self):
        """Tiny cost should show 4 decimal places."""
        bar = StatusBar()
        bar.session_input_tokens = 100
        bar.session_output_tokens = 50
        bar.session_cost = 0.0005

        mock_indicator = MagicMock(spec=Label)
        mock_sep = MagicMock(spec=Label)

        def query_side_effect(selector, typ):
            if "token-indicator" in selector:
                return mock_indicator
            elif "token-sep" in selector:
                return mock_sep
            raise Exception("Unknown selector")

        bar.query_one = MagicMock(side_effect=query_side_effect)

        bar._update_token_display()

        call_arg = mock_indicator.update.call_args[0][0]
        assert "$0.0005" in call_arg

    def test_update_token_display_cost_zero(self):
        """Zero cost should show $0."""
        bar = StatusBar()
        bar.session_input_tokens = 100
        bar.session_output_tokens = 50
        bar.session_cost = 0.0

        mock_indicator = MagicMock(spec=Label)
        mock_sep = MagicMock(spec=Label)

        def query_side_effect(selector, typ):
            if "token-indicator" in selector:
                return mock_indicator
            elif "token-sep" in selector:
                return mock_sep
            raise Exception("Unknown selector")

        bar.query_one = MagicMock(side_effect=query_side_effect)

        bar._update_token_display()

        call_arg = mock_indicator.update.call_args[0][0]
        assert "$0" in call_arg

    def test_update_token_display_exception_handled(self):
        """Query exception should be silently caught."""
        bar = StatusBar()
        bar.session_input_tokens = 100
        bar.session_output_tokens = 50
        bar.query_one = MagicMock(side_effect=Exception("No widget"))
        bar._update_token_display()


class TestStatusBarReactivePropertyChanges:
    """Test that reactive property changes trigger watchers correctly."""

    def test_mode_change_triggers_watcher(self):
        """Changing mode should trigger watch_mode."""
        bar = StatusBar()
        with patch.object(bar, "watch_mode") as mock_watch:
            bar.watch_mode("AI")
            mock_watch.assert_called_with("AI")

    def test_context_change_triggers_watcher(self):
        """Changing context_chars should trigger watch_context_chars."""
        bar = StatusBar()
        with patch.object(bar, "watch_context_chars") as mock_watch:
            bar.watch_context_chars(5000)
            mock_watch.assert_called_with(5000)


class TestStatusBarEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_context_exactly_50_percent(self):
        """Context at exactly 50% should be medium."""
        bar = StatusBar()
        bar.context_chars = 2000
        bar.context_limit = 4000

        mock_label = MagicMock(spec=Label)
        bar.query_one = MagicMock(return_value=mock_label)

        bar._update_context_display()

        mock_label.add_class.assert_called_with("context-medium")

    def test_context_exactly_80_percent(self):
        """Context at exactly 80% should be high."""
        bar = StatusBar()
        bar.context_chars = 3200
        bar.context_limit = 4000

        mock_label = MagicMock(spec=Label)
        bar.query_one = MagicMock(return_value=mock_label)

        bar._update_context_display()

        mock_label.add_class.assert_called_with("context-high")

    def test_token_count_exactly_1000(self):
        """Exactly 1000 tokens should show k notation."""
        bar = StatusBar()
        bar.session_input_tokens = 700
        bar.session_output_tokens = 300
        bar.session_cost = 0.01

        mock_indicator = MagicMock(spec=Label)
        mock_sep = MagicMock(spec=Label)

        def query_side_effect(selector, typ):
            if "token-indicator" in selector:
                return mock_indicator
            elif "token-sep" in selector:
                return mock_sep
            raise Exception("Unknown selector")

        bar.query_one = MagicMock(side_effect=query_side_effect)

        bar._update_token_display()

        call_arg = mock_indicator.update.call_args[0][0]
        assert "1.0k" in call_arg

    def test_token_count_exactly_1000000(self):
        """Exactly 1M tokens should show M notation."""
        bar = StatusBar()
        bar.session_input_tokens = 600000
        bar.session_output_tokens = 400000
        bar.session_cost = 10.00

        mock_indicator = MagicMock(spec=Label)
        mock_sep = MagicMock(spec=Label)

        def query_side_effect(selector, typ):
            if "token-indicator" in selector:
                return mock_indicator
            elif "token-sep" in selector:
                return mock_sep
            raise Exception("Unknown selector")

        bar.query_one = MagicMock(side_effect=query_side_effect)

        bar._update_token_display()

        call_arg = mock_indicator.update.call_args[0][0]
        assert "1.0M" in call_arg

    def test_context_limit_small_no_k_suffix(self):
        """Small context limit should not have k suffix."""
        bar = StatusBar()
        bar.context_chars = 0
        bar.context_limit = 2000

        mock_label = MagicMock(spec=Label)
        bar.query_one = MagicMock(return_value=mock_label)

        bar._update_context_display()

        call_arg = mock_label.update.call_args[0][0]
        assert "500" in call_arg
        assert "k" not in call_arg.split("/")[1].strip()

    def test_negative_values_handled(self):
        """Negative values should not crash (even if invalid)."""
        bar = StatusBar()
        bar.context_chars = -100
        bar.context_limit = 4000

        mock_label = MagicMock(spec=Label)
        bar.query_one = MagicMock(return_value=mock_label)

        bar._update_context_display()


class TestStatusBarClassManagement:
    """Test CSS class management in update methods."""

    def test_mode_removes_all_mode_classes(self):
        """Mode update should remove all mode classes first."""
        bar = StatusBar()
        bar.mode = "CLI"

        mock_label = MagicMock(spec=Label)
        bar.query_one = MagicMock(return_value=mock_label)

        bar._update_mode_display()

        mock_label.remove_class.assert_called_with("mode-cli", "mode-ai", "mode-agent")

    def test_context_removes_all_context_classes(self):
        """Context update should remove all context classes first."""
        bar = StatusBar()
        bar.context_chars = 100
        bar.context_limit = 4000

        mock_label = MagicMock(spec=Label)
        bar.query_one = MagicMock(return_value=mock_label)

        bar._update_context_display()

        mock_label.remove_class.assert_called_with(
            "context-low", "context-medium", "context-high"
        )

    def test_provider_removes_all_provider_classes(self):
        """Provider update should remove all provider classes first."""
        bar = StatusBar()
        bar.provider_name = "Test"
        bar.provider_status = "connected"

        mock_label = MagicMock(spec=Label)
        bar.query_one = MagicMock(return_value=mock_label)

        bar._update_provider_display()

        mock_label.remove_class.assert_called_with(
            "provider-connected", "provider-disconnected", "provider-checking"
        )

    def test_mcp_removes_all_mcp_classes(self):
        """MCP update should remove all MCP classes first."""
        bar = StatusBar()
        bar.mcp_count = 1

        mock_label = MagicMock(spec=Label)
        bar.query_one = MagicMock(return_value=mock_label)

        bar._update_mcp_display()

        mock_label.remove_class.assert_called_with("mcp-active", "mcp-inactive")

    def test_process_removes_all_process_classes(self):
        """Process update should remove all process classes first."""
        bar = StatusBar()
        bar.process_count = 1

        mock_label = MagicMock(spec=Label)
        bar.query_one = MagicMock(return_value=mock_label)

        bar._update_process_display()

        mock_label.remove_class.assert_called_with("process-active", "process-inactive")

    def test_git_removes_all_git_classes(self):
        """Git update should remove all git classes first."""
        bar = StatusBar()
        bar.git_branch = "main"
        bar.git_dirty = False

        mock_label = MagicMock(spec=Label)
        bar.query_one = MagicMock(return_value=mock_label)

        bar._update_git_display()

        mock_label.remove_class.assert_called_with("git-dirty", "git-clean")


class TestStatusBarNewIndicators:
    """Test new indicators (network, system, keyboard)."""

    def test_default_network_status(self):
        """Default network_status should be 'unknown'."""
        bar = StatusBar()
        assert bar.network_status == "unknown"

    def test_default_memory_percent(self):
        """Default memory_percent should be 0.0."""
        bar = StatusBar()
        assert bar.memory_percent == 0.0

    def test_default_cpu_percent(self):
        """Default cpu_percent should be 0.0."""
        bar = StatusBar()
        assert bar.cpu_percent == 0.0

    def test_default_keyboard_mode(self):
        """Default keyboard_mode should be empty."""
        bar = StatusBar()
        assert bar.keyboard_mode == ""

    def test_default_vim_mode_enabled(self):
        """Default vim_mode_enabled should be False."""
        bar = StatusBar()
        assert bar.vim_mode_enabled is False

    def test_set_network_status(self):
        """Setting network status."""
        bar = StatusBar()
        bar.set_network_status("online")
        assert bar.network_status == "online"

    def test_set_system_stats(self):
        """Setting system stats."""
        bar = StatusBar()
        bar.set_system_stats(50.5, 75.3)
        assert bar.cpu_percent == 50.5
        assert bar.memory_percent == 75.3

    def test_set_keyboard_mode(self):
        """Setting keyboard mode."""
        bar = StatusBar()
        bar.set_keyboard_mode("INSERT")
        assert bar.keyboard_mode == "INSERT"

    def test_set_vim_mode(self):
        """Setting vim mode."""
        bar = StatusBar()
        bar.set_vim_mode(True)
        assert bar.vim_mode_enabled is True


class TestStatusBarWatchNewIndicators:
    """Test watchers for new indicators."""

    def test_watch_network_status_calls_update(self):
        """watch_network_status should call _update_network_display."""
        bar = StatusBar()
        with patch.object(bar, "_update_network_display") as mock_update:
            bar.watch_network_status("online")
            mock_update.assert_called_once()

    def test_watch_memory_percent_calls_update(self):
        """watch_memory_percent should call _update_system_display."""
        bar = StatusBar()
        with patch.object(bar, "_update_system_display") as mock_update:
            bar.watch_memory_percent(50.0)
            mock_update.assert_called_once()

    def test_watch_cpu_percent_calls_update(self):
        """watch_cpu_percent should call _update_system_display."""
        bar = StatusBar()
        with patch.object(bar, "_update_system_display") as mock_update:
            bar.watch_cpu_percent(75.0)
            mock_update.assert_called_once()

    def test_watch_keyboard_mode_calls_update(self):
        """watch_keyboard_mode should call _update_keyboard_display."""
        bar = StatusBar()
        with patch.object(bar, "_update_keyboard_display") as mock_update:
            bar.watch_keyboard_mode("NORMAL")
            mock_update.assert_called_once()

    def test_watch_vim_mode_enabled_calls_update(self):
        """watch_vim_mode_enabled should call _update_keyboard_display."""
        bar = StatusBar()
        with patch.object(bar, "_update_keyboard_display") as mock_update:
            bar.watch_vim_mode_enabled(True)
            mock_update.assert_called_once()


class TestStatusBarUpdateNetworkDisplay:
    """Test _update_network_display method."""

    def test_update_network_display_online(self):
        """Online status should show online icon and class."""
        bar = StatusBar()
        bar.network_status = "online"

        mock_indicator = MagicMock(spec=Static)
        mock_sep = MagicMock(spec=Label)

        def query_side_effect(selector, typ=None):
            if "network-indicator" in selector:
                return mock_indicator
            elif "network-sep" in selector:
                return mock_sep
            raise Exception("Unknown selector")

        bar.query_one = MagicMock(side_effect=query_side_effect)
        bar._update_network_display()

        mock_indicator.add_class.assert_called_with("network-online")
        assert mock_indicator.display is True

    def test_update_network_display_offline(self):
        """Offline status should show offline icon and class."""
        bar = StatusBar()
        bar.network_status = "offline"

        mock_indicator = MagicMock(spec=Static)
        mock_sep = MagicMock(spec=Label)

        def query_side_effect(selector, typ=None):
            if "network-indicator" in selector:
                return mock_indicator
            elif "network-sep" in selector:
                return mock_sep
            raise Exception("Unknown selector")

        bar.query_one = MagicMock(side_effect=query_side_effect)
        bar._update_network_display()

        mock_indicator.add_class.assert_called_with("network-offline")

    def test_update_network_display_unknown_hides(self):
        """Unknown status should hide indicator."""
        bar = StatusBar()
        bar.network_status = "unknown"

        mock_indicator = MagicMock(spec=Static)
        mock_sep = MagicMock(spec=Label)

        def query_side_effect(selector, typ=None):
            if "network-indicator" in selector:
                return mock_indicator
            elif "network-sep" in selector:
                return mock_sep
            raise Exception("Unknown selector")

        bar.query_one = MagicMock(side_effect=query_side_effect)
        bar._update_network_display()

        assert mock_indicator.display is False
        assert mock_sep.display is False


class TestStatusBarUpdateSystemDisplay:
    """Test _update_system_display method."""

    def test_update_system_display_low_usage(self):
        """Low usage should add system-low class."""
        bar = StatusBar()
        bar.cpu_percent = 25.0
        bar.memory_percent = 30.0

        mock_indicator = MagicMock(spec=Static)
        mock_sep = MagicMock(spec=Label)

        def query_side_effect(selector, typ=None):
            if "system-indicator" in selector:
                return mock_indicator
            elif "system-sep" in selector:
                return mock_sep
            raise Exception("Unknown selector")

        bar.query_one = MagicMock(side_effect=query_side_effect)
        bar._update_system_display()

        mock_indicator.add_class.assert_called_with("system-low")

    def test_update_system_display_medium_usage(self):
        """Medium usage should add system-medium class."""
        bar = StatusBar()
        bar.cpu_percent = 60.0
        bar.memory_percent = 55.0

        mock_indicator = MagicMock(spec=Static)
        mock_sep = MagicMock(spec=Label)

        def query_side_effect(selector, typ=None):
            if "system-indicator" in selector:
                return mock_indicator
            elif "system-sep" in selector:
                return mock_sep
            raise Exception("Unknown selector")

        bar.query_one = MagicMock(side_effect=query_side_effect)
        bar._update_system_display()

        mock_indicator.add_class.assert_called_with("system-medium")

    def test_update_system_display_high_usage(self):
        """High usage should add system-high class."""
        bar = StatusBar()
        bar.cpu_percent = 90.0
        bar.memory_percent = 85.0

        mock_indicator = MagicMock(spec=Static)
        mock_sep = MagicMock(spec=Label)

        def query_side_effect(selector, typ=None):
            if "system-indicator" in selector:
                return mock_indicator
            elif "system-sep" in selector:
                return mock_sep
            raise Exception("Unknown selector")

        bar.query_one = MagicMock(side_effect=query_side_effect)
        bar._update_system_display()

        mock_indicator.add_class.assert_called_with("system-high")

    def test_update_system_display_zero_hides(self):
        """Zero values should hide indicator."""
        bar = StatusBar()
        bar.cpu_percent = 0.0
        bar.memory_percent = 0.0

        mock_indicator = MagicMock(spec=Static)
        mock_sep = MagicMock(spec=Label)

        def query_side_effect(selector, typ=None):
            if "system-indicator" in selector:
                return mock_indicator
            elif "system-sep" in selector:
                return mock_sep
            raise Exception("Unknown selector")

        bar.query_one = MagicMock(side_effect=query_side_effect)
        bar._update_system_display()

        assert mock_indicator.display is False
        assert mock_sep.display is False


class TestStatusBarUpdateKeyboardDisplay:
    """Test _update_keyboard_display method."""

    def test_update_keyboard_display_insert(self):
        """Insert mode should show INS and add vim-insert class."""
        bar = StatusBar()
        bar.vim_mode_enabled = True
        bar.keyboard_mode = "INSERT"

        mock_indicator = MagicMock(spec=Static)
        mock_sep = MagicMock(spec=Label)

        def query_side_effect(selector, typ=None):
            if "keyboard-indicator" in selector:
                return mock_indicator
            elif "keyboard-sep" in selector:
                return mock_sep
            raise Exception("Unknown selector")

        bar.query_one = MagicMock(side_effect=query_side_effect)
        bar._update_keyboard_display()

        call_arg = mock_indicator.update.call_args[0][0]
        assert "INS" in call_arg
        mock_indicator.add_class.assert_called_with("vim-insert")

    def test_update_keyboard_display_normal(self):
        """Normal mode should show NOR and add vim-normal class."""
        bar = StatusBar()
        bar.vim_mode_enabled = True
        bar.keyboard_mode = "NORMAL"

        mock_indicator = MagicMock(spec=Static)
        mock_sep = MagicMock(spec=Label)

        def query_side_effect(selector, typ=None):
            if "keyboard-indicator" in selector:
                return mock_indicator
            elif "keyboard-sep" in selector:
                return mock_sep
            raise Exception("Unknown selector")

        bar.query_one = MagicMock(side_effect=query_side_effect)
        bar._update_keyboard_display()

        call_arg = mock_indicator.update.call_args[0][0]
        assert "NOR" in call_arg
        mock_indicator.add_class.assert_called_with("vim-normal")

    def test_update_keyboard_display_visual(self):
        """Visual mode should show VIS and add vim-visual class."""
        bar = StatusBar()
        bar.vim_mode_enabled = True
        bar.keyboard_mode = "VISUAL"

        mock_indicator = MagicMock(spec=Static)
        mock_sep = MagicMock(spec=Label)

        def query_side_effect(selector, typ=None):
            if "keyboard-indicator" in selector:
                return mock_indicator
            elif "keyboard-sep" in selector:
                return mock_sep
            raise Exception("Unknown selector")

        bar.query_one = MagicMock(side_effect=query_side_effect)
        bar._update_keyboard_display()

        call_arg = mock_indicator.update.call_args[0][0]
        assert "VIS" in call_arg
        mock_indicator.add_class.assert_called_with("vim-visual")

    def test_update_keyboard_display_disabled_hides(self):
        """Disabled vim mode should hide indicator."""
        bar = StatusBar()
        bar.vim_mode_enabled = False
        bar.keyboard_mode = "INSERT"

        mock_indicator = MagicMock(spec=Static)
        mock_sep = MagicMock(spec=Label)

        def query_side_effect(selector, typ=None):
            if "keyboard-indicator" in selector:
                return mock_indicator
            elif "keyboard-sep" in selector:
                return mock_sep
            raise Exception("Unknown selector")

        bar.query_one = MagicMock(side_effect=query_side_effect)
        bar._update_keyboard_display()

        assert mock_indicator.display is False
        assert mock_sep.display is False

    def test_update_keyboard_display_empty_mode_hides(self):
        """Empty keyboard mode should hide indicator."""
        bar = StatusBar()
        bar.vim_mode_enabled = True
        bar.keyboard_mode = ""

        mock_indicator = MagicMock(spec=Static)
        mock_sep = MagicMock(spec=Label)

        def query_side_effect(selector, typ=None):
            if "keyboard-indicator" in selector:
                return mock_indicator
            elif "keyboard-sep" in selector:
                return mock_sep
            raise Exception("Unknown selector")

        bar.query_one = MagicMock(side_effect=query_side_effect)
        bar._update_keyboard_display()

        assert mock_indicator.display is False
        assert mock_sep.display is False
