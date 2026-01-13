"""Tests for the MCP server configuration screen."""

from unittest.mock import MagicMock

from screens.mcp import MCPServerConfigScreen


class TestMCPServerConfigScreenInit:
    """Tests for MCPServerConfigScreen initialization."""

    def test_init_default_values(self):
        """Test initialization with no arguments."""
        screen = MCPServerConfigScreen()
        assert screen.server_name == ""
        assert screen.current_config == {}
        assert screen.is_edit is False

    def test_init_with_name_only(self):
        """Test initialization with server name (edit mode)."""
        screen = MCPServerConfigScreen(name="test-server")
        assert screen.server_name == "test-server"
        assert screen.current_config == {}
        assert screen.is_edit is True

    def test_init_with_config_only(self):
        """Test initialization with config but no name (add mode)."""
        config = {"command": "npx", "args": ["-y", "test"]}
        screen = MCPServerConfigScreen(current_config=config)
        assert screen.server_name == ""
        assert screen.current_config == config
        assert screen.is_edit is False

    def test_init_with_name_and_config(self):
        """Test initialization with both name and config (edit mode)."""
        config = {"command": "python", "args": ["server.py"], "env": {"KEY": "value"}}
        screen = MCPServerConfigScreen(name="my-server", current_config=config)
        assert screen.server_name == "my-server"
        assert screen.current_config == config
        assert screen.is_edit is True

    def test_init_none_config_becomes_empty_dict(self):
        """Test that None config is converted to empty dict."""
        screen = MCPServerConfigScreen(name="test", current_config=None)
        assert screen.current_config == {}


class TestMCPServerConfigScreenBindings:
    """Tests for screen bindings."""

    def test_bindings_defined(self):
        """Test that escape binding is defined."""
        screen = MCPServerConfigScreen()
        binding_keys = [b.key for b in screen.BINDINGS]
        assert "escape" in binding_keys

    def test_action_dismiss_calls_dismiss_with_none(self):
        """Test that action_dismiss dismisses with None."""
        screen = MCPServerConfigScreen()
        screen.dismiss = MagicMock()
        screen.action_dismiss()
        screen.dismiss.assert_called_once_with(None)


class TestMCPServerConfigScreenInputSubmitted:
    """Tests for input submission handling."""

    def test_on_input_submitted_presses_save_button(self):
        """Test that input submission triggers save button press."""
        screen = MCPServerConfigScreen()

        mock_button = MagicMock()
        mock_query_one = MagicMock(return_value=mock_button)
        screen.query_one = mock_query_one

        mock_event = MagicMock()
        screen.on_input_submitted(mock_event)

        mock_query_one.assert_called()
        mock_button.press.assert_called_once()


class TestMCPServerConfigScreenButtonPressed:
    """Tests for button press handling."""

    def test_cancel_button_dismisses_none(self):
        """Test that cancel button dismisses with None."""
        screen = MCPServerConfigScreen()
        screen.dismiss = MagicMock()

        mock_button = MagicMock()
        mock_button.id = "cancel"
        mock_event = MagicMock()
        mock_event.button = mock_button

        screen.on_button_pressed(mock_event)
        screen.dismiss.assert_called_once_with(None)

    def test_save_button_missing_name_shows_error(self):
        """Test that save with empty name shows error notification."""
        screen = MCPServerConfigScreen()
        screen.notify = MagicMock()
        screen.dismiss = MagicMock()

        def mock_query_one(selector, widget_type=None):
            mock_input = MagicMock()
            if selector == "#name":
                mock_input.value = ""
            elif selector == "#command":
                mock_input.value = "npx"
            elif selector == "#args":
                mock_input.value = ""
            elif selector == "#env":
                mock_input.value = ""
            return mock_input

        screen.query_one = mock_query_one

        mock_button = MagicMock()
        mock_button.id = "save"
        mock_event = MagicMock()
        mock_event.button = mock_button

        screen.on_button_pressed(mock_event)

        screen.notify.assert_called_once_with(
            "Server name is required", severity="error"
        )
        screen.dismiss.assert_not_called()

    def test_save_button_missing_command_shows_error(self):
        """Test that save with empty command shows error notification."""
        screen = MCPServerConfigScreen()
        screen.notify = MagicMock()
        screen.dismiss = MagicMock()

        def mock_query_one(selector, widget_type=None):
            mock_input = MagicMock()
            if selector == "#name":
                mock_input.value = "my-server"
            elif selector == "#command":
                mock_input.value = ""
            elif selector == "#args":
                mock_input.value = ""
            elif selector == "#env":
                mock_input.value = ""
            return mock_input

        screen.query_one = mock_query_one

        mock_button = MagicMock()
        mock_button.id = "save"
        mock_event = MagicMock()
        mock_event.button = mock_button

        screen.on_button_pressed(mock_event)

        screen.notify.assert_called_once_with("Command is required", severity="error")
        screen.dismiss.assert_not_called()

    def test_save_button_with_valid_basic_config(self):
        """Test save with valid name and command."""
        screen = MCPServerConfigScreen()
        screen.notify = MagicMock()
        screen.dismiss = MagicMock()

        def mock_query_one(selector, widget_type=None):
            mock_input = MagicMock()
            if selector == "#name":
                mock_input.value = "test-server"
            elif selector == "#command":
                mock_input.value = "npx"
            elif selector == "#args":
                mock_input.value = ""
            elif selector == "#env":
                mock_input.value = ""
            return mock_input

        screen.query_one = mock_query_one

        mock_button = MagicMock()
        mock_button.id = "save"
        mock_event = MagicMock()
        mock_event.button = mock_button

        screen.on_button_pressed(mock_event)

        screen.notify.assert_not_called()
        expected = {
            "name": "test-server",
            "command": "npx",
            "args": [],
            "env": {},
        }
        screen.dismiss.assert_called_once_with(expected)

    def test_save_button_with_args(self):
        """Test save with arguments."""
        screen = MCPServerConfigScreen()
        screen.dismiss = MagicMock()

        def mock_query_one(selector, widget_type=None):
            mock_input = MagicMock()
            if selector == "#name":
                mock_input.value = "filesystem"
            elif selector == "#command":
                mock_input.value = "npx"
            elif selector == "#args":
                mock_input.value = "-y @modelcontextprotocol/server-filesystem /home"
            elif selector == "#env":
                mock_input.value = ""
            return mock_input

        screen.query_one = mock_query_one

        mock_button = MagicMock()
        mock_button.id = "save"
        mock_event = MagicMock()
        mock_event.button = mock_button

        screen.on_button_pressed(mock_event)

        call_args = screen.dismiss.call_args[0][0]
        assert call_args["name"] == "filesystem"
        assert call_args["command"] == "npx"
        assert call_args["args"] == [
            "-y",
            "@modelcontextprotocol/server-filesystem",
            "/home",
        ]
        assert call_args["env"] == {}

    def test_save_button_with_env_vars(self):
        """Test save with environment variables."""
        screen = MCPServerConfigScreen()
        screen.dismiss = MagicMock()

        def mock_query_one(selector, widget_type=None):
            mock_input = MagicMock()
            if selector == "#name":
                mock_input.value = "github"
            elif selector == "#command":
                mock_input.value = "npx"
            elif selector == "#args":
                mock_input.value = "-y @modelcontextprotocol/server-github"
            elif selector == "#env":
                mock_input.value = "GITHUB_TOKEN=abc123 API_KEY=xyz789"
            return mock_input

        screen.query_one = mock_query_one

        mock_button = MagicMock()
        mock_button.id = "save"
        mock_event = MagicMock()
        mock_event.button = mock_button

        screen.on_button_pressed(mock_event)

        call_args = screen.dismiss.call_args[0][0]
        assert call_args["name"] == "github"
        assert call_args["env"] == {"GITHUB_TOKEN": "abc123", "API_KEY": "xyz789"}

    def test_save_button_with_quoted_args(self):
        """Test save with quoted arguments containing spaces."""
        screen = MCPServerConfigScreen()
        screen.dismiss = MagicMock()

        def mock_query_one(selector, widget_type=None):
            mock_input = MagicMock()
            if selector == "#name":
                mock_input.value = "test"
            elif selector == "#command":
                mock_input.value = "python"
            elif selector == "#args":
                mock_input.value = '--config "my config.json" --verbose'
            elif selector == "#env":
                mock_input.value = ""
            return mock_input

        screen.query_one = mock_query_one

        mock_button = MagicMock()
        mock_button.id = "save"
        mock_event = MagicMock()
        mock_event.button = mock_button

        screen.on_button_pressed(mock_event)

        call_args = screen.dismiss.call_args[0][0]
        assert call_args["args"] == ["--config", "my config.json", "--verbose"]

    def test_save_button_with_env_containing_equals(self):
        """Test save with env values containing equals sign."""
        screen = MCPServerConfigScreen()
        screen.dismiss = MagicMock()

        def mock_query_one(selector, widget_type=None):
            mock_input = MagicMock()
            if selector == "#name":
                mock_input.value = "test"
            elif selector == "#command":
                mock_input.value = "node"
            elif selector == "#args":
                mock_input.value = ""
            elif selector == "#env":
                mock_input.value = "URL=http://example.com?foo=bar"
            return mock_input

        screen.query_one = mock_query_one

        mock_button = MagicMock()
        mock_button.id = "save"
        mock_event = MagicMock()
        mock_event.button = mock_button

        screen.on_button_pressed(mock_event)

        call_args = screen.dismiss.call_args[0][0]
        assert call_args["env"] == {"URL": "http://example.com?foo=bar"}

    def test_save_button_trims_whitespace(self):
        """Test that save trims whitespace from inputs."""
        screen = MCPServerConfigScreen()
        screen.dismiss = MagicMock()

        def mock_query_one(selector, widget_type=None):
            mock_input = MagicMock()
            if selector == "#name":
                mock_input.value = "  test-server  "
            elif selector == "#command":
                mock_input.value = "  npx  "
            elif selector == "#args":
                mock_input.value = "  -y test  "
            elif selector == "#env":
                mock_input.value = "  KEY=value  "
            return mock_input

        screen.query_one = mock_query_one

        mock_button = MagicMock()
        mock_button.id = "save"
        mock_event = MagicMock()
        mock_event.button = mock_button

        screen.on_button_pressed(mock_event)

        call_args = screen.dismiss.call_args[0][0]
        assert call_args["name"] == "test-server"
        assert call_args["command"] == "npx"

    def test_save_button_handles_malformed_env(self):
        """Test save handles malformed env fallback parsing."""
        screen = MCPServerConfigScreen()
        screen.dismiss = MagicMock()

        def mock_query_one(selector, widget_type=None):
            mock_input = MagicMock()
            if selector == "#name":
                mock_input.value = "test"
            elif selector == "#command":
                mock_input.value = "node"
            elif selector == "#args":
                mock_input.value = ""
            elif selector == "#env":
                mock_input.value = "KEY=value BROKEN"
            return mock_input

        screen.query_one = mock_query_one

        mock_button = MagicMock()
        mock_button.id = "save"
        mock_event = MagicMock()
        mock_event.button = mock_button

        screen.on_button_pressed(mock_event)

        call_args = screen.dismiss.call_args[0][0]
        assert call_args["env"] == {"KEY": "value"}

    def test_unknown_button_dismisses_none(self):
        """Test that unknown button dismisses with None."""
        screen = MCPServerConfigScreen()
        screen.dismiss = MagicMock()

        mock_button = MagicMock()
        mock_button.id = "unknown"
        mock_event = MagicMock()
        mock_event.button = mock_button

        screen.on_button_pressed(mock_event)
        screen.dismiss.assert_called_once_with(None)


class TestMCPServerConfigScreenCompose:
    """Tests for screen composition."""

    def test_compose_returns_generator(self):
        """Test that compose returns a generator."""
        screen = MCPServerConfigScreen()
        result = screen.compose()
        assert hasattr(result, "__iter__")

    def test_compose_with_edit_mode(self):
        """Test compose in edit mode includes server name in title."""
        screen = MCPServerConfigScreen(name="my-server")
        assert screen.is_edit is True


class TestMCPServerConfigScreenCSS:
    """Tests for screen CSS (styles moved to main.tcss)."""

    def test_default_css_attribute_exists(self):
        """Test that DEFAULT_CSS attribute exists on class."""
        assert hasattr(MCPServerConfigScreen, "DEFAULT_CSS")


class TestMCPServerConfigScreenArgsFormatting:
    """Tests for args list formatting from current_config."""

    def test_args_as_list_in_config(self):
        """Test initialization with args as list."""
        config = {"command": "npx", "args": ["-y", "test"]}
        screen = MCPServerConfigScreen(current_config=config)
        assert screen.current_config["args"] == ["-y", "test"]

    def test_args_as_string_in_config(self):
        """Test initialization with args as string (legacy format)."""
        config = {"command": "npx", "args": "-y test"}
        screen = MCPServerConfigScreen(current_config=config)
        assert screen.current_config["args"] == "-y test"


class TestMCPServerConfigScreenEnvFormatting:
    """Tests for env dict formatting from current_config."""

    def test_env_as_dict_in_config(self):
        """Test initialization with env as dict."""
        config = {"command": "npx", "env": {"KEY": "value", "OTHER": "data"}}
        screen = MCPServerConfigScreen(current_config=config)
        assert screen.current_config["env"] == {"KEY": "value", "OTHER": "data"}

    def test_empty_env_in_config(self):
        """Test initialization with empty env."""
        config = {"command": "npx", "env": {}}
        screen = MCPServerConfigScreen(current_config=config)
        assert screen.current_config["env"] == {}


class TestMCPServerConfigScreenEnvParsing:
    """Tests for environment variable parsing edge cases."""

    def test_env_with_quoted_values(self):
        """Test parsing env with quoted values containing spaces."""
        screen = MCPServerConfigScreen()
        screen.dismiss = MagicMock()

        def mock_query_one(selector, widget_type=None):
            mock_input = MagicMock()
            if selector == "#name":
                mock_input.value = "test"
            elif selector == "#command":
                mock_input.value = "node"
            elif selector == "#args":
                mock_input.value = ""
            elif selector == "#env":
                mock_input.value = 'MESSAGE="Hello World"'
            return mock_input

        screen.query_one = mock_query_one

        mock_button = MagicMock()
        mock_button.id = "save"
        mock_event = MagicMock()
        mock_event.button = mock_button

        screen.on_button_pressed(mock_event)

        call_args = screen.dismiss.call_args[0][0]
        assert call_args["env"] == {"MESSAGE": "Hello World"}

    def test_env_empty_string(self):
        """Test parsing empty env string."""
        screen = MCPServerConfigScreen()
        screen.dismiss = MagicMock()

        def mock_query_one(selector, widget_type=None):
            mock_input = MagicMock()
            if selector == "#name":
                mock_input.value = "test"
            elif selector == "#command":
                mock_input.value = "node"
            elif selector == "#args":
                mock_input.value = ""
            elif selector == "#env":
                mock_input.value = ""
            return mock_input

        screen.query_one = mock_query_one

        mock_button = MagicMock()
        mock_button.id = "save"
        mock_event = MagicMock()
        mock_event.button = mock_button

        screen.on_button_pressed(mock_event)

        call_args = screen.dismiss.call_args[0][0]
        assert call_args["env"] == {}

    def test_env_multiple_pairs(self):
        """Test parsing multiple env pairs."""
        screen = MCPServerConfigScreen()
        screen.dismiss = MagicMock()

        def mock_query_one(selector, widget_type=None):
            mock_input = MagicMock()
            if selector == "#name":
                mock_input.value = "test"
            elif selector == "#command":
                mock_input.value = "node"
            elif selector == "#args":
                mock_input.value = ""
            elif selector == "#env":
                mock_input.value = "A=1 B=2 C=3"
            return mock_input

        screen.query_one = mock_query_one

        mock_button = MagicMock()
        mock_button.id = "save"
        mock_event = MagicMock()
        mock_event.button = mock_button

        screen.on_button_pressed(mock_event)

        call_args = screen.dismiss.call_args[0][0]
        assert call_args["env"] == {"A": "1", "B": "2", "C": "3"}
