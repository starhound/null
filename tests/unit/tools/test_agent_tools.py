import pytest
from tools.builtin import (
    agent_status,
    agent_history,
    agent_stats,
    set_agent_manager,
    get_agent_manager,
)
from managers.agent import AgentManager, AgentState


@pytest.fixture
def agent_manager():
    manager = AgentManager()
    set_agent_manager(manager)
    yield manager
    set_agent_manager(None)


@pytest.mark.asyncio
async def test_agent_status_no_manager():
    set_agent_manager(None)
    result = await agent_status()
    assert "not initialized" in result


@pytest.mark.asyncio
async def test_agent_status_idle(agent_manager):
    result = await agent_status()
    assert "Agent: idle" in result


@pytest.mark.asyncio
async def test_agent_status_active(agent_manager):
    agent_manager.start_session("Test task")
    result = await agent_status()
    assert "thinking" in result.lower()
    assert "Test task" in result
    agent_manager.end_session()


@pytest.mark.asyncio
async def test_agent_history_empty(agent_manager):
    result = await agent_history()
    assert "No session history" in result


@pytest.mark.asyncio
async def test_agent_history_with_sessions(agent_manager):
    agent_manager.start_session("Task 1")
    agent_manager.record_iteration()
    agent_manager.record_tool_call("test_tool", "{}", "ok", True, 0.5)
    agent_manager.end_session()

    agent_manager.start_session("Task 2")
    agent_manager.end_session()

    result = await agent_history(limit=5)
    assert "Recent agent sessions" in result
    assert "completed" in result


@pytest.mark.asyncio
async def test_agent_stats_empty(agent_manager):
    result = await agent_stats()
    assert "No agent sessions recorded" in result


@pytest.mark.asyncio
async def test_agent_stats_with_data(agent_manager):
    agent_manager.start_session("Task")
    agent_manager.record_iteration()
    agent_manager.record_iteration()
    agent_manager.record_tool_call(
        "read_file", '{"path": "test.py"}', "content", True, 0.1
    )
    agent_manager.record_tokens(500)
    agent_manager.end_session()

    result = await agent_stats()
    assert "Total sessions: 1" in result
    assert "Total iterations: 2" in result
    assert "Total tool calls: 1" in result
    assert "read_file" in result


@pytest.mark.asyncio
async def test_get_agent_manager(agent_manager):
    assert get_agent_manager() is agent_manager
