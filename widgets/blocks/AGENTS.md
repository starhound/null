# AGENTS: WIDGETS/BLOCKS

**Context:** Core UI abstraction for execution output and AI interaction.

## OVERVIEW
Modular widgets representing distinct "blocks" of activity (CLI, AI, Agent) in the terminal void.

## STRUCTURE
*   `base.py`: The `BaseBlockWidget` contract and core bubble-up messages.
*   `command.py`: Standard CLI output with a "TUI mode" switch for interactive apps.
*   `ai_response.py`: Stateless AI Q&A with reasoning (`<think>`) and tool support.
*   `agent_response.py`: Stateful multi-step agent flows using `IterationContainer`.
*   `parts.py`: Reusable sub-components: `BlockHeader`, `BlockFooter`, `BlockMeta`.
*   `actions.py`: The floating `ActionBar` for Copy, Retry, Edit, and Fork.
*   `terminal.py`: Low-level `pyte` terminal emulator for interactive block sessions.

## WHERE TO LOOK
| Component | File | Responsibility |
|-----------|------|----------------|
| **Base Class** | `base.py` | Message definitions and update interface |
| **Shell Output**| `command.py` | Rendering stdout/stderr and TUI transitions |
| **AI Chat** | `ai_response.py`| Parsing tags and rendering markdown/tools |
| **Agent Loop** | `agent_response.py`| Managing nested `Iteration` widgets |
| **Tool UI** | `tool_accordion.py`| Collapsible display of tool calls/results |

## CONVENTIONS
*   **Message Passing**: Use `self.post_message()` for all user actions (Retry, Fork, etc.). Do NOT access `self.app` directly.
*   **State Driven**: Blocks must render based on the provided `BlockState` model.
*   **Late Mounting**: Optional parts (Footers, Tool Accordions) should be mounted/unmounted based on data presence.
*   **Tag Parsing**: AI blocks handle `<think>` and tool-use markers during streaming updates in `update_output`.

## ANTI-PATTERNS
*   **No Direct Styling**: Do NOT set colors/borders in Python. Use `.add_class()` and TCSS.
*   **No Blocking Calls**: Never perform I/O or heavy parsing on the UI thread.
*   **No State Duplication**: Do not store copies of data found in `self.block` (the `BlockState`).
*   **No Manual Focus**: Let `NullApp` handle focus management to avoid navigation traps.
