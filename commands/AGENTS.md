# COMMANDS KNOWLEDGE BASE

**Context:** Slash command system, input routing, functional modules.

## OVERVIEW
The `commands/` directory manages the registration, routing, and execution of slash commands (e.g., `/help`, `/settings`).

## STRUCTURE
```
commands/
├── base.py            # CommandMixin with utilities (show_output, notify)
├── handler.py         # SlashCommandHandler (Registry & Routing)
├── ai.py              # AI-related commands (/provider, /model, /agent)
├── core.py            # App core commands (/help, /status, /clear, /ssh)
├── config.py          # Configuration commands (/settings, /theme)
├── mcp.py             # Model Context Protocol management (/mcp, /tools)
└── session.py         # Session persistence and export (/session, /export)
```

## WHERE TO LOOK
| Task | Location | Notes |
|------|----------|-------|
| **Add New Command** | Relevant module + `handler.py` | Create `cmd_` method, then add to `_command_registry` |
| **New Subcommand** | Relevant module | Parse `args` inside the `cmd_` method |
| **Command Utilities** | `base.py` | Methods like `show_output` and `notify` |
| **Routing Logic** | `handler.py` | `handle()` method parses input and calls registry |

## CONVENTIONS
*   **Method Naming**: All command handlers must be prefixed with `cmd_` (e.g., `cmd_help`).
*   **Registration**: Commands must be manually registered in `SlashCommandHandler._command_registry` with a `CommandInfo` object.
*   **Async Handlers**: Every `cmd_` method must be `async` and accept `args: list[str]`.
*   **Circular Imports**: Use `TYPE_CHECKING` for `NullApp` type hints to avoid circular dependencies with `app.py`.
*   **Output Consistency**: Use `self.show_output()` for block-based results and `self.notify()` for transient messages.

## ANTI-PATTERNS
*   **No Direct Prints**: Never use `print()`; it breaks the TUI. Use `self.notify()` or `self.show_output()`.
*   **Blocking Calls**: Avoid synchronous I/O or long-running computations in command handlers; use the `executor`.
*   **Scattered Registry**: Do not attempt to auto-register commands via decorators; maintain the explicit registry in `handler.py` for clarity.
*   **Direct UI Mutation**: Prefer calling methods on `self.app` or sending messages over directly manipulating deep widget trees.
