# Contributing to Null Terminal

Thank you for your interest in contributing to Null Terminal! This document provides guidelines and instructions for contributing.

## Code of Conduct

Be respectful, inclusive, and constructive. We're building something cool together.

## Getting Started

### Prerequisites

- Python 3.12+
- `uv` package manager
- Git

### Development Setup

```bash
# Clone the repository
git clone https://github.com/starhound/null-terminal.git
cd null-terminal

# Install dependencies
uv sync

# Run the application
uv run main.py

# Run tests
uv run pytest
```

## How to Contribute

### Reporting Bugs

1. Check existing issues to avoid duplicates
2. Use the bug report template
3. Include:
   - Null Terminal version
   - Python version
   - OS and terminal emulator
   - Steps to reproduce
   - Expected vs actual behavior
   - Relevant logs or screenshots

### Suggesting Features

1. Check existing issues/discussions
2. Describe the use case clearly
3. Explain why existing features don't solve it
4. Propose implementation if possible

### Submitting Code

#### 1. Fork and Branch

```bash
# Fork on GitHub, then:
git clone https://github.com/YOUR_USERNAME/null-terminal.git
cd null-terminal
git checkout -b feature/your-feature-name
```

**Branch naming conventions:**
- `feature/` - New features
- `fix/` - Bug fixes
- `docs/` - Documentation changes
- `refactor/` - Code refactoring
- `test/` - Test additions/fixes

#### 2. Make Your Changes

Follow the coding standards below. Commit often with clear messages.

#### 3. Test Your Changes

```bash
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov=. --cov-report=term-missing

# Run specific tests
uv run pytest tests/unit/ai/

# Lint your code
uv run ruff check .
uv run ruff format --check .
```

#### 4. Submit a Pull Request

1. Push your branch to your fork
2. Open a PR against `main`
3. Fill out the PR template
4. Link related issues
5. Wait for review

## Coding Standards

### Python Style

- **Formatter**: We use `ruff format`
- **Linter**: We use `ruff check`
- **Type hints**: Required for all public functions
- **Docstrings**: Required for classes and public methods

```python
async def my_function(param: str, count: int = 10) -> list[str]:
    """Brief description of what this does.
    
    Args:
        param: Description of param
        count: Description of count
        
    Returns:
        Description of return value
    """
    pass
```

### Async Conventions

- All I/O operations must be async
- Use `asyncio.create_subprocess_shell` instead of `subprocess`
- Use `httpx.AsyncClient` instead of `requests`
- Never use `time.sleep()` - use `asyncio.sleep()`

### TUI Conventions

- Never use `print()` - use `self.notify()` or `self.log()`
- Use TCSS classes for styling, not inline styles
- Use `self.post_message()` for widget communication
- Keep widget `compose()` methods simple

### Testing Requirements

- All new features need tests
- All bug fixes need regression tests
- Use the `mock_home` fixture to protect user data
- Integration tests use the `pilot` pattern

```python
import pytest

@pytest.mark.asyncio
async def test_feature(mock_home, mock_storage):
    """Test description."""
    # Arrange
    ...
    # Act
    ...
    # Assert
    assert result == expected
```

### Commit Messages

Follow conventional commits:

```
type(scope): short description

Longer description if needed.

Fixes #123
```

Types: `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`

Examples:
- `feat(ai): add support for Gemini 2.0 Flash`
- `fix(blocks): handle empty command output`
- `docs: update provider configuration guide`
- `test(mcp): add client connection tests`

## Architecture Guidelines

### Adding a New AI Provider

See [DEVELOPMENT.md](docs/DEVELOPMENT.md#2-adding-a-new-ai-provider)

1. Create `ai/newprovider.py` inheriting from `LLMProvider`
2. Implement required methods
3. Register in `ai/factory.py`
4. Add tests in `tests/unit/ai/`
5. Update `docs/user/providers.md`

### Adding a New Command

See [DEVELOPMENT.md](docs/DEVELOPMENT.md#1-adding-a-new-slash-command)

1. Add `cmd_` method to appropriate module in `commands/`
2. Register in `commands/handler.py`
3. Add tests
4. Update `docs/user/commands.md`

### Adding a New Widget

1. Create widget in `widgets/`
2. Use `reactive` properties for state
3. Style via TCSS in `styles/main.tcss`
4. Add integration tests

### Modifying Block Architecture

The block system (`widgets/blocks/`) is critical. Changes here require:
- Unit tests for the widget
- Integration tests for rendering
- Review of `BlockState` model compatibility

## Review Process

1. **Automated checks** must pass (tests, linting)
2. **One approval** required from maintainers
3. **Squash merge** preferred for clean history

### What Reviewers Look For

- Tests included and passing
- Code follows style guidelines
- No breaking changes without discussion
- Documentation updated if needed
- Commit messages are clear

## Release Process

Releases are managed by maintainers:

1. Version bump in `pyproject.toml`
2. Update `CHANGELOG.md`
3. Create GitHub release with tag
4. CI/CD handles PyPI and Docker publishing

## Getting Help

- **Questions**: Open a Discussion on GitHub
- **Bugs**: Open an Issue
- **Chat**: [Discord/Matrix link if available]

## Recognition

Contributors are recognized in:
- GitHub contributors list
- Release notes for significant contributions
- Special thanks in README for major features

---

Thank you for contributing to Null Terminal!
