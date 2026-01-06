# HANDLERS KNOWLEDGE BASE

## OVERVIEW
The orchestration layer managing user input routing and the high-complexity AI/CLI execution workflows.

## STRUCTURE
*   `execution.py`: **Core Logic Hub.** Manages LLM streaming, recursive tool-calling loops, and async process execution.
*   `input.py`: **Traffic Controller.** Parses user input and routes to commands, AI, or shell based on application state.

## WHERE TO LOOK
| Task | File | Key Symbol/Method |
|------|------|-------------------|
| **AI Tool Execution** | `execution.py` | `_execute_with_tools` / `_process_tool_calls` |
| **Agentic Iteration** | `execution.py` | `_execute_agent_mode` (Recursive logic) |
| **Shell/PTY Execution**| `execution.py` | `execute_cli` (PTY spawning) |
| **Input Routing** | `input.py` | `handle_submission` (Primary entry point) |
| **Mode Switching** | `input.py` | `_handle_ai_input` vs `_handle_cli_input` |

## CONVENTIONS
*   **Async-First**: All handlers are `async`. Use `asyncio.create_task` for background operations that shouldn't block the UI.
*   **Stateful Blocks**: Always pass `BlockState` and the target `widget` to execution methods to maintain UI synchronization.
*   **Stream Management**: AI responses must stream tokens immediately to the widget via `update_content` to prevent UI lag.
*   **Error Boundaries**: Wrap execution loops in robust try-except blocks to prevent a single failed tool from crashing the app.

## ANTI-PATTERNS
*   **Sync Blocking**: NEVER use `time.sleep()` or `subprocess` (use `asyncio` equivalents).
*   **Infinite Loops**: Ensure tool-calling iterations in `execution.py` have a hard depth limit (default 10).
*   **Heavy Init**: Avoid heavy imports at the top level; use local imports in methods if the module is only used during execution.
*   **Direct DOM Access**: Handlers should interact with `BaseBlockWidget` methods rather than reaching into sub-widgets directly.
