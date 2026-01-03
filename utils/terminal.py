"""Terminal emulator detection and adapter system.

Detects the current terminal emulator and provides adapters for
terminal-specific features like font control.
"""

import json
import os
import re
import subprocess
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path


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


# =============================================================================
# Terminal Configuration Adapters
# =============================================================================
# These adapters read and write terminal emulator config files directly,
# allowing null-terminal to sync appearance settings with the host terminal.


@dataclass
class TerminalConfig:
    """Terminal configuration settings that can be read/written."""

    font_family: str = ""
    font_size: float = 0.0
    cursor_style: str = ""  # block, beam, underline
    cursor_blink: bool | None = None
    opacity: float = 1.0
    # Raw config data for preserving unknown settings
    raw_config: dict = field(default_factory=dict)


class TerminalConfigAdapter(ABC):
    """Abstract base class for terminal config file adapters.

    Similar to LLMProvider, each terminal emulator gets an adapter
    that knows how to read and write its specific config format.
    """

    def __init__(self, terminal_info: TerminalInfo):
        self.info = terminal_info

    @property
    @abstractmethod
    def config_path(self) -> Path | None:
        """Path to the terminal's config file, or None if not found."""
        pass

    @property
    def config_exists(self) -> bool:
        """Check if the config file exists."""
        path = self.config_path
        return path is not None and path.exists()

    @abstractmethod
    def read_config(self) -> TerminalConfig | None:
        """Read the terminal's current configuration.

        Returns:
            TerminalConfig with current settings, or None if read failed.
        """
        pass

    @abstractmethod
    def write_config(self, config: TerminalConfig) -> bool:
        """Write configuration to the terminal's config file.

        This should preserve any settings not in TerminalConfig.

        Args:
            config: The configuration to write.

        Returns:
            True if write succeeded, False otherwise.
        """
        pass

    def get_font_family(self) -> str | None:
        """Get the current font family from config."""
        config = self.read_config()
        return config.font_family if config and config.font_family else None

    def set_font_family(self, family: str) -> bool:
        """Set font family in config."""
        config = self.read_config()
        if config is None:
            config = TerminalConfig()
        config.font_family = family
        return self.write_config(config)

    def get_font_size(self) -> float | None:
        """Get the current font size from config."""
        config = self.read_config()
        return config.font_size if config and config.font_size > 0 else None

    def set_font_size(self, size: float) -> bool:
        """Set font size in config."""
        config = self.read_config()
        if config is None:
            config = TerminalConfig()
        config.font_size = size
        return self.write_config(config)


class WindowsTerminalConfigAdapter(TerminalConfigAdapter):
    """Adapter for Windows Terminal settings.json.

    Windows Terminal stores settings in LocalState/settings.json under
    the Microsoft.WindowsTerminal package in AppData/Local/Packages.

    This adapter creates and manages a dedicated "Null Terminal" profile,
    keeping null-terminal's settings separate from the user's other profiles.
    """

    # Fixed GUID for the Null Terminal profile
    NULL_PROFILE_GUID = "{9f9a37e7-8b3d-4f5c-a6e8-2d1c3b4e5f6a}"
    NULL_PROFILE_NAME = "Null Terminal"

    def __init__(self, terminal_info: TerminalInfo):
        super().__init__(terminal_info)
        self._config_path: Path | None = None
        self._find_config_path()

    def _find_config_path(self) -> None:
        """Find the Windows Terminal settings.json path."""
        # Check if running in WSL
        wsl_distro = os.environ.get("WSL_DISTRO_NAME")

        if wsl_distro:
            # Running in WSL - find the Windows user's AppData
            # Try to get Windows username from /mnt/c/Users
            users_path = Path("/mnt/c/Users")
            if users_path.exists():
                for user_dir in users_path.iterdir():
                    if user_dir.is_dir() and user_dir.name not in (
                        "Public",
                        "Default",
                        "Default User",
                        "All Users",
                    ):
                        # Look for Windows Terminal package folder
                        appdata = user_dir / "AppData/Local/Packages"
                        if appdata.exists():
                            for pkg in appdata.iterdir():
                                if pkg.name.startswith("Microsoft.WindowsTerminal"):
                                    settings = pkg / "LocalState/settings.json"
                                    if settings.exists():
                                        self._config_path = settings
                                        return
        else:
            # Native Windows - use LOCALAPPDATA
            localappdata = os.environ.get("LOCALAPPDATA")
            if localappdata:
                packages = Path(localappdata) / "Packages"
                if packages.exists():
                    for pkg in packages.iterdir():
                        if pkg.name.startswith("Microsoft.WindowsTerminal"):
                            settings = pkg / "LocalState/settings.json"
                            if settings.exists():
                                self._config_path = settings
                                return

    @property
    def config_path(self) -> Path | None:
        return self._config_path

    def _find_null_profile(self, data: dict) -> dict | None:
        """Find the Null Terminal profile in the profiles list."""
        profiles_list = data.get("profiles", {}).get("list", [])
        for profile in profiles_list:
            if profile.get("guid") == self.NULL_PROFILE_GUID:
                return profile
            if profile.get("name") == self.NULL_PROFILE_NAME:
                return profile
        return None

    def _get_wsl_command(self) -> str | None:
        """Get the WSL command to launch the current distro."""
        wsl_distro = os.environ.get("WSL_DISTRO_NAME")
        if wsl_distro:
            return f"wsl.exe -d {wsl_distro}"
        return None

    def read_config(self) -> TerminalConfig | None:
        """Read Windows Terminal settings from Null Terminal profile or defaults."""
        if not self.config_path or not self.config_path.exists():
            return None

        try:
            with open(self.config_path, encoding="utf-8") as f:
                data = json.load(f)

            config = TerminalConfig(raw_config=data)

            # First check for our dedicated profile
            null_profile = self._find_null_profile(data)
            defaults = data.get("profiles", {}).get("defaults", {})
            source = null_profile if null_profile else defaults

            # Font settings
            font = source.get("font", {})
            if isinstance(font, dict):
                config.font_family = font.get("face", "")
                config.font_size = float(font.get("size", 0))
            elif "fontFace" in source:
                # Legacy format
                config.font_family = source.get("fontFace", "")
                config.font_size = float(source.get("fontSize", 0))

            # Cursor settings
            cursor_shape = source.get("cursorShape", "")
            if cursor_shape:
                # Map WT cursor shapes to our format
                shape_map = {
                    "bar": "beam",
                    "vintage": "underline",
                    "filledBox": "block",
                    "emptyBox": "block",
                    "underscore": "underline",
                }
                config.cursor_style = shape_map.get(cursor_shape, cursor_shape)

            # Opacity
            config.opacity = float(source.get("opacity", 1.0))

            return config

        except Exception:
            return None

    def write_config(self, config: TerminalConfig) -> bool:
        """Write to Windows Terminal - creates/updates Null Terminal profile."""
        if not self.config_path:
            return False

        try:
            # Read existing config to preserve other settings
            if self.config_path.exists():
                with open(self.config_path, encoding="utf-8") as f:
                    data = json.load(f)
            else:
                data = config.raw_config if config.raw_config else {}

            # Ensure profiles structure exists
            if "profiles" not in data:
                data["profiles"] = {}
            if "list" not in data["profiles"]:
                data["profiles"]["list"] = []

            # Find or create the Null Terminal profile
            null_profile = self._find_null_profile(data)
            if null_profile is None:
                # Create new profile
                null_profile = {
                    "guid": self.NULL_PROFILE_GUID,
                    "name": self.NULL_PROFILE_NAME,
                    "hidden": False,
                    "icon": "\u2205",  # Empty set symbol as icon
                }
                # Add WSL command if in WSL
                wsl_cmd = self._get_wsl_command()
                if wsl_cmd:
                    null_profile["commandline"] = wsl_cmd

                data["profiles"]["list"].append(null_profile)

            # Update font settings (use new format)
            if config.font_family or config.font_size > 0:
                if "font" not in null_profile:
                    null_profile["font"] = {}
                if config.font_family:
                    null_profile["font"]["face"] = config.font_family
                if config.font_size > 0:
                    null_profile["font"]["size"] = config.font_size

            # Update cursor settings
            if config.cursor_style:
                # Map our cursor styles to WT format
                style_map = {
                    "beam": "bar",
                    "underline": "underscore",
                    "block": "filledBox",
                }
                null_profile["cursorShape"] = style_map.get(
                    config.cursor_style, config.cursor_style
                )

            # Update opacity
            if config.opacity < 1.0:
                null_profile["opacity"] = config.opacity

            # Write back with pretty formatting
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4)

            return True

        except Exception:
            return False

    def get_profile_guid(self) -> str:
        """Get the GUID for the Null Terminal profile."""
        return self.NULL_PROFILE_GUID

    def activate_profile(self, new_window: bool = False) -> bool:
        """Activate the Null Terminal profile by opening a new tab or window.

        Args:
            new_window: If True, opens a new window. If False, opens a new tab.

        Returns:
            True if activation command was executed successfully.
        """
        try:
            if new_window:
                # Open new Windows Terminal window with our profile
                cmd = ["wt.exe", "-p", self.NULL_PROFILE_NAME]
            else:
                # Open new tab in current Windows Terminal with our profile
                cmd = ["wt.exe", "new-tab", "-p", self.NULL_PROFILE_NAME]

            subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            return True
        except Exception:
            return False

    def is_active_profile(self) -> bool:
        """Check if we're currently running in the Null Terminal profile.

        Note: This is difficult to detect reliably. Windows Terminal doesn't
        expose the current profile GUID via environment variables.
        """
        # WT_PROFILE_ID would be ideal but isn't always set
        # For now, we can't reliably detect this
        return False


class KittyConfigAdapter(TerminalConfigAdapter):
    """Adapter for Kitty terminal config.

    Kitty uses a simple key-value config format in:
    - ~/.config/kitty/kitty.conf

    Format example:
        font_family      JetBrains Mono
        font_size        12.0
        cursor_shape     block
    """

    @property
    def config_path(self) -> Path | None:
        path = Path.home() / ".config/kitty/kitty.conf"
        return path if path.exists() else None

    def read_config(self) -> TerminalConfig | None:
        """Read Kitty configuration."""
        if not self.config_path:
            return None

        try:
            with open(self.config_path, encoding="utf-8") as f:
                content = f.read()

            config = TerminalConfig()

            # Parse key-value pairs
            for line in content.splitlines():
                line = line.strip()
                if not line or line.startswith("#"):
                    continue

                # Split on first whitespace
                parts = line.split(None, 1)
                if len(parts) < 2:
                    continue

                key, value = parts[0], parts[1].strip()

                if key == "font_family":
                    config.font_family = value
                elif key == "font_size":
                    try:
                        config.font_size = float(value)
                    except ValueError:
                        pass
                elif key == "cursor_shape":
                    config.cursor_style = value
                elif key == "cursor_blink_interval":
                    # In Kitty, 0 or negative means no blink
                    try:
                        config.cursor_blink = float(value) > 0
                    except ValueError:
                        pass
                elif key == "background_opacity":
                    try:
                        config.opacity = float(value)
                    except ValueError:
                        pass

            return config

        except Exception:
            return None

    def write_config(self, config: TerminalConfig) -> bool:
        """Write to Kitty configuration."""
        config_path = self.config_path
        if not config_path:
            # Create config directory and file
            config_dir = Path.home() / ".config/kitty"
            config_dir.mkdir(parents=True, exist_ok=True)
            config_path = config_dir / "kitty.conf"

        try:
            # Read existing content to preserve comments and other settings
            existing_lines = []
            if config_path.exists():
                with open(config_path, encoding="utf-8") as f:
                    existing_lines = f.readlines()

            # Settings we want to update
            updates = {}
            if config.font_family:
                updates["font_family"] = config.font_family
            if config.font_size > 0:
                updates["font_size"] = str(config.font_size)
            if config.cursor_style:
                updates["cursor_shape"] = config.cursor_style
            if config.cursor_blink is not None:
                updates["cursor_blink_interval"] = "0.5" if config.cursor_blink else "0"
            if config.opacity < 1.0:
                updates["background_opacity"] = str(config.opacity)

            # Update existing lines or track what's been set
            found_keys = set()
            new_lines = []

            for line in existing_lines:
                stripped = line.strip()
                if stripped and not stripped.startswith("#"):
                    parts = stripped.split(None, 1)
                    if parts and parts[0] in updates:
                        key = parts[0]
                        found_keys.add(key)
                        new_lines.append(f"{key} {updates[key]}\n")
                        continue
                new_lines.append(line)

            # Add any settings not found in existing file
            for key, value in updates.items():
                if key not in found_keys:
                    new_lines.append(f"{key} {value}\n")

            # Write back
            with open(config_path, "w", encoding="utf-8") as f:
                f.writelines(new_lines)

            return True

        except Exception:
            return False


class AlacrittyConfigAdapter(TerminalConfigAdapter):
    """Adapter for Alacritty terminal config.

    Alacritty uses TOML format (as of v0.13+) in:
    - ~/.config/alacritty/alacritty.toml
    - Legacy: ~/.config/alacritty/alacritty.yml (YAML)
    """

    @property
    def config_path(self) -> Path | None:
        # Check TOML first (newer format)
        toml_path = Path.home() / ".config/alacritty/alacritty.toml"
        if toml_path.exists():
            return toml_path

        # Check YAML (legacy)
        yml_path = Path.home() / ".config/alacritty/alacritty.yml"
        if yml_path.exists():
            return yml_path

        return None

    def read_config(self) -> TerminalConfig | None:
        """Read Alacritty configuration."""
        if not self.config_path:
            return None

        try:
            with open(self.config_path, encoding="utf-8") as f:
                content = f.read()

            config = TerminalConfig()

            if self.config_path.suffix == ".toml":
                # Parse TOML format
                # Look for [font.normal] section
                font_match = re.search(
                    r'\[font\.normal\].*?family\s*=\s*["\']([^"\']+)["\']',
                    content,
                    re.DOTALL,
                )
                if font_match:
                    config.font_family = font_match.group(1)

                size_match = re.search(
                    r'\[font\].*?size\s*=\s*([\d.]+)', content, re.DOTALL
                )
                if size_match:
                    config.font_size = float(size_match.group(1))

                # Cursor
                cursor_match = re.search(
                    r'\[cursor\.style\].*?shape\s*=\s*["\'](\w+)["\']',
                    content,
                    re.DOTALL,
                )
                if cursor_match:
                    shape = cursor_match.group(1).lower()
                    config.cursor_style = shape

                blink_match = re.search(
                    r'\[cursor\.style\].*?blinking\s*=\s*["\'](\w+)["\']',
                    content,
                    re.DOTALL,
                )
                if blink_match:
                    config.cursor_blink = blink_match.group(1).lower() != "never"

            else:
                # Parse YAML format (legacy)
                # Simple regex parsing for common patterns
                font_match = re.search(r'family:\s*["\']?([^"\'\n]+)', content)
                if font_match:
                    config.font_family = font_match.group(1).strip()

                size_match = re.search(r'size:\s*([\d.]+)', content)
                if size_match:
                    config.font_size = float(size_match.group(1))

            return config

        except Exception:
            return None

    def write_config(self, config: TerminalConfig) -> bool:
        """Write to Alacritty configuration.

        Note: This uses simple regex replacement which may not handle
        all edge cases. A proper TOML/YAML library would be better.
        """
        if not self.config_path:
            return False

        try:
            with open(self.config_path, encoding="utf-8") as f:
                content = f.read()

            if self.config_path.suffix == ".toml":
                # Update TOML format
                if config.font_family:
                    if "[font.normal]" in content:
                        content = re.sub(
                            r'(\[font\.normal\].*?family\s*=\s*)["\'][^"\']+["\']',
                            f'\\1"{config.font_family}"',
                            content,
                            flags=re.DOTALL,
                        )
                    else:
                        content += f'\n[font.normal]\nfamily = "{config.font_family}"\n'

                if config.font_size > 0:
                    if re.search(r'\[font\].*?size\s*=', content, re.DOTALL):
                        content = re.sub(
                            r'(\[font\].*?size\s*=\s*)[\d.]+',
                            f'\\g<1>{config.font_size}',
                            content,
                            flags=re.DOTALL,
                        )
                    elif "[font]" in content:
                        content = re.sub(
                            r'(\[font\])',
                            f'\\1\nsize = {config.font_size}',
                            content,
                        )
                    else:
                        content += f'\n[font]\nsize = {config.font_size}\n'

            with open(self.config_path, "w", encoding="utf-8") as f:
                f.write(content)

            return True

        except Exception:
            return False


class NoOpConfigAdapter(TerminalConfigAdapter):
    """No-op adapter for terminals without config file support."""

    @property
    def config_path(self) -> Path | None:
        return None

    def read_config(self) -> TerminalConfig | None:
        return None

    def write_config(self, config: TerminalConfig) -> bool:
        return False


def get_terminal_config_adapter() -> TerminalConfigAdapter:
    """Get the appropriate config adapter for the current terminal.

    Returns:
        A TerminalConfigAdapter instance for the detected terminal.
    """
    info = get_terminal_info()

    if info.type == TerminalType.WINDOWS_TERMINAL:
        return WindowsTerminalConfigAdapter(info)
    elif info.type == TerminalType.KITTY:
        return KittyConfigAdapter(info)
    elif info.type == TerminalType.ALACRITTY:
        return AlacrittyConfigAdapter(info)
    else:
        return NoOpConfigAdapter(info)


def sync_terminal_config(
    font_family: str | None = None,
    font_size: float | None = None,
    cursor_style: str | None = None,
    cursor_blink: bool | None = None,
) -> bool:
    """Sync null-terminal settings to the host terminal's config.

    This function writes the specified settings to the terminal's
    config file (e.g., Windows Terminal's settings.json).

    Args:
        font_family: Font family name to set
        font_size: Font size to set
        cursor_style: Cursor style (block, beam, underline)
        cursor_blink: Whether cursor should blink

    Returns:
        True if settings were written successfully, False otherwise.
    """
    adapter = get_terminal_config_adapter()

    if not adapter.config_exists:
        return False

    config = adapter.read_config()
    if config is None:
        config = TerminalConfig()

    # Update only specified settings
    if font_family is not None:
        config.font_family = font_family
    if font_size is not None:
        config.font_size = font_size
    if cursor_style is not None:
        config.cursor_style = cursor_style
    if cursor_blink is not None:
        config.cursor_blink = cursor_blink

    return adapter.write_config(config)


def load_terminal_defaults() -> TerminalConfig | None:
    """Load current terminal settings as defaults for first run.

    Returns:
        TerminalConfig with current terminal settings, or None if unavailable.
    """
    adapter = get_terminal_config_adapter()
    return adapter.read_config()


def activate_null_profile(new_window: bool = False) -> bool:
    """Activate the Null Terminal profile in the current terminal.

    For Windows Terminal, this opens a new tab or window with the
    Null Terminal profile that has our configured settings.

    Args:
        new_window: If True, opens in a new window instead of a tab.

    Returns:
        True if activation was successful, False otherwise.
    """
    adapter = get_terminal_config_adapter()

    if isinstance(adapter, WindowsTerminalConfigAdapter):
        return adapter.activate_profile(new_window=new_window)

    # Other terminals don't need activation - settings apply directly
    return False
