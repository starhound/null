"""Integration tests for PromptsScreen (PromptEditorScreen)."""

import json
from unittest.mock import patch

import pytest
from textual.widgets import Button, Input, TextArea

from app import NullApp
from prompts.manager import PromptManager
from screens.prompts import PromptEditorScreen, PromptListItem


@pytest.fixture
def prompts_app(temp_home, mock_storage, mock_ai_components):
    """Fixture to create NullApp with PromptsScreen pushed."""
    import prompts as prompts_module

    prompts_module._manager = None

    with patch("app.Config._get_storage", return_value=mock_storage):
        with patch("handlers.input.Config._get_storage", return_value=mock_storage):
            app = NullApp()
            yield app, temp_home


def create_user_prompt(temp_home):
    """Helper to create a user prompt file."""
    prompts_dir = temp_home / ".null" / "prompts"
    prompts_dir.mkdir(parents=True, exist_ok=True)
    prompt_data = {
        "name": "Test User Prompt",
        "description": "A test user prompt",
        "content": "You are a test assistant.",
    }
    prompt_file = prompts_dir / "test-user.json"
    prompt_file.write_text(json.dumps(prompt_data, indent=2))
    return prompt_file


class TestPromptsScreenDisplay:
    """Tests for PromptsScreen display."""

    @pytest.mark.asyncio
    async def test_prompts_are_listed(self, prompts_app):
        """Test that prompts are listed in the ListView."""
        app, _ = prompts_app

        async with app.run_test(size=(120, 50)) as pilot:
            screen = PromptEditorScreen()
            app.push_screen(screen)
            await pilot.pause()

            prompt_list = screen.query_one("#prompt-list")
            items = list(prompt_list.query(PromptListItem))

            assert len(items) >= 5

            keys = [item.key for item in items]
            assert "default" in keys
            assert "concise" in keys
            assert "agent" in keys


class TestPromptsScreenSelection:
    """Tests for selecting prompts."""

    @pytest.mark.asyncio
    async def test_selecting_prompt_loads_details(self, prompts_app):
        """Test that selecting a prompt loads its details into the form."""
        app, _ = prompts_app

        async with app.run_test(size=(120, 50)) as pilot:
            screen = PromptEditorScreen()
            app.push_screen(screen)
            await pilot.pause()

            screen.load_prompt_details("default")
            await pilot.pause()

            name_input = screen.query_one("#prompt-name-input")
            assert name_input.value == "default"

    @pytest.mark.asyncio
    async def test_selecting_user_prompt(
        self, temp_home, mock_storage, mock_ai_components
    ):
        """Test that selecting a user prompt loads its details."""
        create_user_prompt(temp_home)

        fresh_pm = PromptManager()

        with patch("app.Config._get_storage", return_value=mock_storage):
            with patch("handlers.input.Config._get_storage", return_value=mock_storage):
                with patch("screens.prompts.get_prompt_manager", return_value=fresh_pm):
                    app = NullApp()

                    async with app.run_test(size=(120, 50)) as pilot:
                        screen = PromptEditorScreen()
                        app.push_screen(screen)
                        await pilot.pause()

                        prompt_list = screen.query_one("#prompt-list")
                        items = list(prompt_list.query(PromptListItem))

                        user_item = next(
                            (i for i in items if i.key == "test-user"), None
                        )
                        assert user_item is not None
                        assert user_item.is_user is True

                        screen.load_prompt_details("test-user")
                        await pilot.pause()

                        name_input = screen.query_one("#prompt-name-input")
                        desc_input = screen.query_one("#prompt-desc-input")
                        content_area = screen.query_one("#prompt-content-area")

                        assert name_input.value == "test-user"
                        assert desc_input.value == "A test user prompt"
                        assert content_area.text == "You are a test assistant."


class TestPromptsScreenCreate:
    """Tests for creating new prompts."""

    @pytest.mark.asyncio
    async def test_new_prompt_clears_form(self, prompts_app):
        """Test that clicking New clears the form."""
        app, _ = prompts_app

        async with app.run_test(size=(120, 50)) as pilot:
            screen = PromptEditorScreen()
            app.push_screen(screen)
            await pilot.pause()

            screen.load_prompt_details("default")
            await pilot.pause()

            screen.action_new_prompt()
            await pilot.pause()

            name_input = screen.query_one("#prompt-name-input")
            desc_input = screen.query_one("#prompt-desc-input")
            content_area = screen.query_one("#prompt-content-area")

            assert name_input.value == ""
            assert desc_input.value == ""
            assert content_area.text == ""
            assert screen.current_key is None

    @pytest.mark.asyncio
    async def test_save_new_prompt(self, temp_home, mock_storage, mock_ai_components):
        """Test saving a new prompt creates a file."""
        fresh_pm = PromptManager()

        with patch("app.Config._get_storage", return_value=mock_storage):
            with patch("handlers.input.Config._get_storage", return_value=mock_storage):
                with patch("screens.prompts.get_prompt_manager", return_value=fresh_pm):
                    app = NullApp()

                    async with app.run_test(size=(120, 50)) as pilot:
                        screen = PromptEditorScreen()
                        app.push_screen(screen)
                        await pilot.pause()

                        screen.action_new_prompt()
                        await pilot.pause()

                        name_input = screen.query_one("#prompt-name-input")
                        desc_input = screen.query_one("#prompt-desc-input")
                        content_area = screen.query_one("#prompt-content-area")

                        name_input.value = "my-new-prompt"
                        desc_input.value = "A brand new prompt"
                        content_area.text = "You are a custom assistant."
                        await pilot.pause()

                        screen.action_save_prompt()
                        await pilot.pause()

                        prompt_file = (
                            temp_home / ".null" / "prompts" / "my-new-prompt.json"
                        )
                        assert prompt_file.exists()

                        data = json.loads(prompt_file.read_text())
                        assert data["name"] == "my-new-prompt"
                        assert data["description"] == "A brand new prompt"
                        assert data["content"] == "You are a custom assistant."


class TestPromptsScreenEdit:
    """Tests for editing existing prompts."""

    @pytest.mark.asyncio
    async def test_edit_user_prompt(self, temp_home, mock_storage, mock_ai_components):
        """Test editing an existing user prompt."""
        prompt_file = create_user_prompt(temp_home)
        fresh_pm = PromptManager()

        with patch("app.Config._get_storage", return_value=mock_storage):
            with patch("handlers.input.Config._get_storage", return_value=mock_storage):
                with patch("screens.prompts.get_prompt_manager", return_value=fresh_pm):
                    app = NullApp()

                    async with app.run_test(size=(120, 50)) as pilot:
                        screen = PromptEditorScreen()
                        app.push_screen(screen)
                        await pilot.pause()

                        screen.load_prompt_details("test-user")
                        await pilot.pause()

                        content_area = screen.query_one("#prompt-content-area")
                        content_area.text = "You are an updated assistant."
                        await pilot.pause()

                        screen.action_save_prompt()
                        await pilot.pause()

                        data = json.loads(prompt_file.read_text())
                        assert data["content"] == "You are an updated assistant."

    @pytest.mark.asyncio
    async def test_delete_button_disabled_for_builtin(self, prompts_app):
        """Test that delete button is disabled for built-in prompts."""
        app, _ = prompts_app

        async with app.run_test(size=(120, 50)) as pilot:
            screen = PromptEditorScreen()
            app.push_screen(screen)
            await pilot.pause()

            screen.load_prompt_details("default")
            await pilot.pause()

            delete_btn = screen.query_one("#delete-btn")
            assert delete_btn.disabled is True

    @pytest.mark.asyncio
    async def test_delete_button_enabled_for_user_prompt(
        self, temp_home, mock_storage, mock_ai_components
    ):
        """Test that delete button is enabled for user prompts."""
        create_user_prompt(temp_home)
        fresh_pm = PromptManager()

        with patch("app.Config._get_storage", return_value=mock_storage):
            with patch("handlers.input.Config._get_storage", return_value=mock_storage):
                with patch("screens.prompts.get_prompt_manager", return_value=fresh_pm):
                    app = NullApp()

                    async with app.run_test(size=(120, 50)) as pilot:
                        screen = PromptEditorScreen()
                        app.push_screen(screen)
                        await pilot.pause()

                        screen.load_prompt_details("test-user")
                        await pilot.pause()

                        delete_btn = screen.query_one("#delete-btn")
                        assert delete_btn.disabled is False

    @pytest.mark.asyncio
    async def test_delete_user_prompt(
        self, temp_home, mock_storage, mock_ai_components
    ):
        """Test deleting a user prompt removes the file."""
        prompt_file = create_user_prompt(temp_home)
        fresh_pm = PromptManager()

        with patch("app.Config._get_storage", return_value=mock_storage):
            with patch("handlers.input.Config._get_storage", return_value=mock_storage):
                with patch("screens.prompts.get_prompt_manager", return_value=fresh_pm):
                    app = NullApp()

                    async with app.run_test(size=(120, 50)) as pilot:
                        screen = PromptEditorScreen()
                        app.push_screen(screen)
                        await pilot.pause()

                        screen.load_prompt_details("test-user")
                        await pilot.pause()

                        screen.action_delete_prompt()
                        await pilot.pause()

                        assert not prompt_file.exists()


class TestPromptsScreenDismiss:
    """Tests for dismissing the screen."""

    @pytest.mark.asyncio
    async def test_close_button_dismisses(self, prompts_app):
        """Test that Close button dismisses the screen."""
        app, _ = prompts_app

        async with app.run_test(size=(120, 50)) as pilot:
            screen = PromptEditorScreen()
            app.push_screen(screen)
            await pilot.pause()

            close_btn = screen.query_one("#close-btn")
            close_btn.press()
            await pilot.pause()

            assert app.screen is not screen

    @pytest.mark.asyncio
    async def test_escape_dismisses(self, prompts_app):
        """Test that Escape key dismisses the screen."""
        app, _ = prompts_app

        async with app.run_test(size=(120, 50)) as pilot:
            screen = PromptEditorScreen()
            app.push_screen(screen)
            await pilot.pause()

            await pilot.press("escape")
            await pilot.pause()

            assert app.screen is not screen
