# Git-Native Operations

Null Terminal treats Git not just as a version control system, but as the foundational **Undo** and **Context** layer for AI-driven development. By integrating deeply with your local repository, Null ensures that every AI interaction is trackable, reversible, and contextually aware.

## Overview

The `GitManager` orchestrates all background Git operations. Whether the AI is refactoring code or creating new files, Null Terminal ensures these changes are staged and documented automatically.

!!! info "Git-as-Undo Philosophy"
    We believe AI edits should never be destructive. By auto-committing AI changes, we provide a robust safety net that allows you to experiment freely and revert to known-good states instantly.

---

## AI-Automated Version Control

### Auto-Commit

When **Auto-Commit** is enabled, Null Terminal automatically stages and commits changes immediately after the AI writes to a file. 

=== "How it Works"
    1. **Diff Analysis**: Null analyzes the changes made by the AI.
    2. **Message Generation**: The AI generates a concise, descriptive commit message based on the diff content.
    3. **Atomic Commit**: Changes are committed, creating a distinct point in history.
    4. **Visual Feedback**: A `CommitBlock` appears in the chat with options to view the diff, revert, or amend.

=== "Configuration"
    You can customize auto-commit behavior in `~/.null/config.json`:
    ```json
    {
      "git": {
        "auto_commit": true,
        "commit_format": "conventional",
        "show_diff_on_commit": true
      }
    }
    ```

!!! tip "Conventional Commits"
    Null Terminal prefers [Conventional Commits](https://www.conventionalcommits.org/) (e.g., `feat:`, `fix:`, `refactor:`) to keep your repository history clean and professional.

---

## Git Slash Commands

Null provides a suite of slash commands to manage your repository without leaving the terminal.

=== "Repository Status"
    | Command | Description |
    |:--- |:--- |
    | `/git status` | Show a summary of staged, unstaged, and untracked files. |
    | `/diff [file]` | View changes in a high-fidelity diff block. (Shortcut for `/git diff`) |
    | `/git log [n]` | View the last `n` commits (defaults to 10). |

=== "Change Management"
    | Command | Description |
    |:--- |:--- |
    | `/git commit [msg]` | Commit staged changes. Generates an AI message if `msg` is omitted. |
    | `/undo` | **The Magic Button.** Reverts the last AI commit and keeps changes staged. |
    | `/git stash` | Stash current changes to a dirty working directory. |
    | `/git stash pop` | Apply the most recently stashed changes. |

=== "Remote & Collaboration"
    | Command | Description |
    |:--- |:--- |
    | `/issue [num/ls]` | View or list GitHub/GitLab issues. |
    | `/pr [num/ls/diff]` | View, list, or see diffs for Pull Requests. |

!!! warning "Dependency"
    Remote operations (`/issue`, `/pr`) require the [GitHub CLI (`gh`)](https://cli.github.com/) or similar to be installed and authenticated on your system.

---

## Visualizing History

### Interactive Commit Blocks
When the AI commits a change, it produces an interactive block in your session:

```text
┌─────────────────────────────────────────────────────────────┐
│ 🔄 AI Commit: refactor(api): simplify endpoint logic        │
├─────────────────────────────────────────────────────────────┤
│ Files changed: 2                                             │
│   M src/api/routes.py (+15, -5)                             │
│   M src/api/utils.py (+2, -1)                               │
│ ─────────────────────────────────────────────────────────── │
│                              [View Diff] [Revert] [Amend]    │
└─────────────────────────────────────────────────────────────┘
```

*   **View Diff**: Opens a syntax-highlighted diff viewer.
*   **Revert**: Immediately performs a `git reset --soft HEAD~1`.
*   **Amend**: Allows you to update the commit message or add more changes.

### Status Bar Integration
Your current Git state is always visible in the Status Bar:
*   **` main`**: Clean working directory.
*   **`± feature-branch`**: Dirty working directory (unstaged changes).

---

## Workflow Example

The following diagram illustrates the typical lifecycle of an AI-assisted change in Null Terminal:

```mermaid
graph TD
    A[User Request] --> B[AI Generates Code]
    B --> C[File Written]
    C --> D{Auto-Commit Enabled?}
    D -- Yes --> E[AI Generates Commit Message]
    E --> F[Git Commit Created]
    F --> G[Interactive Commit Block Shown]
    D -- No --> H[Changes left in Worktree]
    G --> I{User Review}
    I -- Approve --> J[Continue Workflow]
    I -- Dislike --> K[/undo command]
    K --> L[Commit Reverted, Changes Staged]
    L --> M[Ask AI to Fix/Refine]
```

---

## Configuration Reference

Detailed settings for Git operations:

| Key | Type | Default | Description |
|:--- |:--- |:--- |:--- |
| `auto_commit` | `boolean` | `true` | Automatically commit AI changes. |
| `commit_format` | `string` | `"conventional"` | Use conventional commit style. |
| `sign_commits` | `boolean` | `false` | Enable GPG signing for AI commits. |
| `show_diff_on_commit` | `boolean` | `true` | Automatically show diff after a commit. |
| `allow_revert` | `boolean` | `true` | Enable the `/undo` command. |

### Configuration Example
```json
"git": {
  "auto_commit": true,
  "commit_format": "conventional",
  "sign_commits": false,
  "show_diff_on_commit": true,
  "allow_revert": true
}
```
