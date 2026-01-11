# Changelog

All notable changes to Null Terminal will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Comprehensive CONTRIBUTING.md guide
- Enhanced ARCHITECTURE.md with handler patterns and manager lifecycle
- MCP architecture documentation in AGENTS.md
- Token pricing table in providers documentation
- Test coverage audit documentation

### Changed
- Updated DEVELOPMENT.md with accurate command patterns
- Improved AI provider documentation

### Fixed
- Command registration examples now match actual codebase patterns

---

## [0.1.0] - 2026-01-XX

### Added

#### Core Features
- Block-based terminal interface with distinct command and AI response blocks
- Dual-mode operation: CLI mode and AI mode (toggle with Ctrl+Space)
- Agent mode for autonomous multi-step task execution
- Real-time streaming AI responses with token usage tracking

#### AI Integration
- Multi-provider support:
  - **Local**: Ollama, LM Studio, Llama.cpp, NVIDIA NIM
  - **Cloud**: OpenAI, Anthropic, Google (Vertex/AI Studio), Azure, AWS Bedrock
  - **Alternative**: Groq, Mistral, DeepSeek, Cohere, Together, xAI, OpenRouter
- Thinking/reasoning display for compatible models (DeepSeek, Claude, o1)
- Tool calling with approval system
- Session cost tracking and display

#### MCP (Model Context Protocol)
- Full MCP specification implementation
- Server catalog with pre-configured popular servers
- Dynamic tool discovery and registration
- `/mcp` command for server management

#### Developer Workflow
- Integrated todo manager (`/todo`)
- Custom system prompts (`/prompts`)
- Session export to Markdown/JSON
- Git status integration in status bar
- File explorer sidebar

#### RAG / Knowledge Base
- Local codebase indexing (`/index build`)
- Semantic search with vector embeddings
- Context-aware AI responses

#### UI/UX
- 10+ built-in themes (Null Dark, Monokai, Dracula, etc.)
- Custom theme support via `~/.null/themes/`
- Command palette (Ctrl+P)
- History search (Ctrl+R)
- Block search (Ctrl+F)

#### Platform Support
- Linux (primary)
- macOS
- Windows (via PyInstaller)
- Docker container

### Security
- Encrypted API key storage (Fernet)
- Tool approval gates for dangerous operations
- Sandboxed file operations (project directory only)

---

## Version History Template

When releasing new versions, use this template:

```markdown
## [X.Y.Z] - YYYY-MM-DD

### Added
- New features

### Changed
- Changes in existing functionality

### Deprecated
- Features that will be removed in upcoming releases

### Removed
- Removed features

### Fixed
- Bug fixes

### Security
- Security-related changes
```

---

## Links

- [GitHub Releases](https://github.com/starhound/null-terminal/releases)
- [PyPI Package](https://pypi.org/project/null-terminal/)
- [Docker Hub](https://hub.docker.com/r/starhound/null-terminal)
