# Product Roadmap

This roadmap outlines the planned features and strategic direction for Null Terminal. Our goal is to create the ultimate AI-integrated orchestration terminal.

!!! note
    This roadmap is subject to change based on user feedback and community contributions.

---

## 🚀 Active Development

Features currently being designed or implemented.

### 📋 Planning Mode (`/plan`)
**Status:** In Design
**Goal:** Create persistent, editable roadmaps before AI execution.

- **Plan Block**: Visual widget to see the AI's intended steps.
- **Interactive Editing**: Modify, skip, or approve individual steps.
- **Persistence**: Save plans as templates for later use (e.g., standard maintenance procedures).

### 🔄 Git-Native Operations
**Status:** In Design
**Goal:** Make every AI edit a trackable git operation.

- **Auto-Commit**: Automatically generate semantic commit messages for AI changes.
- **In-Chat Diff**: View changes before they are committed.
- **Undo/Revert**: Easily roll back AI mistakes using git infrastructure.

### 📝 Human-in-the-Loop Review
**Status:** In Design
**Goal:** Granular control over AI-generated changes.

- **Diff View**: Review changes per-file or per-hunk.
- **Rationale**: See *why* the AI made a specific change.
- **Safety**: "Propose first, apply later" workflow.

---

## 📅 Coming Soon

Features scheduled for upcoming sprints.

### 🤖 Background Agents
Run long-running tasks (like log analysis, backups, or migrations) in the background while you continue working in the terminal.

### 🔄 Auto-Correction Loop
An agent that automatically iterates on errors (config validation, connection failures, runtime issues) until the task passes verification.

### 🎭 Multi-Agent Orchestration
Specialized agents (Planner, Executor, Auditor, Researcher) collaborating on complex tasks.

---

## 🔮 Future Concepts

Long-term vision and experimental features.

- **Natural Language to Shell**: Convert English descriptions into precise shell commands.
- **Session Sharing**: Share incident post-mortems or workflow logs via URLs.
- **Semantic RAG**: SQLite-backed vector search for your documentation and logs.
- **Visual Branching**: Navigate conversation forks visually.

---

## 💡 Have an Idea?

We welcome community feedback! If you have a feature request, please [open an issue](https://github.com/starhound/null/issues) or start a discussion.
