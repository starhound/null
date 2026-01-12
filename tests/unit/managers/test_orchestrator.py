from datetime import datetime
from unittest.mock import MagicMock

import pytest

from managers.orchestrator import (
    BUILTIN_PROFILES,
    AgentMessage,
    AgentOrchestrator,
    AgentProfile,
    AgentRole,
    OrchestratedResult,
    SubTask,
)


class TestAgentRole:
    def test_all_roles_exist(self):
        assert AgentRole.COORDINATOR.value == "coordinator"
        assert AgentRole.PLANNER.value == "planner"
        assert AgentRole.CODER.value == "coder"
        assert AgentRole.REVIEWER.value == "reviewer"
        assert AgentRole.DEBUGGER.value == "debugger"
        assert AgentRole.TESTER.value == "tester"


class TestAgentProfile:
    def test_profile_creation(self):
        profile = AgentProfile(
            name="Test",
            role=AgentRole.CODER,
            system_prompt="You are a coder",
            tools=["read_file", "write_file"],
            temperature=0.3,
        )
        assert profile.name == "Test"
        assert profile.role == AgentRole.CODER
        assert profile.temperature == 0.3
        assert "read_file" in profile.tools

    def test_profile_defaults(self):
        profile = AgentProfile(
            name="Minimal",
            role=AgentRole.PLANNER,
            system_prompt="Plan",
        )
        assert profile.tools == []
        assert profile.temperature == 0.7


class TestAgentMessage:
    def test_message_creation(self):
        message = AgentMessage(
            from_agent="planner",
            to_agent="coder",
            content="Here is the plan",
        )
        assert message.from_agent == "planner"
        assert message.to_agent == "coder"
        assert message.content == "Here is the plan"
        assert isinstance(message.timestamp, datetime)


class TestSubTask:
    def test_subtask_creation(self):
        subtask = SubTask(
            id="task_1",
            description="Write a function",
            assigned_agent=AgentRole.CODER,
        )
        assert subtask.id == "task_1"
        assert subtask.status == "pending"
        assert subtask.result is None

    def test_subtask_with_result(self):
        subtask = SubTask(
            id="task_2",
            description="Review code",
            assigned_agent=AgentRole.REVIEWER,
            status="completed",
            result="Code looks good",
        )
        assert subtask.status == "completed"
        assert subtask.result == "Code looks good"


class TestOrchestratedResult:
    def test_result_creation(self):
        result = OrchestratedResult(
            success=True,
            subtasks=[],
            messages=[],
            final_result="Task completed",
            duration=10.5,
        )
        assert result.success is True
        assert result.final_result == "Task completed"
        assert result.duration == 10.5


class TestBuiltinProfiles:
    def test_planner_profile_exists(self):
        assert AgentRole.PLANNER in BUILTIN_PROFILES
        profile = BUILTIN_PROFILES[AgentRole.PLANNER]
        assert profile.name == "Planner"
        assert "read_file" in profile.tools

    def test_coder_profile_exists(self):
        assert AgentRole.CODER in BUILTIN_PROFILES
        profile = BUILTIN_PROFILES[AgentRole.CODER]
        assert profile.name == "Coder"
        assert profile.temperature == 0.3
        assert "write_file" in profile.tools

    def test_reviewer_profile_exists(self):
        assert AgentRole.REVIEWER in BUILTIN_PROFILES
        profile = BUILTIN_PROFILES[AgentRole.REVIEWER]
        assert profile.name == "Reviewer"

    def test_debugger_profile_exists(self):
        assert AgentRole.DEBUGGER in BUILTIN_PROFILES

    def test_tester_profile_exists(self):
        assert AgentRole.TESTER in BUILTIN_PROFILES


class TestAgentOrchestrator:
    @pytest.fixture
    def orchestrator(self):
        return AgentOrchestrator()

    @pytest.fixture
    def mock_provider(self):
        provider = MagicMock()
        return provider

    def test_orchestrator_initialization(self, orchestrator):
        assert orchestrator.is_running is False
        assert orchestrator.messages == []
        assert AgentRole.PLANNER in orchestrator.profiles
        assert AgentRole.CODER in orchestrator.profiles

    def test_stop(self, orchestrator):
        orchestrator.is_running = True
        orchestrator.stop()
        assert orchestrator.is_running is False

    def test_log_message(self, orchestrator):
        orchestrator.log_message("planner", "coder", "Do this task")

        assert len(orchestrator.messages) == 1
        msg = orchestrator.messages[0]
        assert msg.from_agent == "planner"
        assert msg.to_agent == "coder"
        assert msg.content == "Do this task"

    def test_profiles_are_accessible(self, orchestrator):
        assert len(orchestrator.profiles) >= 5
        for role in [AgentRole.PLANNER, AgentRole.CODER, AgentRole.REVIEWER]:
            assert role in orchestrator.profiles
