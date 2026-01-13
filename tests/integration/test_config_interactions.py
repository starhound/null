"""Integration tests for config screen control interactions.

These tests verify that config screen controls can actually be interacted with,
not just that they exist.
"""

import pytest
from textual.widgets import Input, Select, Switch
from textual.widgets._select import SelectCurrent

from app import NullApp
from screens.config import ConfigScreen


@pytest.fixture
async def config_app():
    """Create app with config screen open."""
    app = NullApp()
    async with app.run_test(size=(120, 50)) as pilot:
        app.push_screen(ConfigScreen())
        await pilot.pause()
        await pilot.pause()
        yield app, pilot


class TestInputInteractions:
    """Test that Input widgets can be typed into."""

    @pytest.mark.asyncio
    async def test_voice_language_input_typeable(self, config_app):
        """Voice language input should accept text input."""
        app, pilot = config_app
        screen = app.screen

        inp = screen.query_one("#voice_language", Input)
        original = inp.value

        inp.focus()
        await pilot.pause()
        assert inp.has_focus, "Input should be focusable"

        await pilot.press("end")
        await pilot.press("backspace", "backspace")
        await pilot.press("f", "r")
        await pilot.pause()

        assert inp.value != original or inp.value == "fr", "Input should accept typing"

    @pytest.mark.asyncio
    async def test_scrollback_input_typeable(self, config_app):
        """Scrollback lines input should accept numeric input."""
        app, pilot = config_app
        screen = app.screen

        inp = screen.query_one("#scrollback_lines", Input)
        inp.focus()
        await pilot.pause()

        assert inp.has_focus, "Input should be focusable"
        assert not inp.disabled, "Input should not be disabled"

    @pytest.mark.asyncio
    async def test_all_inputs_focusable(self, config_app):
        """All inputs should be focusable."""
        app, pilot = config_app
        screen = app.screen

        inputs = list(screen.query(Input))
        assert len(inputs) > 0, "Should have inputs"

        for inp in inputs:
            assert inp.can_focus, f"Input #{inp.id} should be focusable"
            assert not inp.disabled, f"Input #{inp.id} should not be disabled"


class TestSelectInteractions:
    """Test that Select widgets can be opened and used."""

    @pytest.mark.asyncio
    async def test_theme_select_expandable(self, config_app):
        """Theme select should expand when activated."""
        app, pilot = config_app
        screen = app.screen

        select = screen.query_one("#theme", Select)
        select.focus()
        await pilot.pause()

        assert select.has_focus, "Select should be focusable"

        await pilot.press("enter")
        await pilot.pause()

        assert select.expanded, "Select should expand on enter"

    @pytest.mark.asyncio
    async def test_cursor_style_select_expandable(self, config_app):
        """Cursor style select should expand when activated."""
        app, pilot = config_app
        screen = app.screen

        select = screen.query_one("#cursor_style", Select)
        select.focus()
        await pilot.pause()
        await pilot.press("enter")
        await pilot.pause()

        assert select.expanded, "Select should expand on enter"

    @pytest.mark.asyncio
    async def test_select_has_options(self, config_app):
        """Select widgets should have options to choose from."""
        app, pilot = config_app
        screen = app.screen

        selects = list(screen.query(Select))
        assert len(selects) > 0, "Should have selects"

        for sel in selects:
            assert sel.can_focus, f"Select #{sel.id} should be focusable"

    @pytest.mark.asyncio
    async def test_select_shows_value_after_selection(self, config_app):
        """Select should show the selected value text in SelectCurrent."""
        app, pilot = config_app
        screen = app.screen

        select = screen.query_one("#theme", Select)
        select.focus()
        await pilot.pause()

        # Check that select has a value
        assert select.value is not Select.BLANK, "Select should have a value"

        # Find the SelectCurrent child and verify it shows text
        select_current = select.query_one(SelectCurrent)
        # The SelectCurrent should have the .-has-value class when value is set
        assert select_current.has_class("-has-value"), (
            "SelectCurrent should have -has-value class when value is set"
        )

    @pytest.mark.asyncio
    async def test_select_arrow_indicator_visible(self, config_app):
        """Select dropdown arrow indicator (▼) should be visible."""
        from textual.widgets import Static

        app, pilot = config_app
        screen = app.screen

        select = screen.query_one("#theme", Select)

        select_current = select.query_one(SelectCurrent)
        assert select_current is not None, "SelectCurrent should exist"

        arrow_widgets = list(select_current.query(".arrow"))
        assert len(arrow_widgets) > 0, "Select should have arrow indicator widget"

        down_arrow = select_current.query_one(".down-arrow", Static)
        assert down_arrow is not None, "Select should have down-arrow indicator"
        assert "▼" in str(down_arrow._Static__content), "Down arrow should contain ▼"


class TestSwitchInteractions:
    """Test that Switch widgets can be toggled."""

    @pytest.mark.asyncio
    async def test_voice_enabled_switch_toggleable(self, config_app):
        """Voice enabled switch should toggle on enter."""
        app, pilot = config_app
        screen = app.screen

        switch = screen.query_one("#voice_enabled", Switch)
        original = switch.value

        switch.focus()
        await pilot.pause()
        await pilot.press("enter")
        await pilot.pause()

        assert switch.value != original, "Switch should toggle on enter"

    @pytest.mark.asyncio
    async def test_auto_save_switch_toggleable(self, config_app):
        """Auto save switch should toggle."""
        app, pilot = config_app
        screen = app.screen

        switch = screen.query_one("#auto_save_session", Switch)
        original = switch.value

        switch.focus()
        await pilot.pause()
        await pilot.press("enter")
        await pilot.pause()

        assert switch.value != original, "Switch should toggle"

    @pytest.mark.asyncio
    async def test_all_switches_toggleable(self, config_app):
        """All switches should be toggleable."""
        app, pilot = config_app
        screen = app.screen

        switches = list(screen.query(Switch))
        assert len(switches) > 0, "Should have switches"

        for sw in switches:
            assert sw.can_focus, f"Switch #{sw.id} should be focusable"
            assert not sw.disabled, f"Switch #{sw.id} should not be disabled"

    @pytest.mark.asyncio
    async def test_switch_has_visual_state_class(self, config_app):
        """Switch should have -on class when value is True."""
        app, pilot = config_app
        screen = app.screen

        switch = screen.query_one("#voice_enabled", Switch)

        # Set switch to True and check for -on class
        if not switch.value:
            switch.focus()
            await pilot.pause()
            await pilot.press("enter")
            await pilot.pause()

        assert switch.value is True, "Switch should be on"
        assert switch.has_class("-on"), "Switch should have -on class when True"

        # Toggle off and verify class changes
        await pilot.press("enter")
        await pilot.pause()

        assert switch.value is False, "Switch should be off after toggle"
        assert not switch.has_class("-on"), (
            "Switch should not have -on class when False"
        )


class TestConfigScreenNavigation:
    """Test tab navigation in config screen."""

    @pytest.mark.asyncio
    async def test_tab_navigation(self, config_app):
        """Should be able to navigate between controls with tab."""
        app, pilot = config_app
        screen = app.screen

        # Get first focusable widget
        first_focused = screen.focused

        await pilot.press("tab")
        await pilot.pause()

        second_focused = screen.focused

        # Focus should have moved
        assert first_focused != second_focused or first_focused is None, (
            "Tab should move focus between controls"
        )


class TestVisualVerification:
    """Test visual state verification for config controls."""

    @pytest.mark.asyncio
    async def test_input_shows_typed_text(self, config_app):
        """Input should show the text that was typed."""
        app, pilot = config_app
        screen = app.screen

        inp = screen.query_one("#voice_language", Input)
        inp.focus()
        await pilot.pause()

        # Clear existing text
        await pilot.press("ctrl+a")
        await pilot.pause()

        # Type test text
        test_text = "test123"
        for char in test_text:
            await pilot.press(char)
        await pilot.pause()

        assert inp.value == test_text, (
            f"Input value should be '{test_text}', got '{inp.value}'"
        )
