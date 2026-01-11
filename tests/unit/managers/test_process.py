import signal
from unittest.mock import patch

import pytest

from managers.process import ProcessManager


@pytest.fixture
def process_manager():
    return ProcessManager()


def test_register_process(process_manager):
    process_manager.register(
        block_id="test_block", pid=1234, command="echo hello", master_fd=5, is_tui=False
    )

    assert "test_block" in process_manager._processes
    info = process_manager.get("test_block")
    assert info.pid == 1234
    assert info.command == "echo hello"
    assert info.master_fd == 5
    assert not info.is_tui


def test_unregister_process(process_manager):
    process_manager.register("test_block", 1234, "cmd")
    process_manager.unregister("test_block")
    assert "test_block" not in process_manager._processes


def test_is_running(process_manager):
    process_manager.register("test_block", 1234, "cmd")
    assert process_manager.is_running("test_block")
    assert not process_manager.is_running("other_block")


def test_get_running(process_manager):
    process_manager.register("b1", 100, "cmd1")
    process_manager.register("b2", 101, "cmd2")

    running = process_manager.get_running()
    assert len(running) == 2
    pids = sorted([p.pid for p in running])
    assert pids == [100, 101]


@patch("os.kill")
def test_stop_process_term(mock_kill, process_manager):
    process_manager.register("test_block", 1234, "cmd")

    result = process_manager.stop("test_block", force=False)

    assert result is True
    mock_kill.assert_called_with(1234, signal.SIGTERM)


@patch("os.kill")
def test_stop_process_kill(mock_kill, process_manager):
    process_manager.register("test_block", 1234, "cmd")

    result = process_manager.stop("test_block", force=True)

    assert result is True
    mock_kill.assert_called_with(1234, signal.SIGKILL)


@patch("os.kill")
def test_stop_process_not_found(mock_kill, process_manager):
    result = process_manager.stop("missing_block")
    assert result is False
    mock_kill.assert_not_called()


@patch("os.kill")
def test_stop_process_error(mock_kill, process_manager):
    process_manager.register("test_block", 1234, "cmd")
    mock_kill.side_effect = ProcessLookupError()

    result = process_manager.stop("test_block")

    assert result is False
    assert "test_block" not in process_manager._processes


@patch("os.write")
def test_send_input(mock_write, process_manager):
    process_manager.register("test_block", 1234, "cmd", master_fd=10)

    result = process_manager.send_input("test_block", b"data")

    assert result is True
    mock_write.assert_called_with(10, b"data")


@patch("os.write")
def test_send_input_no_fd(mock_write, process_manager):
    process_manager.register("test_block", 1234, "cmd", master_fd=None)

    result = process_manager.send_input("test_block", b"data")

    assert result is False
    mock_write.assert_not_called()


def test_set_tui_mode(process_manager):
    process_manager.register("test_block", 1234, "cmd")

    process_manager.set_tui_mode("test_block", True)
    assert process_manager.get("test_block").is_tui

    process_manager.set_tui_mode("test_block", False)
    assert not process_manager.get("test_block").is_tui
