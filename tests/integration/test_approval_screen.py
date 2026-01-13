"""Integration tests for ToolApprovalScreen."""

import pytest

from app import NullApp
from screens.approval import ToolApprovalScreen


@pytest.fixture
async def approval_app(temp_home, mock_storage, mock_ai_components):
    """Create app with ToolApprovalScreen pushed."""
    app = NullApp()
    async with app.run_test(size=(120, 50)) as pilot:
        screen = ToolApprovalScreen(
            tool_calls=[{"name": "read_file", "arguments": {"path": "/tmp/test.txt"}}],
            iteration_number=1,
        )
        app.push_screen(screen)
        await pilot.pause()
        yield app, pilot, screen


class TestToolApprovalScreenIntegration:
    """Integration tests for ToolApprovalScreen."""

    @pytest.mark.asyncio
    async def test_displays_title(self, approval_app):
        """Test that approval title is displayed."""
        app, pilot, screen = approval_app

        title = screen.query_one("#approval-title")
        assert "Tool Approval Required" in str(title.content)

    @pytest.mark.asyncio
    async def test_displays_iteration_number(self, approval_app):
        """Test that iteration number is shown in subtitle."""
        app, pilot, screen = approval_app

        subtitle = screen.query_one("#approval-subtitle")
        assert "Iteration 1" in str(subtitle.content)

    @pytest.mark.asyncio
    async def test_displays_tool_name(self, approval_app):
        """Test that tool name is displayed."""
        app, pilot, screen = approval_app

        tool_name_label = screen.query_one(".tool-name")
        assert "read_file" in str(tool_name_label.content)

    @pytest.mark.asyncio
    async def test_approve_button_returns_approve(
        self, temp_home, mock_storage, mock_ai_components
    ):
        """Test that clicking Approve button returns 'approve'."""
        app = NullApp()
        result = None

        def capture_result(value: str) -> None:
            nonlocal result
            result = value

        async with app.run_test(size=(120, 50)) as pilot:
            screen = ToolApprovalScreen(
                tool_calls=[
                    {"name": "read_file", "arguments": {"path": "/tmp/test.txt"}}
                ]
            )
            app.push_screen(screen, callback=capture_result)
            await pilot.pause()

            approve_button = screen.query_one("#approve")
            await pilot.click(approve_button)
            await pilot.pause()

        assert result == "approve"

    @pytest.mark.asyncio
    async def test_approve_all_button_returns_approve_all(
        self, temp_home, mock_storage, mock_ai_components
    ):
        """Test that clicking Approve All button returns 'approve-all'."""
        app = NullApp()
        result = None

        def capture_result(value: str) -> None:
            nonlocal result
            result = value

        async with app.run_test(size=(120, 50)) as pilot:
            screen = ToolApprovalScreen(
                tool_calls=[
                    {"name": "write_file", "arguments": {"path": "/tmp/out.txt"}}
                ]
            )
            app.push_screen(screen, callback=capture_result)
            await pilot.pause()

            approve_all_button = screen.query_one("#approve-all")
            await pilot.click(approve_all_button)
            await pilot.pause()

        assert result == "approve-all"

    @pytest.mark.asyncio
    async def test_reject_button_returns_reject(
        self, temp_home, mock_storage, mock_ai_components
    ):
        """Test that clicking Reject button returns 'reject'."""
        app = NullApp()
        result = None

        def capture_result(value: str) -> None:
            nonlocal result
            result = value

        async with app.run_test(size=(120, 50)) as pilot:
            screen = ToolApprovalScreen(
                tool_calls=[{"name": "run_command", "arguments": {"cmd": "rm -rf /"}}]
            )
            app.push_screen(screen, callback=capture_result)
            await pilot.pause()

            reject_button = screen.query_one("#reject")
            await pilot.click(reject_button)
            await pilot.pause()

        assert result == "reject"

    @pytest.mark.asyncio
    async def test_cancel_button_returns_cancel(
        self, temp_home, mock_storage, mock_ai_components
    ):
        """Test that clicking Cancel button returns 'cancel'."""
        app = NullApp()
        result = None

        def capture_result(value: str) -> None:
            nonlocal result
            result = value

        async with app.run_test(size=(120, 50)) as pilot:
            screen = ToolApprovalScreen(
                tool_calls=[{"name": "read_file", "arguments": {"path": "/etc/passwd"}}]
            )
            app.push_screen(screen, callback=capture_result)
            await pilot.pause()

            cancel_button = screen.query_one("#cancel")
            await pilot.click(cancel_button)
            await pilot.pause()

        assert result == "cancel"

    @pytest.mark.asyncio
    async def test_enter_key_approves(
        self, temp_home, mock_storage, mock_ai_components
    ):
        """Test that Enter key triggers approve action."""
        app = NullApp()
        result = None

        def capture_result(value: str) -> None:
            nonlocal result
            result = value

        async with app.run_test(size=(120, 50)) as pilot:
            screen = ToolApprovalScreen(
                tool_calls=[
                    {"name": "read_file", "arguments": {"path": "/tmp/test.txt"}}
                ]
            )
            app.push_screen(screen, callback=capture_result)
            await pilot.pause()

            await pilot.press("enter")
            await pilot.pause()

        assert result == "approve"

    @pytest.mark.asyncio
    async def test_escape_key_cancels(
        self, temp_home, mock_storage, mock_ai_components
    ):
        """Test that Escape key triggers cancel action."""
        app = NullApp()
        result = None

        def capture_result(value: str) -> None:
            nonlocal result
            result = value

        async with app.run_test(size=(120, 50)) as pilot:
            screen = ToolApprovalScreen(
                tool_calls=[
                    {"name": "read_file", "arguments": {"path": "/tmp/test.txt"}}
                ]
            )
            app.push_screen(screen, callback=capture_result)
            await pilot.pause()

            await pilot.press("escape")
            await pilot.pause()

        assert result == "cancel"

    @pytest.mark.asyncio
    async def test_a_key_approves_all(
        self, temp_home, mock_storage, mock_ai_components
    ):
        """Test that 'a' key triggers approve all action."""
        app = NullApp()
        result = None

        def capture_result(value: str) -> None:
            nonlocal result
            result = value

        async with app.run_test(size=(120, 50)) as pilot:
            screen = ToolApprovalScreen(
                tool_calls=[
                    {"name": "read_file", "arguments": {"path": "/tmp/test.txt"}}
                ]
            )
            app.push_screen(screen, callback=capture_result)
            await pilot.pause()

            await pilot.press("a")
            await pilot.pause()

        assert result == "approve-all"

    @pytest.mark.asyncio
    async def test_r_key_rejects(self, temp_home, mock_storage, mock_ai_components):
        """Test that 'r' key triggers reject action."""
        app = NullApp()
        result = None

        def capture_result(value: str) -> None:
            nonlocal result
            result = value

        async with app.run_test(size=(120, 50)) as pilot:
            screen = ToolApprovalScreen(
                tool_calls=[
                    {"name": "read_file", "arguments": {"path": "/tmp/test.txt"}}
                ]
            )
            app.push_screen(screen, callback=capture_result)
            await pilot.pause()

            await pilot.press("r")
            await pilot.pause()

        assert result == "reject"

    @pytest.mark.asyncio
    async def test_multiple_tool_calls_displayed(
        self, temp_home, mock_storage, mock_ai_components
    ):
        """Test that multiple tool calls are all displayed."""
        app = NullApp()

        async with app.run_test(size=(120, 50)) as pilot:
            screen = ToolApprovalScreen(
                tool_calls=[
                    {"name": "read_file", "arguments": {"path": "/tmp/a.txt"}},
                    {
                        "name": "write_file",
                        "arguments": {"path": "/tmp/b.txt", "content": "hello"},
                    },
                    {"name": "run_command", "arguments": {"cmd": "ls -la"}},
                ],
                iteration_number=3,
            )
            app.push_screen(screen)
            await pilot.pause()

            # Should have 3 tool previews
            tool_names = screen.query(".tool-name")
            assert len(tool_names) == 3

    @pytest.mark.asyncio
    async def test_hint_label_displayed(self, approval_app):
        """Test that keyboard hint label is displayed."""
        app, pilot, screen = approval_app

        hint = screen.query_one("#approval-hint")
        hint_text = str(hint.content)
        assert "Enter" in hint_text
        assert "Approve" in hint_text

    @pytest.mark.asyncio
    async def test_approve_session_button_returns_approve_session(
        self, temp_home, mock_storage, mock_ai_components
    ):
        """Test that clicking Session button returns 'approve-session'."""
        app = NullApp()
        result = None

        def capture_result(value: str) -> None:
            nonlocal result
            result = value

        async with app.run_test(size=(120, 50)) as pilot:
            screen = ToolApprovalScreen(
                tool_calls=[
                    {"name": "read_file", "arguments": {"path": "/tmp/test.txt"}}
                ]
            )
            app.push_screen(screen, callback=capture_result)
            await pilot.pause()

            session_button = screen.query_one("#approve-session")
            await pilot.click(session_button)
            await pilot.pause()

        assert result == "approve-session"

    @pytest.mark.asyncio
    async def test_s_key_approves_session(
        self, temp_home, mock_storage, mock_ai_components
    ):
        """Test that 's' key triggers approve session action."""
        app = NullApp()
        result = None

        def capture_result(value: str) -> None:
            nonlocal result
            result = value

        async with app.run_test(size=(120, 50)) as pilot:
            screen = ToolApprovalScreen(
                tool_calls=[
                    {"name": "read_file", "arguments": {"path": "/tmp/test.txt"}}
                ]
            )
            app.push_screen(screen, callback=capture_result)
            await pilot.pause()

            await pilot.press("s")
            await pilot.pause()

        assert result == "approve-session"

    @pytest.mark.asyncio
    async def test_timeout_shows_in_subtitle(
        self, temp_home, mock_storage, mock_ai_components
    ):
        """Test that timeout is displayed in subtitle when provided."""
        app = NullApp()

        async with app.run_test(size=(120, 50)) as pilot:
            screen = ToolApprovalScreen(
                tool_calls=[
                    {"name": "read_file", "arguments": {"path": "/tmp/test.txt"}}
                ],
                timeout_seconds=30,
            )
            app.push_screen(screen)
            await pilot.pause()

            subtitle = screen.query_one("#approval-subtitle")
            subtitle_text = str(subtitle.content)
            assert "auto-reject in 30s" in subtitle_text

    @pytest.mark.asyncio
    async def test_timeout_auto_rejects(
        self, temp_home, mock_storage, mock_ai_components
    ):
        """Test that timeout triggers auto-reject."""
        import asyncio

        app = NullApp()
        result = None

        def capture_result(value: str) -> None:
            nonlocal result
            result = value

        async with app.run_test(size=(120, 50)) as pilot:
            screen = ToolApprovalScreen(
                tool_calls=[
                    {"name": "read_file", "arguments": {"path": "/tmp/test.txt"}}
                ],
                timeout_seconds=1,
            )
            app.push_screen(screen, callback=capture_result)
            await pilot.pause()

            await asyncio.sleep(1.5)
            await pilot.pause()

        assert result == "timeout"

    @pytest.mark.asyncio
    async def test_get_tool_names(self, temp_home, mock_storage, mock_ai_components):
        """Test that get_tool_names returns tool names from calls."""
        app = NullApp()

        async with app.run_test(size=(120, 50)) as pilot:
            screen = ToolApprovalScreen(
                tool_calls=[
                    {"name": "read_file", "arguments": {"path": "/tmp/a.txt"}},
                    {"name": "write_file", "arguments": {"path": "/tmp/b.txt"}},
                    {"name": "run_command", "arguments": {"cmd": "ls"}},
                ]
            )
            app.push_screen(screen)
            await pilot.pause()

            tool_names = screen.get_tool_names()
            assert tool_names == ["read_file", "write_file", "run_command"]
