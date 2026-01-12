"""Workflow template system for Null Terminal."""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Literal

import yaml

logger = logging.getLogger(__name__)


class WorkflowStepType(Enum):
    """Types of workflow steps."""

    PROMPT = "prompt"
    TOOL = "tool"
    CHECKPOINT = "checkpoint"


@dataclass
class WorkflowStep:
    """A single step in a workflow."""

    type: WorkflowStepType
    content: str  # Prompt text or tool description
    tool_name: str | None = None
    tool_args: dict[str, Any] | None = None
    expected_output: str | None = None  # For validation


@dataclass
class Workflow:
    """A workflow template."""

    id: str
    name: str
    description: str
    tags: list[str] = field(default_factory=list)
    variables: dict[str, str] = field(
        default_factory=dict
    )  # Placeholders like {{filename}}
    steps: list[WorkflowStep] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    source: Literal["local", "builtin"] = "local"


class WorkflowManager:
    """Manages workflow templates."""

    def __init__(self, workflows_dir: Path | None = None):
        """Initialize workflow manager.

        Args:
            workflows_dir: Directory to store workflows. Defaults to ~/.null/workflows/
        """
        self.workflows_dir = workflows_dir or Path.home() / ".null" / "workflows"
        self.workflows: dict[str, Workflow] = {}
        self._ensure_directories()

    def _ensure_directories(self) -> None:
        """Ensure workflow directories exist."""
        self.workflows_dir.mkdir(parents=True, exist_ok=True)
        (self.workflows_dir / "builtin").mkdir(parents=True, exist_ok=True)

    def load_workflows(self) -> None:
        """Load all workflows from the workflows directory."""
        self.workflows.clear()

        # Load local workflows
        if self.workflows_dir.exists():
            for yaml_file in self.workflows_dir.glob("*.yaml"):
                if yaml_file.name != "builtin":
                    try:
                        with open(yaml_file) as f:
                            content = f.read()
                            workflow = self.parse_yaml(content)
                            workflow.source = "local"
                            self.workflows[workflow.id] = workflow
                    except Exception as e:
                        logger.warning(
                            f"Failed to load local workflow {yaml_file}: {e}"
                        )

        # Load builtin workflows
        builtin_dir = self.workflows_dir / "builtin"
        if builtin_dir.exists():
            for yaml_file in builtin_dir.glob("*.yaml"):
                try:
                    with open(yaml_file) as f:
                        content = f.read()
                        workflow = self.parse_yaml(content)
                        workflow.source = "builtin"
                        self.workflows[workflow.id] = workflow
                except Exception as e:
                    logger.warning(f"Failed to load builtin workflow {yaml_file}: {e}")

    def save_workflow(self, workflow: Workflow) -> Path:
        """Save a workflow to YAML file.

        Args:
            workflow: Workflow to save

        Returns:
            Path to saved file
        """
        yaml_content = self.to_yaml(workflow)
        file_path = self.workflows_dir / f"{workflow.id}.yaml"

        with open(file_path, "w") as f:
            f.write(yaml_content)

        self.workflows[workflow.id] = workflow
        return file_path

    def parse_yaml(self, content: str) -> Workflow:
        """Parse YAML workflow definition.

        Args:
            content: YAML content string

        Returns:
            Parsed Workflow object
        """
        data = yaml.safe_load(content)

        if not data:
            raise ValueError("Empty YAML content")

        workflow_id = str(uuid.uuid4())[:8]
        name = data.get("name", "Untitled Workflow")
        description = data.get("description", "")
        tags = data.get("tags", [])
        variables = data.get("variables", {})

        steps: list[WorkflowStep] = []
        for step_data in data.get("steps", []):
            step_type = WorkflowStepType(step_data.get("type", "prompt"))
            content = step_data.get("content", "")
            tool_name = step_data.get("tool_name")
            tool_args = step_data.get("tool_args")
            expected_output = step_data.get("expected_output")

            step = WorkflowStep(
                type=step_type,
                content=content,
                tool_name=tool_name,
                tool_args=tool_args,
                expected_output=expected_output,
            )
            steps.append(step)

        return Workflow(
            id=workflow_id,
            name=name,
            description=description,
            tags=tags,
            variables=variables,
            steps=steps,
            created_at=datetime.now(),
            source="local",
        )

    def to_yaml(self, workflow: Workflow) -> str:
        """Convert workflow to YAML string.

        Args:
            workflow: Workflow to convert

        Returns:
            YAML string representation
        """
        data = {
            "name": workflow.name,
            "description": workflow.description,
            "tags": workflow.tags,
            "variables": workflow.variables,
            "steps": [],
        }

        for step in workflow.steps:
            step_dict: dict[str, Any] = {
                "type": step.type.value,
                "content": step.content,
            }
            if step.tool_name:
                step_dict["tool_name"] = step.tool_name
            if step.tool_args:
                step_dict["tool_args"] = step.tool_args
            if step.expected_output:
                step_dict["expected_output"] = step.expected_output

            data["steps"].append(step_dict)

        return yaml.dump(data, default_flow_style=False, sort_keys=False)

    def substitute_variables(
        self, workflow: Workflow, values: dict[str, str]
    ) -> Workflow:
        """Replace {{variable}} placeholders with actual values.

        Args:
            workflow: Workflow to substitute
            values: Dictionary of variable values

        Returns:
            New Workflow with substituted values
        """
        # Create a copy of the workflow
        new_workflow = Workflow(
            id=workflow.id,
            name=workflow.name,
            description=workflow.description,
            tags=workflow.tags,
            variables=workflow.variables,
            steps=[],
            created_at=workflow.created_at,
            source=workflow.source,
        )

        # Substitute variables in each step
        for step in workflow.steps:
            new_content = step.content
            new_tool_args = step.tool_args

            # Replace {{variable}} with values
            for var_name, var_value in values.items():
                placeholder = f"{{{{{var_name}}}}}"
                new_content = new_content.replace(placeholder, var_value)

                if new_tool_args:
                    # Recursively replace in tool args
                    new_tool_args = self._substitute_in_dict(
                        new_tool_args, placeholder, var_value
                    )

            new_step = WorkflowStep(
                type=step.type,
                content=new_content,
                tool_name=step.tool_name,
                tool_args=new_tool_args,
                expected_output=step.expected_output,
            )
            new_workflow.steps.append(new_step)

        return new_workflow

    def _substitute_in_dict(
        self, data: dict[str, Any], placeholder: str, value: str
    ) -> dict[str, Any]:
        """Recursively substitute placeholders in a dictionary.

        Args:
            data: Dictionary to process
            placeholder: Placeholder string to replace
            value: Replacement value

        Returns:
            Dictionary with substitutions
        """
        result = {}
        for key, val in data.items():
            if isinstance(val, str):
                result[key] = val.replace(placeholder, value)
            elif isinstance(val, dict):
                result[key] = self._substitute_in_dict(val, placeholder, value)
            elif isinstance(val, list):
                result[key] = [
                    item.replace(placeholder, value) if isinstance(item, str) else item
                    for item in val
                ]
            else:
                result[key] = val
        return result

    def list_workflows(self, tags: list[str] | None = None) -> list[Workflow]:
        """List workflows, optionally filtered by tags.

        Args:
            tags: Optional list of tags to filter by

        Returns:
            List of matching workflows
        """
        workflows = list(self.workflows.values())

        if tags:
            workflows = [w for w in workflows if any(tag in w.tags for tag in tags)]

        return sorted(workflows, key=lambda w: w.name)

    def get_workflow(self, workflow_id: str) -> Workflow | None:
        """Get a workflow by ID.

        Args:
            workflow_id: Workflow ID

        Returns:
            Workflow or None if not found
        """
        return self.workflows.get(workflow_id)

    def get_workflow_by_name(self, name: str) -> Workflow | None:
        """Get a workflow by name.

        Args:
            name: Workflow name

        Returns:
            Workflow or None if not found
        """
        for workflow in self.workflows.values():
            if workflow.name.lower() == name.lower():
                return workflow
        return None

    def delete_workflow(self, workflow_id: str) -> bool:
        """Delete a workflow.

        Args:
            workflow_id: Workflow ID

        Returns:
            True if deleted, False if not found
        """
        workflow = self.workflows.get(workflow_id)
        if not workflow:
            return False

        if workflow.source == "local":
            file_path = self.workflows_dir / f"{workflow_id}.yaml"
            if file_path.exists():
                file_path.unlink()

        del self.workflows[workflow_id]
        return True
