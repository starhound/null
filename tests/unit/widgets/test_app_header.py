"""Tests for widgets/app_header.py - AppHeader widget."""

from unittest.mock import MagicMock, patch

from textual.widgets import Label

from widgets.app_header import AppHeader


class TestAppHeaderInit:
    """Test AppHeader initialization."""

    def test_default_title(self):
        """Default title should be 'Null Terminal'."""
        header = AppHeader()
        assert header._title == "Null Terminal"

    def test_custom_title(self):
        """Custom title should be stored."""
        header = AppHeader(title="Custom Header")
        assert header._title == "Custom Header"

    def test_custom_id(self):
        """Custom ID should be passed to parent."""
        header = AppHeader(id="my-header")
        assert header.id == "my-header"

    def test_custom_name(self):
        """Custom name should be passed to parent."""
        header = AppHeader(name="test-header")
        assert header.name == "test-header"

    def test_custom_classes(self):
        """Custom classes should be passed to parent."""
        header = AppHeader(classes="custom-class")
        assert "custom-class" in header.classes


class TestAppHeaderReactiveDefaults:
    """Test reactive property default values."""

    def test_provider_text_default(self):
        """Default provider_text should be empty string."""
        header = AppHeader()
        assert header.provider_text == ""

    def test_connected_default(self):
        """Default connected should be True."""
        header = AppHeader()
        assert header.connected is True


class TestAppHeaderGetTime:
    """Test time formatting."""

    def test_get_time_format(self):
        """_get_time should return HH:MM:SS format."""
        header = AppHeader()
        time_str = header._get_time()

        parts = time_str.split(":")
        assert len(parts) == 3
        assert len(parts[0]) == 2
        assert len(parts[1]) == 2
        assert len(parts[2]) == 2

    def test_get_time_returns_current_time(self):
        """_get_time should return approximately current time."""
        header = AppHeader()

        with patch("widgets.app_header.datetime") as mock_datetime:
            mock_now = MagicMock()
            mock_now.strftime.return_value = "14:30:45"
            mock_datetime.now.return_value = mock_now

            result = header._get_time()
            assert result == "14:30:45"
            mock_now.strftime.assert_called_once_with("%H:%M:%S")


class TestAppHeaderSetProvider:
    """Test set_provider method."""

    def test_set_provider_only(self):
        """Setting provider without model."""
        header = AppHeader()
        header.set_provider("Ollama")

        assert header.provider_text == "Ollama"
        assert header.connected is True

    def test_set_provider_with_model(self):
        """Setting provider with model."""
        header = AppHeader()
        header.set_provider("OpenAI", model="gpt-4")

        assert header.provider_text == "OpenAI \u00b7 gpt-4"

    def test_set_provider_disconnected(self):
        """Setting provider as disconnected."""
        header = AppHeader()
        header.set_provider("Ollama", connected=False)

        assert header.connected is False

    def test_set_provider_connected(self):
        """Setting provider as connected."""
        header = AppHeader()
        header.connected = False
        header.set_provider("Ollama", connected=True)

        assert header.connected is True

    def test_model_path_shortening(self):
        """Models with path separators should show only last part."""
        header = AppHeader()
        header.set_provider("Huggingface", model="meta-llama/llama-3-70b")

        assert header.provider_text == "Huggingface \u00b7 llama-3-70b"

    def test_long_model_name_truncation(self):
        """Long model names should be truncated."""
        header = AppHeader()
        long_model = "a" * 30
        header.set_provider("Test", model=long_model)

        assert header.provider_text.endswith("...")
        assert len(header.provider_text) <= 35

    def test_model_exactly_25_chars(self):
        """Model with exactly 25 chars should not be truncated."""
        header = AppHeader()
        model_25 = "a" * 25
        header.set_provider("Test", model=model_25)

        assert "..." not in header.provider_text
        assert model_25 in header.provider_text

    def test_model_26_chars_truncated(self):
        """Model with 26 chars should be truncated."""
        header = AppHeader()
        model_26 = "a" * 26
        header.set_provider("Test", model=model_26)

        assert "..." in header.provider_text

    def test_model_path_then_truncation(self):
        """Long model name with path should extract last part then truncate."""
        header = AppHeader()
        long_model = "organization/" + "x" * 30
        header.set_provider("Test", model=long_model)

        assert "organization" not in header.provider_text
        assert "..." in header.provider_text

    def test_empty_model_string(self):
        """Empty model string should behave like no model."""
        header = AppHeader()
        header.set_provider("Ollama", model="")

        assert header.provider_text == "Ollama"


class TestAppHeaderWatchProviderText:
    """Test watch_provider_text reactive watcher."""

    def test_watch_calls_update_left_label(self):
        """Watcher should call _update_left_label."""
        header = AppHeader()

        with patch.object(header, "_update_left_label") as mock_update:
            header.watch_provider_text("new text")
            mock_update.assert_called_once()


class TestAppHeaderWatchConnected:
    """Test watch_connected reactive watcher."""

    def test_watch_connected_true_removes_class(self):
        """Connected=True should remove -disconnected class."""
        header = AppHeader()
        header.add_class("-disconnected")

        header.watch_connected(True)

        assert "-disconnected" not in header.classes

    def test_watch_connected_false_adds_class(self):
        """Connected=False should add -disconnected class."""
        header = AppHeader()

        header.watch_connected(False)

        assert "-disconnected" in header.classes

    def test_watch_connected_calls_update_left_label(self):
        """Watcher should call _update_left_label."""
        header = AppHeader()

        with patch.object(header, "_update_left_label") as mock_update:
            header.watch_connected(True)
            mock_update.assert_called_once()


class TestAppHeaderUpdateLeftLabel:
    """Test _update_left_label method."""

    def test_update_left_label_no_widget_no_error(self):
        """Should not raise when widget not mounted."""
        header = AppHeader()
        header._update_left_label()

    def test_update_left_label_connected_icon(self):
        """Connected state should show connected icon."""
        header = AppHeader()
        header.connected = True
        header.provider_text = "Test Provider"

        mock_label = MagicMock(spec=Label)
        header.query_one = MagicMock(return_value=mock_label)

        header._update_left_label()

        call_arg = mock_label.update.call_args[0][0]
        assert "\U000f012c" in call_arg
        assert "Test Provider" in call_arg

    def test_update_left_label_disconnected_icon(self):
        """Disconnected state should show disconnected icon."""
        header = AppHeader()
        header.connected = False
        header.provider_text = "Test Provider"

        mock_label = MagicMock(spec=Label)
        header.query_one = MagicMock(return_value=mock_label)

        header._update_left_label()

        call_arg = mock_label.update.call_args[0][0]
        assert "\U000f0156" in call_arg

    def test_update_left_label_no_provider_text(self):
        """No provider text should show just icon with space."""
        header = AppHeader()
        header.connected = True
        header.provider_text = ""

        mock_label = MagicMock(spec=Label)
        header.query_one = MagicMock(return_value=mock_label)

        header._update_left_label()

        call_arg = mock_label.update.call_args[0][0]
        assert call_arg == "\U000f012c "

    def test_update_left_label_query_exception_handled(self):
        """Query exception should be silently caught."""
        header = AppHeader()
        header.query_one = MagicMock(side_effect=Exception("No widget"))

        header._update_left_label()


class TestAppHeaderUpdateClock:
    """Test _update_clock method."""

    def test_update_clock_no_widget_no_error(self):
        """Should not raise when clock widget not found."""
        header = AppHeader()
        header._update_clock()

    def test_update_clock_updates_label(self):
        """Should update the clock label with current time."""
        header = AppHeader()

        mock_clock = MagicMock(spec=Label)
        header.query_one = MagicMock(return_value=mock_clock)

        with patch.object(header, "_get_time", return_value="12:34:56"):
            header._update_clock()

        mock_clock.update.assert_called_once_with("12:34:56")

    def test_update_clock_query_exception_handled(self):
        """Query exception should be silently caught."""
        header = AppHeader()
        header.query_one = MagicMock(side_effect=Exception("No widget"))

        header._update_clock()


class TestAppHeaderCompose:
    """Test compose method yields correct widgets."""

    def test_compose_yields_three_labels(self):
        """Compose should yield exactly 3 Label widgets."""
        header = AppHeader()
        children = list(header.compose())

        assert len(children) == 3
        assert all(isinstance(child, Label) for child in children)

    def test_compose_left_label_classes(self):
        """Left label should have correct classes."""
        header = AppHeader()
        children = list(header.compose())

        left_label = children[0]
        assert "header-left" in left_label.classes
        assert "header-icon" in left_label.classes

    def test_compose_title_label_classes(self):
        """Title label should have header-title class."""
        header = AppHeader()
        children = list(header.compose())

        title_label = children[1]
        assert "header-title" in title_label.classes

    def test_compose_title_label_content(self):
        """Title label should show the title."""
        header = AppHeader(title="My App")
        children = list(header.compose())

        title_label = children[1]
        assert str(title_label.render()) == "My App"

    def test_compose_clock_label_classes(self):
        """Clock label should have header-right class."""
        header = AppHeader()
        children = list(header.compose())

        clock_label = children[2]
        assert "header-right" in clock_label.classes

    def test_compose_clock_label_id(self):
        """Clock label should have header-clock id."""
        header = AppHeader()
        children = list(header.compose())

        clock_label = children[2]
        assert clock_label.id == "header-clock"


class TestAppHeaderOnMount:
    """Test on_mount lifecycle method."""

    def test_on_mount_sets_interval(self):
        """on_mount should set up clock interval."""
        header = AppHeader()

        with patch.object(header, "set_interval") as mock_set_interval:
            header.on_mount()

            mock_set_interval.assert_called_once_with(1, header._update_clock)
