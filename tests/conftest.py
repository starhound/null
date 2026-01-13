"""Shared test fixtures and configuration."""

import asyncio
import tempfile
from pathlib import Path
from unittest.mock import MagicMock

import pytest


@pytest.fixture(scope="session")
def event_loop():
    """Create an event loop for async tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def temp_dir():
    """Create a temporary directory for test files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def temp_workdir(temp_dir, monkeypatch):
    """Create a temporary directory and change into it (for file operation tests)."""
    monkeypatch.chdir(temp_dir)
    return temp_dir


@pytest.fixture
def mock_home(temp_dir, monkeypatch):
    """Mock home directory to use temp directory."""
    null_dir = temp_dir / ".null"
    null_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(Path, "home", lambda: temp_dir)
    return temp_dir


@pytest.fixture
def mock_storage(mock_home, monkeypatch):
    """Create a mock storage manager with temp database."""
    import config.storage as storage_module
    from config.storage import StorageManager

    # Patch DB_PATH to use temp directory (evaluated at import time)
    temp_db_path = mock_home / ".null" / "null.db"
    monkeypatch.setattr(storage_module, "DB_PATH", temp_db_path)

    # Create fresh storage in temp directory
    storage = StorageManager()
    yield storage
    storage.close()


@pytest.fixture
def mock_config(mock_storage):
    """Provide access to Config with mocked storage."""
    from config import Config

    return Config


@pytest.fixture
def sample_block_state():
    """Create a sample BlockState for testing."""
    from models import BlockState, BlockType

    return BlockState(
        type=BlockType.COMMAND,
        content_input="ls -la",
        content_output="total 0\ndrwxr-xr-x 2 user user 40 Jan 1 00:00 .",
    )


@pytest.fixture
def sample_ai_block_state():
    """Create a sample AI response BlockState."""
    from models import BlockState, BlockType

    return BlockState(
        type=BlockType.AI_RESPONSE,
        content_input="What is Python?",
        content_output="Python is a programming language.",
        metadata={"provider": "test", "model": "test-model"},
    )


@pytest.fixture
def mock_llm_provider():
    """Create a mock LLM provider for testing."""
    provider = MagicMock()
    provider.model = "test-model"
    provider.supports_tools.return_value = True

    async def mock_generate(*args, **kwargs):
        yield "Test response"

    provider.generate = mock_generate
    return provider


@pytest.fixture
def mock_prompt_manager(temp_dir):
    """Create a prompt manager with temp prompts directory."""
    prompts_dir = temp_dir / ".null" / "prompts"
    prompts_dir.mkdir(parents=True, exist_ok=True)

    from prompts.manager import PromptManager

    manager = PromptManager()
    manager.prompts_dir = prompts_dir
    return manager


@pytest.fixture(autouse=True)
def reset_global_singletons():
    """Reset global singletons between tests to ensure isolation."""
    yield

    try:
        import security.sanitizer as sanitizer_mod

        sanitizer_mod._default_sanitizer = None
    except (ImportError, AttributeError):
        pass

    try:
        import security.rate_limiter as rate_mod

        rate_mod._rate_limiter = None
        rate_mod._cost_tracker = None
    except (ImportError, AttributeError):
        pass

    try:
        import security.sandbox as sandbox_mod

        sandbox_mod._sandbox = None
    except (ImportError, AttributeError):
        pass
