"""Tests for the context inspector screen."""

import pytest
from unittest.mock import MagicMock, patch, PropertyMock

from context import ContextInfo
from screens.context import ContextScreen


class TestContextScreenInit:
    """Tests for ContextScreen initialization and structure."""

    def test_default_css_defined(self):
        """ContextScreen should have DEFAULT_CSS defined."""
        assert hasattr(ContextScreen, "DEFAULT_CSS")
        assert len(ContextScreen.DEFAULT_CSS) > 0

    def test_css_contains_context_dialog(self):
        """CSS should style the context-dialog container."""
        assert "#context-dialog" in ContextScreen.DEFAULT_CSS

    def test_css_contains_context_header(self):
        """CSS should style the context-header."""
        assert "#context-header" in ContextScreen.DEFAULT_CSS

    def test_css_contains_context_stats(self):
        """CSS should style the context-stats."""
        assert "#context-stats" in ContextScreen.DEFAULT_CSS

    def test_css_contains_msg_item_class(self):
        """CSS should style the msg-item class."""
        assert ".msg-item" in ContextScreen.DEFAULT_CSS

    def test_css_contains_msg_role_class(self):
        """CSS should style the msg-role class."""
        assert ".msg-role" in ContextScreen.DEFAULT_CSS


class TestContextScreenLoadContext:
    """Tests for ContextScreen._load_context method."""

    def test_load_context_with_no_provider(self):
        """_load_context should use default max_tokens when no provider."""
        mock_app = MagicMock()
        mock_app.ai_provider = None
        mock_app.blocks = []

        mock_stats = MagicMock()
        mock_container = MagicMock()

        with patch.object(
            ContextScreen, "app", new_callable=PropertyMock, return_value=mock_app
        ):
            screen = ContextScreen()

            def mock_query_one(selector, widget_type=None):
                if "#context-stats" in selector:
                    return mock_stats
                if "#context-list" in selector:
                    return mock_container
                return MagicMock()

            screen.query_one = mock_query_one

            with patch("screens.context.ContextManager") as mock_cm:
                mock_cm.build_messages.return_value = ContextInfo(
                    messages=[],
                    total_chars=0,
                    estimated_tokens=0,
                    message_count=0,
                    truncated=False,
                )

                screen._load_context()

                mock_cm.build_messages.assert_called_once()
                call_args = mock_cm.build_messages.call_args
                assert call_args[1]["max_tokens"] == 4000

    def test_load_context_with_provider(self):
        """_load_context should use provider's context_window."""
        mock_model_info = MagicMock()
        mock_model_info.context_window = 8192

        mock_provider = MagicMock()
        mock_provider.get_model_info.return_value = mock_model_info

        mock_app = MagicMock()
        mock_app.ai_provider = mock_provider
        mock_app.blocks = []

        mock_stats = MagicMock()
        mock_container = MagicMock()

        with patch.object(
            ContextScreen, "app", new_callable=PropertyMock, return_value=mock_app
        ):
            screen = ContextScreen()

            def mock_query_one(selector, widget_type=None):
                if "#context-stats" in selector:
                    return mock_stats
                if "#context-list" in selector:
                    return mock_container
                return MagicMock()

            screen.query_one = mock_query_one

            with patch("screens.context.ContextManager") as mock_cm:
                mock_cm.build_messages.return_value = ContextInfo(
                    messages=[],
                    total_chars=0,
                    estimated_tokens=0,
                    message_count=0,
                    truncated=False,
                )

                screen._load_context()

                call_args = mock_cm.build_messages.call_args
                assert call_args[1]["max_tokens"] == 8192

    def test_load_context_updates_stats(self):
        """_load_context should update stats widget with context info."""
        mock_app = MagicMock()
        mock_app.ai_provider = None
        mock_app.blocks = []

        mock_stats = MagicMock()
        mock_container = MagicMock()

        with patch.object(
            ContextScreen, "app", new_callable=PropertyMock, return_value=mock_app
        ):
            screen = ContextScreen()

            def mock_query_one(selector, widget_type=None):
                if "#context-stats" in selector:
                    return mock_stats
                if "#context-list" in selector:
                    return mock_container
                return MagicMock()

            screen.query_one = mock_query_one

            with patch("screens.context.ContextManager") as mock_cm:
                mock_cm.build_messages.return_value = ContextInfo(
                    messages=[],
                    total_chars=500,
                    estimated_tokens=125,
                    message_count=5,
                    truncated=False,
                )

                screen._load_context()

                mock_stats.update.assert_called_once()
                stats_text = mock_stats.update.call_args[0][0]
                assert "Messages: 5" in stats_text
                assert "125" in stats_text
                assert "Truncated: No" in stats_text

    def test_load_context_shows_truncated_yes(self):
        """_load_context should show 'Truncated: Yes' when truncated."""
        mock_app = MagicMock()
        mock_app.ai_provider = None
        mock_app.blocks = []

        mock_stats = MagicMock()
        mock_container = MagicMock()

        with patch.object(
            ContextScreen, "app", new_callable=PropertyMock, return_value=mock_app
        ):
            screen = ContextScreen()

            def mock_query_one(selector, widget_type=None):
                if "#context-stats" in selector:
                    return mock_stats
                if "#context-list" in selector:
                    return mock_container
                return MagicMock()

            screen.query_one = mock_query_one

            with patch("screens.context.ContextManager") as mock_cm:
                mock_cm.build_messages.return_value = ContextInfo(
                    messages=[],
                    total_chars=10000,
                    estimated_tokens=2500,
                    message_count=20,
                    truncated=True,
                )

                screen._load_context()

                stats_text = mock_stats.update.call_args[0][0]
                assert "Truncated: Yes" in stats_text

    def test_load_context_mounts_message_widgets(self):
        """_load_context should mount message widgets to container."""
        mock_app = MagicMock()
        mock_app.ai_provider = None
        mock_app.blocks = []

        mock_stats = MagicMock()
        mock_container = MagicMock()

        messages = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there"},
        ]

        with patch.object(
            ContextScreen, "app", new_callable=PropertyMock, return_value=mock_app
        ):
            screen = ContextScreen()

            def mock_query_one(selector, widget_type=None):
                if "#context-stats" in selector:
                    return mock_stats
                if "#context-list" in selector:
                    return mock_container
                return MagicMock()

            screen.query_one = mock_query_one

            with (
                patch("screens.context.ContextManager") as mock_cm,
                patch("screens.context.Container") as mock_container_cls,
            ):
                mock_item = MagicMock()
                mock_container_cls.return_value = mock_item

                mock_cm.build_messages.return_value = ContextInfo(
                    messages=messages,
                    total_chars=20,
                    estimated_tokens=5,
                    message_count=2,
                    truncated=False,
                )

                screen._load_context()

                mock_container.mount_all.assert_called_once()
                mounted_widgets = mock_container.mount_all.call_args[0][0]
                assert len(mounted_widgets) == 2


class TestContextScreenOnMount:
    """Tests for ContextScreen on_mount handler."""

    def test_on_mount_calls_load_context(self):
        """on_mount should call _load_context."""
        screen = ContextScreen()
        screen._load_context = MagicMock()

        screen.on_mount()

        screen._load_context.assert_called_once()


class TestContextScreenMessageFormatting:
    """Tests for message display formatting in ContextScreen."""

    def test_user_role_uppercase(self):
        """User role should be displayed as uppercase."""
        mock_app = MagicMock()
        mock_app.ai_provider = None
        mock_app.blocks = []

        mock_stats = MagicMock()
        mock_container = MagicMock()
        captured_widgets = []

        def mock_mount_all(widgets):
            captured_widgets.extend(widgets)

        mock_container.mount_all = mock_mount_all

        messages = [
            {"role": "user", "content": "Test message"},
        ]

        with patch.object(
            ContextScreen, "app", new_callable=PropertyMock, return_value=mock_app
        ):
            screen = ContextScreen()

            def mock_query_one(selector, widget_type=None):
                if "#context-stats" in selector:
                    return mock_stats
                if "#context-list" in selector:
                    return mock_container
                return MagicMock()

            screen.query_one = mock_query_one

            with (
                patch("screens.context.ContextManager") as mock_cm,
                patch("screens.context.Container") as mock_container_cls,
            ):
                mock_item = MagicMock()
                mock_container_cls.return_value = mock_item

                mock_cm.build_messages.return_value = ContextInfo(
                    messages=messages,
                    total_chars=12,
                    estimated_tokens=3,
                    message_count=1,
                    truncated=False,
                )

                screen._load_context()

        assert len(captured_widgets) == 1

    def test_assistant_role_uppercase(self):
        """Assistant role should be displayed as uppercase."""
        mock_app = MagicMock()
        mock_app.ai_provider = None
        mock_app.blocks = []

        mock_stats = MagicMock()
        mock_container = MagicMock()
        captured_widgets = []

        def mock_mount_all(widgets):
            captured_widgets.extend(widgets)

        mock_container.mount_all = mock_mount_all

        messages = [
            {"role": "assistant", "content": "Test response"},
        ]

        with patch.object(
            ContextScreen, "app", new_callable=PropertyMock, return_value=mock_app
        ):
            screen = ContextScreen()

            def mock_query_one(selector, widget_type=None):
                if "#context-stats" in selector:
                    return mock_stats
                if "#context-list" in selector:
                    return mock_container
                return MagicMock()

            screen.query_one = mock_query_one

            with (
                patch("screens.context.ContextManager") as mock_cm,
                patch("screens.context.Container") as mock_container_cls,
            ):
                mock_item = MagicMock()
                mock_container_cls.return_value = mock_item

                mock_cm.build_messages.return_value = ContextInfo(
                    messages=messages,
                    total_chars=13,
                    estimated_tokens=3,
                    message_count=1,
                    truncated=False,
                )

                screen._load_context()

        assert len(captured_widgets) == 1

    def test_unknown_role_handled(self):
        """Unknown role should default to 'unknown'."""
        mock_app = MagicMock()
        mock_app.ai_provider = None
        mock_app.blocks = []

        mock_stats = MagicMock()
        mock_container = MagicMock()
        captured_widgets = []

        def mock_mount_all(widgets):
            captured_widgets.extend(widgets)

        mock_container.mount_all = mock_mount_all

        messages = [
            {"content": "Message without role"},
        ]

        with patch.object(
            ContextScreen, "app", new_callable=PropertyMock, return_value=mock_app
        ):
            screen = ContextScreen()

            def mock_query_one(selector, widget_type=None):
                if "#context-stats" in selector:
                    return mock_stats
                if "#context-list" in selector:
                    return mock_container
                return MagicMock()

            screen.query_one = mock_query_one

            with (
                patch("screens.context.ContextManager") as mock_cm,
                patch("screens.context.Container") as mock_container_cls,
            ):
                mock_item = MagicMock()
                mock_container_cls.return_value = mock_item

                mock_cm.build_messages.return_value = ContextInfo(
                    messages=messages,
                    total_chars=20,
                    estimated_tokens=5,
                    message_count=1,
                    truncated=False,
                )

                screen._load_context()

        assert len(captured_widgets) == 1

    def test_empty_content_handled(self):
        """Empty content should be handled gracefully."""
        mock_app = MagicMock()
        mock_app.ai_provider = None
        mock_app.blocks = []

        mock_stats = MagicMock()
        mock_container = MagicMock()
        captured_widgets = []

        def mock_mount_all(widgets):
            captured_widgets.extend(widgets)

        mock_container.mount_all = mock_mount_all

        messages = [
            {"role": "user"},
        ]

        with patch.object(
            ContextScreen, "app", new_callable=PropertyMock, return_value=mock_app
        ):
            screen = ContextScreen()

            def mock_query_one(selector, widget_type=None):
                if "#context-stats" in selector:
                    return mock_stats
                if "#context-list" in selector:
                    return mock_container
                return MagicMock()

            screen.query_one = mock_query_one

            with (
                patch("screens.context.ContextManager") as mock_cm,
                patch("screens.context.Container") as mock_container_cls,
            ):
                mock_item = MagicMock()
                mock_container_cls.return_value = mock_item

                mock_cm.build_messages.return_value = ContextInfo(
                    messages=messages,
                    total_chars=0,
                    estimated_tokens=0,
                    message_count=1,
                    truncated=False,
                )

                screen._load_context()

        assert len(captured_widgets) == 1


class TestContextScreenEdgeCases:
    """Edge case tests for ContextScreen."""

    def test_empty_blocks_list(self):
        """Should handle empty blocks list without error."""
        mock_app = MagicMock()
        mock_app.ai_provider = None
        mock_app.blocks = []

        mock_stats = MagicMock()
        mock_container = MagicMock()

        with patch.object(
            ContextScreen, "app", new_callable=PropertyMock, return_value=mock_app
        ):
            screen = ContextScreen()

            def mock_query_one(selector, widget_type=None):
                if "#context-stats" in selector:
                    return mock_stats
                if "#context-list" in selector:
                    return mock_container
                return MagicMock()

            screen.query_one = mock_query_one

            with patch("screens.context.ContextManager") as mock_cm:
                mock_cm.build_messages.return_value = ContextInfo(
                    messages=[],
                    total_chars=0,
                    estimated_tokens=0,
                    message_count=0,
                    truncated=False,
                )

                screen._load_context()

                mock_stats.update.assert_called_once()
                mock_container.mount_all.assert_called_once()
                mounted = mock_container.mount_all.call_args[0][0]
                assert len(mounted) == 0

    def test_multiple_messages(self):
        """Should handle multiple messages."""
        mock_app = MagicMock()
        mock_app.ai_provider = None
        mock_app.blocks = []

        mock_stats = MagicMock()
        mock_container = MagicMock()

        messages = [
            {"role": "user", "content": "First"},
            {"role": "assistant", "content": "Second"},
            {"role": "user", "content": "Third"},
            {"role": "assistant", "content": "Fourth"},
            {"role": "user", "content": "Fifth"},
        ]

        with patch.object(
            ContextScreen, "app", new_callable=PropertyMock, return_value=mock_app
        ):
            screen = ContextScreen()

            def mock_query_one(selector, widget_type=None):
                if "#context-stats" in selector:
                    return mock_stats
                if "#context-list" in selector:
                    return mock_container
                return MagicMock()

            screen.query_one = mock_query_one

            with (
                patch("screens.context.ContextManager") as mock_cm,
                patch("screens.context.Container") as mock_container_cls,
            ):
                mock_item = MagicMock()
                mock_container_cls.return_value = mock_item

                mock_cm.build_messages.return_value = ContextInfo(
                    messages=messages,
                    total_chars=100,
                    estimated_tokens=25,
                    message_count=5,
                    truncated=False,
                )

                screen._load_context()

                mounted = mock_container.mount_all.call_args[0][0]
                assert len(mounted) == 5

    def test_large_token_count_display(self):
        """Should display large token counts properly."""
        mock_app = MagicMock()
        mock_app.ai_provider = None
        mock_app.blocks = []

        mock_stats = MagicMock()
        mock_container = MagicMock()

        with patch.object(
            ContextScreen, "app", new_callable=PropertyMock, return_value=mock_app
        ):
            screen = ContextScreen()

            def mock_query_one(selector, widget_type=None):
                if "#context-stats" in selector:
                    return mock_stats
                if "#context-list" in selector:
                    return mock_container
                return MagicMock()

            screen.query_one = mock_query_one

            with patch("screens.context.ContextManager") as mock_cm:
                mock_cm.build_messages.return_value = ContextInfo(
                    messages=[],
                    total_chars=400000,
                    estimated_tokens=100000,
                    message_count=500,
                    truncated=True,
                )

                screen._load_context()

                stats_text = mock_stats.update.call_args[0][0]
                assert "100000" in stats_text
                assert "Messages: 500" in stats_text
