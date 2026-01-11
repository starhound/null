# Tools & Agent Mode

Null Terminal supports AI tool use for interactive task execution.

## Built-in Tools

### run_command
Execute shell commands.

```
Tool: run_command
Arguments: {"command": "ls -la"}
Approval: Required
```

- 60-second timeout
- Returns stdout/stderr
- Captures exit code

### read_file
Read file contents.

```
Tool: read_file
Arguments: {"path": "/etc/hosts", "max_lines": 100}
Approval: Not required
```

- Auto-truncates files over 50KB
- Optional `max_lines` parameter

### write_file
Write or create files.

```
Tool: write_file
Arguments: {"path": "script.py", "content": "print('hello')"}
Approval: Required
```

- Creates parent directories automatically
- Overwrites existing files

### list_directory
List directory contents.

```
Tool: list_directory
Arguments: {"path": ".", "show_hidden": true}
Approval: Not required
```

- Optional `show_hidden` parameter
- Returns file names and types

## MCP Tools

Additional tools from MCP servers. See [MCP Servers](mcp.md).

Common MCP tools:
- **brave_search**: Web search
- **read_file** (MCP): Enhanced file reading
- **query** (database): SQL queries
- **fetch**: HTTP requests

## Tool Execution

### Streaming Results
Tool output is streamed in real-time for long-running commands. You don't have to wait for completion to see what's happening.

```
┌─────────────────────────────────────────────────────────┐
│ 🔧 run_command: npm install                    [▼] [■]  │
├─────────────────────────────────────────────────────────┤
│ ⏳ Running... (12s)                                     │
│ ─────────────────────────────────────────────────────── │
│ npm WARN deprecated lodash@4.17.20                      │
│ npm WARN deprecated request@2.88.2                      │
│ added 1247 packages in 10s                              │
│ █████████████████████░░░░░ 85%                          │
└─────────────────────────────────────────────────────────┘
```

- **Stop Button [■]**: Cancel execution immediately (sends SIGTERM).
- **Auto-scroll**: The view follows new output automatically.

### Tool Approval

To ensure safety, sensitive tools require approval before execution.

#### Approval Required
- `run_command` - Shell execution
- `write_file` - File modification
- Most MCP tools that modify state

#### No Approval Required
- `read_file` - File reading
- `list_directory` - Directory listing
- Safe/Read-only MCP tools

#### Approval Dialog
When a tool requires approval:
1. A dialog appears showing tool name and arguments.
2. Review the operation carefully.
3. **Approve** to execute.
4. **Deny** to cancel the tool call.

#### Configuration
You can customize approval settings in `config.json`:

```json
{
  "tools": {
    "require_approval": ["run_command", "write_file", "mcp_*"],
    "auto_approve_safe": true
  }
}
```

## Chat Mode (Default)

In regular chat mode:
- AI can suggest tool calls
- Each tool requires approval
- Single tool execution per response
- Results shown in collapsible accordion

### Example
```
You: What files are in the current directory?

AI: Let me check the directory contents.
    [Tool: list_directory - Click to expand]

    The current directory contains:
    - main.py
    - README.md
    - requirements.txt
```

## Agent Mode

Enable autonomous multi-step task execution.

### Enabling Agent Mode
```bash
/agent
```

Or via status bar toggle.

### How It Works
1. You provide a task
2. AI plans the approach
3. AI executes tools automatically
4. Results feed into next iteration
5. Continues until task complete (max 10 iterations)

### Iteration Display
Each iteration shows:
- Thinking process (if enabled)
- Tool calls with arguments
- Tool results
- Response fragment

### Example
```
You: Create a Python script that fetches weather data and save it

Agent Iteration 1/10:
  Thinking: I'll create a weather fetching script...
  [Tool: write_file] weather.py
  Result: File created

Agent Iteration 2/10:
  Thinking: Now I'll test if it runs...
  [Tool: run_command] python weather.py
  Result: Success - fetched weather for NYC

Final Response:
  I've created weather.py with the following features...
```

### Safety Features
- Maximum 10 iterations per query
- Tool approval still available (configurable)
- Stop button to cancel at any point
- Context preserved between iterations

### Best Practices

**Good for Agent Mode:**
- Multi-step tasks
- File manipulation workflows
- Research and compilation
- Automated testing

**Better for Chat Mode:**
- Simple questions
- Single operations
- Learning/exploration
- Sensitive operations

## Tool Results

### Viewing Results
- Click tool accordion to expand
- Shows arguments and output
- Duration displayed
- Status indicator (success/error)

### In Blocks
Tool calls are displayed in:
- **Chat mode**: Collapsible accordion
- **Agent mode**: Per-iteration display

## Code Execution

AI responses may include code blocks. You can:

1. **Run**: Execute the code directly
2. **Save**: Save to a file
3. **Copy**: Copy to clipboard

Supported languages:
- Python
- Bash/Shell
- JavaScript/Node
- And more

## Tips

### Effective Tool Use
- Be specific about what you want
- Provide file paths when known
- Mention constraints upfront

### Agent Mode Tips
- Start with clear objectives
- Break complex tasks into steps
- Review intermediate results
- Use `/agent` to toggle off if needed

### Troubleshooting
- Check tool output in accordion
- Review error messages
- Verify file permissions
- Ensure commands are available in PATH
