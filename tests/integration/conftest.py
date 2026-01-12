"""Fixtures and configuration for integration tests."""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# Patch AI-related modules before importing the app
@pytest.fixture(autouse=True)
def mock_ai_components(monkeypatch):
    """Mock AI components to prevent network calls during integration tests."""

    async def mock_list_all_models_streaming():
        yield ("openai", ["gpt-4", "gpt-3.5-turbo"], None, 1, 2)
        yield ("anthropic", ["claude-3-sonnet"], None, 2, 2)

    # Mock AIManager
    mock_ai_manager = MagicMock()
    mock_ai_manager.get_active_provider.return_value = None
    mock_ai_manager.get_provider.return_value = None
    mock_ai_manager.get_usable_providers.return_value = []
    mock_ai_manager.list_all_models = AsyncMock(return_value={})
    mock_ai_manager.list_all_models_streaming = mock_list_all_models_streaming
    mock_ai_manager._fetch_models_for_provider = AsyncMock(
        return_value=("test", [], None)
    )

    # Mock MCPManager
    mock_mcp_manager = MagicMock()
    mock_mcp_manager.initialize = AsyncMock()
    mock_mcp_manager.get_all_tools.return_value = []
    mock_mcp_manager.clients = {}

    # Apply patches
    monkeypatch.setattr("app.AIManager", lambda: mock_ai_manager)
    monkeypatch.setattr("app.MCPManager", lambda: mock_mcp_manager)

    return mock_ai_manager, mock_mcp_manager


@pytest.fixture
def temp_home(tmp_path, monkeypatch):
    """Create a temporary home directory for testing."""
    null_dir = tmp_path / ".null"
    null_dir.mkdir(parents=True, exist_ok=True)

    # Create subdirectories
    (null_dir / "prompts").mkdir(exist_ok=True)
    (null_dir / "themes").mkdir(exist_ok=True)
    (null_dir / "sessions").mkdir(exist_ok=True)

    # Patch Path.home to return temp directory
    monkeypatch.setattr(Path, "home", lambda: tmp_path)

    # Patch storage module DB_PATH
    import config.storage as storage_module

    monkeypatch.setattr(storage_module, "DB_PATH", null_dir / "null.db")

    # Patch settings CONFIG_PATH
    import config.settings as settings_module

    monkeypatch.setattr(settings_module, "CONFIG_PATH", null_dir / "config.json")

    # Reset SettingsManager singleton
    settings_module.SettingsManager._instance = None
    settings_module.SettingsManager._settings = None

    return tmp_path


@pytest.fixture
def mock_storage(temp_home):
    """Create a mock storage manager with temp database."""
    from config.storage import StorageManager

    storage = StorageManager()

    # Set disclaimer accepted to skip disclaimer screen
    storage.set_config("disclaimer_accepted", "true")

    yield storage
    storage.close()


@pytest.fixture
def app_with_mocked_storage(temp_home, mock_storage, mock_ai_components):
    """Create a NullApp instance with mocked storage and AI components."""
    from app import NullApp

    # Patch Config._get_storage to use our mock
    with patch("app.Config._get_storage", return_value=mock_storage):
        with patch("handlers.input.Config._get_storage", return_value=mock_storage):
            app = NullApp()
            yield app


@pytest.fixture
async def running_app(app_with_mocked_storage):
    """Start the app and yield for testing, then clean up."""
    app = app_with_mocked_storage

    async with app.run_test() as pilot:
        yield pilot, app

    # Cleanup after test
    try:
        if hasattr(app, "storage") and app.storage:
            app.storage.close()
    except Exception:
        pass


@pytest.fixture
def mock_process_manager():
    """Mock ProcessManager for command execution tests."""
    mock_pm = MagicMock()
    mock_pm.get_count.return_value = 0
    mock_pm.is_running.return_value = False
    mock_pm.stop.return_value = True
    mock_pm.on_change = MagicMock()
    return mock_pm
