# Sessions

Null Terminal automatically saves your conversation and can restore it on restart.

## Auto-Save

### How It Works
- Sessions saved every 30 seconds (configurable)
- Saved to SQLite database (`~/.null/null.db`)
- Previous session restored on startup

### Configuration
In `/config` → Terminal:
- **Auto Save Session**: Enable/disable auto-save
- **Auto Save Interval**: Seconds between saves
- **Clear on Exit**: Clear session when exiting

## Manual Session Management

### Save Session
```bash
/session save              # Save with auto-generated name
/session save my-project   # Save with custom name
```

### Load Session
```bash
/session load              # Load most recent
/session load my-project   # Load by name
```

### List Sessions
```bash
/session list
```

Shows:
- Session name
- Date/time saved
- Number of blocks

### New Session
```bash
/session new
```

Clears current session and starts fresh.

## Export

Export your conversation for sharing or backup.

### Markdown Export
```bash
/export         # Default: markdown
/export md      # Explicit markdown
```

Creates a file like `null_export_20240115_143022.md`

### JSON Export
```bash
/export json
```

Creates a file like `null_export_20240115_143022.json`

### Quick Export
Press `Ctrl+S` for quick markdown export.

## Session Contents

Sessions include:
- All blocks (commands, AI responses, tool calls)
- Block metadata (timestamps, tokens, cost)
- Tool execution results
- Context state

Sessions do NOT include:
- API keys or credentials
- Running process state
- Temporary files

## Context Management

### Token Usage
The status bar shows:
- Current context size
- Maximum context window
- Estimated token count

### Reducing Context
```bash
/compact
```

Summarizes the conversation to reduce token usage while preserving key information.

### Clearing Context
```bash
/clear
```

Removes all blocks and resets context. Use `/session save` first if you want to keep the history.

## Conversation Branching

### Fork
On any AI response block, click **Fork** to:
- Create a branch point
- Keep conversation up to that point
- Start a new direction

Useful for:
- Trying alternative approaches
- Exploring different solutions
- Reverting to earlier state

### Edit & Retry
On any AI response block:
- **Edit**: Modify your original query and resubmit
- **Retry**: Regenerate the response with same query

## Best Practices

### Organizing Sessions
- Use descriptive names: `/session save project-api-design`
- Save before major changes
- Export important conversations

### Managing Context
- Use `/compact` when context gets large
- Clear irrelevant history with `/clear`
- Fork to preserve important checkpoints

### Backup
- Export important sessions to markdown
- Sessions stored in `~/.null/null.db`
- Backup the entire `~/.null/` directory

## Troubleshooting

### Session Won't Load
1. Check session exists: `/session list`
2. Verify database: `ls -la ~/.null/null.db`
3. Try loading by exact name

### Context Too Large
1. Use `/compact` to summarize
2. Clear old history: `/clear`
3. Increase context window in settings

### Lost Session
1. Check auto-save was enabled
2. Look for exports in current directory
3. Check database for saved sessions
