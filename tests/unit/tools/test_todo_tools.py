import pytest
from unittest.mock import patch

from tools.builtin import todo_list, todo_add, todo_update, todo_delete


@pytest.fixture
def mock_todo_file(tmp_path):
    with patch("pathlib.Path.home", return_value=tmp_path):
        yield tmp_path / ".null" / "todos.json"


@pytest.mark.asyncio
async def test_todo_list_empty(mock_todo_file):
    result = await todo_list()
    assert result == "No tasks found."


@pytest.mark.asyncio
async def test_todo_add(mock_todo_file):
    result = await todo_add("Test task")
    assert "Added task" in result
    assert "Test task" in result


@pytest.mark.asyncio
async def test_todo_list_with_items(mock_todo_file):
    await todo_add("Task one")
    await todo_add("Task two")

    result = await todo_list()
    assert "Task one" in result
    assert "Task two" in result
    assert "[pending]" in result


@pytest.mark.asyncio
async def test_todo_update(mock_todo_file):
    add_result = await todo_add("Update me")
    todo_id = add_result.split()[2].rstrip(":")

    result = await todo_update(todo_id, "done")
    assert "Updated task" in result
    assert "done" in result

    list_result = await todo_list()
    assert "[done]" in list_result


@pytest.mark.asyncio
async def test_todo_update_invalid_status(mock_todo_file):
    result = await todo_update("fake-id", "invalid")
    assert "Invalid status" in result


@pytest.mark.asyncio
async def test_todo_update_not_found(mock_todo_file):
    result = await todo_update("fake-id", "done")
    assert "not found" in result


@pytest.mark.asyncio
async def test_todo_delete(mock_todo_file):
    add_result = await todo_add("Delete me")
    todo_id = add_result.split()[2].rstrip(":")

    result = await todo_delete(todo_id)
    assert "Deleted task" in result

    list_result = await todo_list()
    assert "Delete me" not in list_result


@pytest.mark.asyncio
async def test_todo_delete_not_found(mock_todo_file):
    result = await todo_delete("fake-id")
    assert "not found" in result
