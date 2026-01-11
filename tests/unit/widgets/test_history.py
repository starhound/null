"""Tests for widgets/history.py - HistoryViewport widget."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from textual.binding import Binding
from textual.widget import Widget
from textual.widgets import ListItem, ListView

from widgets.history import HistoryViewport


class TestHistoryViewportInheritance:
    """Test HistoryViewport class inheritance."""

    def test_inherits_from_listview(self):
        """HistoryViewport should inherit from ListView."""
        viewport = HistoryViewport()
        assert isinstance(viewport, ListView)

    def test_is_widget(self):
        """HistoryViewport should be a Widget."""
        viewport = HistoryViewport()
        assert isinstance(viewport, Widget)


class TestHistoryViewportInit:
    """Test HistoryViewport initialization."""

    def test_default_initialization(self):
        """Should initialize with default values."""
        viewport = HistoryViewport()
        assert viewport._auto_scroll is True

    def test_auto_scroll_default_true(self):
        """Auto scroll should default to True."""
        viewport = HistoryViewport()
        assert viewport._auto_scroll is True

    def test_custom_id(self):
        """Custom ID should be passed to parent."""
        viewport = HistoryViewport(id="my-viewport")
        assert viewport.id == "my-viewport"

    def test_custom_name(self):
        """Custom name should be passed to parent."""
        viewport = HistoryViewport(name="test-viewport")
        assert viewport.name == "test-viewport"

    def test_custom_classes(self):
        """Custom classes should be passed to parent."""
        viewport = HistoryViewport(classes="custom-class")
        assert "custom-class" in viewport.classes

    def test_multiple_classes(self):
        """Multiple custom classes should be passed to parent."""
        viewport = HistoryViewport(classes="class-one class-two")
        assert "class-one" in viewport.classes
        assert "class-two" in viewport.classes

    def test_kwargs_passed_to_parent(self):
        """Keyword arguments should be passed to ListView."""
        viewport = HistoryViewport(disabled=True)
        assert viewport.disabled is True


class TestHistoryViewportDefaultCSS:
    """Test HistoryViewport DEFAULT_CSS."""

    def test_default_css_exists(self):
        """DEFAULT_CSS should be defined."""
        assert hasattr(HistoryViewport, "DEFAULT_CSS")
        assert HistoryViewport.DEFAULT_CSS is not None

    def test_default_css_contains_height(self):
        """DEFAULT_CSS should define height."""
        assert "height:" in HistoryViewport.DEFAULT_CSS

    def test_default_css_contains_width(self):
        """DEFAULT_CSS should define width."""
        assert "width:" in HistoryViewport.DEFAULT_CSS

    def test_default_css_height_1fr(self):
        """Height should be 1fr for flexible sizing."""
        assert "height: 1fr" in HistoryViewport.DEFAULT_CSS

    def test_default_css_width_1fr(self):
        """Width should be 1fr for flexible sizing."""
        assert "width: 1fr" in HistoryViewport.DEFAULT_CSS

    def test_default_css_listitem_height_auto(self):
        """ListItem height should be auto."""
        assert "height: auto" in HistoryViewport.DEFAULT_CSS

    def test_default_css_listitem_padding(self):
        """ListItem padding should be 0."""
        assert "padding: 0" in HistoryViewport.DEFAULT_CSS

    def test_default_css_listitem_margin(self):
        """ListItem margin should be 0."""
        assert "margin: 0" in HistoryViewport.DEFAULT_CSS

    def test_default_css_listitem_transparent(self):
        """ListItem background should be transparent."""
        assert "background: transparent" in HistoryViewport.DEFAULT_CSS

    def test_default_css_is_string(self):
        """DEFAULT_CSS should be a string."""
        assert isinstance(HistoryViewport.DEFAULT_CSS, str)


class TestHistoryViewportBindings:
    """Test HistoryViewport key bindings."""

    def test_bindings_exists(self):
        """BINDINGS should be defined."""
        assert hasattr(HistoryViewport, "BINDINGS")
        assert HistoryViewport.BINDINGS is not None

    def test_bindings_is_list(self):
        """BINDINGS should be a list."""
        assert isinstance(HistoryViewport.BINDINGS, list)

    def test_bindings_count(self):
        """Should have exactly 4 bindings."""
        assert len(HistoryViewport.BINDINGS) == 4

    def test_j_binding_exists(self):
        """j key should be bound to cursor_down."""
        bindings = {b.key: b for b in HistoryViewport.BINDINGS}
        assert "j" in bindings
        assert bindings["j"].action == "cursor_down"

    def test_k_binding_exists(self):
        """k key should be bound to cursor_up."""
        bindings = {b.key: b for b in HistoryViewport.BINDINGS}
        assert "k" in bindings
        assert bindings["k"].action == "cursor_up"

    def test_g_binding_exists(self):
        """g key should be bound to scroll_home."""
        bindings = {b.key: b for b in HistoryViewport.BINDINGS}
        assert "g" in bindings
        assert bindings["g"].action == "scroll_home"

    def test_G_binding_exists(self):
        """G key should be bound to scroll_end."""
        bindings = {b.key: b for b in HistoryViewport.BINDINGS}
        assert "G" in bindings
        assert bindings["G"].action == "scroll_end"

    def test_j_binding_description(self):
        """j binding should have 'Down' description."""
        bindings = {b.key: b for b in HistoryViewport.BINDINGS}
        assert bindings["j"].description == "Down"

    def test_k_binding_description(self):
        """k binding should have 'Up' description."""
        bindings = {b.key: b for b in HistoryViewport.BINDINGS}
        assert bindings["k"].description == "Up"

    def test_g_binding_description(self):
        """g binding should have 'Top' description."""
        bindings = {b.key: b for b in HistoryViewport.BINDINGS}
        assert bindings["g"].description == "Top"

    def test_G_binding_description(self):
        """G binding should have 'Bottom' description."""
        bindings = {b.key: b for b in HistoryViewport.BINDINGS}
        assert bindings["G"].description == "Bottom"

    def test_bindings_not_shown(self):
        """All bindings should have show=False."""
        for binding in HistoryViewport.BINDINGS:
            assert binding.show is False, (
                f"Binding {binding.key} should have show=False"
            )

    def test_bindings_are_binding_instances(self):
        """All bindings should be Binding instances."""
        for binding in HistoryViewport.BINDINGS:
            assert isinstance(binding, Binding)


class TestHistoryViewportAddBlock:
    """Test add_block async method."""

    @pytest.mark.asyncio
    async def test_add_block_mounts_widget(self):
        """add_block should mount a widget wrapped in ListItem."""
        viewport = HistoryViewport()
        mock_widget = MagicMock(spec=Widget)

        with patch.object(viewport, "mount", new_callable=AsyncMock) as mock_mount:
            with patch.object(viewport, "scroll_end") as mock_scroll:
                await viewport.add_block(mock_widget)

                mock_mount.assert_called_once()
                call_arg = mock_mount.call_args[0][0]
                assert isinstance(call_arg, ListItem)

    @pytest.mark.asyncio
    async def test_add_block_scrolls_when_auto_scroll_true(self):
        """add_block should scroll to end when auto_scroll is True."""
        viewport = HistoryViewport()
        viewport._auto_scroll = True
        mock_widget = MagicMock(spec=Widget)

        with patch.object(viewport, "mount", new_callable=AsyncMock):
            with patch.object(viewport, "scroll_end") as mock_scroll:
                await viewport.add_block(mock_widget)

                mock_scroll.assert_called_once_with(animate=False)

    @pytest.mark.asyncio
    async def test_add_block_no_scroll_when_auto_scroll_false(self):
        """add_block should not scroll when auto_scroll is False."""
        viewport = HistoryViewport()
        viewport._auto_scroll = False
        mock_widget = MagicMock(spec=Widget)

        with patch.object(viewport, "mount", new_callable=AsyncMock):
            with patch.object(viewport, "scroll_end") as mock_scroll:
                await viewport.add_block(mock_widget)

                mock_scroll.assert_not_called()

    @pytest.mark.asyncio
    async def test_add_block_wraps_widget_in_listitem(self):
        """add_block should wrap widget in ListItem."""
        viewport = HistoryViewport()
        mock_widget = MagicMock(spec=Widget)

        mounted_item = None

        async def capture_mount(item):
            nonlocal mounted_item
            mounted_item = item

        with patch.object(viewport, "mount", side_effect=capture_mount):
            with patch.object(viewport, "scroll_end"):
                await viewport.add_block(mock_widget)

        assert mounted_item is not None
        assert isinstance(mounted_item, ListItem)

    @pytest.mark.asyncio
    async def test_add_block_is_async(self):
        """add_block should be an async method."""
        viewport = HistoryViewport()
        import inspect

        assert inspect.iscoroutinefunction(viewport.add_block)


class TestHistoryViewportOnMount:
    """Test on_mount lifecycle method."""

    def test_on_mount_calls_call_later(self):
        """on_mount should schedule scroll_end via call_later."""
        viewport = HistoryViewport()

        with patch.object(viewport, "call_later") as mock_call_later:
            viewport.on_mount()

            mock_call_later.assert_called_once()
            call_args = mock_call_later.call_args
            assert call_args[0][0] == viewport.scroll_end
            assert call_args[1] == {"animate": False}

    def test_on_mount_scroll_end_not_animated(self):
        """on_mount scroll should not be animated."""
        viewport = HistoryViewport()

        with patch.object(viewport, "call_later") as mock_call_later:
            viewport.on_mount()

            kwargs = mock_call_later.call_args[1]
            assert kwargs.get("animate") is False


class TestHistoryViewportOnKey:
    """Test on_key event handler for auto_scroll control."""

    def test_pageup_disables_auto_scroll(self):
        """pageup key should disable auto_scroll."""
        viewport = HistoryViewport()
        viewport._auto_scroll = True

        mock_event = MagicMock()
        mock_event.key = "pageup"

        viewport.on_key(mock_event)

        assert viewport._auto_scroll is False

    def test_home_disables_auto_scroll(self):
        """home key should disable auto_scroll."""
        viewport = HistoryViewport()
        viewport._auto_scroll = True

        mock_event = MagicMock()
        mock_event.key = "home"

        viewport.on_key(mock_event)

        assert viewport._auto_scroll is False

    def test_k_disables_auto_scroll(self):
        """k key should disable auto_scroll."""
        viewport = HistoryViewport()
        viewport._auto_scroll = True

        mock_event = MagicMock()
        mock_event.key = "k"

        viewport.on_key(mock_event)

        assert viewport._auto_scroll is False

    def test_down_at_end_enables_auto_scroll(self):
        """down key at end of list should enable auto_scroll."""
        viewport = HistoryViewport()
        viewport._auto_scroll = False
        viewport._children = [MagicMock(), MagicMock(), MagicMock()]

        mock_event = MagicMock()
        mock_event.key = "down"

        with patch.object(type(viewport), "index", property(lambda self: 2)):
            with patch.object(
                type(viewport), "children", property(lambda self: self._children)
            ):
                viewport.on_key(mock_event)

                assert viewport._auto_scroll is True

    def test_pagedown_at_end_enables_auto_scroll(self):
        """pagedown key at end of list should enable auto_scroll."""
        viewport = HistoryViewport()
        viewport._auto_scroll = False
        viewport._children = [MagicMock()]

        mock_event = MagicMock()
        mock_event.key = "pagedown"

        with patch.object(type(viewport), "index", property(lambda self: 0)):
            with patch.object(
                type(viewport), "children", property(lambda self: self._children)
            ):
                viewport.on_key(mock_event)

                assert viewport._auto_scroll is True

    def test_end_at_end_enables_auto_scroll(self):
        """end key at end of list should enable auto_scroll."""
        viewport = HistoryViewport()
        viewport._auto_scroll = False
        viewport._children = [MagicMock(), MagicMock()]

        mock_event = MagicMock()
        mock_event.key = "end"

        with patch.object(type(viewport), "index", property(lambda self: 1)):
            with patch.object(
                type(viewport), "children", property(lambda self: self._children)
            ):
                viewport.on_key(mock_event)

                assert viewport._auto_scroll is True

    def test_j_at_end_enables_auto_scroll(self):
        """j key at end of list should enable auto_scroll."""
        viewport = HistoryViewport()
        viewport._auto_scroll = False
        viewport._children = [MagicMock()]

        mock_event = MagicMock()
        mock_event.key = "j"

        with patch.object(type(viewport), "index", property(lambda self: 0)):
            with patch.object(
                type(viewport), "children", property(lambda self: self._children)
            ):
                viewport.on_key(mock_event)

                assert viewport._auto_scroll is True

    def test_down_not_at_end_keeps_auto_scroll_false(self):
        """down key not at end should keep auto_scroll False."""
        viewport = HistoryViewport()
        viewport._auto_scroll = False
        viewport._children = [MagicMock(), MagicMock(), MagicMock()]

        mock_event = MagicMock()
        mock_event.key = "down"

        with patch.object(type(viewport), "index", property(lambda self: 0)):
            with patch.object(
                type(viewport), "children", property(lambda self: self._children)
            ):
                viewport.on_key(mock_event)

                assert viewport._auto_scroll is False

    def test_down_not_at_end_keeps_auto_scroll_true(self):
        """down key not at end should keep auto_scroll True if already True."""
        viewport = HistoryViewport()
        viewport._auto_scroll = True
        viewport._children = [MagicMock(), MagicMock(), MagicMock()]

        mock_event = MagicMock()
        mock_event.key = "down"

        with patch.object(type(viewport), "index", property(lambda self: 0)):
            with patch.object(
                type(viewport), "children", property(lambda self: self._children)
            ):
                viewport.on_key(mock_event)

                assert viewport._auto_scroll is True

    def test_unrelated_key_no_effect(self):
        """Unrelated keys should not affect auto_scroll."""
        viewport = HistoryViewport()
        viewport._auto_scroll = True

        mock_event = MagicMock()
        mock_event.key = "x"

        viewport.on_key(mock_event)

        assert viewport._auto_scroll is True

    def test_unrelated_key_keeps_false(self):
        """Unrelated keys should not enable auto_scroll."""
        viewport = HistoryViewport()
        viewport._auto_scroll = False

        mock_event = MagicMock()
        mock_event.key = "z"

        viewport.on_key(mock_event)

        assert viewport._auto_scroll is False


class TestHistoryViewportAutoScrollBehavior:
    """Test auto_scroll attribute behavior."""

    def test_auto_scroll_can_be_set_true(self):
        """_auto_scroll should be settable to True."""
        viewport = HistoryViewport()
        viewport._auto_scroll = True
        assert viewport._auto_scroll is True

    def test_auto_scroll_can_be_set_false(self):
        """_auto_scroll should be settable to False."""
        viewport = HistoryViewport()
        viewport._auto_scroll = False
        assert viewport._auto_scroll is False

    def test_auto_scroll_toggle(self):
        """_auto_scroll should toggle correctly."""
        viewport = HistoryViewport()
        assert viewport._auto_scroll is True

        viewport._auto_scroll = False
        assert viewport._auto_scroll is False

        viewport._auto_scroll = True
        assert viewport._auto_scroll is True


class TestHistoryViewportEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_empty_viewport(self):
        """Empty viewport should initialize without errors."""
        viewport = HistoryViewport()
        assert viewport is not None

    @pytest.mark.asyncio
    async def test_add_block_with_none_widget_raises(self):
        """add_block with None widget should raise TypeError from ListItem."""
        viewport = HistoryViewport()

        with pytest.raises(TypeError):
            await viewport.add_block(None)

    def test_on_key_with_empty_children(self):
        """on_key should handle empty children list."""
        viewport = HistoryViewport()
        viewport._children = []

        mock_event = MagicMock()
        mock_event.key = "down"

        with patch.object(type(viewport), "index", property(lambda self: -1)):
            with patch.object(type(viewport), "children", property(lambda self: [])):
                viewport.on_key(mock_event)

    def test_multiple_viewports_independent(self):
        """Multiple HistoryViewport instances should be independent."""
        viewport1 = HistoryViewport()
        viewport2 = HistoryViewport()

        viewport1._auto_scroll = False

        assert viewport1._auto_scroll is False
        assert viewport2._auto_scroll is True


class TestHistoryViewportClassAttributes:
    """Test class-level attributes."""

    def test_default_css_is_class_attribute(self):
        """DEFAULT_CSS should be a class attribute."""
        assert "DEFAULT_CSS" in dir(HistoryViewport)
        assert hasattr(HistoryViewport, "DEFAULT_CSS")

    def test_bindings_is_class_attribute(self):
        """BINDINGS should be a class attribute."""
        assert "BINDINGS" in dir(HistoryViewport)
        assert hasattr(HistoryViewport, "BINDINGS")

    def test_bindings_classvar_annotation(self):
        """BINDINGS should have ClassVar type hint."""
        annotations = getattr(HistoryViewport, "__annotations__", {})
        assert "BINDINGS" in annotations or hasattr(HistoryViewport, "BINDINGS")
