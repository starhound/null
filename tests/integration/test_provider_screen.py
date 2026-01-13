"""Integration tests for ProviderConfigScreen interactions."""

import pytest
from textual.widgets import Button, Input, Label

from app import NullApp
from screens.provider import ProviderConfigScreen


@pytest.fixture
async def provider_screen_app(mock_storage, mock_ai_components):
    """Create app with ProviderConfigScreen open for a standard provider."""
    app = NullApp()
    async with app.run_test(size=(120, 50)) as pilot:
        # Use openai as a typical API key provider
        app.push_screen(ProviderConfigScreen("openai", {}))
        await pilot.pause()
        await pilot.pause()
        yield app, pilot


@pytest.fixture
async def oauth_provider_screen_app(mock_storage, mock_ai_components):
    """Create app with ProviderConfigScreen open for an OAuth provider."""
    app = NullApp()
    async with app.run_test(size=(120, 50)) as pilot:
        app.push_screen(ProviderConfigScreen("claude_oauth", {}))
        await pilot.pause()
        await pilot.pause()
        yield app, pilot


class TestProviderScreenOpens:
    """Test that ProviderConfigScreen can be opened."""

    @pytest.mark.asyncio
    async def test_screen_opens(self, provider_screen_app):
        """Screen should open without errors."""
        app, pilot = provider_screen_app
        screen = app.screen

        assert isinstance(screen, ProviderConfigScreen)

    @pytest.mark.asyncio
    async def test_screen_has_title(self, provider_screen_app):
        """Screen should display provider title."""
        app, pilot = provider_screen_app
        screen = app.screen

        title = screen.query_one("#config-title", Label)
        title_text = str(title.render())
        assert "OpenAI" in title_text or "Configure" in title_text


class TestInputFieldsExist:
    """Test that input fields exist and can be focused."""

    @pytest.mark.asyncio
    async def test_api_key_input_exists(self, provider_screen_app):
        """API key input should exist for API key providers."""
        app, pilot = provider_screen_app
        screen = app.screen

        api_key_input = screen.query_one("#api_key", Input)
        assert api_key_input is not None

    @pytest.mark.asyncio
    async def test_input_focusable(self, provider_screen_app):
        """Input fields should be focusable."""
        app, pilot = provider_screen_app
        screen = app.screen

        api_key_input = screen.query_one("#api_key", Input)
        api_key_input.focus()
        await pilot.pause()

        assert api_key_input.has_focus, "Input should be focusable"

    @pytest.mark.asyncio
    async def test_all_inputs_not_disabled(self, provider_screen_app):
        """All inputs should not be disabled."""
        app, pilot = provider_screen_app
        screen = app.screen

        inputs = list(screen.query(Input))
        assert len(inputs) > 0, "Should have at least one input"

        for inp in inputs:
            assert not inp.disabled, f"Input #{inp.id} should not be disabled"


class TestInputAcceptsText:
    """Test that input fields accept text input."""

    @pytest.mark.asyncio
    async def test_api_key_accepts_typing(self, provider_screen_app):
        """API key input should accept text."""
        app, pilot = provider_screen_app
        screen = app.screen

        api_key_input = screen.query_one("#api_key", Input)
        api_key_input.focus()
        await pilot.pause()

        # Clear and type new value
        api_key_input.value = ""
        await pilot.press("s", "k", "-", "t", "e", "s", "t")
        await pilot.pause()

        assert api_key_input.value == "sk-test", "Input should accept typing"

    @pytest.mark.asyncio
    async def test_input_password_masked(self, provider_screen_app):
        """API key input should be password masked."""
        app, pilot = provider_screen_app
        screen = app.screen

        api_key_input = screen.query_one("#api_key", Input)
        assert api_key_input.password, "API key input should be password masked"


class TestSaveButton:
    """Test that save button exists and can be clicked."""

    @pytest.mark.asyncio
    async def test_save_button_exists(self, provider_screen_app):
        """Save button should exist."""
        app, pilot = provider_screen_app
        screen = app.screen

        save_btn = screen.query_one("#save", Button)
        assert save_btn is not None

    @pytest.mark.asyncio
    async def test_save_button_focusable(self, provider_screen_app):
        """Save button should be focusable."""
        app, pilot = provider_screen_app
        screen = app.screen

        save_btn = screen.query_one("#save", Button)
        save_btn.focus()
        await pilot.pause()

        assert save_btn.has_focus, "Save button should be focusable"

    @pytest.mark.asyncio
    async def test_save_button_not_disabled_initially(self, provider_screen_app):
        """Save button should not be disabled initially."""
        app, pilot = provider_screen_app
        screen = app.screen

        save_btn = screen.query_one("#save", Button)
        assert not save_btn.disabled, "Save button should not be disabled initially"

    @pytest.mark.asyncio
    async def test_cancel_button_exists(self, provider_screen_app):
        """Cancel button should exist."""
        app, pilot = provider_screen_app
        screen = app.screen

        cancel_btn = screen.query_one("#cancel", Button)
        assert cancel_btn is not None


class TestOAuthProvider:
    """Test OAuth provider screen elements."""

    @pytest.mark.asyncio
    async def test_oauth_login_button_exists(self, oauth_provider_screen_app):
        """OAuth login button should exist for OAuth providers."""
        app, pilot = oauth_provider_screen_app
        screen = app.screen

        oauth_btn = screen.query_one("#oauth-login", Button)
        assert oauth_btn is not None

    @pytest.mark.asyncio
    async def test_oauth_login_button_focusable(self, oauth_provider_screen_app):
        """OAuth login button should be focusable."""
        app, pilot = oauth_provider_screen_app
        screen = app.screen

        oauth_btn = screen.query_one("#oauth-login", Button)
        oauth_btn.focus()
        await pilot.pause()

        assert oauth_btn.has_focus, "OAuth login button should be focusable"

    @pytest.mark.asyncio
    async def test_oauth_no_api_key_input(self, oauth_provider_screen_app):
        """OAuth provider should not have API key input."""
        app, pilot = oauth_provider_screen_app
        screen = app.screen

        inputs = list(screen.query(Input))
        assert len(inputs) == 0, "OAuth provider should not have input fields"


class TestMultiFieldProvider:
    """Test provider with multiple configuration fields."""

    @pytest.mark.asyncio
    async def test_azure_has_multiple_fields(self, mock_storage, mock_ai_components):
        """Azure provider should have multiple configuration fields."""
        app = NullApp()
        async with app.run_test(size=(120, 50)) as pilot:
            app.push_screen(ProviderConfigScreen("azure", {}))
            await pilot.pause()
            await pilot.pause()

            screen = app.screen
            inputs = list(screen.query(Input))

            # Azure has api_key, endpoint, api_version
            assert len(inputs) >= 3, "Azure should have multiple input fields"

            # Check specific fields exist
            api_key = screen.query_one("#api_key", Input)
            endpoint = screen.query_one("#endpoint", Input)
            api_version = screen.query_one("#api_version", Input)

            assert api_key is not None
            assert endpoint is not None
            assert api_version is not None
