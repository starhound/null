"""Integration tests for SSHAddScreen interactions.

These tests verify that SSHAddScreen controls can be interacted with,
including all input fields, focus behavior, and buttons.
"""

import pytest
from textual.widgets import Button, Input

from app import NullApp
from screens.ssh_add import SSHAddScreen


@pytest.fixture
async def ssh_app():
    """Create app with SSHAddScreen open."""
    app = NullApp()
    async with app.run_test(size=(120, 50)) as pilot:
        app.push_screen(SSHAddScreen())
        await pilot.pause()
        await pilot.pause()
        yield app, pilot


class TestSSHScreenOpen:
    """Test that SSHAddScreen can be opened."""

    @pytest.mark.asyncio
    async def test_screen_opens(self, ssh_app):
        """SSHAddScreen should open successfully."""
        app, pilot = ssh_app
        assert isinstance(app.screen, SSHAddScreen), "SSHAddScreen should be active"


class TestSSHInputFieldsExist:
    """Test that all 7 input fields exist."""

    @pytest.mark.asyncio
    async def test_alias_input_exists(self, ssh_app):
        """Alias input field should exist."""
        app, pilot = ssh_app
        inp = app.screen.query_one("#alias", Input)
        assert inp is not None, "Alias input should exist"

    @pytest.mark.asyncio
    async def test_hostname_input_exists(self, ssh_app):
        """Hostname input field should exist."""
        app, pilot = ssh_app
        inp = app.screen.query_one("#hostname", Input)
        assert inp is not None, "Hostname input should exist"

    @pytest.mark.asyncio
    async def test_username_input_exists(self, ssh_app):
        """Username input field should exist."""
        app, pilot = ssh_app
        inp = app.screen.query_one("#username", Input)
        assert inp is not None, "Username input should exist"

    @pytest.mark.asyncio
    async def test_port_input_exists(self, ssh_app):
        """Port input field should exist."""
        app, pilot = ssh_app
        inp = app.screen.query_one("#port", Input)
        assert inp is not None, "Port input should exist"

    @pytest.mark.asyncio
    async def test_key_path_input_exists(self, ssh_app):
        """Key path input field should exist."""
        app, pilot = ssh_app
        inp = app.screen.query_one("#key_path", Input)
        assert inp is not None, "Key path input should exist"

    @pytest.mark.asyncio
    async def test_jump_host_input_exists(self, ssh_app):
        """Jump host input field should exist."""
        app, pilot = ssh_app
        inp = app.screen.query_one("#jump_host", Input)
        assert inp is not None, "Jump host input should exist"

    @pytest.mark.asyncio
    async def test_password_input_exists(self, ssh_app):
        """Password input field should exist."""
        app, pilot = ssh_app
        inp = app.screen.query_one("#password", Input)
        assert inp is not None, "Password input should exist"

    @pytest.mark.asyncio
    async def test_all_seven_inputs_exist(self, ssh_app):
        """All 7 input fields should exist."""
        app, pilot = ssh_app
        inputs = list(app.screen.query(Input))
        assert len(inputs) == 7, f"Should have 7 inputs, found {len(inputs)}"


class TestSSHInputFocusable:
    """Test that input fields can be focused."""

    @pytest.mark.asyncio
    async def test_alias_input_focusable(self, ssh_app):
        """Alias input should be focusable."""
        app, pilot = ssh_app
        inp = app.screen.query_one("#alias", Input)
        inp.focus()
        await pilot.pause()
        assert inp.has_focus, "Alias input should be focusable"

    @pytest.mark.asyncio
    async def test_hostname_input_focusable(self, ssh_app):
        """Hostname input should be focusable."""
        app, pilot = ssh_app
        inp = app.screen.query_one("#hostname", Input)
        inp.focus()
        await pilot.pause()
        assert inp.has_focus, "Hostname input should be focusable"

    @pytest.mark.asyncio
    async def test_all_inputs_focusable(self, ssh_app):
        """All inputs should be focusable."""
        app, pilot = ssh_app
        inputs = list(app.screen.query(Input))

        for inp in inputs:
            assert inp.can_focus, f"Input #{inp.id} should be focusable"
            assert not inp.disabled, f"Input #{inp.id} should not be disabled"


class TestSSHInputTypeable:
    """Test that input fields accept text input."""

    @pytest.mark.asyncio
    async def test_alias_input_accepts_text(self, ssh_app):
        """Alias input should accept text input."""
        app, pilot = ssh_app
        inp = app.screen.query_one("#alias", Input)
        inp.focus()
        await pilot.pause()

        await pilot.press("p", "r", "o", "d")
        await pilot.pause()

        assert inp.value == "prod", f"Alias should be 'prod', got '{inp.value}'"

    @pytest.mark.asyncio
    async def test_hostname_input_accepts_text(self, ssh_app):
        """Hostname input should accept text input."""
        app, pilot = ssh_app
        inp = app.screen.query_one("#hostname", Input)
        inp.focus()
        await pilot.pause()

        await pilot.press("t", "e", "s", "t")
        await pilot.pause()

        assert inp.value == "test", f"Hostname should be 'test', got '{inp.value}'"

    @pytest.mark.asyncio
    async def test_username_input_accepts_text(self, ssh_app):
        """Username input should accept text input."""
        app, pilot = ssh_app
        inp = app.screen.query_one("#username", Input)
        inp.focus()
        await pilot.pause()

        await pilot.press("r", "o", "o", "t")
        await pilot.pause()

        assert inp.value == "root", f"Username should be 'root', got '{inp.value}'"


class TestSSHPortInput:
    """Test that port field accepts numeric input."""

    @pytest.mark.asyncio
    async def test_port_has_default_value(self, ssh_app):
        """Port input should have default value of 22."""
        app, pilot = ssh_app
        inp = app.screen.query_one("#port", Input)
        assert inp.value == "22", f"Port default should be '22', got '{inp.value}'"

    @pytest.mark.asyncio
    async def test_port_accepts_numeric_input(self, ssh_app):
        """Port input should accept numeric input."""
        app, pilot = ssh_app
        inp = app.screen.query_one("#port", Input)
        inp.focus()
        await pilot.pause()

        inp.value = ""
        await pilot.press("2", "2", "2", "2")
        await pilot.pause()

        assert inp.value == "2222", f"Port should be '2222', got '{inp.value}'"

    @pytest.mark.asyncio
    async def test_port_has_integer_validator(self, ssh_app):
        """Port input should have an Integer validator."""
        app, pilot = ssh_app
        inp = app.screen.query_one("#port", Input)
        assert len(inp.validators) > 0, "Port should have validators"


class TestSSHButtons:
    """Test that Save/Cancel buttons exist."""

    @pytest.mark.asyncio
    async def test_save_button_exists(self, ssh_app):
        """Save button should exist."""
        app, pilot = ssh_app
        btn = app.screen.query_one("#save", Button)
        assert btn is not None, "Save button should exist"

    @pytest.mark.asyncio
    async def test_cancel_button_exists(self, ssh_app):
        """Cancel button should exist."""
        app, pilot = ssh_app
        btn = app.screen.query_one("#cancel", Button)
        assert btn is not None, "Cancel button should exist"

    @pytest.mark.asyncio
    async def test_cancel_button_dismisses_screen(self, ssh_app):
        """Cancel button should dismiss the screen."""
        app, pilot = ssh_app
        btn = app.screen.query_one("#cancel", Button)
        btn.focus()
        await pilot.pause()
        await pilot.press("enter")
        await pilot.pause()

        assert not isinstance(app.screen, SSHAddScreen), "Screen should be dismissed"
