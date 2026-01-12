"""Tests for widgets/ssh_terminal.py - SSHTerminal widget."""

from asyncio import Task
from unittest.mock import AsyncMock, MagicMock, PropertyMock, patch

import pytest
from textual.geometry import Size
from textual.strip import Strip

from widgets.ssh_terminal import SSHTerminal


@pytest.fixture
def mock_ssh_session():
    """Create a mock SSH session."""
    session = MagicMock()
    session.start_shell = AsyncMock(
        return_value=(MagicMock(), MagicMock(), MagicMock())
    )
    session.resize = MagicMock()
    return session


@pytest.fixture
def mock_pyte_screen():
    """Create a mock pyte screen."""
    screen = MagicMock()
    screen.lines = 24
    screen.buffer = {}
    screen.resize = MagicMock()
    return screen


@pytest.fixture
def mock_pyte_stream():
    """Create a mock pyte stream."""
    stream = MagicMock()
    stream.feed = MagicMock()
    return stream


class TestSSHTerminalInit:
    """Test SSHTerminal initialization."""

    def test_init_with_session(self, mock_ssh_session):
        """Terminal should store session reference."""
        terminal = SSHTerminal(session=mock_ssh_session)
        assert terminal.session is mock_ssh_session

    def test_init_with_name(self, mock_ssh_session):
        """Custom name should be passed to parent."""
        terminal = SSHTerminal(session=mock_ssh_session, name="test-terminal")
        assert terminal.name == "test-terminal"

    def test_init_with_id(self, mock_ssh_session):
        """Custom ID should be passed to parent."""
        terminal = SSHTerminal(session=mock_ssh_session, id="ssh-term")
        assert terminal.id == "ssh-term"

    def test_init_with_classes(self, mock_ssh_session):
        """Custom classes should be passed to parent."""
        terminal = SSHTerminal(session=mock_ssh_session, classes="custom-class")
        assert "custom-class" in terminal.classes

    def test_init_creates_pyte_screen(self, mock_ssh_session):
        """Initialization should create pyte screen with default size."""
        with patch("widgets.ssh_terminal.pyte") as mock_pyte:
            mock_screen = MagicMock()
            mock_pyte.Screen.return_value = mock_screen

            terminal = SSHTerminal(session=mock_ssh_session)

            mock_pyte.Screen.assert_called_once_with(80, 24)
            assert terminal.pyte_screen is mock_screen

    def test_init_creates_pyte_stream(self, mock_ssh_session):
        """Initialization should create pyte stream connected to screen."""
        with patch("widgets.ssh_terminal.pyte") as mock_pyte:
            mock_screen = MagicMock()
            mock_stream = MagicMock()
            mock_pyte.Screen.return_value = mock_screen
            mock_pyte.Stream.return_value = mock_stream

            terminal = SSHTerminal(session=mock_ssh_session)

            mock_pyte.Stream.assert_called_once_with(mock_screen)
            assert terminal.pyte_stream is mock_stream

    def test_init_listen_task_is_none(self, mock_ssh_session):
        """Listen task should be None initially."""
        terminal = SSHTerminal(session=mock_ssh_session)
        assert terminal._listen_task is None

    def test_init_stdin_is_none(self, mock_ssh_session):
        """Stdin should be None initially."""
        terminal = SSHTerminal(session=mock_ssh_session)
        assert terminal._stdin is None

    def test_init_connected_is_false(self, mock_ssh_session):
        """Connected flag should be False initially."""
        terminal = SSHTerminal(session=mock_ssh_session)
        assert terminal._connected is False


class TestSSHTerminalDefaultCSS:
    """Test default CSS properties."""

    def test_default_css_contains_height(self, mock_ssh_session):
        """Default CSS should set height to 1fr."""
        assert "height: 1fr" in SSHTerminal.DEFAULT_CSS

    def test_default_css_contains_background(self, mock_ssh_session):
        """Default CSS should set background to black."""
        assert "background: black" in SSHTerminal.DEFAULT_CSS

    def test_default_css_contains_color(self, mock_ssh_session):
        """Default CSS should set color to white."""
        assert "color: white" in SSHTerminal.DEFAULT_CSS

    def test_default_css_contains_overflow(self, mock_ssh_session):
        """Default CSS should set overflow to hidden."""
        assert "overflow: hidden" in SSHTerminal.DEFAULT_CSS


class TestSSHTerminalOnMount:
    """Test on_mount lifecycle method."""

    def test_on_mount_calls_after_refresh(self, mock_ssh_session):
        """on_mount should schedule _start_ssh after refresh."""
        terminal = SSHTerminal(session=mock_ssh_session)

        with patch.object(terminal, "call_after_refresh") as mock_call_after:
            terminal.on_mount()
            mock_call_after.assert_called_once_with(terminal._start_ssh)


class TestSSHTerminalOnResize:
    """Test on_resize event handler."""

    def test_on_resize_updates_pyte_screen(self, mock_ssh_session):
        """Resize should update pyte screen dimensions."""
        terminal = SSHTerminal(session=mock_ssh_session)
        terminal.pyte_screen = MagicMock()
        terminal.refresh = MagicMock()

        event = MagicMock()
        event.size = (100, 40)

        terminal.on_resize(event)

        terminal.pyte_screen.resize.assert_called_once_with(40, 100)

    def test_on_resize_sends_to_session_when_connected(self, mock_ssh_session):
        """Resize should send to SSH session when connected."""
        terminal = SSHTerminal(session=mock_ssh_session)
        terminal.pyte_screen = MagicMock()
        terminal._connected = True
        terminal.refresh = MagicMock()

        event = MagicMock()
        event.size = (120, 50)

        terminal.on_resize(event)

        mock_ssh_session.resize.assert_called_once_with(120, 50)

    def test_on_resize_no_session_call_when_disconnected(self, mock_ssh_session):
        """Resize should not call session when disconnected."""
        terminal = SSHTerminal(session=mock_ssh_session)
        terminal.pyte_screen = MagicMock()
        terminal._connected = False
        terminal.refresh = MagicMock()

        event = MagicMock()
        event.size = (80, 24)

        terminal.on_resize(event)

        mock_ssh_session.resize.assert_not_called()

    def test_on_resize_calls_refresh(self, mock_ssh_session):
        """Resize should trigger refresh."""
        terminal = SSHTerminal(session=mock_ssh_session)
        terminal.pyte_screen = MagicMock()
        terminal.refresh = MagicMock()

        event = MagicMock()
        event.size = (80, 24)

        terminal.on_resize(event)

        terminal.refresh.assert_called_once()


class TestSSHTerminalStartSSH:
    """Test _start_ssh async method."""

    @pytest.mark.asyncio
    async def test_start_ssh_calls_session_start_shell(self, mock_ssh_session):
        """_start_ssh should call session.start_shell."""
        terminal = SSHTerminal(session=mock_ssh_session)

        with patch.object(
            type(terminal), "size", new_callable=PropertyMock
        ) as mock_size:
            mock_size.return_value = Size(100, 40)
            await terminal._start_ssh()

        mock_ssh_session.start_shell.assert_called_once_with(cols=100, lines=40)

    @pytest.mark.asyncio
    async def test_start_ssh_stores_stdin(self, mock_ssh_session):
        """_start_ssh should store stdin writer."""
        stdin = MagicMock()
        mock_ssh_session.start_shell.return_value = (stdin, MagicMock(), MagicMock())

        terminal = SSHTerminal(session=mock_ssh_session)

        with patch.object(
            type(terminal), "size", new_callable=PropertyMock
        ) as mock_size:
            mock_size.return_value = Size(80, 24)
            await terminal._start_ssh()

        assert terminal._stdin is stdin

    @pytest.mark.asyncio
    async def test_start_ssh_sets_connected_true(self, mock_ssh_session):
        """_start_ssh should set _connected to True on success."""
        terminal = SSHTerminal(session=mock_ssh_session)

        with patch.object(
            type(terminal), "size", new_callable=PropertyMock
        ) as mock_size:
            mock_size.return_value = Size(80, 24)
            await terminal._start_ssh()

        assert terminal._connected is True

    @pytest.mark.asyncio
    async def test_start_ssh_creates_read_loop_task(self, mock_ssh_session):
        """_start_ssh should create a task for read_loop."""
        stdout = MagicMock()
        mock_ssh_session.start_shell.return_value = (MagicMock(), stdout, MagicMock())

        terminal = SSHTerminal(session=mock_ssh_session)

        with patch("widgets.ssh_terminal.asyncio.create_task") as mock_create_task:
            mock_task = MagicMock(spec=Task)
            mock_create_task.return_value = mock_task

            with patch.object(
                type(terminal), "size", new_callable=PropertyMock
            ) as mock_size:
                mock_size.return_value = Size(80, 24)
                await terminal._start_ssh()

            assert terminal._listen_task is mock_task

    @pytest.mark.asyncio
    async def test_start_ssh_notifies_on_error(self, mock_ssh_session):
        """_start_ssh should notify on connection error."""
        mock_ssh_session.start_shell.side_effect = Exception("Connection failed")

        terminal = SSHTerminal(session=mock_ssh_session)
        terminal.notify = MagicMock()

        with patch.object(
            type(terminal), "size", new_callable=PropertyMock
        ) as mock_size:
            mock_size.return_value = Size(80, 24)
            await terminal._start_ssh()

        terminal.notify.assert_called_once()
        assert "SSH Error" in terminal.notify.call_args[0][0]
        assert terminal.notify.call_args[1]["severity"] == "error"


class TestSSHTerminalReadLoop:
    """Test _read_loop async method."""

    @pytest.mark.asyncio
    async def test_read_loop_feeds_data_to_pyte(self, mock_ssh_session):
        """_read_loop should feed received data to pyte stream."""
        terminal = SSHTerminal(session=mock_ssh_session)
        terminal.pyte_stream = MagicMock()
        terminal.refresh = MagicMock()

        stdout = AsyncMock()
        stdout.read.side_effect = ["test data", ""]  # Second call returns empty to exit

        await terminal._read_loop(stdout)

        terminal.pyte_stream.feed.assert_called_once_with("test data")

    @pytest.mark.asyncio
    async def test_read_loop_calls_refresh_after_data(self, mock_ssh_session):
        """_read_loop should refresh widget after receiving data."""
        terminal = SSHTerminal(session=mock_ssh_session)
        terminal.pyte_stream = MagicMock()
        terminal.refresh = MagicMock()

        stdout = AsyncMock()
        stdout.read.side_effect = ["data", ""]

        await terminal._read_loop(stdout)

        terminal.refresh.assert_called()

    @pytest.mark.asyncio
    async def test_read_loop_exits_on_empty_data(self, mock_ssh_session):
        """_read_loop should exit when receiving empty data."""
        terminal = SSHTerminal(session=mock_ssh_session)
        terminal.pyte_stream = MagicMock()
        terminal.refresh = MagicMock()

        stdout = AsyncMock()
        stdout.read.return_value = ""

        await terminal._read_loop(stdout)

        terminal.pyte_stream.feed.assert_not_called()

    @pytest.mark.asyncio
    async def test_read_loop_sets_disconnected_on_exception(self, mock_ssh_session):
        """_read_loop should set _connected to False on exception."""
        terminal = SSHTerminal(session=mock_ssh_session)
        terminal._connected = True
        terminal.notify = MagicMock()

        stdout = AsyncMock()
        stdout.read.side_effect = Exception("Connection lost")

        await terminal._read_loop(stdout)

        assert terminal._connected is False

    @pytest.mark.asyncio
    async def test_read_loop_notifies_on_exception(self, mock_ssh_session):
        """_read_loop should notify user on connection exception."""
        terminal = SSHTerminal(session=mock_ssh_session)
        terminal._connected = True
        terminal.notify = MagicMock()

        stdout = AsyncMock()
        stdout.read.side_effect = Exception("Network error")

        await terminal._read_loop(stdout)

        terminal.notify.assert_called_once()
        assert "Connection lost" in terminal.notify.call_args[0][0]


class TestSSHTerminalOnKey:
    """Test on_key event handler."""

    def test_on_key_ignores_when_disconnected(self, mock_ssh_session):
        """on_key should do nothing when not connected."""
        terminal = SSHTerminal(session=mock_ssh_session)
        terminal._connected = False
        terminal._stdin = MagicMock()

        event = MagicMock()
        event.character = "a"
        event.key = "a"

        terminal.on_key(event)

        terminal._stdin.write.assert_not_called()

    def test_on_key_ignores_when_no_stdin(self, mock_ssh_session):
        """on_key should do nothing when stdin is None."""
        terminal = SSHTerminal(session=mock_ssh_session)
        terminal._connected = True
        terminal._stdin = None

        event = MagicMock()
        event.character = "a"
        event.key = "a"

        # Should not raise
        terminal.on_key(event)

    def test_on_key_writes_character(self, mock_ssh_session):
        """on_key should write regular characters to stdin."""
        terminal = SSHTerminal(session=mock_ssh_session)
        terminal._connected = True
        terminal._stdin = MagicMock()

        event = MagicMock()
        event.character = "x"
        event.key = "x"

        terminal.on_key(event)

        terminal._stdin.write.assert_called_once_with("x")

    def test_on_key_enter_sends_carriage_return(self, mock_ssh_session):
        """Enter key should send carriage return."""
        terminal = SSHTerminal(session=mock_ssh_session)
        terminal._connected = True
        terminal._stdin = MagicMock()

        event = MagicMock()
        event.character = None
        event.key = "enter"

        terminal.on_key(event)

        terminal._stdin.write.assert_called_once_with("\r")

    def test_on_key_backspace_sends_delete(self, mock_ssh_session):
        """Backspace key should send DEL character."""
        terminal = SSHTerminal(session=mock_ssh_session)
        terminal._connected = True
        terminal._stdin = MagicMock()

        event = MagicMock()
        event.character = None
        event.key = "backspace"

        terminal.on_key(event)

        terminal._stdin.write.assert_called_once_with("\x7f")

    def test_on_key_tab_sends_tab(self, mock_ssh_session):
        """Tab key should send tab character."""
        terminal = SSHTerminal(session=mock_ssh_session)
        terminal._connected = True
        terminal._stdin = MagicMock()

        event = MagicMock()
        event.character = None
        event.key = "tab"

        terminal.on_key(event)

        terminal._stdin.write.assert_called_once_with("\t")

    def test_on_key_escape_sends_escape(self, mock_ssh_session):
        """Escape key should send escape character."""
        terminal = SSHTerminal(session=mock_ssh_session)
        terminal._connected = True
        terminal._stdin = MagicMock()

        event = MagicMock()
        event.character = None
        event.key = "escape"

        terminal.on_key(event)

        terminal._stdin.write.assert_called_once_with("\x1b")

    def test_on_key_up_sends_ansi_sequence(self, mock_ssh_session):
        """Up arrow should send ANSI escape sequence."""
        terminal = SSHTerminal(session=mock_ssh_session)
        terminal._connected = True
        terminal._stdin = MagicMock()

        event = MagicMock()
        event.character = None
        event.key = "up"

        terminal.on_key(event)

        terminal._stdin.write.assert_called_once_with("\x1b[A")

    def test_on_key_down_sends_ansi_sequence(self, mock_ssh_session):
        """Down arrow should send ANSI escape sequence."""
        terminal = SSHTerminal(session=mock_ssh_session)
        terminal._connected = True
        terminal._stdin = MagicMock()

        event = MagicMock()
        event.character = None
        event.key = "down"

        terminal.on_key(event)

        terminal._stdin.write.assert_called_once_with("\x1b[B")

    def test_on_key_right_sends_ansi_sequence(self, mock_ssh_session):
        """Right arrow should send ANSI escape sequence."""
        terminal = SSHTerminal(session=mock_ssh_session)
        terminal._connected = True
        terminal._stdin = MagicMock()

        event = MagicMock()
        event.character = None
        event.key = "right"

        terminal.on_key(event)

        terminal._stdin.write.assert_called_once_with("\x1b[C")

    def test_on_key_left_sends_ansi_sequence(self, mock_ssh_session):
        """Left arrow should send ANSI escape sequence."""
        terminal = SSHTerminal(session=mock_ssh_session)
        terminal._connected = True
        terminal._stdin = MagicMock()

        event = MagicMock()
        event.character = None
        event.key = "left"

        terminal.on_key(event)

        terminal._stdin.write.assert_called_once_with("\x1b[D")

    def test_on_key_no_write_when_char_is_none(self, mock_ssh_session):
        """No write when character is None and key not mapped."""
        terminal = SSHTerminal(session=mock_ssh_session)
        terminal._connected = True
        terminal._stdin = MagicMock()

        event = MagicMock()
        event.character = None
        event.key = "f12"  # Unmapped key

        terminal.on_key(event)

        terminal._stdin.write.assert_not_called()


class TestSSHTerminalRenderLine:
    """Test render_line method."""

    def test_render_line_returns_blank_for_out_of_bounds(self, mock_ssh_session):
        """render_line should return blank strip for lines beyond screen."""
        terminal = SSHTerminal(session=mock_ssh_session)
        terminal.pyte_screen = MagicMock()
        terminal.pyte_screen.lines = 24
        terminal._size = Size(80, 24)

        result = terminal.render_line(30)

        assert isinstance(result, Strip)

    def test_render_line_returns_strip(self, mock_ssh_session):
        """render_line should return a Strip object."""
        terminal = SSHTerminal(session=mock_ssh_session)
        terminal.pyte_screen = MagicMock()
        terminal.pyte_screen.lines = 24
        terminal.pyte_screen.buffer = {0: {}}
        terminal._size = Size(80, 24)

        result = terminal.render_line(0)

        assert isinstance(result, Strip)

    def test_render_line_handles_empty_buffer_line(self, mock_ssh_session):
        """render_line should handle empty buffer lines."""
        terminal = SSHTerminal(session=mock_ssh_session)
        terminal.pyte_screen = MagicMock()
        terminal.pyte_screen.lines = 24
        terminal.pyte_screen.buffer = {0: {}}
        terminal._size = Size(80, 24)

        result = terminal.render_line(0)

        assert isinstance(result, Strip)

    def test_render_line_with_character_data(self, mock_ssh_session):
        """render_line should render character data from buffer."""
        terminal = SSHTerminal(session=mock_ssh_session)
        terminal.pyte_screen = MagicMock()
        terminal.pyte_screen.lines = 24

        # Create mock character
        mock_char = MagicMock()
        mock_char.data = "A"
        mock_char.fg = "white"
        mock_char.bg = "black"
        mock_char.bold = False
        mock_char.italics = False
        mock_char.reverse = False

        terminal.pyte_screen.buffer = {0: {0: mock_char}}
        terminal._size = Size(80, 24)

        result = terminal.render_line(0)

        assert isinstance(result, Strip)

    def test_render_line_with_default_colors(self, mock_ssh_session):
        """render_line should handle default color values."""
        terminal = SSHTerminal(session=mock_ssh_session)
        terminal.pyte_screen = MagicMock()
        terminal.pyte_screen.lines = 24

        mock_char = MagicMock()
        mock_char.data = "X"
        mock_char.fg = "default"
        mock_char.bg = "default"
        mock_char.bold = False
        mock_char.italics = False
        mock_char.reverse = False

        terminal.pyte_screen.buffer = {0: {0: mock_char}}
        terminal._size = Size(80, 24)

        result = terminal.render_line(0)

        assert isinstance(result, Strip)

    def test_render_line_with_styled_text(self, mock_ssh_session):
        """render_line should apply character styles."""
        terminal = SSHTerminal(session=mock_ssh_session)
        terminal.pyte_screen = MagicMock()
        terminal.pyte_screen.lines = 24

        mock_char = MagicMock()
        mock_char.data = "B"
        mock_char.fg = "red"
        mock_char.bg = "blue"
        mock_char.bold = True
        mock_char.italics = True
        mock_char.reverse = False

        terminal.pyte_screen.buffer = {0: {0: mock_char}}
        terminal._size = Size(80, 24)

        result = terminal.render_line(0)

        assert isinstance(result, Strip)

    def test_render_line_with_multiple_characters(self, mock_ssh_session):
        """render_line should handle multiple characters on a line."""
        terminal = SSHTerminal(session=mock_ssh_session)
        terminal.pyte_screen = MagicMock()
        terminal.pyte_screen.lines = 24

        def make_char(char):
            mock = MagicMock()
            mock.data = char
            mock.fg = "white"
            mock.bg = "black"
            mock.bold = False
            mock.italics = False
            mock.reverse = False
            return mock

        terminal.pyte_screen.buffer = {
            0: {
                0: make_char("H"),
                1: make_char("i"),
            }
        }
        terminal._size = Size(80, 24)

        result = terminal.render_line(0)

        assert isinstance(result, Strip)

    def test_render_line_with_style_changes(self, mock_ssh_session):
        """render_line should handle style changes within a line."""
        terminal = SSHTerminal(session=mock_ssh_session)
        terminal.pyte_screen = MagicMock()
        terminal.pyte_screen.lines = 24

        char1 = MagicMock()
        char1.data = "A"
        char1.fg = "red"
        char1.bg = "black"
        char1.bold = True
        char1.italics = False
        char1.reverse = False

        char2 = MagicMock()
        char2.data = "B"
        char2.fg = "green"
        char2.bg = "black"
        char2.bold = False
        char2.italics = False
        char2.reverse = False

        terminal.pyte_screen.buffer = {0: {0: char1, 1: char2}}
        terminal._size = Size(80, 24)

        result = terminal.render_line(0)

        assert isinstance(result, Strip)


class TestSSHTerminalGetContentHeight:
    """Test get_content_height method."""

    def test_get_content_height_returns_pyte_lines(self, mock_ssh_session):
        """get_content_height should return pyte screen lines."""
        terminal = SSHTerminal(session=mock_ssh_session)
        terminal.pyte_screen = MagicMock()
        terminal.pyte_screen.lines = 30

        container = Size(100, 50)
        viewport = Size(100, 50)

        result = terminal.get_content_height(container, viewport, 100)

        assert result == 30

    def test_get_content_height_default_24_lines(self, mock_ssh_session):
        """get_content_height should return 24 for default pyte screen."""
        terminal = SSHTerminal(session=mock_ssh_session)
        # Default pyte screen is 24 lines

        container = Size(80, 24)
        viewport = Size(80, 24)

        result = terminal.get_content_height(container, viewport, 80)

        assert result == 24
