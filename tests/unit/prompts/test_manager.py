"""Tests for prompts/manager.py module."""

import json
from pathlib import Path

import pytest


@pytest.fixture
def temp_prompts_dir(temp_dir):
    """Create a temporary prompts directory."""
    prompts_dir = temp_dir / ".null" / "prompts"
    prompts_dir.mkdir(parents=True, exist_ok=True)
    return prompts_dir


@pytest.fixture
def prompt_manager_with_temp_dir(temp_dir, monkeypatch):
    """Create a PromptManager with a temporary home directory."""
    monkeypatch.setattr(Path, "home", lambda: temp_dir)

    from prompts.manager import PromptManager

    return PromptManager()


class TestPromptManagerInit:
    """Tests for PromptManager initialization."""

    def test_creates_prompts_directory(self, temp_dir, monkeypatch):
        """Should create ~/.null/prompts directory if it doesn't exist."""
        monkeypatch.setattr(Path, "home", lambda: temp_dir)

        from prompts.manager import PromptManager

        PromptManager()

        expected_dir = temp_dir / ".null" / "prompts"
        assert expected_dir.exists()
        assert expected_dir.is_dir()

    def test_creates_example_files(self, temp_dir, monkeypatch):
        """Should create example prompt files on first init."""
        monkeypatch.setattr(Path, "home", lambda: temp_dir)

        from prompts.manager import PromptManager

        PromptManager()

        prompts_dir = temp_dir / ".null" / "prompts"
        example_md = prompts_dir / "example.md.example"
        example_json = prompts_dir / "example.json.example"

        assert example_md.exists()
        assert example_json.exists()

    def test_example_json_is_valid(self, temp_dir, monkeypatch):
        """Example JSON file should be valid JSON with expected structure."""
        monkeypatch.setattr(Path, "home", lambda: temp_dir)

        from prompts.manager import PromptManager

        PromptManager()

        example_json = temp_dir / ".null" / "prompts" / "example.json.example"
        data = json.loads(example_json.read_text())

        assert "name" in data
        assert "description" in data
        assert "content" in data
        assert "provider_overrides" in data


class TestLoadUserPrompts:
    """Tests for loading user-defined prompts."""

    def test_load_markdown_prompt(self, temp_prompts_dir, temp_dir, monkeypatch):
        """Should load .md files as prompts."""
        monkeypatch.setattr(Path, "home", lambda: temp_dir)

        # Create a test markdown prompt
        prompt_file = temp_prompts_dir / "my-prompt.md"
        prompt_file.write_text("# Custom Prompt\n\nYou are a helpful assistant.")

        from prompts.manager import PromptManager

        manager = PromptManager()

        prompts = manager.get_all_prompts()
        assert "my-prompt" in prompts
        assert (
            prompts["my-prompt"]["content"]
            == "# Custom Prompt\n\nYou are a helpful assistant."
        )
        assert prompts["my-prompt"]["source"] == str(prompt_file)

    def test_load_txt_prompt(self, temp_prompts_dir, temp_dir, monkeypatch):
        """Should load .txt files as prompts."""
        monkeypatch.setattr(Path, "home", lambda: temp_dir)

        # Create a test txt prompt
        prompt_file = temp_prompts_dir / "simple-prompt.txt"
        prompt_file.write_text("You are a simple assistant.")

        from prompts.manager import PromptManager

        manager = PromptManager()

        prompts = manager.get_all_prompts()
        assert "simple-prompt" in prompts
        assert prompts["simple-prompt"]["content"] == "You are a simple assistant."

    def test_load_json_prompt(self, temp_prompts_dir, temp_dir, monkeypatch):
        """Should load .json files with metadata."""
        monkeypatch.setattr(Path, "home", lambda: temp_dir)

        # Create a test JSON prompt
        prompt_data = {
            "name": "Advanced Prompt",
            "description": "A prompt with extra features",
            "content": "You are an advanced assistant.",
            "provider_overrides": {"ollama": {"temperature": 0.8}},
        }
        prompt_file = temp_prompts_dir / "advanced.json"
        prompt_file.write_text(json.dumps(prompt_data))

        from prompts.manager import PromptManager

        manager = PromptManager()

        prompts = manager.get_all_prompts()
        assert "advanced" in prompts
        assert prompts["advanced"]["name"] == "Advanced Prompt"
        assert prompts["advanced"]["description"] == "A prompt with extra features"
        assert prompts["advanced"]["content"] == "You are an advanced assistant."
        assert prompts["advanced"]["provider_overrides"] == {
            "ollama": {"temperature": 0.8}
        }

    def test_skip_example_files(self, temp_prompts_dir, temp_dir, monkeypatch):
        """Should skip files ending in .example."""
        monkeypatch.setattr(Path, "home", lambda: temp_dir)

        # Create both example and real prompts
        (temp_prompts_dir / "test.md.example").write_text("Example content")
        (temp_prompts_dir / "real.md").write_text("Real content")

        from prompts.manager import PromptManager

        manager = PromptManager()

        prompts = manager.get_all_prompts()
        assert "real" in prompts
        # Example files should not create a prompt
        assert "test.md" not in prompts
        assert "test" not in prompts

    def test_name_formatting_from_filename(
        self, temp_prompts_dir, temp_dir, monkeypatch
    ):
        """Prompt names should be formatted from filenames."""
        monkeypatch.setattr(Path, "home", lambda: temp_dir)

        (temp_prompts_dir / "my-custom-prompt.md").write_text("Content")
        (temp_prompts_dir / "another_prompt.txt").write_text("Content")

        from prompts.manager import PromptManager

        manager = PromptManager()

        prompts = manager.get_all_prompts()
        assert prompts["my-custom-prompt"]["name"] == "My Custom Prompt"
        assert prompts["another_prompt"]["name"] == "Another Prompt"

    def test_handle_invalid_json(self, temp_prompts_dir, temp_dir, monkeypatch):
        """Should gracefully handle invalid JSON files."""
        monkeypatch.setattr(Path, "home", lambda: temp_dir)

        (temp_prompts_dir / "invalid.json").write_text("not valid json {")

        from prompts.manager import PromptManager

        # Should not raise an exception
        manager = PromptManager()

        prompts = manager.get_all_prompts()
        assert "invalid" not in prompts


class TestGetPrompt:
    """Tests for getting individual prompts."""

    def test_get_builtin_prompt(self, prompt_manager_with_temp_dir):
        """Should retrieve built-in prompts."""
        manager = prompt_manager_with_temp_dir

        prompt = manager.get_prompt("default")
        assert prompt is not None
        assert "content" in prompt
        assert "name" in prompt

    def test_get_nonexistent_prompt(self, prompt_manager_with_temp_dir):
        """Should return None for non-existent prompts."""
        manager = prompt_manager_with_temp_dir

        prompt = manager.get_prompt("nonexistent_xyz_123")
        assert prompt is None

    def test_get_user_prompt(self, temp_prompts_dir, temp_dir, monkeypatch):
        """Should retrieve user-defined prompts."""
        monkeypatch.setattr(Path, "home", lambda: temp_dir)

        (temp_prompts_dir / "user-prompt.md").write_text("User content")

        from prompts.manager import PromptManager

        manager = PromptManager()

        prompt = manager.get_prompt("user-prompt")
        assert prompt is not None
        assert prompt["content"] == "User content"


class TestGetPromptContent:
    """Tests for getting prompt content with provider overrides."""

    def test_get_content_without_provider(self, prompt_manager_with_temp_dir):
        """Should return base content without provider."""
        manager = prompt_manager_with_temp_dir

        content = manager.get_prompt_content("default")
        assert isinstance(content, str)
        assert len(content) > 0

    def test_fallback_to_default_for_nonexistent(self, prompt_manager_with_temp_dir):
        """Should fall back to default prompt for non-existent key."""
        manager = prompt_manager_with_temp_dir

        from prompts.templates import BUILTIN_PROMPTS

        content = manager.get_prompt_content("nonexistent_xyz")
        assert content == BUILTIN_PROMPTS["default"]["content"]

    def test_provider_content_suffix(self, temp_prompts_dir, temp_dir, monkeypatch):
        """Should apply content_suffix for provider."""
        monkeypatch.setattr(Path, "home", lambda: temp_dir)

        prompt_data = {
            "name": "Test",
            "description": "Test prompt",
            "content": "Base content",
            "provider_overrides": {"ollama": {"content_suffix": "\nExtra for Ollama."}},
        }
        (temp_prompts_dir / "test.json").write_text(json.dumps(prompt_data))

        from prompts.manager import PromptManager

        manager = PromptManager()

        content = manager.get_prompt_content("test", provider="ollama")
        assert content == "Base content\nExtra for Ollama."

    def test_provider_content_prefix(self, temp_prompts_dir, temp_dir, monkeypatch):
        """Should apply content_prefix for provider."""
        monkeypatch.setattr(Path, "home", lambda: temp_dir)

        prompt_data = {
            "name": "Test",
            "description": "Test prompt",
            "content": "Base content",
            "provider_overrides": {"openai": {"content_prefix": "Prefix: "}},
        }
        (temp_prompts_dir / "test.json").write_text(json.dumps(prompt_data))

        from prompts.manager import PromptManager

        manager = PromptManager()

        content = manager.get_prompt_content("test", provider="openai")
        assert content == "Prefix: Base content"

    def test_provider_content_override(self, temp_prompts_dir, temp_dir, monkeypatch):
        """Should replace content for provider."""
        monkeypatch.setattr(Path, "home", lambda: temp_dir)

        prompt_data = {
            "name": "Test",
            "description": "Test prompt",
            "content": "Base content",
            "provider_overrides": {
                "anthropic": {"content": "Completely different content"}
            },
        }
        (temp_prompts_dir / "test.json").write_text(json.dumps(prompt_data))

        from prompts.manager import PromptManager

        manager = PromptManager()

        content = manager.get_prompt_content("test", provider="anthropic")
        assert content == "Completely different content"

    def test_no_override_for_unspecified_provider(
        self, temp_prompts_dir, temp_dir, monkeypatch
    ):
        """Should not apply overrides for unspecified provider."""
        monkeypatch.setattr(Path, "home", lambda: temp_dir)

        prompt_data = {
            "name": "Test",
            "description": "Test prompt",
            "content": "Base content",
            "provider_overrides": {"ollama": {"content_suffix": "\nOllama specific"}},
        }
        (temp_prompts_dir / "test.json").write_text(json.dumps(prompt_data))

        from prompts.manager import PromptManager

        manager = PromptManager()

        content = manager.get_prompt_content("test", provider="openai")
        assert content == "Base content"


class TestListPrompts:
    """Tests for listing all prompts."""

    def test_list_includes_builtin(self, prompt_manager_with_temp_dir):
        """Should include all built-in prompts."""
        manager = prompt_manager_with_temp_dir

        prompts = manager.list_prompts()
        keys = [p[0] for p in prompts]

        assert "default" in keys
        assert "concise" in keys
        assert "agent" in keys
        assert "code" in keys
        assert "devops" in keys

    def test_list_format(self, prompt_manager_with_temp_dir):
        """List should return tuples of (key, name, description, is_user)."""
        manager = prompt_manager_with_temp_dir

        prompts = manager.list_prompts()

        for prompt in prompts:
            assert len(prompt) == 4
            key, name, description, is_user = prompt
            assert isinstance(key, str)
            assert isinstance(name, str)
            assert isinstance(description, str)
            assert isinstance(is_user, bool)

    def test_builtin_marked_as_not_user(self, prompt_manager_with_temp_dir):
        """Built-in prompts should have is_user=False."""
        manager = prompt_manager_with_temp_dir

        prompts = manager.list_prompts()
        builtin_keys = {"default", "concise", "agent", "code", "devops"}

        for key, _name, _description, is_user in prompts:
            if key in builtin_keys:
                assert is_user is False

    def test_user_prompts_marked_as_user(self, temp_prompts_dir, temp_dir, monkeypatch):
        """User prompts should have is_user=True."""
        monkeypatch.setattr(Path, "home", lambda: temp_dir)

        (temp_prompts_dir / "custom.md").write_text("Custom content")

        from prompts.manager import PromptManager

        manager = PromptManager()

        prompts = manager.list_prompts()

        for key, _name, _description, is_user in prompts:
            if key == "custom":
                assert is_user is True
                break
        else:
            pytest.fail("Custom prompt not found in list")


class TestSavePrompt:
    """Tests for saving new prompts."""

    def test_save_creates_json_file(self, temp_prompts_dir, temp_dir, monkeypatch):
        """Should create a JSON file with prompt data."""
        monkeypatch.setattr(Path, "home", lambda: temp_dir)

        from prompts.manager import PromptManager

        manager = PromptManager()

        filepath = manager.save_prompt(
            key="new-prompt",
            name="New Prompt",
            description="A new test prompt",
            content="You are a test assistant.",
        )

        assert filepath.exists()
        assert filepath.name == "new-prompt.json"

        data = json.loads(filepath.read_text())
        assert data["name"] == "New Prompt"
        assert data["description"] == "A new test prompt"
        assert data["content"] == "You are a test assistant."

    def test_save_reloads_prompts(self, temp_prompts_dir, temp_dir, monkeypatch):
        """Saving should reload prompts so new one is available."""
        monkeypatch.setattr(Path, "home", lambda: temp_dir)

        from prompts.manager import PromptManager

        manager = PromptManager()

        manager.save_prompt(
            key="saved-prompt", name="Saved", description="Test", content="Content"
        )

        prompt = manager.get_prompt("saved-prompt")
        assert prompt is not None
        assert prompt["name"] == "Saved"


class TestDeletePrompt:
    """Tests for deleting prompts."""

    def test_cannot_delete_builtin(self, prompt_manager_with_temp_dir):
        """Should not allow deleting built-in prompts."""
        manager = prompt_manager_with_temp_dir

        result = manager.delete_prompt("default")
        assert result is False

    def test_delete_user_prompt(self, temp_prompts_dir, temp_dir, monkeypatch):
        """Should delete user-created prompts."""
        monkeypatch.setattr(Path, "home", lambda: temp_dir)

        prompt_file = temp_prompts_dir / "to-delete.md"
        prompt_file.write_text("Delete me")

        from prompts.manager import PromptManager

        manager = PromptManager()

        # Verify it exists first
        assert manager.get_prompt("to-delete") is not None

        result = manager.delete_prompt("to-delete")
        assert result is True
        assert not prompt_file.exists()
        assert manager.get_prompt("to-delete") is None

    def test_delete_nonexistent_returns_false(self, prompt_manager_with_temp_dir):
        """Should return False for non-existent prompts."""
        manager = prompt_manager_with_temp_dir

        result = manager.delete_prompt("nonexistent_xyz_123")
        assert result is False


class TestReload:
    """Tests for reloading prompts from disk."""

    def test_reload_picks_up_new_files(self, temp_prompts_dir, temp_dir, monkeypatch):
        """Reload should pick up newly created files."""
        monkeypatch.setattr(Path, "home", lambda: temp_dir)

        from prompts.manager import PromptManager

        manager = PromptManager()

        # Initially no user prompt
        assert manager.get_prompt("new-file") is None

        # Create file after init
        (temp_prompts_dir / "new-file.md").write_text("New content")

        # Reload and check
        manager.reload()
        prompt = manager.get_prompt("new-file")
        assert prompt is not None
        assert prompt["content"] == "New content"

    def test_reload_removes_deleted_files(
        self, temp_prompts_dir, temp_dir, monkeypatch
    ):
        """Reload should remove prompts for deleted files."""
        monkeypatch.setattr(Path, "home", lambda: temp_dir)

        # Create file before init
        prompt_file = temp_prompts_dir / "temp-prompt.md"
        prompt_file.write_text("Temporary")

        from prompts.manager import PromptManager

        manager = PromptManager()

        # Should exist
        assert manager.get_prompt("temp-prompt") is not None

        # Delete file
        prompt_file.unlink()

        # Reload
        manager.reload()
        assert manager.get_prompt("temp-prompt") is None


class TestGetPromptManager:
    """Tests for global prompt manager instance."""

    def test_returns_prompt_manager_instance(self, temp_dir, monkeypatch):
        """get_prompt_manager should return a PromptManager instance."""
        monkeypatch.setattr(Path, "home", lambda: temp_dir)

        # Reset global state
        import prompts.manager

        prompts.manager._manager = None

        from prompts.manager import PromptManager, get_prompt_manager

        manager = get_prompt_manager()
        assert isinstance(manager, PromptManager)

    def test_returns_same_instance(self, temp_dir, monkeypatch):
        """get_prompt_manager should return the same instance on repeated calls."""
        monkeypatch.setattr(Path, "home", lambda: temp_dir)

        # Reset global state
        import prompts.manager

        prompts.manager._manager = None

        from prompts.manager import get_prompt_manager

        manager1 = get_prompt_manager()
        manager2 = get_prompt_manager()
        assert manager1 is manager2


class TestGetAllPrompts:
    """Tests for getting all prompts (built-in + user)."""

    def test_includes_builtin_prompts(self, prompt_manager_with_temp_dir):
        """Should include all built-in prompts."""
        manager = prompt_manager_with_temp_dir

        prompts = manager.get_all_prompts()

        assert "default" in prompts
        assert "concise" in prompts
        assert "agent" in prompts
        assert "code" in prompts
        assert "devops" in prompts

    def test_includes_user_prompts(self, temp_prompts_dir, temp_dir, monkeypatch):
        """Should include user-defined prompts."""
        monkeypatch.setattr(Path, "home", lambda: temp_dir)

        (temp_prompts_dir / "user-custom.md").write_text("User content")

        from prompts.manager import PromptManager

        manager = PromptManager()

        prompts = manager.get_all_prompts()
        assert "user-custom" in prompts

    def test_user_prompts_override_builtin(
        self, temp_prompts_dir, temp_dir, monkeypatch
    ):
        """User prompts with same key should override built-in."""
        monkeypatch.setattr(Path, "home", lambda: temp_dir)

        # Create user prompt with same key as builtin
        (temp_prompts_dir / "default.md").write_text("User's default prompt")

        from prompts.manager import PromptManager

        manager = PromptManager()

        prompts = manager.get_all_prompts()
        assert prompts["default"]["content"] == "User's default prompt"
