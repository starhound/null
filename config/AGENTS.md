# AGENTS: config/

## OVERVIEW
Centralized management for application settings, encrypted storage, and persistent state.

## STRUCTURE
```
config/
├── ai.py              # Facade for AI/LLM configuration settings
├── defaults.py        # Default values for all configuration fields
├── keys.py            # Key definitions and sensitivity registry (is_sensitive_key)
├── settings.py        # TUI appearance & behavior (JSON-based config.json)
└── storage.py         # Persistent state (SQLite) and SecurityManager (Fernet)
```

## WHERE TO LOOK
| Task | File | Key Component |
|------|------|---------------|
| **Modify UI defaults** | `settings.py` | `AppearanceSettings` |
| **Add SQL table/field** | `storage.py` | `StorageManager._create_schema` |
| **Add sensitive key** | `keys.py` | `SENSITIVE_KEYS` registry |
| **Encryption logic** | `storage.py` | `SecurityManager` (Fernet + Keyring) |
| **SSH Host management**| `storage.py` | `StorageManager.add_ssh_host` |
| **Config access facade**| `ai.py` | `Config.get` / `Config.set` |

## CONVENTIONS
*   **SecurityManager**: All sensitive values (API keys, passwords) MUST be encrypted before persistence via `SecurityManager.encrypt()`.
*   **Layered Storage**:
    *   `config.json`: Appearance, editor, and terminal behavior.
    *   `null.db`: Command history, encrypted keys, SSH profiles, and AI settings.
*   **Keyring Integration**: Primary encryption key resides in system keyring; fallback to `~/.null/.key` if keyring is unavailable.
*   **Sensitivity Registry**: New API-related keys must be registered in `keys.py` to ensure automatic encryption in `Config.set()`.
*   **Isolated Testing**: Always use the `mock_home` fixture to prevent writing to real user config directories.

## ANTI-PATTERNS
*   **Hardcoded Secrets**: Never store raw API keys, tokens, or passwords in source or plain text files.
*   **Direct DB Access**: Avoid direct `sqlite3` interaction outside `StorageManager`.
*   **Mixing Logic**: Keep UI-specific settings (JSON) distinct from state/secrets (SQLite).
*   **Blocking I/O**: Do not perform heavy DB migrations or config writes on the main Textual event loop.
