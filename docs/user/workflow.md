# Workflows & Agents

Null Terminal allows you to save successful agent sessions as reusable workflows and orchestrate multi-agent tasks.

## Workflow Templates

Workflows are saved sequences of prompts and tool executions that can be replayed with different variables.

### Browsing Workflows

Use the `/workflow` command to open the workflow browser:

```bash
/workflow
```

You'll see a list of available workflows, including built-in ones and those you've saved.

### Running a Workflow

Select a workflow to run it. You may be prompted to provide values for variables defined in the template (e.g., `{{filename}}`, `{{error_message}}`).

```bash
/workflow run debug-python
```

### Creating Workflows

You can save any successful agent session as a workflow:

```bash
/workflow save "Refactor Component"
```

Null Terminal will attempt to identify variables (like file paths) and parameterize them for future use.

## Background Agents

For long-running tasks, you can spawn agents in the background.

### Starting a Background Task

```bash
/bg Analyze the entire codebase for security vulnerabilities
```

This creates a detached agent process. You can continue using the terminal while it works.

### Managing Tasks

-   `/bg list`: View all running background tasks.
-   `/bg status <id>`: Check the progress of a specific task.
-   `/bg logs <id>`: View the execution logs.
-   `/bg cancel <id>`: Stop a task.

## Multi-Agent Orchestration

Null Terminal supports specialized agents working together.

### Roles

-   **Planner**: Breaks down complex tasks.
-   **Coder**: Writes and modifies code.
-   **Reviewer**: Checks code for quality and bugs.
-   **Tester**: Writes and runs tests.

### Starting an Orchestrated Task

```bash
/orchestrate Implement a new user registration flow
```

A **Coordinator Agent** will analyze your request and assign subtasks to the appropriate specialized agents. You'll see a live view of their collaboration.

## Configuration

Customize agent behavior in `~/.null/config.json`:

```json
{
  "background_agents": {
    "enabled": true,
    "max_concurrent": 3
  },
  "orchestration": {
    "enabled": true,
    "parallel_execution": true
  }
}
```
