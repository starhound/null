import pytest
from unittest.mock import MagicMock


class TestExecutionHandler:
    @pytest.fixture
    def mock_app(self):
        app = MagicMock()
        app.blocks = []
        app.ai_mode = False
        app.ai_manager = MagicMock()
        app.mcp_manager = MagicMock()
        app.notify = MagicMock()
        return app

    @pytest.fixture
    def handler(self, mock_app):
        from handlers.execution import ExecutionHandler

        return ExecutionHandler(mock_app)

    def test_init(self, handler, mock_app):
        assert handler.app == mock_app

    def test_has_execute_ai_method(self, handler):
        assert hasattr(handler, "execute_ai")
        assert callable(handler.execute_ai)

    def test_has_execute_cli_method(self, handler):
        assert hasattr(handler, "execute_cli")
        assert callable(handler.execute_cli)


class TestInputHandler:
    @pytest.fixture
    def mock_app(self):
        app = MagicMock()
        app.blocks = []
        app.ai_mode = False
        app.ai_manager = MagicMock()
        app.mcp_manager = MagicMock()
        app.notify = MagicMock()
        app.query_one = MagicMock(side_effect=Exception("Not found"))
        return app

    @pytest.fixture
    def handler(self, mock_app):
        from handlers.input import InputHandler

        return InputHandler(mock_app)

    def test_init(self, handler, mock_app):
        assert handler.app == mock_app

    def test_has_handle_submission_method(self, handler):
        assert hasattr(handler, "handle_submission")
        assert callable(handler.handle_submission)

    def test_has_handle_builtin_method(self, handler):
        assert hasattr(handler, "handle_builtin")
        assert callable(handler.handle_builtin)
