from datetime import datetime

import pytest

from managers.workflow import (
    Workflow,
    WorkflowManager,
    WorkflowStep,
    WorkflowStepType,
)


class TestWorkflowStepType:
    def test_prompt_type(self):
        assert WorkflowStepType.PROMPT.value == "prompt"

    def test_tool_type(self):
        assert WorkflowStepType.TOOL.value == "tool"

    def test_checkpoint_type(self):
        assert WorkflowStepType.CHECKPOINT.value == "checkpoint"

    def test_all_types_exist(self):
        types = [
            WorkflowStepType.PROMPT,
            WorkflowStepType.TOOL,
            WorkflowStepType.CHECKPOINT,
        ]
        assert len(types) == 3

    def test_enum_from_value_prompt(self):
        step_type = WorkflowStepType("prompt")
        assert step_type == WorkflowStepType.PROMPT

    def test_enum_from_value_tool(self):
        step_type = WorkflowStepType("tool")
        assert step_type == WorkflowStepType.TOOL

    def test_enum_from_value_checkpoint(self):
        step_type = WorkflowStepType("checkpoint")
        assert step_type == WorkflowStepType.CHECKPOINT


class TestWorkflowStep:
    def test_create_basic_step(self):
        step = WorkflowStep(
            type=WorkflowStepType.PROMPT, content="Ask the user a question"
        )
        assert step.type == WorkflowStepType.PROMPT
        assert step.content == "Ask the user a question"
        assert step.tool_name is None
        assert step.tool_args is None
        assert step.expected_output is None

    def test_create_tool_step(self):
        step = WorkflowStep(
            type=WorkflowStepType.TOOL,
            content="Run a command",
            tool_name="run_command",
            tool_args={"command": "ls -la"},
        )
        assert step.type == WorkflowStepType.TOOL
        assert step.content == "Run a command"
        assert step.tool_name == "run_command"
        assert step.tool_args == {"command": "ls -la"}

    def test_create_checkpoint_step(self):
        step = WorkflowStep(type=WorkflowStepType.CHECKPOINT, content="Review progress")
        assert step.type == WorkflowStepType.CHECKPOINT
        assert step.content == "Review progress"

    def test_step_with_expected_output(self):
        step = WorkflowStep(
            type=WorkflowStepType.PROMPT,
            content="Generate code",
            expected_output="Python function",
        )
        assert step.expected_output == "Python function"

    def test_step_with_complex_tool_args(self):
        tool_args = {
            "command": "python script.py",
            "timeout": 30,
            "env": {"VAR": "value"},
        }
        step = WorkflowStep(
            type=WorkflowStepType.TOOL,
            content="Execute script",
            tool_name="run_command",
            tool_args=tool_args,
        )
        assert step.tool_args == tool_args
        assert step.tool_args["timeout"] == 30

    def test_step_default_none_values(self):
        step = WorkflowStep(type=WorkflowStepType.PROMPT, content="Test")
        assert step.tool_name is None
        assert step.tool_args is None
        assert step.expected_output is None


class TestWorkflow:
    def test_create_workflow_basic(self):
        workflow = Workflow(
            id="test123", name="Test Workflow", description="A test workflow"
        )
        assert workflow.id == "test123"
        assert workflow.name == "Test Workflow"
        assert workflow.description == "A test workflow"
        assert workflow.tags == []
        assert workflow.variables == {}
        assert workflow.steps == []
        assert workflow.source == "local"

    def test_create_workflow_with_tags(self):
        workflow = Workflow(
            id="test123", name="Test", description="Test", tags=["python", "automation"]
        )
        assert workflow.tags == ["python", "automation"]

    def test_create_workflow_with_variables(self):
        variables = {"filename": "data.txt", "timeout": "30"}
        workflow = Workflow(
            id="test123", name="Test", description="Test", variables=variables
        )
        assert workflow.variables == variables

    def test_create_workflow_with_steps(self):
        step1 = WorkflowStep(type=WorkflowStepType.PROMPT, content="Step 1")
        step2 = WorkflowStep(
            type=WorkflowStepType.TOOL, content="Step 2", tool_name="run"
        )
        workflow = Workflow(
            id="test123", name="Test", description="Test", steps=[step1, step2]
        )
        assert len(workflow.steps) == 2
        assert workflow.steps[0] == step1
        assert workflow.steps[1] == step2

    def test_create_workflow_with_source_builtin(self):
        workflow = Workflow(
            id="test123", name="Test", description="Test", source="builtin"
        )
        assert workflow.source == "builtin"

    def test_workflow_created_at_default(self):
        workflow = Workflow(id="test123", name="Test", description="Test")
        assert isinstance(workflow.created_at, datetime)

    def test_workflow_created_at_custom(self):
        custom_time = datetime(2024, 1, 1, 12, 0, 0)
        workflow = Workflow(
            id="test123", name="Test", description="Test", created_at=custom_time
        )
        assert workflow.created_at == custom_time

    def test_workflow_default_factory_tags(self):
        w1 = Workflow(id="1", name="W1", description="D1")
        w2 = Workflow(id="2", name="W2", description="D2")
        w1.tags.append("tag1")
        assert w2.tags == []

    def test_workflow_default_factory_variables(self):
        w1 = Workflow(id="1", name="W1", description="D1")
        w2 = Workflow(id="2", name="W2", description="D2")
        w1.variables["key"] = "value"
        assert w2.variables == {}

    def test_workflow_default_factory_steps(self):
        w1 = Workflow(id="1", name="W1", description="D1")
        w2 = Workflow(id="2", name="W2", description="D2")
        w1.steps.append(WorkflowStep(type=WorkflowStepType.PROMPT, content="S1"))
        assert w2.steps == []


class TestWorkflowManager:
    def test_init_default_workflows_dir(self, mock_home):
        manager = WorkflowManager()
        expected_dir = mock_home / ".null" / "workflows"
        assert manager.workflows_dir == expected_dir
        assert manager.workflows == {}

    def test_init_custom_workflows_dir(self, temp_dir):
        custom_dir = temp_dir / "custom_workflows"
        manager = WorkflowManager(workflows_dir=custom_dir)
        assert manager.workflows_dir == custom_dir

    def test_ensure_directories_creates_dirs(self, temp_dir):
        workflows_dir = temp_dir / "workflows"
        WorkflowManager(workflows_dir=workflows_dir)
        assert workflows_dir.exists()
        assert (workflows_dir / "builtin").exists()

    def test_ensure_directories_idempotent(self, temp_dir):
        workflows_dir = temp_dir / "workflows"
        manager = WorkflowManager(workflows_dir=workflows_dir)
        manager._ensure_directories()
        assert workflows_dir.exists()
        assert (workflows_dir / "builtin").exists()

    def test_parse_yaml_basic(self):
        manager = WorkflowManager()
        yaml_content = """
name: Test Workflow
description: A test workflow
tags:
  - python
  - test
variables:
  filename: data.txt
steps:
  - type: prompt
    content: Ask a question
  - type: tool
    content: Run command
    tool_name: run_command
    tool_args:
      command: ls -la
"""
        workflow = manager.parse_yaml(yaml_content)
        assert workflow.name == "Test Workflow"
        assert workflow.description == "A test workflow"
        assert "python" in workflow.tags
        assert "test" in workflow.tags
        assert workflow.variables["filename"] == "data.txt"
        assert len(workflow.steps) == 2
        assert workflow.steps[0].type == WorkflowStepType.PROMPT
        assert workflow.steps[1].type == WorkflowStepType.TOOL
        assert workflow.steps[1].tool_name == "run_command"

    def test_parse_yaml_empty_raises(self):
        manager = WorkflowManager()
        with pytest.raises(ValueError, match="Empty YAML content"):
            manager.parse_yaml("")

    def test_parse_yaml_null_raises(self):
        manager = WorkflowManager()
        with pytest.raises(ValueError, match="Empty YAML content"):
            manager.parse_yaml("null")

    def test_parse_yaml_defaults(self):
        manager = WorkflowManager()
        yaml_content = """
name: Minimal
"""
        workflow = manager.parse_yaml(yaml_content)
        assert workflow.name == "Minimal"
        assert workflow.description == ""
        assert workflow.tags == []
        assert workflow.variables == {}
        assert workflow.steps == []

    def test_parse_yaml_missing_name(self):
        manager = WorkflowManager()
        yaml_content = """
description: No name
"""
        workflow = manager.parse_yaml(yaml_content)
        assert workflow.name == "Untitled Workflow"
        assert workflow.description == "No name"

    def test_parse_yaml_with_checkpoint(self):
        manager = WorkflowManager()
        yaml_content = """
name: With Checkpoint
steps:
  - type: checkpoint
    content: Review progress
"""
        workflow = manager.parse_yaml(yaml_content)
        assert workflow.steps[0].type == WorkflowStepType.CHECKPOINT

    def test_parse_yaml_step_with_expected_output(self):
        manager = WorkflowManager()
        yaml_content = """
name: Test
steps:
  - type: prompt
    content: Generate code
    expected_output: Python function
"""
        workflow = manager.parse_yaml(yaml_content)
        assert workflow.steps[0].expected_output == "Python function"

    def test_parse_yaml_step_defaults(self):
        manager = WorkflowManager()
        yaml_content = """
name: Test
steps:
  - type: prompt
    content: Test step
"""
        workflow = manager.parse_yaml(yaml_content)
        step = workflow.steps[0]
        assert step.tool_name is None
        assert step.tool_args is None
        assert step.expected_output is None

    def test_parse_yaml_generates_unique_ids(self):
        manager = WorkflowManager()
        yaml_content = "name: Test"
        w1 = manager.parse_yaml(yaml_content)
        w2 = manager.parse_yaml(yaml_content)
        assert w1.id != w2.id

    def test_to_yaml_basic(self):
        manager = WorkflowManager()
        workflow = Workflow(
            id="test123",
            name="Test",
            description="Test description",
            tags=["tag1", "tag2"],
            variables={"var1": "value1"},
        )
        yaml_str = manager.to_yaml(workflow)
        assert "name: Test" in yaml_str
        assert "description: Test description" in yaml_str
        assert "tag1" in yaml_str
        assert "var1" in yaml_str

    def test_to_yaml_with_steps(self):
        manager = WorkflowManager()
        step1 = WorkflowStep(type=WorkflowStepType.PROMPT, content="Step 1")
        step2 = WorkflowStep(
            type=WorkflowStepType.TOOL,
            content="Step 2",
            tool_name="run_command",
            tool_args={"command": "ls"},
        )
        workflow = Workflow(
            id="test123", name="Test", description="Test", steps=[step1, step2]
        )
        yaml_str = manager.to_yaml(workflow)
        assert "type: prompt" in yaml_str
        assert "type: tool" in yaml_str
        assert "tool_name: run_command" in yaml_str
        assert "command: ls" in yaml_str

    def test_to_yaml_step_without_optional_fields(self):
        manager = WorkflowManager()
        step = WorkflowStep(type=WorkflowStepType.PROMPT, content="Test")
        workflow = Workflow(id="test123", name="Test", description="Test", steps=[step])
        yaml_str = manager.to_yaml(workflow)
        assert "tool_name:" not in yaml_str
        assert "tool_args:" not in yaml_str
        assert "expected_output:" not in yaml_str

    def test_to_yaml_roundtrip(self):
        manager = WorkflowManager()
        original = Workflow(
            id="test123",
            name="Test Workflow",
            description="Test description",
            tags=["python", "automation"],
            variables={"filename": "data.txt"},
            steps=[
                WorkflowStep(type=WorkflowStepType.PROMPT, content="Ask question"),
                WorkflowStep(
                    type=WorkflowStepType.TOOL,
                    content="Run tool",
                    tool_name="run_command",
                    tool_args={"command": "ls"},
                ),
            ],
        )
        yaml_str = manager.to_yaml(original)
        parsed = manager.parse_yaml(yaml_str)
        assert parsed.name == original.name
        assert parsed.description == original.description
        assert parsed.tags == original.tags
        assert parsed.variables == original.variables
        assert len(parsed.steps) == len(original.steps)

    def test_save_workflow(self, temp_dir):
        manager = WorkflowManager(workflows_dir=temp_dir)
        workflow = Workflow(id="test123", name="Test", description="Test")
        file_path = manager.save_workflow(workflow)
        assert file_path == temp_dir / "test123.yaml"
        assert file_path.exists()
        assert workflow.id in manager.workflows

    def test_save_workflow_updates_dict(self, temp_dir):
        manager = WorkflowManager(workflows_dir=temp_dir)
        workflow = Workflow(id="test123", name="Test", description="Test")
        manager.save_workflow(workflow)
        assert manager.workflows["test123"] == workflow

    def test_save_workflow_overwrites(self, temp_dir):
        manager = WorkflowManager(workflows_dir=temp_dir)
        workflow1 = Workflow(id="test123", name="V1", description="V1")
        workflow2 = Workflow(id="test123", name="V2", description="V2")
        manager.save_workflow(workflow1)
        manager.save_workflow(workflow2)
        assert manager.workflows["test123"].name == "V2"

    def test_load_workflows_empty_dir(self, temp_dir):
        manager = WorkflowManager(workflows_dir=temp_dir)
        manager.load_workflows()
        assert manager.workflows == {}

    def test_load_workflows_local(self, temp_dir):
        manager = WorkflowManager(workflows_dir=temp_dir)
        workflow = Workflow(id="test123", name="Test", description="Test")
        manager.save_workflow(workflow)
        manager.workflows.clear()
        manager.load_workflows()
        assert len(manager.workflows) == 1
        loaded_workflow = next(iter(manager.workflows.values()))
        assert loaded_workflow.name == "Test"
        assert loaded_workflow.source == "local"

    def test_load_workflows_builtin(self, temp_dir):
        manager = WorkflowManager(workflows_dir=temp_dir)
        builtin_dir = temp_dir / "builtin"
        builtin_dir.mkdir(parents=True, exist_ok=True)
        yaml_content = "name: Builtin Workflow"
        (builtin_dir / "builtin123.yaml").write_text(yaml_content)
        manager.load_workflows()
        assert len(manager.workflows) == 1
        workflow = next(iter(manager.workflows.values()))
        assert workflow.source == "builtin"

    def test_load_workflows_both_local_and_builtin(self, temp_dir):
        manager = WorkflowManager(workflows_dir=temp_dir)
        local_workflow = Workflow(id="local1", name="Local", description="Local")
        manager.save_workflow(local_workflow)
        builtin_dir = temp_dir / "builtin"
        builtin_dir.mkdir(parents=True, exist_ok=True)
        (builtin_dir / "builtin1.yaml").write_text("name: Builtin")
        manager.workflows.clear()
        manager.load_workflows()
        assert len(manager.workflows) == 2
        local = [w for w in manager.workflows.values() if w.source == "local"]
        builtin = [w for w in manager.workflows.values() if w.source == "builtin"]
        assert len(local) == 1
        assert len(builtin) == 1

    def test_load_workflows_handles_invalid_yaml(self, temp_dir):
        manager = WorkflowManager(workflows_dir=temp_dir)
        (temp_dir / "invalid.yaml").write_text(":\n  - invalid\n    - yaml")
        manager.load_workflows()
        assert manager.workflows == {}

    def test_load_workflows_handles_missing_fields(self, temp_dir):
        manager = WorkflowManager(workflows_dir=temp_dir)
        (temp_dir / "minimal.yaml").write_text("name: Minimal")
        manager.load_workflows()
        assert len(manager.workflows) == 1

    def test_substitute_variables_simple(self):
        manager = WorkflowManager()
        step = WorkflowStep(
            type=WorkflowStepType.PROMPT, content="Process {{filename}}"
        )
        workflow = Workflow(id="test", name="Test", description="Test", steps=[step])
        result = manager.substitute_variables(workflow, {"filename": "data.txt"})
        assert result.steps[0].content == "Process data.txt"

    def test_substitute_variables_multiple(self):
        manager = WorkflowManager()
        step = WorkflowStep(
            type=WorkflowStepType.PROMPT,
            content="Process {{filename}} with timeout {{timeout}}",
        )
        workflow = Workflow(id="test", name="Test", description="Test", steps=[step])
        result = manager.substitute_variables(
            workflow, {"filename": "data.txt", "timeout": "30"}
        )
        assert result.steps[0].content == "Process data.txt with timeout 30"

    def test_substitute_variables_in_tool_args(self):
        manager = WorkflowManager()
        step = WorkflowStep(
            type=WorkflowStepType.TOOL,
            content="Run command",
            tool_name="run_command",
            tool_args={"command": "process {{filename}}"},
        )
        workflow = Workflow(id="test", name="Test", description="Test", steps=[step])
        result = manager.substitute_variables(workflow, {"filename": "data.txt"})
        assert result.steps[0].tool_args["command"] == "process data.txt"

    def test_substitute_variables_nested_dict(self):
        manager = WorkflowManager()
        step = WorkflowStep(
            type=WorkflowStepType.TOOL,
            content="Test",
            tool_name="test",
            tool_args={"outer": {"inner": "value {{var}}"}},
        )
        workflow = Workflow(id="test", name="Test", description="Test", steps=[step])
        result = manager.substitute_variables(workflow, {"var": "replaced"})
        assert result.steps[0].tool_args["outer"]["inner"] == "value replaced"

    def test_substitute_variables_in_list(self):
        manager = WorkflowManager()
        step = WorkflowStep(
            type=WorkflowStepType.TOOL,
            content="Test",
            tool_name="test",
            tool_args={"items": ["item {{var}}", "static"]},
        )
        workflow = Workflow(id="test", name="Test", description="Test", steps=[step])
        result = manager.substitute_variables(workflow, {"var": "1"})
        assert result.steps[0].tool_args["items"][0] == "item 1"
        assert result.steps[0].tool_args["items"][1] == "static"

    def test_substitute_variables_preserves_original(self):
        manager = WorkflowManager()
        step = WorkflowStep(
            type=WorkflowStepType.PROMPT, content="Process {{filename}}"
        )
        workflow = Workflow(id="test", name="Test", description="Test", steps=[step])
        result = manager.substitute_variables(workflow, {"filename": "data.txt"})
        assert workflow.steps[0].content == "Process {{filename}}"
        assert result.steps[0].content == "Process data.txt"

    def test_substitute_variables_no_substitution(self):
        manager = WorkflowManager()
        step = WorkflowStep(type=WorkflowStepType.PROMPT, content="No variables here")
        workflow = Workflow(id="test", name="Test", description="Test", steps=[step])
        result = manager.substitute_variables(workflow, {"filename": "data.txt"})
        assert result.steps[0].content == "No variables here"

    def test_substitute_in_dict_string_value(self):
        manager = WorkflowManager()
        data = {"key": "value {{var}}"}
        result = manager._substitute_in_dict(data, "{{var}}", "replaced")
        assert result["key"] == "value replaced"

    def test_substitute_in_dict_nested_dict(self):
        manager = WorkflowManager()
        data = {"outer": {"inner": "{{var}}"}}
        result = manager._substitute_in_dict(data, "{{var}}", "replaced")
        assert result["outer"]["inner"] == "replaced"

    def test_substitute_in_dict_list_of_strings(self):
        manager = WorkflowManager()
        data = {"items": ["{{var}}", "static"]}
        result = manager._substitute_in_dict(data, "{{var}}", "replaced")
        assert result["items"][0] == "replaced"
        assert result["items"][1] == "static"

    def test_substitute_in_dict_mixed_types(self):
        manager = WorkflowManager()
        data = {
            "string": "{{var}}",
            "number": 42,
            "list": ["{{var}}", 123],
            "nested": {"key": "{{var}}"},
        }
        result = manager._substitute_in_dict(data, "{{var}}", "replaced")
        assert result["string"] == "replaced"
        assert result["number"] == 42
        assert result["list"][0] == "replaced"
        assert result["list"][1] == 123
        assert result["nested"]["key"] == "replaced"

    def test_substitute_in_dict_non_string_list_items(self):
        manager = WorkflowManager()
        data = {"items": [123, 456]}
        result = manager._substitute_in_dict(data, "{{var}}", "replaced")
        assert result["items"] == [123, 456]

    def test_list_workflows_empty(self):
        manager = WorkflowManager()
        workflows = manager.list_workflows()
        assert workflows == []

    def test_list_workflows_all(self):
        manager = WorkflowManager()
        w1 = Workflow(id="1", name="Zebra", description="Z")
        w2 = Workflow(id="2", name="Alpha", description="A")
        w3 = Workflow(id="3", name="Beta", description="B")
        manager.workflows = {"1": w1, "2": w2, "3": w3}
        workflows = manager.list_workflows()
        assert len(workflows) == 3
        assert workflows[0].name == "Alpha"
        assert workflows[1].name == "Beta"
        assert workflows[2].name == "Zebra"

    def test_list_workflows_filter_by_single_tag(self):
        manager = WorkflowManager()
        w1 = Workflow(id="1", name="W1", description="D1", tags=["python"])
        w2 = Workflow(id="2", name="W2", description="D2", tags=["javascript"])
        w3 = Workflow(
            id="3", name="W3", description="D3", tags=["python", "automation"]
        )
        manager.workflows = {"1": w1, "2": w2, "3": w3}
        workflows = manager.list_workflows(tags=["python"])
        assert len(workflows) == 2
        assert w1 in workflows
        assert w3 in workflows

    def test_list_workflows_filter_by_multiple_tags(self):
        manager = WorkflowManager()
        w1 = Workflow(id="1", name="W1", description="D1", tags=["python"])
        w2 = Workflow(id="2", name="W2", description="D2", tags=["javascript"])
        w3 = Workflow(id="3", name="W3", description="D3", tags=["automation"])
        manager.workflows = {"1": w1, "2": w2, "3": w3}
        workflows = manager.list_workflows(tags=["python", "automation"])
        assert len(workflows) == 2
        assert w1 in workflows
        assert w3 in workflows

    def test_list_workflows_filter_no_matches(self):
        manager = WorkflowManager()
        w1 = Workflow(id="1", name="W1", description="D1", tags=["python"])
        manager.workflows = {"1": w1}
        workflows = manager.list_workflows(tags=["nonexistent"])
        assert workflows == []

    def test_list_workflows_sorted_by_name(self):
        manager = WorkflowManager()
        w1 = Workflow(id="1", name="Zebra", description="D1")
        w2 = Workflow(id="2", name="Alpha", description="D2")
        w3 = Workflow(id="3", name="Beta", description="D3")
        manager.workflows = {"1": w1, "2": w2, "3": w3}
        workflows = manager.list_workflows()
        names = [w.name for w in workflows]
        assert names == ["Alpha", "Beta", "Zebra"]

    def test_get_workflow_exists(self):
        manager = WorkflowManager()
        workflow = Workflow(id="test123", name="Test", description="Test")
        manager.workflows["test123"] = workflow
        result = manager.get_workflow("test123")
        assert result == workflow

    def test_get_workflow_not_found(self):
        manager = WorkflowManager()
        result = manager.get_workflow("nonexistent")
        assert result is None

    def test_get_workflow_by_name_exact_match(self):
        manager = WorkflowManager()
        workflow = Workflow(id="test123", name="Test Workflow", description="Test")
        manager.workflows["test123"] = workflow
        result = manager.get_workflow_by_name("Test Workflow")
        assert result == workflow

    def test_get_workflow_by_name_case_insensitive(self):
        manager = WorkflowManager()
        workflow = Workflow(id="test123", name="Test Workflow", description="Test")
        manager.workflows["test123"] = workflow
        result = manager.get_workflow_by_name("test workflow")
        assert result == workflow

    def test_get_workflow_by_name_case_insensitive_upper(self):
        manager = WorkflowManager()
        workflow = Workflow(id="test123", name="Test Workflow", description="Test")
        manager.workflows["test123"] = workflow
        result = manager.get_workflow_by_name("TEST WORKFLOW")
        assert result == workflow

    def test_get_workflow_by_name_not_found(self):
        manager = WorkflowManager()
        workflow = Workflow(id="test123", name="Test", description="Test")
        manager.workflows["test123"] = workflow
        result = manager.get_workflow_by_name("Nonexistent")
        assert result is None

    def test_get_workflow_by_name_multiple_workflows(self):
        manager = WorkflowManager()
        w1 = Workflow(id="1", name="Alpha", description="D1")
        w2 = Workflow(id="2", name="Beta", description="D2")
        w3 = Workflow(id="3", name="Gamma", description="D3")
        manager.workflows = {"1": w1, "2": w2, "3": w3}
        result = manager.get_workflow_by_name("beta")
        assert result == w2

    def test_delete_workflow_local(self, temp_dir):
        manager = WorkflowManager(workflows_dir=temp_dir)
        workflow = Workflow(
            id="test123", name="Test", description="Test", source="local"
        )
        manager.save_workflow(workflow)
        assert (temp_dir / "test123.yaml").exists()
        result = manager.delete_workflow("test123")
        assert result is True
        assert "test123" not in manager.workflows
        assert not (temp_dir / "test123.yaml").exists()

    def test_delete_workflow_builtin(self, temp_dir):
        manager = WorkflowManager(workflows_dir=temp_dir)
        workflow = Workflow(
            id="builtin123", name="Builtin", description="Test", source="builtin"
        )
        manager.workflows["builtin123"] = workflow
        result = manager.delete_workflow("builtin123")
        assert result is True
        assert "builtin123" not in manager.workflows

    def test_delete_workflow_not_found(self):
        manager = WorkflowManager()
        result = manager.delete_workflow("nonexistent")
        assert result is False

    def test_delete_workflow_removes_from_dict(self, temp_dir):
        manager = WorkflowManager(workflows_dir=temp_dir)
        workflow = Workflow(
            id="test123", name="Test", description="Test", source="local"
        )
        manager.save_workflow(workflow)
        manager.delete_workflow("test123")
        assert manager.get_workflow("test123") is None

    def test_delete_workflow_file_not_exists(self, temp_dir):
        manager = WorkflowManager(workflows_dir=temp_dir)
        workflow = Workflow(
            id="test123", name="Test", description="Test", source="local"
        )
        manager.workflows["test123"] = workflow
        result = manager.delete_workflow("test123")
        assert result is True
        assert "test123" not in manager.workflows
