# Planning Mode

Null Terminal includes a powerful Planning Mode that allows you to create, review, and execute detailed roadmaps for your AI tasks. This ensures you have control over the AI's approach before any code is written.

## Overview

Planning Mode breaks down complex objectives into a series of actionable steps. You can review the plan, edit specific steps, and execute them sequentially or all at once.

## Usage

To start planning mode, use the `/plan` command followed by your goal:

```bash
/plan Refactor the authentication module to use JWTs
```

The AI will analyze your request and generate a structured plan.

### Plan Interface

The plan is displayed as an interactive block in your terminal:

```
┌─────────────────────────────────────────────────────────────┐
│ 📋 Plan: Refactor authentication module              [Edit] │
├─────────────────────────────────────────────────────────────┤
│ ☑ 1. Read current auth implementation                       │
│      └─ read_file: src/auth/handler.py                      │
│ ☐ 2. Identify security vulnerabilities          [Skip] [✓]  │
│      └─ Analyze for common auth pitfalls                    │
│ ☐ 3. Create new JWT-based auth module           [Skip] [✓]  │
│      └─ write_file: src/auth/jwt_handler.py                 │
│ ☐ 4. Update tests                               [Skip] [✓]  │
│      └─ Modify existing test cases                          │
│ ─────────────────────────────────────────────────────────── │
│                    [Approve All] [Execute] [Cancel]          │
└─────────────────────────────────────────────────────────────┘
```

### Interacting with Plans

- **Approve All**: Accepts the entire plan and begins execution.
- **Execute**: Starts executing the approved steps.
- **Edit**: Allows you to modify the plan's goal or steps.
- **Skip**: Skips a specific step.
- **✓ (Check)**: Manually marks a step as complete.

## Commands

| Command | Description |
|---------|-------------|
| `/plan <goal>` | Generate a plan for the goal |
| `/plan show` | Show the current plan |
| `/plan approve` | Approve all pending steps |
| `/plan execute` | Start executing approved steps |
| `/plan save <name>` | Save the current plan as a workflow template |
| `/plan load <name>` | Load a saved plan |

## Configuration

Planning mode behavior can be customized in your `~/.null/config.json`:

```json
{
  "planning": {
    "enabled": true,
    "auto_approve_read_only": true,
    "max_steps": 20,
    "require_approval": true,
    "save_plans": true
  }
}
```

## Best Practices

1.  **Be Specific**: The more specific your goal, the better the generated plan.
2.  **Review Critical Steps**: Pay close attention to steps involving file writes or deletions.
3.  **Iterate**: Use the edit functionality to refine the plan if the AI misses something.
