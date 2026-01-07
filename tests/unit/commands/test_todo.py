"""Test todo management."""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from commands.todo import TodoManager


@pytest.fixture
def mock_todo_file(tmp_path):
    """Create a temporary todo file."""
    # Patch Path.home() to return tmp_path
    with patch("pathlib.Path.home", return_value=tmp_path):
        yield tmp_path / ".null" / "todos.json"


def test_todo_manager_init(mock_todo_file):
    """Test manager initialization creates file."""
    manager = TodoManager()
    assert mock_todo_file.exists()
    assert mock_todo_file.read_text() == "[]"


def test_todo_add_list(mock_todo_file):
    """Test adding and listing todos."""
    manager = TodoManager()
    item = manager.add("Buy milk")

    assert item["content"] == "Buy milk"
    assert item["status"] == "pending"
    assert item["id"]

    todos = manager.load()
    assert len(todos) == 1
    assert todos[0]["content"] == "Buy milk"


def test_todo_update_status(mock_todo_file):
    """Test updating todo status."""
    manager = TodoManager()
    item = manager.add("Task 1")

    success = manager.update_status(item["id"], "done")
    assert success

    todos = manager.load()
    assert todos[0]["status"] == "done"

    # Test updating non-existent
    assert not manager.update_status("fake-id", "done")


def test_todo_delete(mock_todo_file):
    """Test deleting todos."""
    manager = TodoManager()
    item1 = manager.add("Task 1")
    item2 = manager.add("Task 2")

    assert len(manager.load()) == 2

    success = manager.delete(item1["id"])
    assert success

    todos = manager.load()
    assert len(todos) == 1
    assert todos[0]["content"] == "Task 2"

    assert not manager.delete("fake-id")


def test_todo_clear_completed(mock_todo_file):
    """Test clearing completed tasks."""
    manager = TodoManager()
    manager.add("Task 1")
    t2 = manager.add("Task 2")
    manager.update_status(t2["id"], "done")

    manager.clear_completed()
    todos = manager.load()
    assert len(todos) == 1
    assert todos[0]["content"] == "Task 1"
