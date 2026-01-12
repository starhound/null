"""Planning mode manager for AI-assisted task planning."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ai.base import LLMProvider


class PlanStatus(Enum):
    DRAFT = "draft"
    APPROVED = "approved"
    EXECUTING = "executing"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class StepStatus(Enum):
    PENDING = "pending"
    APPROVED = "approved"
    SKIPPED = "skipped"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"


class StepType(Enum):
    PROMPT = "prompt"
    TOOL = "tool"
    CHECKPOINT = "checkpoint"


@dataclass
class PlanStep:
    id: str
    order: int
    description: str
    step_type: StepType
    tool_name: str | None = None
    tool_args: dict[str, Any] | None = None
    status: StepStatus = StepStatus.PENDING
    result: str | None = None
    error: str | None = None
    duration: float | None = None

    @classmethod
    def create(
        cls,
        order: int,
        description: str,
        step_type: StepType = StepType.PROMPT,
        tool_name: str | None = None,
        tool_args: dict[str, Any] | None = None,
    ) -> PlanStep:
        return cls(
            id=str(uuid.uuid4())[:8],
            order=order,
            description=description,
            step_type=step_type,
            tool_name=tool_name,
            tool_args=tool_args,
        )


@dataclass
class Plan:
    id: str
    goal: str
    steps: list[PlanStep] = field(default_factory=list)
    status: PlanStatus = PlanStatus.DRAFT
    created_at: datetime = field(default_factory=datetime.now)
    variables: dict[str, str] = field(default_factory=dict)
    current_step: int = 0

    @classmethod
    def create(cls, goal: str) -> Plan:
        return cls(
            id=str(uuid.uuid4())[:8],
            goal=goal,
        )

    def add_step(
        self,
        description: str,
        step_type: StepType = StepType.PROMPT,
        tool_name: str | None = None,
        tool_args: dict[str, Any] | None = None,
    ) -> PlanStep:
        step = PlanStep.create(
            order=len(self.steps) + 1,
            description=description,
            step_type=step_type,
            tool_name=tool_name,
            tool_args=tool_args,
        )
        self.steps.append(step)
        return step

    def get_step(self, step_id: str) -> PlanStep | None:
        for step in self.steps:
            if step.id == step_id:
                return step
        return None

    def approve_step(self, step_id: str) -> bool:
        step = self.get_step(step_id)
        if step and step.status == StepStatus.PENDING:
            step.status = StepStatus.APPROVED
            return True
        return False

    def skip_step(self, step_id: str) -> bool:
        step = self.get_step(step_id)
        if step and step.status in (StepStatus.PENDING, StepStatus.APPROVED):
            step.status = StepStatus.SKIPPED
            return True
        return False

    def approve_all(self) -> int:
        count = 0
        for step in self.steps:
            if step.status == StepStatus.PENDING:
                step.status = StepStatus.APPROVED
                count += 1
        return count

    def get_next_step(self) -> PlanStep | None:
        for step in self.steps:
            if step.status == StepStatus.APPROVED:
                return step
        return None

    @property
    def is_complete(self) -> bool:
        return all(
            step.status in (StepStatus.COMPLETED, StepStatus.SKIPPED, StepStatus.FAILED)
            for step in self.steps
        )

    @property
    def progress(self) -> float:
        if not self.steps:
            return 0.0
        done = sum(
            1
            for s in self.steps
            if s.status in (StepStatus.COMPLETED, StepStatus.SKIPPED, StepStatus.FAILED)
        )
        return done / len(self.steps)


PLAN_GENERATION_PROMPT = """You are a task planner. Create a step-by-step plan to achieve the user's goal.

IMPORTANT: Output ONLY the plan steps. Do NOT output any code, explanations, or other content.

Each step must follow this EXACT format:

STEP 1: Brief description of what to do
TYPE: prompt

STEP 2: Brief description of next action
TYPE: tool
TOOL: run_command
ARGS: {{"command": "the shell command"}}

Available step types:
- "prompt" = AI will think/reason about this step
- "tool" = Execute a tool (run_command, read_file, write_file)
- "checkpoint" = Pause for user review

Available tools for TYPE: tool:
- run_command: Run a shell command. ARGS: {{"command": "..."}}
- read_file: Read a file. ARGS: {{"path": "..."}}
- write_file: Write a file. ARGS: {{"path": "...", "content": "..."}}

Goal: {goal}

{context}

Now output the plan steps (3-7 steps, nothing else):"""


class PlanManager:
    def __init__(self):
        self.plans: dict[str, Plan] = {}
        self.active_plan_id: str | None = None

    @property
    def active_plan(self) -> Plan | None:
        if self.active_plan_id:
            return self.plans.get(self.active_plan_id)
        return None

    async def generate_plan(
        self,
        goal: str,
        provider: LLMProvider,
        context: str = "",
    ) -> Plan:
        plan = Plan.create(goal)

        prompt = PLAN_GENERATION_PROMPT.format(
            goal=goal,
            context=context[:2000] if context else "No additional context.",
        )

        response = ""
        async for chunk in provider.generate(
            prompt,
            [],
            system_prompt="You are a precise task planner. Output only the plan steps in the exact format specified.",
        ):
            response += chunk

        self._parse_plan_response(plan, response)

        self.plans[plan.id] = plan
        self.active_plan_id = plan.id

        return plan

    def _parse_plan_response(self, plan: Plan, response: str) -> None:
        import re

        type_pattern = r"TYPE:\s*(prompt|tool|checkpoint)"
        tool_pattern = r"TOOL:\s*(\w+)"
        args_pattern = r"ARGS:\s*(\{.+?\})"

        lines = response.strip().split("\n")
        current_step: dict[str, Any] = {}

        for line in lines:
            line = line.strip()
            if not line:
                continue

            if line.upper().startswith("STEP"):
                if current_step.get("description"):
                    self._add_parsed_step(plan, current_step)
                match = re.search(r"STEP\s*\d+:\s*(.+)", line, re.IGNORECASE)
                current_step = {
                    "description": match.group(1).strip() if match else line,
                    "type": StepType.PROMPT,
                }
            elif line.upper().startswith("TYPE:"):
                match = re.search(type_pattern, line, re.IGNORECASE)
                if match:
                    type_str = match.group(1).lower()
                    current_step["type"] = {
                        "prompt": StepType.PROMPT,
                        "tool": StepType.TOOL,
                        "checkpoint": StepType.CHECKPOINT,
                    }.get(type_str, StepType.PROMPT)
            elif line.upper().startswith("TOOL:"):
                match = re.search(tool_pattern, line, re.IGNORECASE)
                if match:
                    current_step["tool_name"] = match.group(1)
            elif line.upper().startswith("ARGS:"):
                match = re.search(args_pattern, line, re.IGNORECASE)
                if match:
                    try:
                        import json

                        current_step["tool_args"] = json.loads(match.group(1))
                    except json.JSONDecodeError:
                        pass

        if current_step.get("description"):
            self._add_parsed_step(plan, current_step)

        if not plan.steps:
            plan.add_step(f"Execute: {plan.goal}", StepType.PROMPT)

    def _add_parsed_step(self, plan: Plan, step_data: dict[str, Any]) -> None:
        plan.add_step(
            description=step_data.get("description", ""),
            step_type=step_data.get("type", StepType.PROMPT),
            tool_name=step_data.get("tool_name"),
            tool_args=step_data.get("tool_args"),
        )

    def get_plan(self, plan_id: str) -> Plan | None:
        return self.plans.get(plan_id)

    def approve_step(self, plan_id: str, step_id: str) -> bool:
        plan = self.get_plan(plan_id)
        if plan:
            return plan.approve_step(step_id)
        return False

    def skip_step(self, plan_id: str, step_id: str) -> bool:
        plan = self.get_plan(plan_id)
        if plan:
            return plan.skip_step(step_id)
        return False

    def approve_all(self, plan_id: str) -> int:
        plan = self.get_plan(plan_id)
        if plan:
            return plan.approve_all()
        return 0

    def cancel_plan(self, plan_id: str) -> bool:
        plan = self.get_plan(plan_id)
        if plan:
            plan.status = PlanStatus.CANCELLED
            if self.active_plan_id == plan_id:
                self.active_plan_id = None
            return True
        return False

    def start_execution(self, plan_id: str) -> bool:
        plan = self.get_plan(plan_id)
        if plan and plan.status in (PlanStatus.DRAFT, PlanStatus.APPROVED):
            plan.status = PlanStatus.EXECUTING
            return True
        return False

    def complete_step(
        self,
        plan_id: str,
        step_id: str,
        result: str | None = None,
        error: str | None = None,
        duration: float | None = None,
    ) -> bool:
        plan = self.get_plan(plan_id)
        if not plan:
            return False

        step = plan.get_step(step_id)
        if not step:
            return False

        if error:
            step.status = StepStatus.FAILED
            step.error = error
        else:
            step.status = StepStatus.COMPLETED
            step.result = result

        step.duration = duration

        if plan.is_complete:
            plan.status = PlanStatus.COMPLETED

        return True
