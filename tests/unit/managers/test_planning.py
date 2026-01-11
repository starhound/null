import pytest
from unittest.mock import MagicMock, AsyncMock

from managers.planning import (
    Plan,
    PlanManager,
    PlanStatus,
    PlanStep,
    StepStatus,
    StepType,
)


class TestPlanStep:
    def test_create_basic_step(self):
        step = PlanStep.create(order=1, description="Test step")
        assert step.order == 1
        assert step.description == "Test step"
        assert step.step_type == StepType.PROMPT
        assert step.status == StepStatus.PENDING
        assert step.id is not None
        assert len(step.id) == 8

    def test_create_tool_step(self):
        step = PlanStep.create(
            order=2,
            description="Run command",
            step_type=StepType.TOOL,
            tool_name="run_command",
            tool_args={"command": "ls -la"},
        )
        assert step.step_type == StepType.TOOL
        assert step.tool_name == "run_command"
        assert step.tool_args == {"command": "ls -la"}

    def test_create_checkpoint_step(self):
        step = PlanStep.create(
            order=3, description="Review progress", step_type=StepType.CHECKPOINT
        )
        assert step.step_type == StepType.CHECKPOINT

    def test_step_default_values(self):
        step = PlanStep.create(order=1, description="Test")
        assert step.tool_name is None
        assert step.tool_args is None
        assert step.result is None
        assert step.error is None
        assert step.duration is None


class TestPlan:
    def test_create_plan(self):
        plan = Plan.create(goal="Test goal")
        assert plan.goal == "Test goal"
        assert plan.status == PlanStatus.DRAFT
        assert plan.steps == []
        assert plan.id is not None
        assert len(plan.id) == 8

    def test_add_step(self):
        plan = Plan.create(goal="Test")
        step = plan.add_step("First step")
        assert len(plan.steps) == 1
        assert step.order == 1
        assert step.description == "First step"

    def test_add_multiple_steps(self):
        plan = Plan.create(goal="Test")
        plan.add_step("Step 1")
        plan.add_step("Step 2")
        plan.add_step("Step 3")
        assert len(plan.steps) == 3
        assert plan.steps[0].order == 1
        assert plan.steps[1].order == 2
        assert plan.steps[2].order == 3

    def test_get_step_by_id(self):
        plan = Plan.create(goal="Test")
        step = plan.add_step("Find me")
        found = plan.get_step(step.id)
        assert found == step

    def test_get_step_not_found(self):
        plan = Plan.create(goal="Test")
        plan.add_step("Step 1")
        assert plan.get_step("nonexistent") is None

    def test_approve_step(self):
        plan = Plan.create(goal="Test")
        step = plan.add_step("Approve me")
        assert step.status == StepStatus.PENDING
        result = plan.approve_step(step.id)
        assert result is True
        assert step.status == StepStatus.APPROVED

    def test_approve_step_already_approved(self):
        plan = Plan.create(goal="Test")
        step = plan.add_step("Step")
        step.status = StepStatus.APPROVED
        result = plan.approve_step(step.id)
        assert result is False

    def test_skip_step_from_pending(self):
        plan = Plan.create(goal="Test")
        step = plan.add_step("Skip me")
        result = plan.skip_step(step.id)
        assert result is True
        assert step.status == StepStatus.SKIPPED

    def test_skip_step_from_approved(self):
        plan = Plan.create(goal="Test")
        step = plan.add_step("Skip me")
        step.status = StepStatus.APPROVED
        result = plan.skip_step(step.id)
        assert result is True
        assert step.status == StepStatus.SKIPPED

    def test_skip_completed_step_fails(self):
        plan = Plan.create(goal="Test")
        step = plan.add_step("Completed")
        step.status = StepStatus.COMPLETED
        result = plan.skip_step(step.id)
        assert result is False

    def test_approve_all(self):
        plan = Plan.create(goal="Test")
        plan.add_step("Step 1")
        plan.add_step("Step 2")
        plan.add_step("Step 3")
        count = plan.approve_all()
        assert count == 3
        assert all(s.status == StepStatus.APPROVED for s in plan.steps)

    def test_approve_all_skips_non_pending(self):
        plan = Plan.create(goal="Test")
        plan.add_step("Step 1")
        step2 = plan.add_step("Step 2")
        step2.status = StepStatus.COMPLETED
        plan.add_step("Step 3")
        count = plan.approve_all()
        assert count == 2

    def test_get_next_step(self):
        plan = Plan.create(goal="Test")
        step1 = plan.add_step("Step 1")
        step2 = plan.add_step("Step 2")
        step1.status = StepStatus.APPROVED
        next_step = plan.get_next_step()
        assert next_step == step1

    def test_get_next_step_none_approved(self):
        plan = Plan.create(goal="Test")
        plan.add_step("Step 1")
        next_step = plan.get_next_step()
        assert next_step is None

    def test_is_complete_all_done(self):
        plan = Plan.create(goal="Test")
        step1 = plan.add_step("Step 1")
        step2 = plan.add_step("Step 2")
        step1.status = StepStatus.COMPLETED
        step2.status = StepStatus.SKIPPED
        assert plan.is_complete is True

    def test_is_complete_with_pending(self):
        plan = Plan.create(goal="Test")
        step1 = plan.add_step("Step 1")
        step2 = plan.add_step("Step 2")
        step1.status = StepStatus.COMPLETED
        assert plan.is_complete is False

    def test_is_complete_empty_plan(self):
        plan = Plan.create(goal="Test")
        assert plan.is_complete is True

    def test_progress_empty(self):
        plan = Plan.create(goal="Test")
        assert plan.progress == 0.0

    def test_progress_partial(self):
        plan = Plan.create(goal="Test")
        step1 = plan.add_step("Step 1")
        step2 = plan.add_step("Step 2")
        step1.status = StepStatus.COMPLETED
        assert plan.progress == 0.5

    def test_progress_complete(self):
        plan = Plan.create(goal="Test")
        step1 = plan.add_step("Step 1")
        step2 = plan.add_step("Step 2")
        step1.status = StepStatus.COMPLETED
        step2.status = StepStatus.FAILED
        assert plan.progress == 1.0


class TestPlanManager:
    def test_init(self):
        manager = PlanManager()
        assert manager.plans == {}
        assert manager.active_plan_id is None

    def test_active_plan_none(self):
        manager = PlanManager()
        assert manager.active_plan is None

    def test_active_plan_exists(self):
        manager = PlanManager()
        plan = Plan.create(goal="Test")
        manager.plans[plan.id] = plan
        manager.active_plan_id = plan.id
        assert manager.active_plan == plan

    def test_get_plan(self):
        manager = PlanManager()
        plan = Plan.create(goal="Test")
        manager.plans[plan.id] = plan
        assert manager.get_plan(plan.id) == plan

    def test_get_plan_not_found(self):
        manager = PlanManager()
        assert manager.get_plan("nonexistent") is None

    def test_approve_step(self):
        manager = PlanManager()
        plan = Plan.create(goal="Test")
        step = plan.add_step("Step")
        manager.plans[plan.id] = plan
        result = manager.approve_step(plan.id, step.id)
        assert result is True
        assert step.status == StepStatus.APPROVED

    def test_approve_step_invalid_plan(self):
        manager = PlanManager()
        assert manager.approve_step("invalid", "step") is False

    def test_skip_step(self):
        manager = PlanManager()
        plan = Plan.create(goal="Test")
        step = plan.add_step("Step")
        manager.plans[plan.id] = plan
        result = manager.skip_step(plan.id, step.id)
        assert result is True
        assert step.status == StepStatus.SKIPPED

    def test_approve_all(self):
        manager = PlanManager()
        plan = Plan.create(goal="Test")
        plan.add_step("Step 1")
        plan.add_step("Step 2")
        manager.plans[plan.id] = plan
        count = manager.approve_all(plan.id)
        assert count == 2

    def test_approve_all_invalid_plan(self):
        manager = PlanManager()
        assert manager.approve_all("invalid") == 0

    def test_cancel_plan(self):
        manager = PlanManager()
        plan = Plan.create(goal="Test")
        manager.plans[plan.id] = plan
        manager.active_plan_id = plan.id
        result = manager.cancel_plan(plan.id)
        assert result is True
        assert plan.status == PlanStatus.CANCELLED
        assert manager.active_plan_id is None

    def test_cancel_plan_not_active(self):
        manager = PlanManager()
        plan = Plan.create(goal="Test")
        manager.plans[plan.id] = plan
        result = manager.cancel_plan(plan.id)
        assert result is True
        assert plan.status == PlanStatus.CANCELLED

    def test_cancel_plan_not_found(self):
        manager = PlanManager()
        assert manager.cancel_plan("invalid") is False

    def test_start_execution(self):
        manager = PlanManager()
        plan = Plan.create(goal="Test")
        manager.plans[plan.id] = plan
        result = manager.start_execution(plan.id)
        assert result is True
        assert plan.status == PlanStatus.EXECUTING

    def test_start_execution_already_executing(self):
        manager = PlanManager()
        plan = Plan.create(goal="Test")
        plan.status = PlanStatus.EXECUTING
        manager.plans[plan.id] = plan
        result = manager.start_execution(plan.id)
        assert result is False

    def test_complete_step_success(self):
        manager = PlanManager()
        plan = Plan.create(goal="Test")
        step = plan.add_step("Step")
        manager.plans[plan.id] = plan
        result = manager.complete_step(plan.id, step.id, result="Done", duration=1.5)
        assert result is True
        assert step.status == StepStatus.COMPLETED
        assert step.result == "Done"
        assert step.duration == 1.5

    def test_complete_step_with_error(self):
        manager = PlanManager()
        plan = Plan.create(goal="Test")
        step = plan.add_step("Step")
        manager.plans[plan.id] = plan
        result = manager.complete_step(plan.id, step.id, error="Failed", duration=0.5)
        assert result is True
        assert step.status == StepStatus.FAILED
        assert step.error == "Failed"

    def test_complete_step_completes_plan(self):
        manager = PlanManager()
        plan = Plan.create(goal="Test")
        plan.status = PlanStatus.EXECUTING
        step = plan.add_step("Step")
        manager.plans[plan.id] = plan
        manager.complete_step(plan.id, step.id, result="Done")
        assert plan.status == PlanStatus.COMPLETED

    def test_complete_step_invalid_plan(self):
        manager = PlanManager()
        assert manager.complete_step("invalid", "step") is False

    def test_complete_step_invalid_step(self):
        manager = PlanManager()
        plan = Plan.create(goal="Test")
        manager.plans[plan.id] = plan
        assert manager.complete_step(plan.id, "invalid") is False

    @pytest.mark.asyncio
    async def test_generate_plan(self):
        manager = PlanManager()
        mock_provider = MagicMock()

        async def mock_generate(*args, **kwargs):
            yield "STEP 1: First step\n"
            yield "TYPE: prompt\n"
            yield "STEP 2: Second step\n"
            yield "TYPE: tool\n"
            yield "TOOL: run_command\n"

        mock_provider.generate = mock_generate
        plan = await manager.generate_plan("Test goal", mock_provider)
        assert plan.goal == "Test goal"
        assert len(plan.steps) >= 1
        assert manager.active_plan_id == plan.id

    def test_parse_plan_response_basic(self):
        manager = PlanManager()
        plan = Plan.create(goal="Test")
        response = """STEP 1: First step
TYPE: prompt
STEP 2: Second step
TYPE: tool
TOOL: run_command
"""
        manager._parse_plan_response(plan, response)
        assert len(plan.steps) == 2
        assert plan.steps[0].description == "First step"
        assert plan.steps[0].step_type == StepType.PROMPT
        assert plan.steps[1].description == "Second step"
        assert plan.steps[1].step_type == StepType.TOOL
        assert plan.steps[1].tool_name == "run_command"

    def test_parse_plan_response_with_args(self):
        manager = PlanManager()
        plan = Plan.create(goal="Test")
        response = """STEP 1: Run a command
TYPE: tool
TOOL: run_command
ARGS: {"command": "ls -la"}
"""
        manager._parse_plan_response(plan, response)
        assert len(plan.steps) == 1
        assert plan.steps[0].tool_args == {"command": "ls -la"}

    def test_parse_plan_response_checkpoint(self):
        manager = PlanManager()
        plan = Plan.create(goal="Test")
        response = """STEP 1: Review progress
TYPE: checkpoint
"""
        manager._parse_plan_response(plan, response)
        assert plan.steps[0].step_type == StepType.CHECKPOINT

    def test_parse_plan_response_empty(self):
        manager = PlanManager()
        plan = Plan.create(goal="Test goal")
        manager._parse_plan_response(plan, "")
        assert len(plan.steps) == 1
        assert "Test goal" in plan.steps[0].description

    def test_parse_plan_response_invalid_json_args(self):
        manager = PlanManager()
        plan = Plan.create(goal="Test")
        response = """STEP 1: Test
TYPE: tool
TOOL: test
ARGS: {invalid json}
"""
        manager._parse_plan_response(plan, response)
        assert plan.steps[0].tool_args is None


class TestStepStatusEnum:
    def test_all_statuses(self):
        assert StepStatus.PENDING.value == "pending"
        assert StepStatus.APPROVED.value == "approved"
        assert StepStatus.SKIPPED.value == "skipped"
        assert StepStatus.EXECUTING.value == "executing"
        assert StepStatus.COMPLETED.value == "completed"
        assert StepStatus.FAILED.value == "failed"


class TestPlanStatusEnum:
    def test_all_statuses(self):
        assert PlanStatus.DRAFT.value == "draft"
        assert PlanStatus.APPROVED.value == "approved"
        assert PlanStatus.EXECUTING.value == "executing"
        assert PlanStatus.COMPLETED.value == "completed"
        assert PlanStatus.CANCELLED.value == "cancelled"


class TestStepTypeEnum:
    def test_all_types(self):
        assert StepType.PROMPT.value == "prompt"
        assert StepType.TOOL.value == "tool"
        assert StepType.CHECKPOINT.value == "checkpoint"
