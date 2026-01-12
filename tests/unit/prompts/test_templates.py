"""Tests for prompts/templates.py module."""

from pathlib import Path
from unittest.mock import patch


class TestBuiltinPrompts:
    """Tests for BUILTIN_PROMPTS loading and structure."""

    def test_builtin_prompts_contains_expected_keys(self):
        """BUILTIN_PROMPTS should contain all expected prompt keys."""
        from prompts.templates import BUILTIN_PROMPTS

        expected_keys = {"default", "concise", "agent", "code", "devops"}
        assert set(BUILTIN_PROMPTS.keys()) == expected_keys

    def test_each_prompt_has_required_fields(self):
        """Each prompt should have name, description, and content fields."""
        from prompts.templates import BUILTIN_PROMPTS

        for key, prompt in BUILTIN_PROMPTS.items():
            assert "name" in prompt, f"Prompt '{key}' missing 'name'"
            assert "description" in prompt, f"Prompt '{key}' missing 'description'"
            assert "content" in prompt, f"Prompt '{key}' missing 'content'"

    def test_prompt_content_is_non_empty_string(self):
        """Each prompt content should be a non-empty string."""
        from prompts.templates import BUILTIN_PROMPTS

        for key, prompt in BUILTIN_PROMPTS.items():
            assert isinstance(prompt["content"], str), (
                f"Prompt '{key}' content is not a string"
            )
            assert len(prompt["content"]) > 0, f"Prompt '{key}' content is empty"

    def test_prompt_names_are_human_readable(self):
        """Prompt names should be human-readable strings."""
        from prompts.templates import BUILTIN_PROMPTS

        for key, prompt in BUILTIN_PROMPTS.items():
            assert isinstance(prompt["name"], str)
            assert len(prompt["name"]) > 0
            # Names should not be all lowercase (they should be formatted)
            assert prompt["name"] != key or key.istitle()

    def test_prompt_descriptions_are_meaningful(self):
        """Prompt descriptions should provide useful information."""
        from prompts.templates import BUILTIN_PROMPTS

        for prompt in BUILTIN_PROMPTS.values():
            assert isinstance(prompt["description"], str)
            assert len(prompt["description"]) > 5  # More than just a word


class TestConvenienceAccessors:
    """Tests for backward compatibility convenience accessors."""

    def test_default_prompt_exists(self):
        """DEFAULT_PROMPT should be a non-empty string."""
        from prompts.templates import DEFAULT_PROMPT

        assert isinstance(DEFAULT_PROMPT, str)
        assert len(DEFAULT_PROMPT) > 0

    def test_concise_prompt_exists(self):
        """CONCISE_PROMPT should be a non-empty string."""
        from prompts.templates import CONCISE_PROMPT

        assert isinstance(CONCISE_PROMPT, str)
        assert len(CONCISE_PROMPT) > 0

    def test_agent_prompt_exists(self):
        """AGENT_PROMPT should be a non-empty string."""
        from prompts.templates import AGENT_PROMPT

        assert isinstance(AGENT_PROMPT, str)
        assert len(AGENT_PROMPT) > 0

    def test_code_prompt_exists(self):
        """CODE_PROMPT should be a non-empty string."""
        from prompts.templates import CODE_PROMPT

        assert isinstance(CODE_PROMPT, str)
        assert len(CODE_PROMPT) > 0

    def test_devops_prompt_exists(self):
        """DEVOPS_PROMPT should be a non-empty string."""
        from prompts.templates import DEVOPS_PROMPT

        assert isinstance(DEVOPS_PROMPT, str)
        assert len(DEVOPS_PROMPT) > 0

    def test_convenience_accessors_match_builtin_prompts(self):
        """Convenience accessors should match BUILTIN_PROMPTS content."""
        from prompts.templates import (
            AGENT_PROMPT,
            BUILTIN_PROMPTS,
            CODE_PROMPT,
            CONCISE_PROMPT,
            DEFAULT_PROMPT,
            DEVOPS_PROMPT,
        )

        assert DEFAULT_PROMPT == BUILTIN_PROMPTS["default"]["content"]
        assert CONCISE_PROMPT == BUILTIN_PROMPTS["concise"]["content"]
        assert AGENT_PROMPT == BUILTIN_PROMPTS["agent"]["content"]
        assert CODE_PROMPT == BUILTIN_PROMPTS["code"]["content"]
        assert DEVOPS_PROMPT == BUILTIN_PROMPTS["devops"]["content"]


class TestLoadPromptFile:
    """Tests for _load_prompt_file function."""

    def test_load_existing_prompt_file(self):
        """Should successfully load content from an existing file."""
        from prompts.templates import _load_prompt_file

        # The 'default' prompt file should exist
        result = _load_prompt_file("default")
        assert result is not None
        assert isinstance(result, str)
        assert len(result) > 0

    def test_load_nonexistent_prompt_file(self):
        """Should return None for non-existent file."""
        from prompts.templates import _load_prompt_file

        result = _load_prompt_file("nonexistent_prompt_xyz")
        assert result is None

    def test_load_all_builtin_files(self):
        """All expected builtin prompt files should be loadable."""
        from prompts.templates import _load_prompt_file

        for name in ["default", "concise", "agent", "code", "devops"]:
            result = _load_prompt_file(name)
            assert result is not None, f"Failed to load {name}.md"


class TestFallbacks:
    """Tests for fallback prompt content."""

    def test_fallback_prompts_exist(self):
        """All fallback prompts should be defined."""
        from prompts.templates import _FALLBACKS

        expected_keys = {"default", "concise", "agent", "code", "devops"}
        assert set(_FALLBACKS.keys()) == expected_keys

    def test_fallback_prompts_are_non_empty(self):
        """All fallback prompts should have content."""
        from prompts.templates import _FALLBACKS

        for key, content in _FALLBACKS.items():
            assert isinstance(content, str)
            assert len(content) > 0, f"Fallback '{key}' is empty"

    def test_prompt_meta_exists(self):
        """All prompt metadata should be defined."""
        from prompts.templates import _PROMPT_META

        expected_keys = {"default", "concise", "agent", "code", "devops"}
        assert set(_PROMPT_META.keys()) == expected_keys

    def test_prompt_meta_has_required_fields(self):
        """Each metadata entry should have name and description."""
        from prompts.templates import _PROMPT_META

        for key, meta in _PROMPT_META.items():
            assert "name" in meta, f"Meta '{key}' missing 'name'"
            assert "description" in meta, f"Meta '{key}' missing 'description'"


class TestLoadBuiltinPromptsWithMissingFiles:
    """Tests for fallback behavior when static files are missing."""

    def test_fallback_used_when_file_missing(self, temp_dir):
        """Should use fallback when static file doesn't exist."""
        # Create a mock static directory without files
        mock_static_dir = temp_dir / "static"
        mock_static_dir.mkdir()

        with patch("prompts.templates.STATIC_DIR", mock_static_dir):
            # Import after patching to test fresh loading
            from prompts.templates import _load_prompt_file

            # File doesn't exist, should return None
            result = _load_prompt_file("default")
            assert result is None

    def test_builtin_prompts_work_without_static_files(self, temp_dir):
        """BUILTIN_PROMPTS should still work with fallbacks when files missing."""
        # Create empty static directory
        mock_static_dir = temp_dir / "static"
        mock_static_dir.mkdir()

        with patch("prompts.templates.STATIC_DIR", mock_static_dir):
            from prompts.templates import _FALLBACKS, _load_builtin_prompts

            prompts = _load_builtin_prompts()

            # Should still have all prompts via fallback
            assert "default" in prompts
            assert prompts["default"]["content"] == _FALLBACKS["default"]


class TestStaticDir:
    """Tests for STATIC_DIR configuration."""

    def test_static_dir_is_path(self):
        """STATIC_DIR should be a Path object."""
        from prompts.templates import STATIC_DIR

        assert isinstance(STATIC_DIR, Path)

    def test_static_dir_points_to_correct_location(self):
        """STATIC_DIR should point to prompts/static directory."""
        from prompts.templates import STATIC_DIR

        assert STATIC_DIR.name == "static"
        assert STATIC_DIR.parent.name == "prompts"
