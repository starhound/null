"""Terminal emulator detection and adapter system.

Detects the current terminal emulator and provides adapters for
terminal-specific features like font control.
"""

import os
import subprocess
from dataclasses import dataclass
from enum import Enum


class TerminalType(Enum):
    """Known terminal emulator types."""

    KITTY = "kitty"
    WEZTERM = "wezterm"
    ALACRITTY = "alacritty"
    ITERM2 = "iterm2"
    GNOME = "gnome-terminal"
    KONSOLE = "konsole"
    TILIX = "tilix"
    XTERM = "xterm"
    TMUX = "tmux"
    VSCODE = "vscode"
    WINDOWS_TERMINAL = "windows-terminal"
    UNKNOWN = "unknown"


@dataclass
class TerminalInfo:
    """Information about the detected terminal."""

    type: TerminalType
    name: str
    supports_font_change: bool
    supports_true_color: bool = True
    supports_osc: bool = True  # Operating System Commands
    version: str = ""
    config_path: str = ""


def detect_terminal() -> TerminalInfo:
    """Detect the current terminal emulator from environment variables.

    Returns:
        TerminalInfo with detected terminal type and capabilities.
    """
    # Check TERM_PROGRAM first (set by many modern terminals)
    term_program = os.environ.get("TERM_PROGRAM", "").lower()

    # VS Code integrated terminal
    if term_program == "vscode" or os.environ.get("VSCODE_INJECTION"):
        version = os.environ.get("TERM_PROGRAM_VERSION", "")
        return TerminalInfo(
            type=TerminalType.VSCODE,
            name="VS Code Terminal",
            supports_font_change=False,  # Controlled via VS Code settings
            supports_true_color=True,
            supports_osc=True,
            version=version,
        )
    # Check for Kitty
    if os.environ.get("KITTY_PID"):
        return TerminalInfo(
            type=TerminalType.KITTY,
            name="Kitty",
            supports_font_change=True,
            supports_true_color=True,
            supports_osc=True,
            config_path=os.path.expanduser("~/.config/kitty/kitty.conf"),
        )

    # Check for WezTerm
    if os.environ.get("WEZTERM_EXECUTABLE") or os.environ.get("WEZTERM_PANE"):
        return TerminalInfo(
            type=TerminalType.WEZTERM,
            name="WezTerm",
            supports_font_change=True,
            supports_true_color=True,
            supports_osc=True,
            config_path=os.path.expanduser("~/.config/wezterm/wezterm.lua"),
        )

    # Check for Alacritty
    if os.environ.get("ALACRITTY_LOG") or os.environ.get("ALACRITTY_SOCKET"):
        return TerminalInfo(
            type=TerminalType.ALACRITTY,
            name="Alacritty",
            supports_font_change=False,  # Requires config file edit
            supports_true_color=True,
            supports_osc=True,
            config_path=os.path.expanduser("~/.config/alacritty/alacritty.toml"),
        )

    # Check for iTerm2 (macOS)
    if os.environ.get("ITERM_SESSION_ID"):
        return TerminalInfo(
            type=TerminalType.ITERM2,
            name="iTerm2",
            supports_font_change=True,
            supports_true_color=True,
            supports_osc=True,
        )

    # Check for GNOME Terminal
    if os.environ.get("GNOME_TERMINAL_SCREEN"):
        return TerminalInfo(
            type=TerminalType.GNOME,
            name="GNOME Terminal",
            supports_font_change=False,
            supports_true_color=True,
            supports_osc=True,
        )

    # Check for Konsole
    if os.environ.get("KONSOLE_VERSION"):
        return TerminalInfo(
            type=TerminalType.KONSOLE,
            name="Konsole",
            supports_font_change=False,
            supports_true_color=True,
            supports_osc=True,
        )

    # Check for Tilix
    if os.environ.get("TILIX_ID"):
        return TerminalInfo(
            type=TerminalType.TILIX,
            name="Tilix",
            supports_font_change=False,
            supports_true_color=True,
            supports_osc=True,
        )

    # Check for tmux (passthrough to underlying terminal)
    if os.environ.get("TMUX"):
        return TerminalInfo(
            type=TerminalType.TMUX,
            name="tmux",
            supports_font_change=False,
            supports_true_color=True,
            supports_osc=True,
        )

    # Check TERM_PROGRAM (set by some terminals)
    # Note: term_program is already defined at the top of the function
    if "kitty" in term_program:
        return TerminalInfo(TerminalType.KITTY, "Kitty", True)
    if "wezterm" in term_program:
        return TerminalInfo(TerminalType.WEZTERM, "WezTerm", True)
    if "iterm" in term_program:
        return TerminalInfo(TerminalType.ITERM2, "iTerm2", True)
    if "alacritty" in term_program:
        return TerminalInfo(TerminalType.ALACRITTY, "Alacritty", False)

    # Check for Windows Terminal via WSL
    # WSL sets WSL_DISTRO_NAME and WT_SESSION for Windows Terminal
    wt_session = os.environ.get("WT_SESSION")
    wsl_distro = os.environ.get("WSL_DISTRO_NAME")

    if wt_session or (
        wsl_distro and os.path.exists("/proc/sys/fs/binfmt_misc/WSLInterop")
    ):
        return TerminalInfo(
            type=TerminalType.WINDOWS_TERMINAL,
            name="Windows Terminal" + (f" (WSL: {wsl_distro})" if wsl_distro else ""),
            supports_font_change=False,  # Controlled via Windows Terminal settings
            supports_true_color=True,
            supports_osc=True,
        )

    # Fallback to TERM variable
    term = os.environ.get("TERM", "")
    if "xterm" in term.lower():
        return TerminalInfo(
            type=TerminalType.XTERM,
            name="xterm-compatible",
            supports_font_change=False,
            supports_true_color="256color" in term or "truecolor" in term,
            supports_osc=True,
        )

    return TerminalInfo(
        type=TerminalType.UNKNOWN,
        name="Unknown Terminal",
        supports_font_change=False,
        supports_true_color=False,
        supports_osc=False,
    )


# Global cached terminal info
_terminal_info: TerminalInfo | None = None


def get_terminal_info() -> TerminalInfo:
    """Get cached terminal info (detects once on first call)."""
    global _terminal_info
    if _terminal_info is None:
        _terminal_info = detect_terminal()
    return _terminal_info


def refresh_terminal_info() -> TerminalInfo:
    """Force re-detection of terminal (useful if terminal changed)."""
    global _terminal_info
    _terminal_info = detect_terminal()
    return _terminal_info


# =============================================================================
# Terminal Adapters for font/appearance control
# =============================================================================


class TerminalAdapter:
    """Base class for terminal-specific adapters."""

    def __init__(self, terminal_info: TerminalInfo):
        self.info = terminal_info

    def set_font(self, family: str, size: int) -> bool:
        """Set terminal font. Returns True if successful."""
        return False

    def set_font_size(self, size: int) -> bool:
        """Set terminal font size. Returns True if successful."""
        return False

    def get_font(self) -> tuple | None:
        """Get current font (family, size) if possible."""
        return None

    def set_opacity(self, opacity: float) -> bool:
        """Set terminal opacity (0.0 - 1.0). Returns True if successful."""
        return False


class KittyAdapter(TerminalAdapter):
    """Adapter for Kitty terminal."""

    def set_font(self, family: str, size: int) -> bool:
        """Set font using Kitty remote control."""
        try:
            # Kitty uses @ commands via socket
            cmd = ["kitty", "@", "set-font-size", str(size)]
            result = subprocess.run(cmd, capture_output=True, timeout=2)
            return result.returncode == 0
        except Exception:
            return False

    def set_font_size(self, size: int) -> bool:
        """Set font size using kitty @ command."""
        try:
            result = subprocess.run(
                ["kitty", "@", "set-font-size", str(size)],
                capture_output=True,
                timeout=2,
            )
            return result.returncode == 0
        except Exception:
            return False

    def set_opacity(self, opacity: float) -> bool:
        """Set opacity using Kitty remote control."""
        try:
            # Convert to percentage
            cmd = ["kitty", "@", "set-background-opacity", str(opacity)]
            result = subprocess.run(cmd, capture_output=True, timeout=2)
            return result.returncode == 0
        except Exception:
            return False


class WezTermAdapter(TerminalAdapter):
    """Adapter for WezTerm terminal."""

    def set_font(self, family: str, size: int) -> bool:
        """WezTerm requires lua config changes or cli."""
        # WezTerm can be controlled via CLI in some cases
        # For now, return False - would need more complex config editing
        return False

    def set_font_size(self, size: int) -> bool:
        """WezTerm font changes require config file modification.

        WezTerm doesn't support runtime font size changes via commands.
        Could potentially use OSC sequences but not widely supported.
        """
        return False


class WindowsTerminalAdapter(TerminalAdapter):
    """Adapter for Windows Terminal (via WSL or native)."""

    def set_cursor_style(self, style: str, blink: bool = True) -> bool:
        """Set cursor style via ANSI DECSCUSR sequence.

        Windows Terminal supports:
        - Block: steady=2, blink=1
        - Underline: steady=4, blink=3
        - Beam/Bar: steady=6, blink=5

        Args:
            style: Cursor style - "block", "underline", "beam", or "bar"
            blink: Whether the cursor should blink

        Returns:
            True if the sequence was written successfully, False otherwise
        """
        codes = {
            ("block", True): 1,
            ("block", False): 2,
            ("underline", True): 3,
            ("underline", False): 4,
            ("beam", True): 5,
            ("beam", False): 6,
            ("bar", True): 5,  # alias for beam
            ("bar", False): 6,
        }
        code = codes.get((style.lower(), blink), 1)
        try:
            import sys

            sys.stdout.write(f"\x1b[{code} q")
            sys.stdout.flush()
            return True
        except Exception:
            return False


class GenericAdapter(TerminalAdapter):
    """Generic adapter for unsupported terminals."""

    pass


def get_terminal_adapter() -> TerminalAdapter:
    """Get the appropriate adapter for the current terminal."""
    info = get_terminal_info()

    if info.type == TerminalType.KITTY:
        return KittyAdapter(info)
    elif info.type == TerminalType.WEZTERM:
        return WezTermAdapter(info)
    elif info.type == TerminalType.WINDOWS_TERMINAL:
        return WindowsTerminalAdapter(info)
    else:
        return GenericAdapter(info)


def apply_appearance_settings(font_size: int | None = None) -> bool:
    """Apply appearance settings to the terminal if supported.

    Gets the terminal adapter and applies font size if the terminal
    supports font changes.

    Args:
        font_size: The font size to apply, or None to skip font changes.

    Returns:
        True if all requested settings were applied successfully,
        False if any setting failed or was not supported.
    """
    adapter = get_terminal_adapter()
    success = True

    if font_size is not None:
        if adapter.info.supports_font_change:
            if not adapter.set_font_size(font_size):
                success = False
        else:
            # Terminal doesn't support font changes
            success = False

    return success


def apply_cursor_settings(style: str, blink: bool = True) -> bool:
    """Apply cursor style settings via ANSI DECSCUSR sequence.

    This function works across all terminals that support DECSCUSR
    (most modern terminals do, including Windows Terminal, iTerm2,
    Kitty, WezTerm, GNOME Terminal, Konsole, and others).

    The DECSCUSR (DEC Set Cursor Style) sequence uses the format:
    ESC [ Ps SP q

    Where Ps is:
    - 0: Default cursor shape configured by the terminal
    - 1: Blinking block
    - 2: Steady block
    - 3: Blinking underline
    - 4: Steady underline
    - 5: Blinking bar (beam)
    - 6: Steady bar (beam)

    Args:
        style: Cursor style - "block", "underline", "beam", or "bar"
        blink: Whether the cursor should blink (default: True)

    Returns:
        True if the sequence was written successfully, False otherwise
    """
    codes = {
        ("block", True): 1,
        ("block", False): 2,
        ("underline", True): 3,
        ("underline", False): 4,
        ("beam", True): 5,
        ("beam", False): 6,
        ("bar", True): 5,  # alias for beam
        ("bar", False): 6,
    }
    code = codes.get((style.lower(), blink), 1)
    try:
        # Write directly to terminal, bypassing any stdout redirection
        # (Textual redirects sys.stdout for its own rendering)
        with open("/dev/tty", "w") as tty:
            tty.write(f"\x1b[{code} q")
            tty.flush()
        return True
    except Exception:
        # Fallback to sys.__stdout__ if /dev/tty isn't available
        try:
            import sys

            if sys.__stdout__:
                sys.__stdout__.write(f"\x1b[{code} q")
                sys.__stdout__.flush()
                return True
        except Exception:
            pass
        return False
