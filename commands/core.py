"""Core commands: help, status, clear, quit."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app import NullApp
    from managers.git import GitManager

from .base import CommandMixin


class CoreCommands(CommandMixin):
    """Core application commands."""

    def __init__(self, app: NullApp):
        self.app = app

    async def cmd_help(self, args: list[str]):
        """Show help screen."""
        from screens import HelpScreen

        self.app.push_screen(HelpScreen())

    async def cmd_status(self, args: list[str]):
        """Show current status."""
        from context import ContextManager

        provider_name = self.app.config.get("ai", {}).get("provider", "none")

        # Get model from actual provider instance (most accurate)
        if self.app.ai_provider and self.app.ai_provider.model:
            model = self.app.ai_provider.model
        else:
            # Fallback to config
            from config import Config

            model = Config.get(f"ai.{provider_name}.model") or "none"

        persona = self.app.config.get("ai", {}).get("active_prompt", "default")
        blocks_count = len(self.app.blocks)

        context_str = ContextManager.get_context(self.app.blocks)
        context_chars = len(context_str)
        context_tokens = context_chars // 4

        try:
            status_bar = self.app.query_one("#status-bar")
            provider_status = status_bar.provider_status

            # Token usage info
            total_tokens = (
                status_bar.session_input_tokens + status_bar.session_output_tokens
            )
            session_cost = status_bar.session_cost

            s_in = status_bar.session_input_tokens
            s_out = status_bar.session_output_tokens
        except Exception:
            provider_status = "unknown"
            total_tokens = 0
            session_cost = 0.0
            s_in = 0
            s_out = 0

        lines = [
            f"  Provider:      {provider_name} ({provider_status})",
            f"  Model:         {model}",
            f"  Persona:       {persona}",
            f"  Blocks:        {blocks_count}",
            f"  Context:       ~{context_tokens} tokens ({context_chars} chars)",
            f"  Session Tokens: {total_tokens:,} ({s_in:,} in / {s_out:,} out)",
            f"  Session Cost:   ${session_cost:.4f}",
        ]
        await self.show_output("/status", "\n".join(lines))

    async def cmd_clear(self, args: list[str]):
        """Clear history and context."""
        self.app.blocks = []
        self.app.current_cli_block = None
        self.app.current_cli_widget = None

        # Avoid direct import if possible, or use string selector
        try:
            history = self.app.query_one("#history")
            await history.remove_children()
        except Exception:
            pass

        # Reset token usage in status bar
        try:
            status_bar = self.app.query_one("#status-bar")
            if hasattr(status_bar, "reset_token_usage"):
                status_bar.reset_token_usage()
        except Exception:
            pass

        self.app._update_status_bar()
        self.notify("History and context cleared")

    async def cmd_quit(self, args: list[str]):
        """Quit the application."""
        self.app.exit()

    async def cmd_exit(self, args: list[str]):
        """Exit the application (alias)."""
        self.app.exit()

    async def cmd_ssh(self, args: list[str]):
        """Connect to an SSH host: /ssh <alias>"""
        if not args:
            self.notify("Usage: /ssh <alias>", severity="error")
            return

        alias = args[0]
        host_config = self.app.storage.get_ssh_host(alias)

        if not host_config:
            self.notify(f"Unknown host alias: {alias}", severity="error")
            return

        from screens.ssh import SSHScreen
        from utils.ssh_client import SSHSession

        # Resolve jump host if configured
        tunnel_session = None
        jump_alias = host_config.get("jump_host")

        if jump_alias:
            jump_config = self.app.storage.get_ssh_host(jump_alias)
            if not jump_config:
                self.notify(
                    f"Jump host alias not found: {jump_alias}", severity="error"
                )
                return

            tunnel_session = SSHSession(
                hostname=jump_config["hostname"],
                port=jump_config["port"],
                username=jump_config["username"],
                password=jump_config["password"],
                key_path=jump_config["key_path"],
            )

        session = SSHSession(
            hostname=host_config["hostname"],
            port=host_config["port"],
            username=host_config["username"],
            password=host_config["password"],
            key_path=host_config["key_path"],
            tunnel=tunnel_session,
        )

        self.app.push_screen(SSHScreen(session, alias))

    async def cmd_ssh_add(self, args: list[str]):
        """Add SSH host: /ssh-add [alias host user port key] or interactive form."""
        if not args:
            # Show interactive form
            from screens.ssh_add import SSHAddScreen

            self.app.push_screen(SSHAddScreen())
            return

        if len(args) < 3:
            self.notify(
                "Usage: /ssh-add <alias> <host> <user> [port] [key_path]",
                severity="error",
            )
            return

        alias = args[0]
        hostname = args[1]
        username = args[2]
        port = int(args[3]) if len(args) > 3 else 22
        key_path = args[4] if len(args) > 4 else None

        self.app.storage.add_ssh_host(alias, hostname, port, username, key_path)
        self.notify(f"Added SSH host: {alias}")

    async def cmd_ssh_list(self, args: list[str]):
        """List saved SSH hosts."""
        hosts = self.app.storage.list_ssh_hosts()
        if not hosts:
            self.notify("No SSH hosts saved.")
            return

        lines = ["SSH Hosts:", "----------"]
        for h in hosts:
            lines.append(f"{h['alias']}: {h['username']}@{h['hostname']}:{h['port']}")

        await self.show_output("/ssh-list", "\n".join(lines))

    async def cmd_ssh_del(self, args: list[str]):
        """Delete SSH host: /ssh-del <alias>"""
        if not args:
            self.notify("Usage: /ssh-del <alias>", severity="error")
            return

        alias = args[0]
        self.app.storage.delete_ssh_host(alias)
        self.notify(f"Deleted SSH host: {alias}")

    async def cmd_nullify(self, args: list[str]):
        """Open a new terminal tab/window with the Null Terminal profile.

        Usage:
            /nullify        - Open new tab with Null Terminal profile
            /nullify window - Open new window with Null Terminal profile
        """
        from utils.terminal import (
            TerminalType,
            activate_null_profile,
            get_terminal_info,
        )

        info = get_terminal_info()

        if info.type != TerminalType.WINDOWS_TERMINAL:
            self.notify(
                f"{info.name} doesn't require profile activation",
                severity="warning",
            )
            return

        new_window = "window" in args or "-w" in args

        if activate_null_profile(new_window=new_window):
            action = "window" if new_window else "tab"
            self.notify(f"Opening new {action} with Null Terminal profile...")
        else:
            self.notify("Failed to activate Null Terminal profile", severity="error")

    async def cmd_reload(self, args: list[str]):
        try:
            from themes import get_all_themes

            for theme in get_all_themes().values():
                self.app.register_theme(theme)

            self.app.mcp_manager.reload_config()
            await self.app.mcp_manager.initialize()

            self.notify("Configuration reloaded")
        except Exception as e:
            self.notify(f"Reload failed: {e}", severity="error")

    async def cmd_git(self, args: list[str]):
        """Git operations: /git [status|diff|commit|undo|log]"""
        from managers.git import GitManager

        git = GitManager()

        if not await git.is_repo():
            self.notify("Not a git repository", severity="warning")
            return

        if not args or args[0] == "status":
            await self._git_status(git)
        elif args[0] == "diff":
            file = args[1] if len(args) > 1 else None
            await self._git_diff(git, file)
        elif args[0] == "commit":
            message = " ".join(args[1:]) if len(args) > 1 else None
            await self._git_commit(git, message)
        elif args[0] == "undo":
            await self._git_undo(git)
        elif args[0] == "log":
            limit = int(args[1]) if len(args) > 1 and args[1].isdigit() else 10
            await self._git_log(git, limit)
        elif args[0] == "stash":
            if len(args) > 1 and args[1] == "pop":
                await self._git_stash_pop(git)
            else:
                message = " ".join(args[1:]) if len(args) > 1 else None
                await self._git_stash(git, message)
        else:
            self.notify(f"Unknown git subcommand: {args[0]}", severity="error")

    async def _git_status(self, git: "GitManager"):
        branch = await git.get_branch()
        staged = await git.get_staged_files()
        unstaged = await git.get_unstaged_files()
        untracked = await git.get_untracked_files()

        lines = [f"  Branch: {branch}"]

        if staged:
            lines.append(f"\n  Staged ({len(staged)}):")
            for f in staged[:10]:
                lines.append(f"    + {f}")
            if len(staged) > 10:
                lines.append(f"    ... and {len(staged) - 10} more")

        if unstaged:
            lines.append(f"\n  Modified ({len(unstaged)}):")
            for f in unstaged[:10]:
                lines.append(f"    M {f}")
            if len(unstaged) > 10:
                lines.append(f"    ... and {len(unstaged) - 10} more")

        if untracked:
            lines.append(f"\n  Untracked ({len(untracked)}):")
            for f in untracked[:5]:
                lines.append(f"    ? {f}")
            if len(untracked) > 5:
                lines.append(f"    ... and {len(untracked) - 5} more")

        if not staged and not unstaged and not untracked:
            lines.append("\n  Working tree clean")

        await self.show_output("/git status", "\n".join(lines))

    async def _git_diff(self, git: "GitManager", file: str | None):
        staged = await git.get_staged_files()
        diff_content = await git.get_diff(staged=bool(staged), file=file)

        if not diff_content:
            self.notify("No changes to show")
            return

        title = f"/git diff {file}" if file else "/git diff"
        await self.show_output(title, f"```diff\n{diff_content[:5000]}\n```")

    async def _git_commit(self, git: "GitManager", message: str | None):
        staged = await git.get_staged_files()

        if not staged:
            unstaged = await git.get_unstaged_files()
            if unstaged:
                self.notify(
                    "No staged changes. Use 'git add' first or stage all with /git commit --all"
                )
                return
            self.notify("Nothing to commit")
            return

        if not message and self.app.ai_provider:
            self.notify("Generating commit message...")
            message = await git.generate_commit_message(self.app.ai_provider)
        elif not message:
            self.notify(
                "No AI provider for auto-message. Provide a message: /git commit <message>"
            )
            return

        result = await git.commit(message)

        if result.success:
            self.notify(f"Committed: {result.sha[:7]} - {result.message}")
        else:
            self.notify(f"Commit failed: {result.error}", severity="error")

    async def _git_undo(self, git: "GitManager"):
        commits = await git.get_recent_commits(1)
        if not commits:
            self.notify("No commits to undo")
            return

        last = commits[0]
        success = await git.undo_last_commit(keep_changes=True)

        if success:
            self.notify(f"Undid commit: {last.sha[:7]} - {last.message}")
        else:
            self.notify("Failed to undo commit", severity="error")

    async def _git_log(self, git: "GitManager", limit: int):
        commits = await git.get_recent_commits(limit)

        if not commits:
            self.notify("No commits found")
            return

        lines = []
        for c in commits:
            ai_badge = " [AI]" if c.is_ai_generated else ""
            lines.append(f"  {c.sha[:7]} {c.message[:50]}{ai_badge}")
            lines.append(f"           {c.author} - {c.date.strftime('%Y-%m-%d %H:%M')}")

        await self.show_output("/git log", "\n".join(lines))

    async def _git_stash(self, git: "GitManager", message: str | None):
        success = await git.stash(message)
        if success:
            self.notify("Changes stashed")
        else:
            self.notify("Failed to stash changes", severity="error")

    async def _git_stash_pop(self, git: "GitManager"):
        success = await git.stash_pop()
        if success:
            self.notify("Stash applied")
        else:
            self.notify("Failed to pop stash", severity="error")

    async def cmd_diff(self, args: list[str]):
        """/diff [file] - Show git diff"""
        from managers.git import GitManager

        git = GitManager()
        if not await git.is_repo():
            self.notify("Not a git repository", severity="warning")
            return

        file = args[0] if args else None
        await self._git_diff(git, file)

    async def cmd_undo(self, args: list[str]):
        from managers.git import GitManager

        git = GitManager()
        if not await git.is_repo():
            self.notify("Not a git repository", severity="warning")
            return

        await self._git_undo(git)

    async def cmd_fix(self, args: list[str]):
        from managers.error_detector import ErrorDetector

        if not hasattr(self.app, "error_detector"):
            self.app.error_detector = ErrorDetector()

        detector = self.app.error_detector

        if args:
            error_output = " ".join(args)
            errors = detector.detect(error_output)
            if errors:
                await self._show_fix_for_error(errors[0])
            else:
                self.notify("Could not parse error from input")
            return

        last_error = detector.get_last_error()
        if not last_error:
            self.notify(
                "No errors detected. Run a command first or provide error text."
            )
            return

        await self._show_fix_for_error(last_error)

    async def _show_fix_for_error(self, error):
        from managers.error_detector import AutoCorrectionLoop

        if not self.app.ai_provider:
            self.notify("AI provider not configured", severity="error")
            return

        self.notify(f"Generating fix for: {error.message[:50]}...")

        file_content = ""
        if error.file:
            try:
                from tools.builtin import read_file

                file_content = await read_file(error.file)
            except Exception:
                pass

        loop = AutoCorrectionLoop()
        fix = await loop.generate_fix(error, self.app.ai_provider, file_content)

        lines = [
            f"Error: {error.error_type.value}",
            f"Message: {error.message}",
            f"Location: {error.location}",
            "=" * 50,
            "",
            "Suggested Fix:",
            fix,
        ]

        await self.show_output("/fix", "\n".join(lines))

    async def cmd_watch(self, args: list[str]):
        from managers.error_detector import ErrorDetector

        if not hasattr(self.app, "error_detector"):
            self.app.error_detector = ErrorDetector()

        if not hasattr(self.app, "_watch_mode"):
            self.app._watch_mode = False

        if args and args[0].lower() in ("stop", "off"):
            self.app._watch_mode = False
            self.notify("Watch mode disabled")
            return

        self.app._watch_mode = not self.app._watch_mode
        status = "enabled" if self.app._watch_mode else "disabled"
        self.notify(f"Watch mode {status}")

        if self.app._watch_mode:
            await self.show_output(
                "/watch",
                "Watch mode enabled.\n\n"
                "Errors in command output will be automatically detected.\n"
                "Use /fix to generate corrections for the last error.\n"
                "Use /watch stop to disable.",
            )

    async def cmd_review(self, args: list[str]):
        review = self.app.review_manager

        if not args:
            await self._review_status()
            return

        subcommand = args[0].lower()

        if subcommand == "status":
            await self._review_status()
        elif subcommand == "accept":
            if len(args) > 1:
                if args[1].lower() == "all":
                    count = review.accept_all()
                    self.notify(f"Accepted {count} hunks")
                else:
                    file = args[1]
                    hunk_id = args[2] if len(args) > 2 else None
                    if hunk_id:
                        if review.accept_hunk(file, hunk_id):
                            self.notify(f"Accepted hunk {hunk_id}")
                        else:
                            self.notify("Hunk not found", severity="error")
                    else:
                        if review.accept_file(file):
                            self.notify(f"Accepted all hunks in {file}")
                        else:
                            self.notify("File not found", severity="error")
            else:
                count = review.accept_all()
                self.notify(f"Accepted {count} hunks")
        elif subcommand == "reject":
            if len(args) > 1:
                if args[1].lower() == "all":
                    count = review.reject_all()
                    self.notify(f"Rejected {count} hunks")
                else:
                    file = args[1]
                    hunk_id = args[2] if len(args) > 2 else None
                    if hunk_id:
                        if review.reject_hunk(file, hunk_id):
                            self.notify(f"Rejected hunk {hunk_id}")
                        else:
                            self.notify("Hunk not found", severity="error")
                    else:
                        if review.reject_file(file):
                            self.notify(f"Rejected all hunks in {file}")
                        else:
                            self.notify("File not found", severity="error")
            else:
                count = review.reject_all()
                self.notify(f"Rejected {count} hunks")
        elif subcommand == "apply":
            applied = await review.apply_accepted()
            if applied:
                self.notify(f"Applied changes to {len(applied)} file(s)")
            else:
                self.notify("No accepted changes to apply")
        elif subcommand == "clear":
            review.clear()
            self.notify("Cleared all pending changes")
        elif subcommand == "show":
            if len(args) > 1:
                await self._review_show_file(args[1])
            else:
                await self._review_status()
        else:
            self.notify(
                "Usage: /review [status|accept|reject|apply|clear|show]",
                severity="warning",
            )

    async def _review_status(self):
        summary = self.app.review_manager.get_summary()
        await self.show_output("/review", summary)

    async def _review_show_file(self, file: str):
        change = self.app.review_manager.get_change(file)
        if not change:
            self.notify(f"No pending changes for {file}")
            return

        from managers.review import HunkStatus

        status_icons = {
            HunkStatus.PENDING: "○",
            HunkStatus.ACCEPTED: "✓",
            HunkStatus.REJECTED: "✗",
        }

        lines = [
            f"File: {change.file}",
            f"Rationale: {change.rationale}" if change.rationale else "",
            f"Changes: +{change.total_additions}/-{change.total_deletions}",
            "=" * 50,
            "",
        ]

        for hunk in change.hunks:
            icon = status_icons.get(hunk.status, "?")
            lines.append(
                f"{icon} Hunk {hunk.id} (lines {hunk.start_line}-{hunk.end_line}):"
            )

            for line in hunk.context_before[-2:]:
                lines.append(f"   {line}")

            for line in hunk.original_lines:
                lines.append(f" - {line}")

            for line in hunk.proposed_lines:
                lines.append(f" + {line}")

            for line in hunk.context_after[:2]:
                lines.append(f"   {line}")

            lines.append("")

            await self.show_output(f"/review show {file}", "\n".join(lines))

    async def cmd_cmd(self, args: list[str]):
        if not args:
            self.notify(
                "Usage: /cmd <natural language description>", severity="warning"
            )
            return

        if not self.app.ai_provider:
            self.notify("AI provider not configured", severity="error")
            return

        from managers.nl2shell import NL2Shell

        nl2shell = NL2Shell()
        description = " ".join(args)

        self.notify(f"Translating: {description[:40]}...")

        suggestion = await nl2shell.translate(description, self.app.ai_provider)

        lines = [
            f"Command: {suggestion.command}",
            "",
            f"Explanation: {suggestion.explanation}",
            f"Confidence: {suggestion.confidence * 100:.0f}%",
        ]

        if suggestion.alternatives:
            lines.append(f"\nAlternatives: {', '.join(suggestion.alternatives)}")

        if suggestion.warnings:
            lines.append(f"\nWarnings: {', '.join(suggestion.warnings)}")

        if suggestion.requires_sudo:
            lines.append("\nNote: This command may require sudo")

        lines.extend(
            [
                "",
                "To run this command, copy it to your terminal or type it directly.",
            ]
        )

        await self.show_output(f"/cmd {description[:20]}...", "\n".join(lines))

    async def cmd_explain(self, args: list[str]):
        if not args:
            self.notify("Usage: /explain <command>", severity="warning")
            return

        if not self.app.ai_provider:
            self.notify("AI provider not configured", severity="error")
            return

        from managers.nl2shell import NL2Shell

        nl2shell = NL2Shell()
        command = " ".join(args)

        self.notify(f"Explaining: {command[:40]}...")

        explanation = await nl2shell.explain(command, self.app.ai_provider)

        await self.show_output(f"/explain {command}", explanation)

    async def cmd_workflow(self, args: list[str]):
        """Workflow template management: /workflow [list|run|save|import|export]"""
        from managers.workflow import WorkflowManager

        manager = WorkflowManager()
        manager.load_workflows()

        if not args:
            await self._workflow_list(manager)
            return

        subcommand = args[0].lower()

        if subcommand == "list":
            await self._workflow_list(manager)
        elif subcommand == "run":
            if len(args) < 2:
                self.notify("Usage: /workflow run <name>", severity="error")
                return
            workflow_name = " ".join(args[1:])
            await self._workflow_run(manager, workflow_name)
        elif subcommand == "save":
            workflow_name = " ".join(args[1:]) if len(args) > 1 else "Saved Workflow"
            await self._workflow_save(manager, workflow_name)
        elif subcommand == "import":
            if len(args) < 2:
                self.notify("Usage: /workflow import <file>", severity="error")
                return
            file_path = args[1]
            await self._workflow_import(manager, file_path)
        elif subcommand == "export":
            if len(args) < 2:
                self.notify("Usage: /workflow export <name>", severity="error")
                return
            workflow_name = " ".join(args[1:])
            await self._workflow_export(manager, workflow_name)
        else:
            self.notify(
                "Usage: /workflow [list|run|save|import|export]", severity="error"
            )

    async def _workflow_list(self, manager):
        """List all available workflows."""
        manager.load_workflows()
        workflows = manager.list_workflows()

        if not workflows:
            self.notify("No workflows found")
            return

        lines = ["Available Workflows:", "=" * 50]
        for workflow in workflows:
            source_badge = (
                f" [{workflow.source}]" if workflow.source == "builtin" else ""
            )
            tags_str = f" #{', #'.join(workflow.tags)}" if workflow.tags else ""
            lines.append(f"\n• {workflow.name}{source_badge}")
            lines.append(f"  {workflow.description}")
            if tags_str:
                lines.append(f"  Tags:{tags_str}")
            if workflow.variables:
                var_list = ", ".join(workflow.variables.keys())
                lines.append(f"  Variables: {var_list}")

        await self.show_output("/workflow list", "\n".join(lines))

    async def _workflow_run(self, manager, workflow_name: str):
        """Run a workflow with variable substitution."""
        workflow = manager.get_workflow_by_name(workflow_name)

        if not workflow:
            self.notify(f"Workflow not found: {workflow_name}", severity="error")
            return

        if not workflow.variables:
            await self._execute_workflow(workflow)
            return

        lines = [f"Workflow: {workflow.name}", "=" * 50, ""]
        lines.append("Please provide values for the following variables:")
        lines.append("")

        for var_name, var_description in workflow.variables.items():
            lines.append(f"  {var_name}: {var_description}")

        lines.append("")
        lines.append("(Use /workflow run <name> and provide values when prompted)")

        await self.show_output(f"/workflow run {workflow_name}", "\n".join(lines))
        self.notify(
            f"Workflow '{workflow_name}' ready. Provide variable values to execute."
        )

    async def _execute_workflow(self, workflow):
        """Execute a workflow (placeholder for future integration)."""
        lines = [f"Executing: {workflow.name}", "=" * 50, ""]

        for i, step in enumerate(workflow.steps, 1):
            lines.append(f"Step {i}: {step.type.value.upper()}")
            lines.append(f"  {step.content[:100]}...")
            if step.tool_name:
                lines.append(f"  Tool: {step.tool_name}")

        lines.append("")
        lines.append("(Workflow execution integration coming soon)")

        await self.show_output(f"Executing: {workflow.name}", "\n".join(lines))

    async def _workflow_save(self, manager, workflow_name: str):
        """Save current session as a workflow."""
        from datetime import datetime

        from managers.workflow import Workflow, WorkflowStep, WorkflowStepType

        context_str = ""
        try:
            from context import ContextManager

            context_str = ContextManager.get_context(self.app.blocks)
        except Exception:
            pass

        now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
        workflow = Workflow(
            id="",
            name=workflow_name,
            description=f"Saved from session at {now_str}",
            tags=["saved"],
            steps=[
                WorkflowStep(
                    type=WorkflowStepType.PROMPT,
                    content=context_str[:500] if context_str else "Session context",
                )
            ],
        )

        try:
            import uuid

            workflow.id = str(uuid.uuid4())[:8]
            manager.save_workflow(workflow)
            self.notify(f"Workflow saved: {workflow_name}")
        except Exception as e:
            self.notify(f"Failed to save workflow: {e}", severity="error")

    async def _workflow_import(self, manager, file_path: str):
        """Import a workflow from a YAML file."""
        from pathlib import Path

        try:
            path = Path(file_path).expanduser()
            if not path.exists():
                self.notify(f"File not found: {file_path}", severity="error")
                return

            with open(path) as f:
                content = f.read()

            workflow = manager.parse_yaml(content)
            manager.save_workflow(workflow)
            self.notify(f"Workflow imported: {workflow.name}")
        except Exception as e:
            self.notify(f"Failed to import workflow: {e}", severity="error")

    async def _workflow_export(self, manager, workflow_name: str):
        """Export a workflow to YAML."""
        workflow = manager.get_workflow_by_name(workflow_name)

        if not workflow:
            self.notify(f"Workflow not found: {workflow_name}", severity="error")
            return

        yaml_content = manager.to_yaml(workflow)
        await self.show_output(
            f"/workflow export {workflow_name}", f"```yaml\n{yaml_content}\n```"
        )

    async def cmd_map(self, args: list[str]):
        """Show project architecture: /map [path] [--format mermaid] [--depth N] [component]"""
        from pathlib import Path

        from managers.architecture import ArchitectureMapper

        mapper = ArchitectureMapper()

        path = None
        format_type = "ascii"
        max_depth = 3
        component_name = None

        i = 0
        while i < len(args):
            arg = args[i]
            if arg == "--format" and i + 1 < len(args):
                format_type = args[i + 1]
                i += 2
            elif arg == "--depth" and i + 1 < len(args):
                try:
                    max_depth = int(args[i + 1])
                    i += 2
                except ValueError:
                    i += 1
            elif arg.startswith("--"):
                i += 1
            elif not path and (Path(arg).exists() or arg in [".", ".."]):
                path = Path(arg)
                i += 1
            else:
                component_name = arg
                i += 1

        try:
            arch_map = await mapper.scan(path, max_depth=max_depth)

            if component_name:
                output = mapper.get_component_detail(arch_map, component_name)
                await self.show_output(f"/map {component_name}", output)
            elif format_type == "mermaid":
                output = mapper.to_mermaid(arch_map)
                await self.show_output(
                    "/map --format mermaid", f"```mermaid\n{output}\n```"
                )
            else:
                output = mapper.to_ascii(arch_map)
                await self.show_output("/map", output)

        except Exception as e:
            self.notify(f"Architecture mapping failed: {e}", severity="error")

    async def cmd_issue(self, args: list[str]):
        """GitHub issue operations: /issue [<number>|list|create]"""
        from managers.github import GitHubContextManager

        github = GitHubContextManager()

        if not args:
            self.notify("Usage: /issue <number|list|create>", severity="error")
            return

        if args[0] == "list":
            await self._issue_list(github)
        elif args[0] == "create":
            await self._issue_create(github)
        elif args[0].isdigit():
            await self._issue_view(github, int(args[0]))
        else:
            self.notify(f"Unknown issue subcommand: {args[0]}", severity="error")

    async def _issue_view(self, github: "GitHubContextManager", number: int):
        """View a specific issue."""
        issue = await github.get_issue(number)
        if not issue:
            self.notify(f"Failed to fetch issue #{number}", severity="error")
            return

        context = github.format_issue_context(issue)
        await self.show_output(f"/issue {number}", context)

    async def _issue_list(self, github: "GitHubContextManager"):
        """List open issues."""
        issues = await github.list_issues(state="open", limit=20)
        if not issues:
            self.notify("No open issues found", severity="warning")
            return

        lines = ["# Open Issues", ""]
        for issue in issues:
            labels_str = f" [{', '.join(issue.labels)}]" if issue.labels else ""
            lines.append(f"#{issue.number}: {issue.title}{labels_str}")

        await self.show_output("/issue list", "\n".join(lines))

    async def _issue_create(self, github: "GitHubContextManager"):
        """Create a new issue (interactive)."""
        from textual.widgets import Input
        from textual.containers import Container
        from textual.widgets import Label, Button
        from textual.app import ComposeResult

        class IssueCreateScreen:
            def __init__(self, github_manager):
                self.github = github_manager
                self.title = ""
                self.body = ""

        self.notify(
            "Issue creation not yet implemented in TUI mode", severity="warning"
        )

    async def cmd_pr(self, args: list[str]):
        """GitHub PR operations: /pr [<number>|list|create|diff]"""
        from managers.github import GitHubContextManager

        github = GitHubContextManager()

        if not args:
            self.notify(
                "Usage: /pr <number|list|create|diff <number>>", severity="error"
            )
            return

        if args[0] == "list":
            await self._pr_list(github)
        elif args[0] == "create":
            await self._pr_create(github)
        elif args[0] == "diff" and len(args) > 1:
            await self._pr_diff(github, int(args[1]))
        elif args[0].isdigit():
            await self._pr_view(github, int(args[0]))
        else:
            self.notify(f"Unknown pr subcommand: {args[0]}", severity="error")

    async def _pr_view(self, github: "GitHubContextManager", number: int):
        """View a specific PR."""
        pr = await github.get_pr(number)
        if not pr:
            self.notify(f"Failed to fetch PR #{number}", severity="error")
            return

        context = github.format_pr_context(pr)
        await self.show_output(f"/pr {number}", context)

    async def _pr_list(self, github: "GitHubContextManager"):
        """List open PRs."""
        prs = await github.list_prs(state="open", limit=20)
        if not prs:
            self.notify("No open PRs found", severity="warning")
            return

        lines = ["# Open Pull Requests", ""]
        for pr in prs:
            lines.append(f"#{pr.number}: {pr.title}")
            lines.append(f"  {pr.head_branch} → {pr.base_branch}")

        await self.show_output("/pr list", "\n".join(lines))

    async def _pr_diff(self, github: "GitHubContextManager", number: int):
        """Show PR diff."""
        diff = await github.get_pr_diff(number)
        if not diff:
            self.notify(f"Failed to fetch diff for PR #{number}", severity="error")
            return

        await self.show_output(f"/pr diff {number}", f"```diff\n{diff}\n```")

    async def _pr_create(self, github: "GitHubContextManager"):
        """Create a new PR (interactive)."""
        self.notify("PR creation not yet implemented in TUI mode", severity="warning")
