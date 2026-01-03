# Configuration

Settings are stored in `~/.null/config.json` and accessed via `/config` or `/settings`.

## Settings Categories

### Appearance

| Setting | Default | Description |
|---------|---------|-------------|
| `theme` | `null-dark` | Color theme |
| `font_family` | `monospace` | Terminal font |
| `font_size` | `14` | Font size in pixels |
| `line_height` | `1.4` | Line spacing multiplier |
| `show_timestamps` | `true` | Show timestamps on blocks |
| `show_line_numbers` | `true` | Line numbers in code blocks |

### Editor

| Setting | Default | Description |
|---------|---------|-------------|
| `tab_size` | `4` | Spaces per tab |
| `word_wrap` | `true` | Wrap long lines |
| `auto_indent` | `true` | Auto-indent new lines |
| `vim_mode` | `false` | Vim-style keybindings |

### Terminal

| Setting | Default | Description |
|---------|---------|-------------|
| `shell` | `$SHELL` | Shell to use |
| `scrollback_lines` | `10000` | History buffer size |
| `clear_on_exit` | `false` | Clear session on exit |
| `confirm_on_exit` | `true` | Confirm before quitting |
| `auto_save_session` | `true` | Auto-save sessions |
| `auto_save_interval` | `30` | Seconds between saves |
| `cursor_style` | `block` | Cursor: block, beam, underline |
| `cursor_blink` | `true` | Cursor blinking |
| `bold_is_bright` | `true` | Bold text as bright colors |

### AI

| Setting | Default | Description |
|---------|---------|-------------|
| `provider` | `ollama` | Default AI provider |
| `default_model` | `""` | Default model (auto-detect) |
| `active_prompt` | `default` | System prompt/persona |
| `context_window` | `4000` | Context size (tokens) |
| `max_tokens` | `2048` | Max response tokens |
| `temperature` | `0.7` | Creativity (0.0-2.0) |
| `stream_responses` | `true` | Stream AI responses |
| `autocomplete_enabled` | `false` | AI command suggestions |
| `autocomplete_provider` | `""` | Provider for autocomplete |
| `autocomplete_model` | `""` | Model for autocomplete |

## Configuration Files

### Main Settings
`~/.null/config.json`

```json
{
  "appearance": {
    "theme": "null-dark",
    "font_size": 14
  },
  "terminal": {
    "cursor_style": "beam",
    "auto_save_session": true
  },
  "ai": {
    "provider": "ollama",
    "temperature": 0.7
  }
}
```

### Database (SQLite)
`~/.null/null.db`

Stores:
- API keys (encrypted)
- Provider configurations
- Saved sessions
- SSH host configurations
- Command history

### MCP Configuration
`~/.null/mcp.json`

See [MCP Servers](mcp.md) for details.

## Environment Variables

These environment variables are read for defaults:

| Variable | Used For |
|----------|----------|
| `SHELL` | Default shell |
| `TERM` | Terminal type |
| `COLORTERM` | Color support |
| `LANG` | Locale |

## Per-Provider Settings

Each provider has its own configuration keys:

```
ai.<provider>.api_key     - API key
ai.<provider>.endpoint    - Custom endpoint
ai.<provider>.model       - Selected model
ai.<provider>.region      - Region (cloud providers)
ai.<provider>.project_id  - Project ID (Google)
```

Access via `/provider <name>` to configure.

## Resetting Configuration

### Reset All Settings
In `/config` screen, click "Reset to Defaults"

### Manual Reset
```bash
rm ~/.null/config.json
# Restart application - defaults will be created
```

### Reset Database
```bash
rm ~/.null/null.db
# Warning: This deletes all API keys and sessions
```
