"""Tests for keybinding configuration."""

import json
import pytest
from pathlib import Path
from unittest.mock import patch

from config.keybindings import (
    DEFAULT_KEYBINDINGS,
    KeyBinding,
    KeybindingManager,
    KeyConflict,
    get_keybinding_manager,
    reload_keybindings,
)


class TestKeyBinding:
    def test_to_dict(self):
        binding = KeyBinding(
            id="test",
            key="ctrl+t",
            action="test_action",
            description="Test",
            context="app",
            show=True,
        )
        result = binding.to_dict()
        assert result["id"] == "test"
        assert result["key"] == "ctrl+t"
        assert result["action"] == "test_action"

    def test_from_dict(self):
        data = {
            "id": "test",
            "key": "ctrl+t",
            "action": "test_action",
            "description": "Test",
        }
        binding = KeyBinding.from_dict(data)
        assert binding.id == "test"
        assert binding.key == "ctrl+t"


class TestKeybindingManager:
    def test_load_defaults(self):
        manager = KeybindingManager()
        bindings = manager.get_all_bindings()
        assert len(bindings) == len(DEFAULT_KEYBINDINGS)

    def test_get_binding(self):
        manager = KeybindingManager()
        binding = manager.get_binding("help")
        assert binding is not None
        assert binding.key == "f1"
        assert binding.action == "open_help"

    def test_get_bindings_by_context(self):
        manager = KeybindingManager()
        app_bindings = manager.get_bindings_by_context("app")
        assert len(app_bindings) > 0
        assert all(b.context == "app" for b in app_bindings)

    def test_set_binding(self):
        manager = KeybindingManager()
        conflicts = manager.set_binding("help", "ctrl+h")
        assert manager.get_binding("help").key == "ctrl+h"

    def test_set_binding_conflict_detection(self):
        manager = KeybindingManager()
        conflicts = manager.set_binding("help", "f2")
        assert len(conflicts) == 1
        assert conflicts[0].key == "f2"

    def test_reset_binding(self):
        manager = KeybindingManager()
        manager.set_binding("help", "ctrl+h")
        assert manager.get_binding("help").key == "ctrl+h"
        manager.reset_binding("help")
        assert manager.get_binding("help").key == "f1"

    def test_is_modified(self):
        manager = KeybindingManager()
        assert not manager.is_modified("help")
        manager.set_binding("help", "ctrl+h")
        assert manager.is_modified("help")

    def test_get_default_key(self):
        manager = KeybindingManager()
        default = manager.get_default_key("help")
        assert default == "f1"

    def test_reset_to_defaults(self):
        manager = KeybindingManager()
        manager.set_binding("help", "ctrl+h")
        manager.set_binding("clear_history", "ctrl+k")
        manager.reset_to_defaults()
        assert manager.get_binding("help").key == "f1"
        assert manager.get_binding("clear_history").key == "ctrl+l"

    def test_get_keymap(self):
        manager = KeybindingManager()
        keymap = manager.get_keymap()
        assert "help" in keymap
        assert keymap["help"] == "f1"


class TestKeyNormalization:
    def test_normalize_simple(self):
        assert KeybindingManager.normalize_key("ctrl+c") == "ctrl+c"

    def test_normalize_uppercase(self):
        assert KeybindingManager.normalize_key("Ctrl+Shift+C") == "ctrl+shift+c"

    def test_normalize_spaces(self):
        assert KeybindingManager.normalize_key("ctrl + shift + c") == "ctrl+shift+c"

    def test_normalize_modifier_order(self):
        assert KeybindingManager.normalize_key("shift+ctrl+c") == "ctrl+shift+c"


class TestKeyValidation:
    def test_valid_simple_key(self):
        is_valid, _ = KeybindingManager.validate_key("a")
        assert is_valid

    def test_valid_modifier_key(self):
        is_valid, _ = KeybindingManager.validate_key("ctrl+a")
        assert is_valid

    def test_valid_multiple_modifiers(self):
        is_valid, _ = KeybindingManager.validate_key("ctrl+shift+a")
        assert is_valid

    def test_valid_function_key(self):
        is_valid, _ = KeybindingManager.validate_key("f1")
        assert is_valid

    def test_valid_special_key(self):
        is_valid, _ = KeybindingManager.validate_key("escape")
        assert is_valid

    def test_invalid_empty(self):
        is_valid, error = KeybindingManager.validate_key("")
        assert not is_valid
        assert "empty" in error.lower()

    def test_invalid_modifier_ignored(self):
        is_valid, _ = KeybindingManager.validate_key("badmod+a")
        assert is_valid

    def test_invalid_key(self):
        is_valid, error = KeybindingManager.validate_key("ctrl+invalidkey")
        assert not is_valid


class TestKeyDisplay:
    def test_format_simple(self):
        manager = KeybindingManager()
        assert manager.format_key_display("ctrl+s") == "Ctrl+S"

    def test_format_special_keys(self):
        manager = KeybindingManager()
        assert manager.format_key_display("escape") == "Esc"
        assert manager.format_key_display("backspace") == "Bksp"

    def test_format_function_key(self):
        manager = KeybindingManager()
        assert manager.format_key_display("f1") == "F1"


class TestConflictDetection:
    def test_detect_all_conflicts_no_conflicts(self):
        manager = KeybindingManager()
        conflicts = manager.detect_all_conflicts()
        assert len(conflicts) == 0

    def test_detect_conflicts_same_context(self):
        manager = KeybindingManager()
        manager.set_binding("help", "f2")
        conflicts = manager.detect_all_conflicts()
        assert len(conflicts) > 0


class TestKeyConflict:
    def test_description(self):
        bindings = [
            KeyBinding("a", "ctrl+a", "action_a", "Action A", "app"),
            KeyBinding("b", "ctrl+a", "action_b", "Action B", "app"),
        ]
        conflict = KeyConflict(key="ctrl+a", bindings=bindings)
        desc = conflict.description
        assert "ctrl+a" in desc
        assert "Action A" in desc
        assert "Action B" in desc


class TestPersistence:
    def test_save_and_load(self, tmp_path, monkeypatch):
        config_file = tmp_path / "keybindings.json"
        monkeypatch.setattr("config.keybindings.KEYBINDINGS_PATH", config_file)

        manager = KeybindingManager()
        manager.load()
        manager.set_binding("help", "ctrl+h")
        manager.save()

        assert config_file.exists()
        data = json.loads(config_file.read_text())
        assert data["bindings"]["help"] == "ctrl+h"

        manager2 = KeybindingManager()
        manager2.load()
        assert manager2.get_binding("help").key == "ctrl+h"

    def test_save_only_modified(self, tmp_path, monkeypatch):
        config_file = tmp_path / "keybindings.json"
        monkeypatch.setattr("config.keybindings.KEYBINDINGS_PATH", config_file)

        manager = KeybindingManager()
        manager.load()
        manager.set_binding("help", "ctrl+h")
        manager.save()

        data = json.loads(config_file.read_text())
        assert len(data["bindings"]) == 1
        assert "help" in data["bindings"]
