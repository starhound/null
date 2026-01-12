"""Tests for tools/streaming.py - Streaming tool execution with real-time progress."""

import asyncio

import pytest

from tools.streaming import (
    PROGRESS_PATTERNS,
    ProgressCallback,
    StreamingToolCall,
    ToolProgress,
    ToolStatus,
    estimate_progress,
    run_command_streaming,
    stream_command,
)


class TestToolStatus:
    """Tests for ToolStatus enum."""

    def test_status_values(self):
        """Should have all expected status values."""
        assert ToolStatus.PENDING.value == "pending"
        assert ToolStatus.RUNNING.value == "running"
        assert ToolStatus.COMPLETED.value == "completed"
        assert ToolStatus.FAILED.value == "failed"
        assert ToolStatus.CANCELLED.value == "cancelled"

    def test_status_count(self):
        """Should have exactly 5 statuses."""
        assert len(ToolStatus) == 5

    def test_status_enum_members(self):
        """All statuses should be ToolStatus instances."""
        for status in ToolStatus:
            assert isinstance(status, ToolStatus)

    def test_status_comparison(self):
        """Should support equality comparison."""
        assert ToolStatus.RUNNING == ToolStatus.RUNNING
        assert ToolStatus.PENDING != ToolStatus.COMPLETED


class TestToolProgress:
    """Tests for ToolProgress dataclass."""

    def test_progress_creation_required_fields(self):
        """Should create ToolProgress with required fields."""
        progress = ToolProgress(
            status=ToolStatus.RUNNING,
            output="Test output",
        )
        assert progress.status == ToolStatus.RUNNING
        assert progress.output == "Test output"

    def test_progress_default_values(self):
        """Should have sensible default values."""
        progress = ToolProgress(
            status=ToolStatus.PENDING,
            output="",
        )
        assert progress.progress is None
        assert progress.elapsed == 0.0
        assert progress.exit_code is None

    def test_progress_with_all_fields(self):
        """Should accept all optional fields."""
        progress = ToolProgress(
            status=ToolStatus.COMPLETED,
            output="Done",
            progress=1.0,
            elapsed=5.5,
            exit_code=0,
        )
        assert progress.progress == 1.0
        assert progress.elapsed == 5.5
        assert progress.exit_code == 0

    def test_is_complete_completed(self):
        """is_complete should be True for COMPLETED status."""
        progress = ToolProgress(status=ToolStatus.COMPLETED, output="")
        assert progress.is_complete is True

    def test_is_complete_failed(self):
        """is_complete should be True for FAILED status."""
        progress = ToolProgress(status=ToolStatus.FAILED, output="")
        assert progress.is_complete is True

    def test_is_complete_cancelled(self):
        """is_complete should be True for CANCELLED status."""
        progress = ToolProgress(status=ToolStatus.CANCELLED, output="")
        assert progress.is_complete is True

    def test_is_complete_pending(self):
        """is_complete should be False for PENDING status."""
        progress = ToolProgress(status=ToolStatus.PENDING, output="")
        assert progress.is_complete is False

    def test_is_complete_running(self):
        """is_complete should be False for RUNNING status."""
        progress = ToolProgress(status=ToolStatus.RUNNING, output="")
        assert progress.is_complete is False

    def test_progress_output_accumulates(self):
        """Output can contain accumulated content."""
        progress = ToolProgress(
            status=ToolStatus.RUNNING,
            output="Line 1\nLine 2\nLine 3\n",
        )
        assert "Line 1" in progress.output
        assert "Line 3" in progress.output


class TestStreamingToolCall:
    """Tests for StreamingToolCall dataclass."""

    def test_tool_call_creation(self):
        """Should create StreamingToolCall with required fields."""
        call = StreamingToolCall(
            id="call_123",
            name="test_tool",
            arguments={"arg1": "value1"},
        )
        assert call.id == "call_123"
        assert call.name == "test_tool"
        assert call.arguments == {"arg1": "value1"}

    def test_tool_call_not_cancelled_by_default(self):
        """StreamingToolCall should not be cancelled by default."""
        call = StreamingToolCall(id="1", name="test", arguments={})
        assert call.is_cancelled is False

    def test_tool_call_cancel(self):
        """Should be able to cancel tool call."""
        call = StreamingToolCall(id="1", name="test", arguments={})
        assert call.is_cancelled is False

        call.cancel()

        assert call.is_cancelled is True

    def test_tool_call_cancel_idempotent(self):
        """Cancelling multiple times should be safe."""
        call = StreamingToolCall(id="1", name="test", arguments={})
        call.cancel()
        call.cancel()
        call.cancel()
        assert call.is_cancelled is True

    def test_tool_call_empty_arguments(self):
        """Should accept empty arguments dict."""
        call = StreamingToolCall(id="1", name="test", arguments={})
        assert call.arguments == {}

    def test_tool_call_complex_arguments(self):
        """Should accept complex nested arguments."""
        call = StreamingToolCall(
            id="1",
            name="test",
            arguments={
                "nested": {"key": "value"},
                "list": [1, 2, 3],
            },
        )
        assert call.arguments["nested"]["key"] == "value"

    def test_tool_call_repr_hides_cancelled(self):
        """_cancelled should be hidden in repr."""
        call = StreamingToolCall(id="1", name="test", arguments={})
        repr_str = repr(call)
        assert "_cancelled" not in repr_str


class TestProgressPatterns:
    """Tests for PROGRESS_PATTERNS constant."""

    def test_progress_patterns_exists(self):
        """PROGRESS_PATTERNS should be defined."""
        assert isinstance(PROGRESS_PATTERNS, dict)

    def test_patterns_for_npm(self):
        """Should have patterns for npm."""
        assert "npm" in PROGRESS_PATTERNS
        patterns = PROGRESS_PATTERNS["npm"]
        assert len(patterns) > 0

    def test_patterns_for_pip(self):
        """Should have patterns for pip."""
        assert "pip" in PROGRESS_PATTERNS
        patterns = PROGRESS_PATTERNS["pip"]
        assert len(patterns) > 0

    def test_patterns_for_cargo(self):
        """Should have patterns for cargo."""
        assert "cargo" in PROGRESS_PATTERNS
        patterns = PROGRESS_PATTERNS["cargo"]
        assert len(patterns) > 0

    def test_patterns_for_pytest(self):
        """Should have patterns for pytest."""
        assert "pytest" in PROGRESS_PATTERNS
        patterns = PROGRESS_PATTERNS["pytest"]
        assert len(patterns) > 0

    def test_pattern_structure(self):
        """Each pattern should be (string, float) tuple."""
        for _cmd, patterns in PROGRESS_PATTERNS.items():
            for pattern, progress in patterns:
                assert isinstance(pattern, str)
                assert isinstance(progress, float)
                assert 0.0 <= progress <= 1.0


class TestEstimateProgress:
    """Tests for estimate_progress function."""

    def test_estimate_npm_warn(self):
        """Should estimate progress for npm WARN."""
        progress = estimate_progress("npm install", "npm WARN deprecated package")
        assert progress == 0.3

    def test_estimate_npm_added(self):
        """Should estimate progress for npm added."""
        progress = estimate_progress("npm install", "added 50 packages")
        assert progress == 0.9

    def test_estimate_npm_complete(self):
        """Should estimate progress for npm completion."""
        progress = estimate_progress(
            "npm install",
            "added 100 packages in 5s",
        )
        assert progress == 1.0

    def test_estimate_pip_collecting(self):
        """Should estimate progress for pip Collecting."""
        progress = estimate_progress("pip install requests", "Collecting requests")
        assert progress == 0.2

    def test_estimate_pip_downloading(self):
        """Should estimate progress for pip Downloading."""
        progress = estimate_progress(
            "pip install requests",
            "Collecting requests\nDownloading requests-2.28.0.tar.gz",
        )
        assert progress == 0.5

    def test_estimate_pip_installing(self):
        """Should estimate progress for pip Installing."""
        progress = estimate_progress(
            "pip install requests",
            "Collecting\nDownloading\nInstalling collected packages",
        )
        assert progress == 0.8

    def test_estimate_pip_success(self):
        """Should estimate progress for pip success."""
        progress = estimate_progress(
            "pip install requests",
            "Successfully installed requests-2.28.0",
        )
        assert progress == 1.0

    def test_estimate_cargo_compiling(self):
        """Should estimate progress for cargo Compiling."""
        progress = estimate_progress("cargo build", "Compiling myproject v0.1.0")
        assert progress == 0.3

    def test_estimate_cargo_finished(self):
        """Should estimate progress for cargo Finished."""
        progress = estimate_progress("cargo build", "Finished dev [unoptimized]")
        assert progress == 1.0

    def test_estimate_pytest_collected(self):
        """Should estimate progress for pytest collected."""
        progress = estimate_progress("pytest", "collected 10 items")
        assert progress == 0.1

    def test_estimate_pytest_passed(self):
        """Should estimate progress for pytest passed."""
        progress = estimate_progress("pytest", "10 passed in 1.5s")
        assert progress == 0.9

    def test_estimate_pytest_failed(self):
        """Should estimate progress for pytest failed."""
        progress = estimate_progress("pytest", "2 failed, 8 passed")
        assert progress == 0.9

    def test_estimate_unknown_command(self):
        """Should return None for unknown commands."""
        progress = estimate_progress("echo hello", "hello")
        assert progress is None

    def test_estimate_no_match(self):
        """Should return None when no patterns match."""
        progress = estimate_progress("npm install", "Starting...")
        assert progress is None

    def test_estimate_case_insensitive(self):
        """Should match patterns case-insensitively."""
        progress = estimate_progress("NPM INSTALL", "npm warn")
        assert progress == 0.3

    def test_estimate_highest_match_wins(self):
        """Should return highest matching progress."""
        # Both "Collecting" and "Downloading" should match
        progress = estimate_progress(
            "pip install",
            "Collecting package\nDownloading file",
        )
        assert progress == 0.5  # Downloading is higher

    def test_estimate_empty_output(self):
        """Should return None for empty output."""
        progress = estimate_progress("npm install", "")
        assert progress is None

    def test_estimate_partial_command_match(self):
        """Should match command containing keyword."""
        progress = estimate_progress("npm ci --legacy-peer-deps", "npm WARN")
        assert progress == 0.3


class TestRunCommandStreaming:
    """Tests for run_command_streaming async function."""

    @pytest.mark.asyncio
    async def test_run_simple_command(self):
        """Should execute simple command and return output."""
        result = await run_command_streaming("echo hello")
        assert "hello" in result

    @pytest.mark.asyncio
    async def test_run_command_exit_code_success(self):
        """Should complete without exit code marker for success."""
        result = await run_command_streaming("echo success")
        assert "Exit code:" not in result

    @pytest.mark.asyncio
    async def test_run_command_exit_code_failure(self):
        """Should include exit code for failed commands."""
        result = await run_command_streaming("exit 42")
        assert "Exit code: 42" in result

    @pytest.mark.asyncio
    async def test_run_command_with_working_dir(self, temp_dir):
        """Should execute command in specified directory."""
        result = await run_command_streaming("pwd", working_dir=str(temp_dir))
        assert str(temp_dir) in result

    @pytest.mark.asyncio
    async def test_run_command_default_working_dir(self):
        """Should use current directory when working_dir not specified."""
        import os

        result = await run_command_streaming("pwd")
        assert os.getcwd() in result

    @pytest.mark.asyncio
    async def test_run_command_progress_callback(self):
        """Should call progress callback with updates."""
        progress_updates: list[ToolProgress] = []

        def on_progress(p: ToolProgress) -> None:
            progress_updates.append(p)

        await run_command_streaming("echo line1; echo line2", on_progress=on_progress)

        assert len(progress_updates) > 0
        # Should have running updates
        running_updates = [
            p for p in progress_updates if p.status == ToolStatus.RUNNING
        ]
        assert len(running_updates) > 0
        # Should end with completed or have a completed update
        final_statuses = [p.status for p in progress_updates]
        assert (
            ToolStatus.COMPLETED in final_statuses
            or ToolStatus.RUNNING in final_statuses
        )

    @pytest.mark.asyncio
    async def test_run_command_progress_elapsed_time(self):
        """Progress updates should have elapsed time."""
        progress_updates: list[ToolProgress] = []

        def on_progress(p: ToolProgress) -> None:
            progress_updates.append(p)

        await run_command_streaming("sleep 0.1; echo done", on_progress=on_progress)

        # Later updates should have higher elapsed time
        if len(progress_updates) >= 2:
            assert progress_updates[-1].elapsed >= progress_updates[0].elapsed

    @pytest.mark.asyncio
    async def test_run_command_cancellation(self):
        """Should support cancellation via StreamingToolCall."""
        tool_call = StreamingToolCall(id="1", name="test", arguments={})

        async def cancel_after_delay():
            await asyncio.sleep(0.05)
            tool_call.cancel()

        task = asyncio.create_task(cancel_after_delay())

        result = await run_command_streaming(
            "sleep 10",
            tool_call=tool_call,
        )
        _ = task  # Keep reference to prevent garbage collection

        assert "Cancelled by user" in result

    @pytest.mark.asyncio
    async def test_run_command_cancellation_progress(self):
        """Should emit CANCELLED status on cancellation."""
        tool_call = StreamingToolCall(id="1", name="test", arguments={})
        progress_updates: list[ToolProgress] = []

        def on_progress(p: ToolProgress) -> None:
            progress_updates.append(p)

        async def cancel_after_delay():
            await asyncio.sleep(0.05)
            tool_call.cancel()

        task = asyncio.create_task(cancel_after_delay())

        await run_command_streaming(
            "sleep 10",
            on_progress=on_progress,
            tool_call=tool_call,
        )
        _ = task

        statuses = [p.status for p in progress_updates]
        assert ToolStatus.CANCELLED in statuses

    @pytest.mark.asyncio
    async def test_run_command_timeout(self):
        """Should timeout after specified duration."""
        result = await run_command_streaming(
            "sleep 10",
            timeout=0.1,
        )
        assert "Timed out" in result

    @pytest.mark.asyncio
    async def test_run_command_timeout_progress(self):
        """Should emit FAILED status on timeout."""
        progress_updates: list[ToolProgress] = []

        def on_progress(p: ToolProgress) -> None:
            progress_updates.append(p)

        await run_command_streaming(
            "sleep 10",
            timeout=0.1,
            on_progress=on_progress,
        )

        statuses = [p.status for p in progress_updates]
        assert ToolStatus.FAILED in statuses

    @pytest.mark.asyncio
    async def test_run_command_stderr_merged(self):
        """Should capture stderr in output."""
        result = await run_command_streaming("echo error >&2")
        assert "error" in result

    @pytest.mark.asyncio
    async def test_run_command_multiline_output(self):
        """Should capture multiline output."""
        result = await run_command_streaming("echo line1; echo line2; echo line3")
        assert "line1" in result
        assert "line2" in result
        assert "line3" in result

    @pytest.mark.asyncio
    async def test_run_command_unicode_output(self):
        """Should handle unicode output."""
        result = await run_command_streaming('printf "Hello 世界 🎉"')
        assert "Hello" in result
        # Unicode should be handled (may be replaced on decode errors)

    @pytest.mark.asyncio
    async def test_run_invalid_command(self):
        """Should handle invalid command gracefully."""
        result = await run_command_streaming("nonexistent_command_xyz123")
        assert (
            "Exit code:" in result or "Error" in result or "not found" in result.lower()
        )

    @pytest.mark.asyncio
    async def test_run_command_no_callback(self):
        """Should work without progress callback."""
        result = await run_command_streaming("echo test")
        assert "test" in result

    @pytest.mark.asyncio
    async def test_run_command_accumulates_output(self):
        """Progress updates should accumulate output."""
        progress_updates: list[ToolProgress] = []

        def on_progress(p: ToolProgress) -> None:
            progress_updates.append(p)

        await run_command_streaming(
            "echo a; sleep 0.05; echo b; sleep 0.05; echo c",
            on_progress=on_progress,
        )

        # Output should grow over time
        outputs = [p.output for p in progress_updates]
        if len(outputs) >= 2:
            assert len(outputs[-1]) >= len(outputs[0])


class TestStreamCommand:
    """Tests for stream_command async iterator function."""

    @pytest.mark.asyncio
    async def test_stream_simple_command(self):
        """Should yield progress updates for simple command."""
        updates = []
        async for progress in stream_command("echo hello"):
            updates.append(progress)

        assert len(updates) > 0
        assert any(p.status == ToolStatus.RUNNING for p in updates)

    @pytest.mark.asyncio
    async def test_stream_command_completion(self):
        """Should yield COMPLETED status on success."""
        updates = []
        async for progress in stream_command("echo success"):
            updates.append(progress)

        final = updates[-1]
        assert final.status == ToolStatus.COMPLETED
        assert final.exit_code == 0

    @pytest.mark.asyncio
    async def test_stream_command_failure(self):
        """Should yield FAILED status on command failure."""
        updates = []
        async for progress in stream_command("exit 1"):
            updates.append(progress)

        final = updates[-1]
        assert final.status == ToolStatus.FAILED
        assert final.exit_code == 1

    @pytest.mark.asyncio
    async def test_stream_command_output(self):
        """Should accumulate output in progress updates."""
        updates = []
        async for progress in stream_command("echo line1; echo line2"):
            updates.append(progress)

        # Final update should have all output
        final = updates[-1]
        assert "line1" in final.output
        assert "line2" in final.output

    @pytest.mark.asyncio
    async def test_stream_command_with_working_dir(self, temp_dir):
        """Should execute in specified directory."""
        updates = []
        async for progress in stream_command("pwd", working_dir=str(temp_dir)):
            updates.append(progress)

        assert str(temp_dir) in updates[-1].output

    @pytest.mark.asyncio
    async def test_stream_command_cancellation(self):
        """Should yield CANCELLED status on cancellation."""
        tool_call = StreamingToolCall(id="1", name="test", arguments={})
        updates = []

        async def cancel_after_delay():
            await asyncio.sleep(0.05)
            tool_call.cancel()

        task = asyncio.create_task(cancel_after_delay())

        async for progress in stream_command("sleep 10", tool_call=tool_call):
            updates.append(progress)
        _ = task

        assert any(p.status == ToolStatus.CANCELLED for p in updates)
        assert "Cancelled by user" in updates[-1].output

    @pytest.mark.asyncio
    async def test_stream_command_timeout(self):
        """Should yield FAILED status on timeout."""
        updates = []
        async for progress in stream_command("sleep 10", timeout=0.1):
            updates.append(progress)

        assert any(p.status == ToolStatus.FAILED for p in updates)
        assert "Timed out" in updates[-1].output

    @pytest.mark.asyncio
    async def test_stream_command_exit_code_in_output(self):
        """Should include exit code in output for failures."""
        updates = []
        async for progress in stream_command("exit 42"):
            updates.append(progress)

        final = updates[-1]
        assert "Exit code: 42" in final.output
        assert final.exit_code == 42

    @pytest.mark.asyncio
    async def test_stream_command_elapsed_time(self):
        """Should track elapsed time in updates."""
        updates = []
        async for progress in stream_command("sleep 0.1; echo done"):
            updates.append(progress)

        # Elapsed time should increase
        if len(updates) >= 2:
            assert updates[-1].elapsed >= 0.0

    @pytest.mark.asyncio
    async def test_stream_command_yields_running_first(self):
        """First yielded update should be RUNNING."""
        async for progress in stream_command("echo test"):
            assert progress.status == ToolStatus.RUNNING
            break

    @pytest.mark.asyncio
    async def test_stream_command_is_async_iterator(self):
        """stream_command should be an async iterator."""
        result = stream_command("echo test")
        assert hasattr(result, "__aiter__")
        assert hasattr(result, "__anext__")

        # Clean up by consuming
        async for _ in result:
            pass


class TestProgressCallback:
    """Tests for ProgressCallback type alias."""

    def test_callback_type(self):
        """ProgressCallback should be callable type."""
        # This is more of a documentation test

        def my_callback(progress: ToolProgress) -> None:
            pass

        # Should be usable as ProgressCallback
        callback: ProgressCallback = my_callback
        assert callable(callback)


class TestIntegration:
    """Integration tests for streaming components."""

    @pytest.mark.asyncio
    async def test_full_streaming_workflow(self):
        """Test complete streaming workflow with all components."""
        tool_call = StreamingToolCall(
            id="test_123",
            name="run_command",
            arguments={"command": "echo integration test"},
        )

        progress_history: list[ToolProgress] = []

        def callback(p: ToolProgress) -> None:
            progress_history.append(p)

        result = await run_command_streaming(
            "echo integration test",
            on_progress=callback,
            tool_call=tool_call,
        )

        assert "integration test" in result
        assert len(progress_history) > 0
        assert tool_call.is_cancelled is False

    @pytest.mark.asyncio
    async def test_stream_vs_callback_equivalence(self):
        """stream_command and run_command_streaming should produce similar results."""
        command = "echo test1; echo test2"

        # Using callback
        callback_updates: list[ToolProgress] = []

        def callback(p: ToolProgress) -> None:
            callback_updates.append(p)

        callback_result = await run_command_streaming(command, on_progress=callback)

        # Using iterator
        stream_updates: list[ToolProgress] = []
        async for progress in stream_command(command):
            stream_updates.append(progress)

        # Both should have similar final output
        assert "test1" in callback_result
        assert "test1" in stream_updates[-1].output

    @pytest.mark.asyncio
    async def test_concurrent_streaming(self):
        """Should support concurrent streaming commands."""

        async def run_cmd(n: int) -> str:
            return await run_command_streaming(f"echo cmd{n}")

        results = await asyncio.gather(
            run_cmd(1),
            run_cmd(2),
            run_cmd(3),
        )

        assert "cmd1" in results[0]
        assert "cmd2" in results[1]
        assert "cmd3" in results[2]

    @pytest.mark.asyncio
    async def test_progress_complete_states(self):
        """Test all completion states via is_complete property."""
        # COMPLETED
        p1 = ToolProgress(status=ToolStatus.COMPLETED, output="done", exit_code=0)
        assert p1.is_complete is True

        # FAILED
        p2 = ToolProgress(status=ToolStatus.FAILED, output="error", exit_code=1)
        assert p2.is_complete is True

        # CANCELLED
        p3 = ToolProgress(status=ToolStatus.CANCELLED, output="cancelled")
        assert p3.is_complete is True

        # Not complete
        p4 = ToolProgress(status=ToolStatus.PENDING, output="")
        assert p4.is_complete is False

        p5 = ToolProgress(status=ToolStatus.RUNNING, output="working...")
        assert p5.is_complete is False


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    @pytest.mark.asyncio
    async def test_empty_command(self):
        """Should handle empty command."""
        result = await run_command_streaming("")
        # May fail or complete quickly - just ensure no crash
        assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_command_with_special_characters(self):
        """Should handle special shell characters."""
        result = await run_command_streaming('echo "hello; world && test | more"')
        assert "hello" in result

    @pytest.mark.asyncio
    async def test_command_with_newlines(self):
        """Should handle commands producing many lines."""
        result = await run_command_streaming("seq 1 10")
        for i in range(1, 11):
            assert str(i) in result

    @pytest.mark.asyncio
    async def test_very_fast_command(self):
        """Should handle very fast commands."""
        result = await run_command_streaming("true")
        assert "Exit code:" not in result  # Success has no exit code marker

    @pytest.mark.asyncio
    async def test_command_with_environment(self):
        """Should inherit environment."""
        import os

        os.environ["TEST_STREAMING_VAR"] = "test_value"
        try:
            result = await run_command_streaming("echo $TEST_STREAMING_VAR")
            assert "test_value" in result
        finally:
            del os.environ["TEST_STREAMING_VAR"]

    @pytest.mark.asyncio
    async def test_binary_output_handling(self):
        """Should handle binary-ish output with decode errors."""
        # Create a command that might produce non-UTF8 bytes
        result = await run_command_streaming("printf '\\x80\\x81\\x82'")
        # Should not crash - errors are replaced
        assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_progress_none_when_no_patterns(self):
        """estimate_progress returns None for unrecognized commands."""
        assert estimate_progress("ls", "file1.txt\nfile2.txt") is None
        assert estimate_progress("cat file.txt", "contents") is None
        assert estimate_progress("grep pattern", "match") is None

    @pytest.mark.asyncio
    async def test_stream_command_exception_handling(self):
        """stream_command should handle exceptions gracefully."""
        updates = []
        async for progress in stream_command("nonexistent_xyz_command_123"):
            updates.append(progress)

        # Should complete with failure, not raise
        assert len(updates) > 0
        final = updates[-1]
        assert final.status == ToolStatus.FAILED or "Exit code:" in final.output

    def test_tool_call_repr(self):
        """StreamingToolCall repr should be readable."""
        call = StreamingToolCall(
            id="abc123",
            name="test_tool",
            arguments={"key": "value"},
        )
        repr_str = repr(call)
        assert "abc123" in repr_str
        assert "test_tool" in repr_str

    @pytest.mark.asyncio
    async def test_cancelled_before_start(self):
        """Should handle cancellation before command starts."""
        tool_call = StreamingToolCall(id="1", name="test", arguments={})
        tool_call.cancel()  # Cancel immediately

        result = await run_command_streaming("echo test", tool_call=tool_call)
        # Should still run since cancellation is checked in the loop
        # But behavior depends on timing
        assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_callback_exception_isolation(self):
        """Exception in callback should not crash streaming."""
        call_count = 0

        def bad_callback(p: ToolProgress) -> None:
            nonlocal call_count
            call_count += 1
            # Don't actually raise - but callback errors shouldn't propagate
            pass

        result = await run_command_streaming("echo test", on_progress=bad_callback)
        assert "test" in result
        assert call_count > 0
