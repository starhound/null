# Planning Mode

Planning Mode allows you to orchestrate complex AI tasks by creating a structured roadmap before execution. It provides a safety layer where you can review, modify, and approve each step the AI intends to take.

## Overview

When you initiate Planning Mode, the AI analyzes your objective and breaks it down into a series of actionable steps. This "Look Before You Leap" approach ensures that you maintain full control over the AI's actions, especially when dealing with file modifications or system commands.

---

## Getting Started

To create a new plan, use the `/plan` command followed by your goal.

### Example
```bash
/plan Refactor the authentication module to use JWTs
```

The AI will generate a plan consisting of multiple steps, which will be displayed in an interactive block.

---

## Interactive Interface

The Plan Interface is a specialized block that allows you to manage the lifecycle of your task.

```text
┌─────────────────────────────────────────────────────────────┐
│ 📋 Plan: Refactor authentication module              [Edit] │
├─────────────────────────────────────────────────────────────┤
│ ◉ 1. [a1b2c3d4] [tool] Read current auth implementation      │
│      Tool: read_file(path="src/auth/handler.py")            │
│ ○ 2. [e5f6g7h8] [prompt] Identify security vulnerabilities   │
│ ○ 3. [i9j0k1l2] [tool] Create new JWT auth module            │
│      Tool: write_file(path="src/auth/jwt_handler.py", ...)  │
│ ○ 4. [m3n4o5p6] [checkpoint] Review implementation           │
│ ─────────────────────────────────────────────────────────── │
│                    [Approve All] [Execute] [Cancel]          │
└─────────────────────────────────────────────────────────────┘
```

### Step Status Indicators

| Icon | Status | Description |
| :--- | :--- | :--- |
| `○` | **Pending** | Step is waiting for approval. |
| `◉` | **Approved** | Step is ready to be executed. |
| `▶` | **Executing** | Step is currently running. |
| `✓` | **Completed** | Step finished successfully. |
| `✗` | **Failed** | Step encountered an error. |
| `⊘` | **Skipped** | Step was manually skipped. |

---

## Command Reference

Planning Mode supports several subcommands for fine-grained control.

=== "/plan <goal>"
    Generates a new plan for the specified goal.
    ```bash
    /plan "Implement a new feature in the dashboard"
    ```

=== "/plan status"
    Shows the details and progress of the currently active plan.

=== "/plan approve"
    Approves steps for execution.
    ```bash
    /plan approve all       # Approve all pending steps
    /plan approve a1b2c3d4  # Approve a specific step by ID
    ```

=== "/plan skip"
    Skips a specific step.
    ```bash
    /plan skip e5f6g7h8
    ```

=== "/plan execute"
    Starts or continues the execution of all approved steps.

=== "/plan cancel"
    Aborts the active plan and clears it from the current session.

=== "/plan list"
    Lists all plans created in the current session.

---

## Step Types

Plans consist of three primary types of steps:

| Type | Description |
| :--- | :--- |
| `prompt` | The AI performs reasoning, analysis, or code generation without side effects. |
| `tool` | The AI executes a specific tool (e.g., `read_file`, `write_file`, `run_command`). |
| `checkpoint` | Execution pauses automatically, allowing you to review the state before proceeding. |

!!! info "Tool Approvals"
    Even if a step is approved in the plan, Null Terminal may still prompt for confirmation before executing "dangerous" tools like `write_file` or `run_command`, depending on your [Security Settings](configuration.md#security).

---

## Configuration

You can customize the planning behavior in your `config.json`.

```json title="~/.null/config.json"
{
  "planning": {
    "enabled": true,
    "max_steps": 20,
    "require_approval": true,
    "auto_approve_read_only": true
  }
}
```

| Setting | Default | Description |
| :--- | :--- | :--- |
| `enabled` | `true` | Globally enable or disable planning mode. |
| `max_steps` | `20` | Maximum number of steps the AI can generate for a single plan. |
| `require_approval` | `true` | If true, steps must be approved before they can be executed. |
| `auto_approve_read_only`| `true` | Automatically approve `read_file` and other non-destructive tools. |

---

## Best Practices

!!! tip "Be Specific"
    The quality of the generated plan depends heavily on the specificity of your goal. Instead of "Fix the bug," try "Fix the race condition in the message queue handler."

!!! warning "Review Tool Arguments"
    Always check the arguments of `tool` steps (especially `run_command`) before approving them. You can see the full tool call in the plan status.

!!! info "Iterative Planning"
    If the generated plan isn't quite right, you can `/plan cancel` and try again with more context or a more refined goal.
