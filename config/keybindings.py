"""Keybinding configuration management with conflict detection."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


# Keybindings config file path
KEYBINDINGS_PATH = Path.home() / ".null" / "keybindings.json"


@dataclass
class KeyBinding:
    """A single keybinding definition."""

    id: str
    """Unique identifier for the binding."""
    key: str
    """Key combination (e.g., 'ctrl+shift+c')."""
    action: str
    """Action name to trigger."""
    description: str
    """Human-readable description."""
    context: str = "app"
    """Context where binding is active (app, input, block, etc.)."""
    show: bool = True
    """Whether to show in footer/help."""

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "id": self.id,
            "key": self.key,
            "action": self.action,
            "description": self.description,
            "context": self.context,
            "show": self.show,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "KeyBinding":
        """Create KeyBinding from dictionary."""
        return cls(
            id=data["id"],
            key=data["key"],
            action=data["action"],
            description=data.get("description", ""),
            context=data.get("context", "app"),
            show=data.get("show", True),
        )


@dataclass
class KeyConflict:
    """Represents a keybinding conflict."""

    key: str
    """The conflicting key combination."""
    bindings: list[KeyBinding]
    """List of bindings that conflict."""

    @property
    def description(self) -> str:
        """Human-readable conflict description."""
        binding_names = [f"'{b.description}'" for b in self.bindings]
        return f"Key '{self.key}' is bound to: {', '.join(binding_names)}"


# Default keybindings - these match the current app.py BINDINGS
DEFAULT_KEYBINDINGS: list[KeyBinding] = [
    # Global app bindings
    KeyBinding("cancel", "escape", "cancel_operation", "Cancel", "app"),
    KeyBinding("clear_history", "ctrl+l", "clear_history", "Clear History", "app"),
    KeyBinding("quick_export", "ctrl+s", "quick_export", "Export", "app"),
    KeyBinding("search_history", "ctrl+r", "search_history", "Search History", "app"),
    KeyBinding("search_blocks", "ctrl+f", "search_blocks", "Search Blocks", "app"),
    KeyBinding(
        "command_palette", "ctrl+p", "open_command_palette", "Command Palette", "app"
    ),
    KeyBinding("help", "f1", "open_help", "Help", "app"),
    KeyBinding("select_model", "f2", "select_model", "Select Model", "app"),
    KeyBinding("select_theme", "f3", "select_theme", "Change Theme", "app"),
    KeyBinding("select_provider", "f4", "select_provider", "Select Provider", "app"),
    KeyBinding(
        "toggle_ai_mode", "ctrl+space", "toggle_ai_mode", "Toggle AI Mode", "app"
    ),
    KeyBinding(
        "toggle_ai_mode_alt", "ctrl+t", "toggle_ai_mode", "Toggle AI Mode", "app", False
    ),
    KeyBinding(
        "toggle_file_tree", "ctrl+backslash", "toggle_file_tree", "Files", "app"
    ),
    KeyBinding("toggle_branches", "ctrl+b", "toggle_branches", "Branches", "app"),
    KeyBinding("toggle_voice", "ctrl+m", "toggle_voice", "Voice Input", "app"),
    # Input bindings
    KeyBinding("submit", "enter", "submit", "Submit", "input"),
    KeyBinding("newline", "shift+enter", "newline", "New Line", "input"),
    KeyBinding("copy_selection", "ctrl+shift+c", "copy_selection", "Copy", "input"),
    KeyBinding("clear_to_start", "ctrl+u", "clear_to_start", "Clear Line", "input"),
    KeyBinding(
        "accept_ghost", "right", "accept_ghost", "Accept Suggestion", "input", False
    ),
    # Block bindings
    KeyBinding("copy_menu", "c", "show_copy_menu", "Copy Menu", "block", False),
    KeyBinding("copy_content", "y", "copy_content", "Copy", "block", False),
    KeyBinding("retry_block", "r", "retry_block", "Retry", "block", False),
    KeyBinding("edit_block", "e", "edit_block", "Edit", "block", False),
    KeyBinding("fork_block", "f", "fork_block", "Fork", "block", False),
]


# Valid modifier keys
VALID_MODIFIERS = {"ctrl", "alt", "shift", "meta", "cmd", "super"}

# Valid special keys
VALID_SPECIAL_KEYS = {
    "escape",
    "enter",
    "tab",
    "space",
    "backspace",
    "delete",
    "insert",
    "home",
    "end",
    "pageup",
    "pagedown",
    "up",
    "down",
    "left",
    "right",
    "f1",
    "f2",
    "f3",
    "f4",
    "f5",
    "f6",
    "f7",
    "f8",
    "f9",
    "f10",
    "f11",
    "f12",
    "backslash",
    "slash",
    "comma",
    "period",
    "semicolon",
    "apostrophe",
    "bracketleft",
    "bracketright",
    "minus",
    "equal",
    "grave",
}


@dataclass
class KeybindingManager:
    """Manages custom keybindings with conflict detection."""

    _bindings: dict[str, KeyBinding] = field(default_factory=dict)
    _loaded: bool = False

    def __post_init__(self):
        """Initialize with default bindings."""
        if not self._loaded:
            self._load_defaults()

    def _load_defaults(self):
        """Load default keybindings."""
        for binding in DEFAULT_KEYBINDINGS:
            self._bindings[binding.id] = binding

    def load(self) -> None:
        """Load custom keybindings from config file."""
        self._load_defaults()  # Always start with defaults

        if not KEYBINDINGS_PATH.exists():
            return

        try:
            data = json.loads(KEYBINDINGS_PATH.read_text(encoding="utf-8"))
            custom_bindings = data.get("bindings", {})

            # Overlay custom bindings on defaults
            for binding_id, key in custom_bindings.items():
                if binding_id in self._bindings:
                    self._bindings[binding_id] = KeyBinding(
                        id=binding_id,
                        key=key,
                        action=self._bindings[binding_id].action,
                        description=self._bindings[binding_id].description,
                        context=self._bindings[binding_id].context,
                        show=self._bindings[binding_id].show,
                    )
            self._loaded = True
        except (json.JSONDecodeError, OSError) as e:
            # Log error but continue with defaults
            import logging

            logging.getLogger(__name__).warning(f"Failed to load keybindings: {e}")

    def save(self) -> None:
        """Save custom keybindings to config file."""
        # Only save bindings that differ from defaults
        custom_bindings = {}
        default_map = {b.id: b.key for b in DEFAULT_KEYBINDINGS}

        for binding_id, binding in self._bindings.items():
            default_key = default_map.get(binding_id)
            if default_key and binding.key != default_key:
                custom_bindings[binding_id] = binding.key

        data = {"bindings": custom_bindings}

        KEYBINDINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
        KEYBINDINGS_PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def get_binding(self, binding_id: str) -> KeyBinding | None:
        """Get a binding by ID."""
        return self._bindings.get(binding_id)

    def get_all_bindings(self) -> list[KeyBinding]:
        """Get all bindings."""
        return list(self._bindings.values())

    def get_bindings_by_context(self, context: str) -> list[KeyBinding]:
        """Get bindings for a specific context."""
        return [b for b in self._bindings.values() if b.context == context]

    def set_binding(self, binding_id: str, key: str) -> list[KeyConflict]:
        """Set a binding key, returning any conflicts.

        Args:
            binding_id: The binding ID to update.
            key: The new key combination.

        Returns:
            List of conflicts found (may be empty).
        """
        # Normalize the key
        key = self.normalize_key(key)

        # Find conflicts
        conflicts = self.detect_conflicts(binding_id, key)

        # Update the binding anyway (user can resolve conflicts)
        if binding_id in self._bindings:
            old_binding = self._bindings[binding_id]
            self._bindings[binding_id] = KeyBinding(
                id=binding_id,
                key=key,
                action=old_binding.action,
                description=old_binding.description,
                context=old_binding.context,
                show=old_binding.show,
            )

        return conflicts

    def detect_conflicts(self, binding_id: str, new_key: str) -> list[KeyConflict]:
        """Detect if a key change would cause conflicts.

        Args:
            binding_id: The binding being changed.
            new_key: The new key combination.

        Returns:
            List of conflicts found.
        """
        conflicts = []
        binding = self._bindings.get(binding_id)
        if not binding:
            return conflicts

        # Find other bindings with the same key in the same context
        conflicting_bindings = []
        for other_id, other_binding in self._bindings.items():
            if other_id == binding_id:
                continue
            # Check if same key AND overlapping context
            if other_binding.key == new_key:
                # Same context or one is 'app' (global)
                if (
                    other_binding.context == binding.context
                    or other_binding.context == "app"
                    or binding.context == "app"
                ):
                    conflicting_bindings.append(other_binding)

        if conflicting_bindings:
            # Include the binding being set in the conflict
            conflicts.append(
                KeyConflict(
                    key=new_key,
                    bindings=[binding, *conflicting_bindings],
                )
            )

        return conflicts

    def detect_all_conflicts(self) -> list[KeyConflict]:
        """Detect all current conflicts in the keybindings.

        Returns:
            List of all conflicts found.
        """
        conflicts = []
        seen_keys: dict[str, list[KeyBinding]] = {}

        for binding in self._bindings.values():
            # Group by key+context
            key = binding.key
            for context_key in [
                f"{key}:{binding.context}",
                f"{key}:app" if binding.context != "app" else None,
            ]:
                if context_key is None:
                    continue
                if context_key not in seen_keys:
                    seen_keys[context_key] = []
                seen_keys[context_key].append(binding)

        for key_context, bindings in seen_keys.items():
            if len(bindings) > 1:
                key = key_context.split(":")[0]
                conflicts.append(KeyConflict(key=key, bindings=bindings))

        return conflicts

    def reset_to_defaults(self) -> None:
        """Reset all bindings to defaults."""
        self._bindings.clear()
        self._load_defaults()
        # Remove custom config file
        if KEYBINDINGS_PATH.exists():
            KEYBINDINGS_PATH.unlink()

    def reset_binding(self, binding_id: str) -> bool:
        """Reset a single binding to its default.

        Args:
            binding_id: The binding ID to reset.

        Returns:
            True if reset succeeded, False if binding not found.
        """
        default = next((b for b in DEFAULT_KEYBINDINGS if b.id == binding_id), None)
        if default and binding_id in self._bindings:
            self._bindings[binding_id] = default
            return True
        return False

    def get_default_key(self, binding_id: str) -> str | None:
        """Get the default key for a binding.

        Args:
            binding_id: The binding ID.

        Returns:
            The default key, or None if not found.
        """
        default = next((b for b in DEFAULT_KEYBINDINGS if b.id == binding_id), None)
        return default.key if default else None

    def is_modified(self, binding_id: str) -> bool:
        """Check if a binding has been modified from default.

        Args:
            binding_id: The binding ID.

        Returns:
            True if modified, False otherwise.
        """
        current = self._bindings.get(binding_id)
        default_key = self.get_default_key(binding_id)
        return (
            current is not None
            and default_key is not None
            and current.key != default_key
        )

    @staticmethod
    def normalize_key(key: str) -> str:
        """Normalize a key combination string.

        Args:
            key: Key combination (e.g., 'Ctrl+Shift+C').

        Returns:
            Normalized key (e.g., 'ctrl+shift+c').
        """
        # Convert to lowercase and normalize separators
        key = key.lower().strip()
        key = re.sub(r"\s*\+\s*", "+", key)  # Normalize spaces around +

        # Split and sort modifiers
        parts = key.split("+")
        if len(parts) > 1:
            modifiers = [p for p in parts[:-1] if p in VALID_MODIFIERS]
            base_key = parts[-1]
            # Sort modifiers consistently: ctrl, alt, shift, meta
            modifier_order = ["ctrl", "alt", "shift", "meta", "cmd", "super"]
            modifiers.sort(
                key=lambda m: modifier_order.index(m) if m in modifier_order else 99
            )
            return "+".join(modifiers + [base_key])

        return key

    @staticmethod
    def validate_key(key: str) -> tuple[bool, str]:
        """Validate a key combination string.

        Args:
            key: Key combination to validate.

        Returns:
            Tuple of (is_valid, error_message).
        """
        if not key or not key.strip():
            return False, "Key cannot be empty"

        key = KeybindingManager.normalize_key(key)
        parts = key.split("+")

        # Check modifiers
        modifiers = parts[:-1]
        for mod in modifiers:
            if mod not in VALID_MODIFIERS:
                return False, f"Invalid modifier: '{mod}'"

        # Check base key
        base_key = parts[-1]
        if len(base_key) == 1 and base_key.isalnum():
            return True, ""
        if base_key in VALID_SPECIAL_KEYS:
            return True, ""

        return False, f"Invalid key: '{base_key}'"

    def get_keymap(self) -> dict[str, str]:
        """Get the bindings as a Textual Keymap.

        Returns a mapping of binding IDs to key strings for use with
        Textual's apply_keymap method.
        """
        return {b.id: b.key for b in self._bindings.values()}

    def format_key_display(self, key: str) -> str:
        """Format a key for display (e.g., 'ctrl+s' -> 'Ctrl+S').

        Args:
            key: Key combination.

        Returns:
            Formatted key string.
        """
        parts = key.split("+")
        formatted = []
        for part in parts:
            if part in VALID_MODIFIERS:
                formatted.append(part.capitalize())
            elif part in VALID_SPECIAL_KEYS:
                # Special formatting for certain keys
                special_display = {
                    "escape": "Esc",
                    "backspace": "Bksp",
                    "delete": "Del",
                    "pageup": "PgUp",
                    "pagedown": "PgDn",
                    "backslash": "\\",
                    "space": "Space",
                }
                formatted.append(special_display.get(part, part.upper()))
            else:
                formatted.append(part.upper())
        return "+".join(formatted)


# Singleton instance
_manager: KeybindingManager | None = None


def get_keybinding_manager() -> KeybindingManager:
    """Get the global KeybindingManager instance."""
    global _manager
    if _manager is None:
        _manager = KeybindingManager()
        _manager.load()
    return _manager


def reload_keybindings() -> KeybindingManager:
    """Reload keybindings from disk."""
    global _manager
    _manager = KeybindingManager()
    _manager.load()
    return _manager
