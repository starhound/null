# Git Operations

Null Terminal integrates deeply with Git to make version control seamless within your AI workflow. Every AI edit becomes a trackable git operation with auto-generated commit messages.

## Overview

The `GitManager` handles all git interactions, ensuring that changes made by the AI are properly staged, committed, and documented.

## Features

### Auto-Commit

When enabled, the AI will automatically commit changes after writing files. It analyzes the diff and generates a conventional commit message.

```
┌─────────────────────────────────────────────────────────────┐
│ 🔄 AI Commit: feat(auth): add JWT refresh token support     │
├─────────────────────────────────────────────────────────────┤
│ Files changed: 3                                             │
│   M src/auth/handler.py (+45, -12)                          │
│   A src/auth/jwt.py (+120)                                  │
│   M tests/test_auth.py (+30, -5)                            │
│ ─────────────────────────────────────────────────────────── │
│                              [View Diff] [Revert] [Amend]    │
└─────────────────────────────────────────────────────────────┘
```

### Diff Viewer

Inspect changes before or after they are applied.

```bash
/diff src/auth/handler.py
```

### Context Awareness

The AI is aware of your repository's state, including:
- Current branch
- Modified files
- Recent commits

This allows for smarter suggestions and context-aware actions.

## Commands

| Command | Description |
|---------|-------------|
| `/diff [file]` | Show diff for file or all changes |
| `/commit [message]` | Commit staged changes (AI generates message if empty) |
| `/undo` | Revert the last AI commit |
| `/git log` | Show recent commits with AI badges |
| `/git stash` | Stash current changes |
| `/git checkout <file>` | Discard changes to a file |

## Configuration

Configure git behavior in `~/.null/config.json`:

```json
{
  "git": {
    "auto_commit": true,
    "commit_format": "conventional",
    "sign_commits": false,
    "show_diff_on_commit": true,
    "allow_revert": true
  }
}
```

## Workflow Example

1.  **AI Change**: You ask the AI to "Refactor the login function".
2.  **Auto-Commit**: The AI modifies `login.py`. Null Terminal detects the change, stages it, generates a commit message like `refactor(auth): simplify login logic`, and commits it.
3.  **Review**: You see the commit block. You click "View Diff" to verify the changes.
4.  **Undo (Optional)**: If the change isn't what you wanted, you type `/undo` to revert the commit and restore the file.
