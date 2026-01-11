# Tools & Autonomous Agents

Null Terminal empowers AI models with the ability to interact directly with your system through **Tools**. Whether you're in a simple chat or running a complex autonomous agent, tools bridge the gap between conversation and execution.

---

## 🛠️ Built-in Tools

Null Terminal comes pre-equipped with a core set of tools for system interaction.

| Tool | Purpose | Approval | Description |
|:---|:---|:---:|:---|
| `run_command` | Shell Execution | **Required** | Executes any shell command via PTY. Returns stdout/stderr. |
| `read_file` | Read Content | Auto | Reads file contents with automatic truncation for large files. |
| `write_file` | Write Content | **Required** | Creates or overwrites files. Automatically builds parent directories. |
| `list_directory`| File Discovery | Auto | Lists directory contents, including file types and hidden files. |

!!! warning "Security Risk"
    Tools like `run_command` and `write_file` can modify or delete data. Always review the tool arguments before granting approval.

---

## 🔌 MCP Integration

Beyond built-in tools, Null Terminal supports the **Model Context Protocol (MCP)**, allowing you to plug in hundreds of external tools.

Common MCP capabilities include:
- **Web Research**: via Brave Search or Google Search.
- **Database Access**: Query SQL or NoSQL databases.
- **API Interaction**: Fetch data from GitHub, Slack, or Linear.
- **Enhanced Filesystem**: Advanced search and grep capabilities.

For details on setting up and managing these, see the [MCP Servers Guide](mcp.md).

---

## 🔄 Execution Workflow

### 1. Request & Approval
When the AI decides to use a tool, it generates a "Tool Call."

- **Safe Tools**: (e.g., `read_file`) execute automatically to maintain flow.
- **Sensitive Tools**: (e.g., `run_command`) trigger an **Approval Dialog**. You must manually click **Approve** or **Deny**.

### 2. Real-time Streaming
For long-running processes (like `npm install` or complex builds), output is streamed directly into the block.

- **Stop Button [■]**: Sends a `SIGTERM` to the process immediately.
- **Auto-scroll**: The UI tracks the latest output automatically.
- **Duration**: Real-time timer shows exactly how long the tool has been running.

---

## ⚡ Interaction Modes

Null Terminal operates in two distinct modes for tool execution. Use the `/agent` command or the status bar toggle to switch.

=== "Chat Mode (Default)"

    *The standard experience for targeted assistance.*

    - **One-at-a-time**: AI suggests a tool, you approve, it executes, and the AI responds to the result.
    - **Controlled**: Best for sensitive operations where you want to oversee every step.
    - **Display**: Tool calls appear as collapsible accordions within the chat flow.

    **Example:**
    > "What files are in the current directory?"
    >
    > AI: "Let me check the directory contents."
    > [Tool: list_directory]
    >
    > "The current directory contains main.py, README.md..."

=== "Agent Mode (Autonomous)"

    *Multi-step task execution with minimal intervention.*

    - **Chained Execution**: The AI plans a sequence of actions and executes them in an "Iteration Loop."
    - **Self-Correcting**: If a tool fails (e.g., a command returns an error), the AI analyzes the output and tries a different approach.
    - **Display**: Shows a specialized "Iteration Block" containing:
        1. **Thinking**: The AI's internal reasoning for this step.
        2. **Tool Call**: The specific command being run.
        3. **Result**: The immediate output of the tool.

    !!! tip "Iteration Limit"
        Agent Mode is capped at **10 iterations** per task by default to prevent infinite loops and runaway costs.

---

## ⚙️ Configuration

You can customize tool behavior in your `config.json` (located in `~/.null/`):

```json
{
  "tools": {
    "require_approval": ["run_command", "write_file", "mcp_*"],
    "auto_approve_safe": true,
    "agent_max_iterations": 10,
    "timeout_seconds": 60
  }
}
```

---

## 💡 Best Practices

### For Chat Mode
- **Be Specific**: "Read the first 50 lines of main.py" is better than "Look at the code."
- **Chain Manually**: Use the output of one tool to inform your next prompt.

### For Agent Mode
- **Clear Objectives**: Start with a well-defined goal. "Fix the bug in tests/test_api.py" is better than "Fix the app."
- **Monitor Progress**: Watch the "Thinking" blocks to ensure the agent isn't heading down a rabbit hole.
- **Stop Early**: If you see the agent making a mistake, use the **Stop** button immediately rather than waiting for it to finish.

### Troubleshooting
- **PATH Issues**: Ensure any commands you want the AI to run are in your system `$PATH`.
- **Permissions**: Null Terminal runs with your user permissions. It cannot execute `sudo` without manual password entry in the PTY.
- **Context Overload**: If a tool returns massive output, the AI might lose track of the original goal. Try to limit `read_file` or `run_command` output when possible.
