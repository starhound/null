# Configuration

Null Terminal uses a layered configuration system designed for both ease of use and security. Most settings can be modified directly within the application via the `/settings` or `/config` commands, or by manually editing the configuration files.

---

## Configuration Overview

Null Terminal stores its state and settings in the `~/.null/` directory:

| Component | Storage Type | Purpose |
| :--- | :--- | :--- |
| **Main Settings** | `config.json` | TUI appearance, editor preferences, and terminal behavior. |
| **Secrets & State** | `null.db` | Encrypted API keys, provider configurations, sessions, and history. |
| **MCP Config** | `mcp.json` | Configuration for Model Context Protocol servers. |
| **Custom Themes** | `themes/` | User-defined color schemes (JSON). |
| **System Prompts**| `prompts/` | Custom personas and system instructions. |

---

## Settings Categories

### Appearance
Customize the look and feel of the terminal interface. These settings are stored in `config.json`.

| Setting | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `theme` | `string` | `"null-dark"` | The active color theme. See [Themes](themes.md) for more. |
| `font_family` | `string` | `"monospace"` | Font used for the terminal interface. |
| `font_size` | `integer` | `14` | Font size in pixels. |
| `line_height` | `float` | `1.4` | Line spacing multiplier for better readability. |
| `show_timestamps` | `boolean` | `true` | Display the time of execution for each block. |
| `show_line_numbers` | `boolean` | `true` | Show line numbers in code blocks and editor. |

### Editor
Settings for the input field and text interaction.

| Setting | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `tab_size` | `integer` | `4` | Number of spaces per tab character. |
| `word_wrap` | `boolean` | `true` | Wrap long lines in the output blocks. |
| `auto_indent` | `boolean` | `true` | Automatically indent new lines in the editor. |
| `vim_mode` | `boolean` | `false` | Enable Vim-style keybindings for the input field. |

### Terminal
Configure terminal behavior and session management.

| Setting | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `shell` | `string` | `$SHELL` | The shell to use for CLI blocks (e.g., `/bin/zsh`). |
| `scrollback_lines` | `integer` | `10000` | Number of lines to keep in the output buffer. |
| `max_history_blocks` | `integer` | `100` | Maximum number of blocks to retain in the viewport. |
| `confirm_on_exit` | `boolean` | `true` | Prompt for confirmation before quitting. |
| `auto_save_session` | `boolean` | `true` | Automatically save the current session to `null.db`. |
| `cursor_style` | `string` | `"block"` | Cursor shape: `block`, `beam`, or `underline`. |
| `cursor_blink` | `boolean` | `true` | Enable or disable cursor blinking. |
| `bold_is_bright` | `boolean` | `true` | Whether bold text should use bright color variants. |

### AI Core Settings
Basic AI behavior. Detailed provider settings are stored securely in `null.db`.

| Setting | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `provider` | `string` | `"ollama"` | The active AI provider. |
| `active_prompt` | `string` | `"default"` | The system prompt/persona currently in use. |
| `context_window` | `integer` | `4000` | Max context size in tokens sent to the AI. |
| `temperature` | `float` | `0.7` | Sampling temperature (0.0 to 2.0). |
| `stream_responses` | `boolean` | `true` | Stream AI responses in real-time. |
| `embedding_provider` | `string` | `"ollama"` | Provider for vector embeddings. |
| `embedding_model` | `string` | `"nomic-embed-text"`| Model for vector embeddings. |

---

## Advanced Configuration

### The `config.json` Structure
For users who prefer manual editing, `~/.null/config.json` follows a nested structure.

??? note "View Example config.json"
    ```json
    {
      "appearance": {
        "theme": "null-dark",
        "font_family": "monospace",
        "font_size": 14,
        "line_height": 1.4,
        "show_timestamps": true,
        "show_line_numbers": true
      },
      "editor": {
        "tab_size": 4,
        "word_wrap": true,
        "auto_indent": true,
        "vim_mode": false
      },
      "terminal": {
        "shell": "/bin/bash",
        "scrollback_lines": 10000,
        "max_history_blocks": 100,
        "clear_on_exit": false,
        "confirm_on_exit": true,
        "auto_save_session": true,
        "auto_save_interval": 30,
        "cursor_style": "block",
        "cursor_blink": true,
        "bold_is_bright": true
      },
      "ai": {
        "provider": "ollama",
        "default_model": "",
        "active_prompt": "default",
        "context_window": 4000,
        "max_tokens": 2048,
        "temperature": 0.7,
        "stream_responses": true,
        "autocomplete_enabled": false
      }
    }
    ```

### Per-Provider Configuration
While general settings reside in `config.json`, sensitive data like API keys and specific model endpoints are stored in the `null.db` SQLite database and encrypted using system-level keyring or a local master key.

You can configure these via the UI using `/provider <name>` or `/settings`.

??? note "Advanced Provider Settings"
    Each provider supports the following keys (stored in `null.db`):
    - `ai.<provider>.api_key`: Encrypted API credential.
    - `ai.<provider>.endpoint`: Custom API endpoint (useful for local proxies).
    - `ai.<provider>.model`: Default model for this specific provider.
    - `ai.<provider>.region`: Region for cloud providers (e.g., AWS Bedrock, GCP).

---

## Security

Null Terminal prioritizes the safety of your local environment. Security settings control how the AI interacts with your system and tools.

| Setting | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `require_tool_approval` | `boolean` | `true` | Always prompt before executing any tool. |
| `allowed_commands` | `array` | `[]` | List of shell commands that don't require approval. |
| `blocked_paths` | `array` | `["~/.ssh", "~/.gnupg"]` | Filesystem paths the AI is never allowed to access. |

You can also configure "dangerous" tools to always require manual confirmation in the `/settings` menu.

---

## Keyboard Shortcuts

Null Terminal provides several global shortcuts to manage your workflow. You can view the full list in the [Shortcuts Guide](shortcuts.md).

| Category | Shortcut | Action |
| :--- | :--- | :--- |
| **Navigation** | `Ctrl+P` | Open Command Palette |
| | `Ctrl+R` | Search Command History |
| | `Ctrl+F` | Search Block Content |
| | `Ctrl+\` | Toggle File Sidebar |
| **Modes** | `Ctrl+Space` | Toggle CLI / AI Mode |
| | `F2` | Open Model Selector |
| | `F4` | Open Provider Selector |
| **System** | `F3` | Open Theme Selector |
| | `Ctrl+L` | Clear Session History |
| | `Escape` | Cancel Running Operation |

---

## Theme Configuration

Null Terminal supports highly customizable themes. Themes are JSON files located in `~/.null/themes/`.

- **Switching Themes**: Use the `/theme` command or press `F3`.
- **Custom Themes**: Place your `.json` theme files in the `themes/` directory. They will be automatically detected on startup.

For a detailed guide on creating your own themes, see the [Themes Documentation](themes.md).

---

## Environment Variables

The following environment variables are respected for default values:

| Variable | Description |
| :--- | :--- |
| `SHELL` | Default shell for CLI blocks. |
| `TERM` | Terminal type hint. |
| `COLORTERM` | Enables 24-bit color if set to `truecolor`. |
| `LANG` | Locale settings. |

---

## Resetting Configuration

If you need to start fresh, you can reset specific parts of the configuration:

### Reset UI Settings
To reset `config.json` only:
```bash
rm ~/.null/config.json
# Restart Null Terminal to regenerate defaults
```

### Reset All Data (Caution)
To delete all settings, encrypted API keys, and session history:
```bash
rm -rf ~/.null/
# Warning: This is irreversible and will delete all stored secrets.
```
