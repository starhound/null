"""Tests for themes.py module."""

import json
from pathlib import Path
from unittest.mock import patch

import pytest
from textual.theme import Theme


@pytest.fixture
def temp_themes_dir(temp_dir):
    """Create a temporary themes directory structure."""
    builtin_dir = temp_dir / "styles" / "themes"
    builtin_dir.mkdir(parents=True, exist_ok=True)

    user_dir = temp_dir / ".null" / "themes"
    user_dir.mkdir(parents=True, exist_ok=True)

    return builtin_dir, user_dir


@pytest.fixture
def sample_theme_data():
    """Sample valid theme data."""
    return {
        "name": "test-theme",
        "description": "A test theme",
        "dark": True,
        "primary": "#FF0000",
        "secondary": "#00FF00",
        "accent": "#0000FF",
        "foreground": "#FFFFFF",
        "background": "#000000",
        "surface": "#111111",
        "panel": "#222222",
        "success": "#00FF00",
        "warning": "#FFFF00",
        "error": "#FF0000",
        "boost": "#00FFFF",
        "luminosity_spread": 0.15,
        "text_alpha": 0.95,
        "variables": {"custom-var": "#AABBCC"},
    }


@pytest.fixture
def minimal_theme_data():
    """Minimal valid theme data (only required fields)."""
    return {"name": "minimal-theme", "primary": "#FF0000"}


class TestLoadThemeFromDict:
    """Tests for _load_theme_from_dict function."""

    def test_load_complete_theme(self, sample_theme_data):
        """Should create Theme from complete data."""
        from themes import _load_theme_from_dict

        theme = _load_theme_from_dict(sample_theme_data)

        assert theme is not None
        assert isinstance(theme, Theme)
        assert theme.name == "test-theme"
        assert theme.dark is True
        assert theme.primary == "#FF0000"

    def test_load_minimal_theme(self, minimal_theme_data):
        """Should create Theme with only required fields."""
        from themes import _load_theme_from_dict

        theme = _load_theme_from_dict(minimal_theme_data)

        assert theme is not None
        assert theme.name == "minimal-theme"
        assert theme.primary == "#FF0000"
        # Default value for dark
        assert theme.dark is True

    def test_use_fallback_name(self):
        """Should use fallback name if not in data."""
        from themes import _load_theme_from_dict

        data = {"primary": "#FF0000"}
        theme = _load_theme_from_dict(data, name_fallback="fallback-name")

        assert theme is not None
        assert theme.name == "fallback-name"

    def test_returns_none_without_primary(self):
        """Should return None if primary color is missing."""
        from themes import _load_theme_from_dict

        data = {"name": "no-primary", "secondary": "#00FF00"}
        theme = _load_theme_from_dict(data)

        assert theme is None

    def test_returns_none_for_empty_primary(self):
        """Should return None if primary is empty string."""
        from themes import _load_theme_from_dict

        data = {"name": "empty-primary", "primary": ""}
        theme = _load_theme_from_dict(data)

        assert theme is None

    def test_handles_invalid_data(self):
        """Should return None for completely invalid data."""
        from themes import _load_theme_from_dict

        # Invalid color format might cause Theme to fail
        # But should be caught and return None
        theme = _load_theme_from_dict({})
        assert theme is None

    def test_loads_variables(self, sample_theme_data):
        """Should load custom variables from data."""
        from themes import _load_theme_from_dict

        theme = _load_theme_from_dict(sample_theme_data)

        assert theme is not None
        assert theme.variables is not None
        assert "custom-var" in theme.variables

    def test_loads_luminosity_spread(self, sample_theme_data):
        """Should load luminosity_spread from data."""
        from themes import _load_theme_from_dict

        theme = _load_theme_from_dict(sample_theme_data)

        assert theme is not None
        assert theme.luminosity_spread == 0.15

    def test_default_luminosity_spread(self, minimal_theme_data):
        """Should use default luminosity_spread if not specified."""
        from themes import _load_theme_from_dict

        theme = _load_theme_from_dict(minimal_theme_data)

        assert theme is not None
        assert theme.luminosity_spread == 0.15  # Default value


class TestLoadThemeFile:
    """Tests for _load_theme_file function."""

    def test_load_valid_theme_file(self, temp_dir, sample_theme_data):
        """Should load theme from valid JSON file."""
        from themes import _load_theme_file

        theme_file = temp_dir / "valid-theme.json"
        theme_file.write_text(json.dumps(sample_theme_data))

        theme, data = _load_theme_file(theme_file)

        assert theme is not None
        assert data is not None
        assert theme.name == "test-theme"
        assert data["primary"] == "#FF0000"

    def test_load_nonexistent_file(self, temp_dir):
        """Should return None for non-existent file."""
        from themes import _load_theme_file

        theme_file = temp_dir / "nonexistent.json"

        theme, data = _load_theme_file(theme_file)

        assert theme is None
        assert data is None

    def test_load_invalid_json(self, temp_dir):
        """Should return None for invalid JSON."""
        from themes import _load_theme_file

        theme_file = temp_dir / "invalid.json"
        theme_file.write_text("not valid json {")

        theme, data = _load_theme_file(theme_file)

        assert theme is None
        assert data is None

    def test_use_filename_as_fallback_name(self, temp_dir):
        """Should use filename stem as fallback name."""
        from themes import _load_theme_file

        # Theme data without name
        data = {"primary": "#FF0000"}
        theme_file = temp_dir / "my-theme-name.json"
        theme_file.write_text(json.dumps(data))

        theme, _ = _load_theme_file(theme_file)

        assert theme is not None
        assert theme.name == "my-theme-name"


class TestLoadBuiltinThemes:
    """Tests for _load_builtin_themes function."""

    def test_load_from_styles_themes(self):
        """Should load themes from styles/themes directory."""
        from themes import _load_builtin_themes

        themes = _load_builtin_themes()

        # There should be at least some themes
        # Based on the project, we expect null-dark, null-warm, etc.
        assert isinstance(themes, dict)
        # If the themes directory exists and has files, should have themes
        if themes:
            for name, theme in themes.items():
                assert isinstance(theme, Theme)
                assert isinstance(name, str)

    def test_returns_empty_dict_if_no_dir(self, temp_dir):
        """Should return empty dict if themes directory doesn't exist."""
        fake_dir = temp_dir / "nonexistent" / "themes"

        with patch("themes.BUILTIN_THEMES_DIR", fake_dir):
            from themes import _load_builtin_themes

            themes = _load_builtin_themes()
            assert themes == {}

    def test_loads_all_json_files(self, temp_themes_dir, sample_theme_data):
        """Should load all .json files in directory."""
        builtin_dir, _ = temp_themes_dir

        # Create multiple theme files
        for i in range(3):
            theme_data = sample_theme_data.copy()
            theme_data["name"] = f"theme-{i}"
            (builtin_dir / f"theme-{i}.json").write_text(json.dumps(theme_data))

        with patch("themes.BUILTIN_THEMES_DIR", builtin_dir):
            from themes import _load_builtin_themes

            themes = _load_builtin_themes()

            assert len(themes) == 3
            assert "theme-0" in themes
            assert "theme-1" in themes
            assert "theme-2" in themes


class TestLoadUserThemes:
    """Tests for load_user_themes function."""

    def test_creates_user_themes_dir(self, temp_dir, monkeypatch):
        """Should create user themes directory if it doesn't exist."""
        user_themes_dir = temp_dir / ".null" / "themes"
        monkeypatch.setattr("themes.USER_THEMES_DIR", user_themes_dir)

        # Ensure directory doesn't exist
        assert not user_themes_dir.exists()

        from themes import load_user_themes

        load_user_themes()

        assert user_themes_dir.exists()

    def test_loads_user_theme_files(self, temp_dir, sample_theme_data, monkeypatch):
        """Should load theme files from user directory."""
        user_themes_dir = temp_dir / ".null" / "themes"
        user_themes_dir.mkdir(parents=True, exist_ok=True)

        # Create marker file to skip example creation
        (user_themes_dir / ".initialized").write_text("initialized")

        # Create user theme
        sample_theme_data["name"] = "user-theme"
        (user_themes_dir / "user-theme.json").write_text(json.dumps(sample_theme_data))

        monkeypatch.setattr("themes.USER_THEMES_DIR", user_themes_dir)
        # Also mock BUILTIN_THEMES_DIR to prevent copying
        monkeypatch.setattr("themes.BUILTIN_THEMES_DIR", temp_dir / "nonexistent")

        from themes import load_user_themes

        themes = load_user_themes()

        assert "user-theme" in themes
        assert themes["user-theme"].primary == "#FF0000"

    def test_skips_example_files(self, temp_dir, sample_theme_data, monkeypatch):
        """Should skip files ending in .example."""
        user_themes_dir = temp_dir / ".null" / "themes"
        user_themes_dir.mkdir(parents=True, exist_ok=True)
        (user_themes_dir / ".initialized").write_text("initialized")

        # Create example and real theme
        sample_theme_data["name"] = "example-theme"
        (user_themes_dir / "example-theme.json.example").write_text(
            json.dumps(sample_theme_data)
        )

        sample_theme_data["name"] = "real-theme"
        (user_themes_dir / "real-theme.json").write_text(json.dumps(sample_theme_data))

        monkeypatch.setattr("themes.USER_THEMES_DIR", user_themes_dir)
        monkeypatch.setattr("themes.BUILTIN_THEMES_DIR", temp_dir / "nonexistent")

        from themes import load_user_themes

        themes = load_user_themes()

        assert "real-theme" in themes
        assert "example-theme" not in themes


class TestGetBuiltinThemes:
    """Tests for get_builtin_themes function."""

    def test_returns_dict_of_themes(self):
        """Should return dictionary of Theme objects."""
        from themes import get_builtin_themes

        themes = get_builtin_themes()

        assert isinstance(themes, dict)
        for _name, theme in themes.items():
            assert isinstance(theme, Theme)


class TestGetAllThemes:
    """Tests for get_all_themes function."""

    def test_includes_builtin_themes(self):
        """Should include built-in themes."""
        from themes import get_all_themes, get_builtin_themes

        all_themes = get_all_themes()
        builtin_themes = get_builtin_themes()

        # All builtin should be in all (unless overridden)
        for name in builtin_themes:
            assert name in all_themes

    def test_user_themes_override_builtin(
        self, temp_dir, sample_theme_data, monkeypatch
    ):
        """User themes should override built-in themes with same name."""
        builtin_dir = temp_dir / "builtin"
        user_dir = temp_dir / ".null" / "themes"

        builtin_dir.mkdir(parents=True)
        user_dir.mkdir(parents=True)
        (user_dir / ".initialized").write_text("initialized")

        # Create builtin theme
        builtin_data = sample_theme_data.copy()
        builtin_data["name"] = "shared-name"
        builtin_data["primary"] = "#111111"
        (builtin_dir / "shared-name.json").write_text(json.dumps(builtin_data))

        # Create user theme with same name but different primary
        user_data = sample_theme_data.copy()
        user_data["name"] = "shared-name"
        user_data["primary"] = "#999999"
        (user_dir / "shared-name.json").write_text(json.dumps(user_data))

        monkeypatch.setattr("themes.BUILTIN_THEMES_DIR", builtin_dir)
        monkeypatch.setattr("themes.USER_THEMES_DIR", user_dir)

        from themes import get_all_themes

        themes = get_all_themes()

        assert themes["shared-name"].primary == "#999999"  # User override


class TestGetAllThemesWithFallback:
    """Tests for get_all_themes_with_fallback function."""

    def test_returns_themes_when_available(self):
        """Should return themes when they exist."""
        from themes import get_all_themes_with_fallback

        themes = get_all_themes_with_fallback()

        assert isinstance(themes, dict)
        assert len(themes) > 0

    def test_includes_null_dark_fallback_when_no_themes(self, temp_dir, monkeypatch):
        """Should include null-dark fallback when no themes found."""
        # Point to empty directories
        monkeypatch.setattr("themes.BUILTIN_THEMES_DIR", temp_dir / "empty1")
        monkeypatch.setattr("themes.USER_THEMES_DIR", temp_dir / "empty2")
        (temp_dir / "empty2").mkdir()
        (temp_dir / "empty2" / ".initialized").write_text("initialized")

        from themes import get_all_themes_with_fallback

        themes = get_all_themes_with_fallback()

        assert "null-dark" in themes
        assert isinstance(themes["null-dark"], Theme)


class TestFallbackTheme:
    """Tests for fallback null-dark theme."""

    def test_fallback_theme_is_valid(self):
        """Fallback theme should be a valid Theme object."""
        from themes import _FALLBACK_NULL_DARK

        assert isinstance(_FALLBACK_NULL_DARK, Theme)
        assert _FALLBACK_NULL_DARK.name == "null-dark"
        assert _FALLBACK_NULL_DARK.dark is True
        assert _FALLBACK_NULL_DARK.primary is not None


class TestBuiltinThemesConstant:
    """Tests for BUILTIN_THEMES constant."""

    def test_builtin_themes_is_dict(self):
        """BUILTIN_THEMES should be a dictionary."""
        from themes import BUILTIN_THEMES

        assert isinstance(BUILTIN_THEMES, dict)

    def test_builtin_themes_contains_null_dark(self):
        """BUILTIN_THEMES should contain at least null-dark."""
        from themes import BUILTIN_THEMES

        assert "null-dark" in BUILTIN_THEMES

    def test_builtin_themes_all_valid(self):
        """All themes in BUILTIN_THEMES should be Theme objects."""
        from themes import BUILTIN_THEMES

        for name, theme in BUILTIN_THEMES.items():
            assert isinstance(theme, Theme), f"{name} is not a Theme"


class TestThemesConstant:
    """Tests for THEMES constant (backward compatibility)."""

    def test_themes_equals_builtin_themes(self):
        """THEMES should equal BUILTIN_THEMES for compatibility."""
        from themes import BUILTIN_THEMES, THEMES

        assert THEMES == BUILTIN_THEMES


class TestEnsureUserThemesDir:
    """Tests for _ensure_user_themes_dir function."""

    def test_creates_directory(self, temp_dir, monkeypatch):
        """Should create user themes directory."""
        user_dir = temp_dir / ".null" / "themes"
        monkeypatch.setattr("themes.USER_THEMES_DIR", user_dir)
        monkeypatch.setattr("themes.BUILTIN_THEMES_DIR", temp_dir / "nonexistent")

        from themes import _ensure_user_themes_dir

        _ensure_user_themes_dir()

        assert user_dir.exists()

    def test_creates_initialized_marker(self, temp_dir, monkeypatch):
        """Should create .initialized marker file."""
        user_dir = temp_dir / ".null" / "themes"
        monkeypatch.setattr("themes.USER_THEMES_DIR", user_dir)
        monkeypatch.setattr("themes.BUILTIN_THEMES_DIR", temp_dir / "nonexistent")

        from themes import _ensure_user_themes_dir

        _ensure_user_themes_dir()

        marker = user_dir / ".initialized"
        assert marker.exists()

    def test_skips_if_already_initialized(
        self, temp_dir, sample_theme_data, monkeypatch
    ):
        """Should skip copying if .initialized exists."""
        user_dir = temp_dir / ".null" / "themes"
        builtin_dir = temp_dir / "builtin"

        user_dir.mkdir(parents=True)
        builtin_dir.mkdir(parents=True)

        # Create marker
        (user_dir / ".initialized").write_text("initialized")

        # Create builtin theme that would be copied
        (builtin_dir / "copy-me.json").write_text(json.dumps(sample_theme_data))

        monkeypatch.setattr("themes.USER_THEMES_DIR", user_dir)
        monkeypatch.setattr("themes.BUILTIN_THEMES_DIR", builtin_dir)

        from themes import _ensure_user_themes_dir

        _ensure_user_themes_dir()

        # Should NOT have copied the builtin theme
        assert not (user_dir / "copy-me.json").exists()


class TestCreateExampleTheme:
    """Tests for _create_example_theme function."""

    def test_creates_example_file(self, temp_dir):
        """Should create example theme file."""
        from themes import _create_example_theme

        _create_example_theme(temp_dir)

        example_file = temp_dir / "my-custom-theme.json.example"
        assert example_file.exists()

    def test_example_is_valid_json(self, temp_dir):
        """Example file should be valid JSON."""
        from themes import _create_example_theme

        _create_example_theme(temp_dir)

        example_file = temp_dir / "my-custom-theme.json.example"
        data = json.loads(example_file.read_text())

        assert "name" in data
        assert "primary" in data
        assert "dark" in data

    def test_example_theme_is_loadable(self, temp_dir):
        """Example theme should be loadable as a Theme."""
        from themes import _create_example_theme, _load_theme_from_dict

        _create_example_theme(temp_dir)

        example_file = temp_dir / "my-custom-theme.json.example"
        data = json.loads(example_file.read_text())

        theme = _load_theme_from_dict(data)
        assert theme is not None
        assert theme.name == "my-custom-theme"


class TestDirectoryConstants:
    """Tests for directory path constants."""

    def test_builtin_themes_dir_is_path(self):
        """BUILTIN_THEMES_DIR should be a Path object."""
        from themes import BUILTIN_THEMES_DIR

        assert isinstance(BUILTIN_THEMES_DIR, Path)

    def test_builtin_themes_dir_correct_location(self):
        """BUILTIN_THEMES_DIR should point to styles/themes."""
        from themes import BUILTIN_THEMES_DIR

        assert BUILTIN_THEMES_DIR.name == "themes"
        assert BUILTIN_THEMES_DIR.parent.name == "styles"

    def test_user_themes_dir_is_path(self):
        """USER_THEMES_DIR should be a Path object."""
        from themes import USER_THEMES_DIR

        assert isinstance(USER_THEMES_DIR, Path)

    def test_user_themes_dir_in_null_dir(self):
        """USER_THEMES_DIR should be in ~/.null/themes."""
        from themes import USER_THEMES_DIR

        assert USER_THEMES_DIR.name == "themes"
        assert USER_THEMES_DIR.parent.name == ".null"
