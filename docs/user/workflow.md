# Workflows & Orchestration

Null Terminal provides powerful tools for automating repetitive tasks and orchestrating multiple AI agents to solve complex problems.

## Workflow Templates

Workflows are reusable sequences of prompts and tool executions. They allow you to capture successful agent sessions and replay them with different parameters.

### Managing Workflows

Use the `/workflow` command to manage your templates.

=== "/workflow list"
    Displays all available workflows, including built-in templates and your saved sessions.
    ```bash
    /workflow list
    ```

=== "/workflow run"
    Executes a workflow by name. If the workflow defines variables, you will be prompted to provide values.
    ```bash
    /workflow run "Debug Python"
    ```

=== "/workflow save"
    Captures the current or last active agent session as a new workflow template.
    ```bash
    /workflow save "Refactor Component"
    ```

=== "/workflow import/export"
    Share workflows using YAML files.
    ```bash
    /workflow import ./my-workflow.yaml
    /workflow export "Refactor Component"
    ```

!!! tip "Variable Substitution"
    Workflows support dynamic variables using the `{{variable_name}}` syntax. When running a workflow, Null Terminal will automatically detect these placeholders and ask for input.

### Template Format (YAML)

Workflows are stored as YAML files in `~/.null/workflows/`.

```yaml
name: "Python Docstring Generator"
description: "Automatically generates docstrings for all functions in a file"
tags: ["python", "documentation"]
variables:
  file_path: "Path to the Python file"
steps:
  - type: "tool"
    tool_name: "read_file"
    tool_args:
      path: "{{file_path}}"
  - type: "prompt"
    content: "Analyze the functions in {{file_path}} and generate Google-style docstrings for any that are missing."
```

---

## Background Agents (`/bg`)

For long-running tasks that don't require your immediate attention, you can spawn agents in the background. This allows you to continue using the terminal for other tasks while the agent works in a detached process.

### Commands

| Command | Description |
|---------|-------------|
| `/bg <goal>` | Start a new background task with the specified goal. |
| `/bg list` | View all active, queued, and completed background tasks. |
| `/bg status <id>` | Check the detailed progress and results of a specific task. |
| `/bg logs <id>` | View the execution logs for a background agent. |
| `/bg cancel <id>` | Stop a running background task. |
| `/bg clear` | Remove completed tasks from the list. |

!!! info "Detached Execution"
    Background agents run independently of your main session. You can even close Null Terminal and the tasks will continue to run (if configured as a persistent daemon).

---

## Multi-Agent Orchestration (`/orchestrate`)

Complex projects often require different skill sets. Orchestration allows you to deploy a **Coordinator Agent** that manages specialized sub-agents.

### Specialized Roles

The Coordinator delegates tasks to agents with specific profiles:

*   **Planner**: Breaks down the high-level goal into actionable subtasks.
*   **Coder**: Implements features and writes code.
*   **Reviewer**: Analyzes code quality and suggests improvements.
*   **Debugger**: Investigates and fixes failing tests or identified bugs.
*   **Tester**: Generates and executes test suites to ensure correctness.

### Usage

To start an orchestrated task, use the `/orchestrate` command followed by your goal:

```bash
/orchestrate "Build a full-stack Todo app with FastAPI and React"
```

The Coordinator will:
1.  **Analyze** the request and create a multi-step plan.
2.  **Assign** subtasks to specialized agents (e.g., Coder for implementation, Tester for validation).
3.  **Synthesize** the results into a final response.

---

## Configuration

You can tune the behavior of workflows and agents in your `~/.null/config.json`:

```json
{
  "ai": {
    "agent_max_iterations": 20,
    "agent_approval_mode": "per_tool",
    "background_agents": {
      "max_concurrent": 5
    }
  },
  "orchestration": {
    "parallel_execution": true
  }
}
```

!!! warning "Token Usage"
    Multi-agent orchestration and background tasks can consume a significant number of tokens. Keep an eye on the cost tracker in the status bar.
