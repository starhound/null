import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from pathlib import Path

from managers.suggestions import (
    Suggestion,
    ContextState,
    HistoryProvider,
    ContextProvider,
    AISuggestionProvider,
    SuggestionEngine,
)


class TestSuggestion:
    def test_create_basic_suggestion(self):
        sugg = Suggestion(
            command="ls -la",
            description="List files",
            source="history",
        )
        assert sugg.command == "ls -la"
        assert sugg.description == "List files"
        assert sugg.source == "history"
        assert sugg.score == 0.0
        assert sugg.icon == "⏱"

    def test_suggestion_icon_history(self):
        sugg = Suggestion(
            command="test",
            description="test",
            source="history",
        )
        assert sugg.icon == "⏱"

    def test_suggestion_icon_context(self):
        sugg = Suggestion(
            command="test",
            description="test",
            source="context",
        )
        assert sugg.icon == "📁"

    def test_suggestion_icon_ai(self):
        sugg = Suggestion(
            command="test",
            description="test",
            source="ai",
        )
        assert sugg.icon == "✨"

    def test_suggestion_custom_icon(self):
        sugg = Suggestion(
            command="test",
            description="test",
            source="history",
            icon="🔥",
        )
        assert sugg.icon == "🔥"

    def test_suggestion_with_score(self):
        sugg = Suggestion(
            command="test",
            description="test",
            source="history",
            score=0.85,
        )
        assert sugg.score == 0.85

    def test_suggestion_post_init_sets_icon(self):
        sugg = Suggestion(
            command="git status",
            description="View status",
            source="context",
        )
        assert sugg.icon == "📁"


class TestContextState:
    def test_create_default_context_state(self):
        ctx = ContextState()
        assert ctx.cwd == ""
        assert ctx.git_branch == ""
        assert ctx.git_dirty is False
        assert ctx.recent_commands == []
        assert ctx.recent_errors == []
        assert ctx.directory_contents == []

    def test_create_context_state_with_values(self):
        ctx = ContextState(
            cwd="/home/user",
            git_branch="main",
            git_dirty=True,
            recent_commands=["ls", "cd"],
            recent_errors=["Error 1"],
            directory_contents=["file.py", "file.js"],
        )
        assert ctx.cwd == "/home/user"
        assert ctx.git_branch == "main"
        assert ctx.git_dirty is True
        assert ctx.recent_commands == ["ls", "cd"]
        assert ctx.recent_errors == ["Error 1"]
        assert ctx.directory_contents == ["file.py", "file.js"]

    def test_context_state_partial_values(self):
        ctx = ContextState(cwd="/tmp", git_branch="develop")
        assert ctx.cwd == "/tmp"
        assert ctx.git_branch == "develop"
        assert ctx.git_dirty is False
        assert ctx.recent_commands == []


class TestHistoryProvider:
    def test_init(self):
        provider = HistoryProvider()
        assert provider._history == []

    def test_add_command_single(self):
        provider = HistoryProvider()
        provider.add_command("ls -la")
        assert provider._history == ["ls -la"]

    def test_add_command_multiple(self):
        provider = HistoryProvider()
        provider.add_command("ls -la")
        provider.add_command("cd /tmp")
        provider.add_command("pwd")
        assert provider._history == ["pwd", "cd /tmp", "ls -la"]

    def test_add_command_deduplication(self):
        provider = HistoryProvider()
        provider.add_command("ls -la")
        provider.add_command("cd /tmp")
        provider.add_command("ls -la")
        assert "ls -la" in provider._history
        assert "cd /tmp" in provider._history
        assert len(provider._history) == 2
        assert provider._history == ["cd /tmp", "ls -la"]

    def test_add_command_empty_string(self):
        provider = HistoryProvider()
        provider.add_command("")
        assert provider._history == []

    def test_add_command_max_limit(self):
        provider = HistoryProvider()
        for i in range(600):
            provider.add_command(f"cmd_{i}")
        assert len(provider._history) == 500
        assert provider._history[0] == "cmd_599"
        assert provider._history[-1] == "cmd_100"

    def test_suggest_empty_history(self):
        provider = HistoryProvider()
        suggestions = provider.suggest("ls")
        assert suggestions == []

    def test_suggest_prefix_matching(self):
        provider = HistoryProvider()
        provider.add_command("ls -la")
        provider.add_command("ls -l")
        provider.add_command("cd /tmp")
        suggestions = provider.suggest("ls")
        assert len(suggestions) == 2
        assert suggestions[0].command in ["ls -la", "ls -l"]
        assert suggestions[1].command in ["ls -la", "ls -l"]

    def test_suggest_case_insensitive(self):
        provider = HistoryProvider()
        provider.add_command("LS -LA")
        provider.add_command("ls -l")
        suggestions = provider.suggest("ls")
        assert len(suggestions) == 2

    def test_suggest_no_match(self):
        provider = HistoryProvider()
        provider.add_command("ls -la")
        provider.add_command("cd /tmp")
        suggestions = provider.suggest("git")
        assert suggestions == []

    def test_suggest_limit(self):
        provider = HistoryProvider()
        for i in range(10):
            provider.add_command(f"ls_{i}")
        suggestions = provider.suggest("ls", limit=3)
        assert len(suggestions) == 3

    def test_suggest_scoring_recency(self):
        provider = HistoryProvider()
        provider.add_command("ls -la")
        provider.add_command("ls -l")
        provider.add_command("ls -la")
        suggestions = provider.suggest("ls", limit=5)
        assert len(suggestions) >= 2
        assert suggestions[0].score >= suggestions[1].score

    def test_suggest_scoring_frequency(self):
        provider = HistoryProvider()
        provider.add_command("ls -la")
        provider.add_command("ls -la")
        provider.add_command("ls -la")
        provider.add_command("ls -l")
        suggestions = provider.suggest("ls", limit=5)
        assert len(suggestions) >= 2
        assert suggestions[0].score >= suggestions[1].score

    def test_suggest_all_have_history_source(self):
        provider = HistoryProvider()
        provider.add_command("ls -la")
        provider.add_command("cd /tmp")
        suggestions = provider.suggest("l", limit=5)
        assert all(s.source == "history" for s in suggestions)

    def test_suggest_all_have_description(self):
        provider = HistoryProvider()
        provider.add_command("ls -la")
        suggestions = provider.suggest("ls", limit=5)
        assert all(s.description == "From history" for s in suggestions)


class TestContextProvider:
    def test_suggest_empty_context(self):
        provider = ContextProvider()
        ctx = ContextState()
        suggestions = provider.suggest("git", ctx)
        assert suggestions == []

    def test_suggest_git_dirty_status(self):
        provider = ContextProvider()
        ctx = ContextState(git_dirty=True)
        suggestions = provider.suggest("git", ctx)
        assert len(suggestions) == 3
        assert suggestions[0].command == "git status"
        assert suggestions[1].command == "git diff"
        assert suggestions[2].command == "git add ."

    def test_suggest_git_dirty_no_match_prefix(self):
        provider = ContextProvider()
        ctx = ContextState(git_dirty=True)
        suggestions = provider.suggest("ls", ctx)
        assert suggestions == []

    def test_suggest_git_not_dirty(self):
        provider = ContextProvider()
        ctx = ContextState(git_dirty=False)
        suggestions = provider.suggest("git", ctx)
        assert suggestions == []

    def test_suggest_python_file(self):
        provider = ContextProvider()
        ctx = ContextState(directory_contents=["script.py", "test.py"])
        suggestions = provider.suggest("python", ctx)
        assert len(suggestions) >= 1
        assert any("script.py" in s.command for s in suggestions)

    def test_suggest_python_short_prefix(self):
        provider = ContextProvider()
        ctx = ContextState(directory_contents=["script.py"])
        suggestions = provider.suggest("py", ctx)
        assert len(suggestions) >= 1
        assert "python script.py" in [s.command for s in suggestions]

    def test_suggest_node_js_file(self):
        provider = ContextProvider()
        ctx = ContextState(directory_contents=["app.js"])
        suggestions = provider.suggest("node", ctx)
        assert len(suggestions) >= 1
        assert "node app.js" in [s.command for s in suggestions]

    def test_suggest_node_ts_file(self):
        provider = ContextProvider()
        ctx = ContextState(directory_contents=["app.ts"])
        suggestions = provider.suggest("node", ctx)
        assert len(suggestions) >= 1
        assert "node app.ts" in [s.command for s in suggestions]

    def test_suggest_npm_commands(self):
        provider = ContextProvider()
        ctx = ContextState(directory_contents=["package.json"])
        suggestions = provider.suggest("npm", ctx)
        commands = [s.command for s in suggestions]
        assert "npm install" in commands
        assert "npm run" in commands
        assert "npm test" in commands
        assert "npm start" in commands

    def test_suggest_npm_partial_match(self):
        provider = ContextProvider()
        ctx = ContextState(directory_contents=["package.json"])
        suggestions = provider.suggest("npm i", ctx)
        assert len(suggestions) >= 1
        assert "npm install" in [s.command for s in suggestions]

    def test_suggest_npm_no_package_json(self):
        provider = ContextProvider()
        ctx = ContextState(directory_contents=["file.js"])
        suggestions = provider.suggest("npm", ctx)
        assert suggestions == []

    def test_suggest_recent_error_module_not_found(self):
        provider = ContextProvider()
        ctx = ContextState(
            recent_errors=["ModuleNotFoundError: No module named 'requests'"]
        )
        suggestions = provider.suggest("pip", ctx)
        assert len(suggestions) >= 1
        assert suggestions[0].command == "pip install"

    def test_suggest_recent_error_import_error(self):
        provider = ContextProvider()
        ctx = ContextState(recent_errors=["ImportError: cannot import name 'foo'"])
        suggestions = provider.suggest("pip", ctx)
        assert len(suggestions) >= 1
        assert suggestions[0].command == "pip install"

    def test_suggest_recent_error_no_match(self):
        provider = ContextProvider()
        ctx = ContextState(recent_errors=["ValueError: invalid value"])
        suggestions = provider.suggest("pip", ctx)
        assert suggestions == []

    def test_suggest_respects_limit(self):
        provider = ContextProvider()
        ctx = ContextState(
            git_dirty=True,
            directory_contents=["script.py", "app.js"],
        )
        suggestions = provider.suggest("git", ctx, limit=2)
        assert len(suggestions) <= 2

    def test_suggest_all_have_context_source(self):
        provider = ContextProvider()
        ctx = ContextState(git_dirty=True)
        suggestions = provider.suggest("git", ctx)
        assert all(s.source == "context" for s in suggestions)

    def test_suggest_directory_contents_limit(self):
        provider = ContextProvider()
        files = [f"file_{i}.py" for i in range(20)]
        ctx = ContextState(directory_contents=files)
        suggestions = provider.suggest("python", ctx)
        assert len(suggestions) <= 10


class TestAISuggestionProvider:
    @pytest.mark.asyncio
    async def test_suggest_basic(self):
        provider = AISuggestionProvider()
        mock_llm = MagicMock()

        async def mock_generate(*args, **kwargs):
            yield "ls -la | List files\n"
            yield "cd /tmp | Change directory\n"

        mock_llm.generate = mock_generate
        ctx = ContextState(cwd="/home")
        suggestions = await provider.suggest("ls", ctx, mock_llm)
        assert len(suggestions) == 2
        assert suggestions[0].command == "ls -la"
        assert suggestions[0].description == "List files"
        assert suggestions[1].command == "cd /tmp"

    @pytest.mark.asyncio
    async def test_suggest_without_description(self):
        provider = AISuggestionProvider()
        mock_llm = MagicMock()

        async def mock_generate(*args, **kwargs):
            yield "git status\n"

        mock_llm.generate = mock_generate
        ctx = ContextState()
        suggestions = await provider.suggest("git", ctx, mock_llm)
        assert len(suggestions) == 1
        assert suggestions[0].command == "git status"
        assert suggestions[0].description == "AI suggestion"

    @pytest.mark.asyncio
    async def test_suggest_respects_limit(self):
        provider = AISuggestionProvider()
        mock_llm = MagicMock()

        async def mock_generate(*args, **kwargs):
            for i in range(10):
                yield f"cmd_{i} | Description {i}\n"

        mock_llm.generate = mock_generate
        ctx = ContextState()
        suggestions = await provider.suggest("cmd", ctx, mock_llm, limit=3)
        assert len(suggestions) == 3

    @pytest.mark.asyncio
    async def test_suggest_filters_input_text(self):
        provider = AISuggestionProvider()
        mock_llm = MagicMock()

        async def mock_generate(*args, **kwargs):
            yield "ls | List\n"
            yield "ls -la | List all\n"

        mock_llm.generate = mock_generate
        ctx = ContextState()
        suggestions = await provider.suggest("ls", ctx, mock_llm)
        assert all(s.command != "ls" for s in suggestions)

    @pytest.mark.asyncio
    async def test_suggest_skips_empty_lines(self):
        provider = AISuggestionProvider()
        mock_llm = MagicMock()

        async def mock_generate(*args, **kwargs):
            yield "ls -la | List\n"
            yield "\n"
            yield "cd /tmp | Change\n"

        mock_llm.generate = mock_generate
        ctx = ContextState()
        suggestions = await provider.suggest("ls", ctx, mock_llm)
        assert len(suggestions) == 2

    @pytest.mark.asyncio
    async def test_suggest_skips_comments(self):
        provider = AISuggestionProvider()
        mock_llm = MagicMock()

        async def mock_generate(*args, **kwargs):
            yield "# This is a comment\n"
            yield "ls -la | List\n"

        mock_llm.generate = mock_generate
        ctx = ContextState()
        suggestions = await provider.suggest("ls", ctx, mock_llm)
        assert len(suggestions) == 1
        assert suggestions[0].command == "ls -la"

    @pytest.mark.asyncio
    async def test_suggest_strips_backticks(self):
        provider = AISuggestionProvider()
        mock_llm = MagicMock()

        async def mock_generate(*args, **kwargs):
            yield "`ls -la` | List\n"

        mock_llm.generate = mock_generate
        ctx = ContextState()
        suggestions = await provider.suggest("ls", ctx, mock_llm)
        assert suggestions[0].command == "ls -la"

    @pytest.mark.asyncio
    async def test_suggest_includes_context_in_prompt(self):
        provider = AISuggestionProvider()
        mock_llm = MagicMock()
        prompt_captured = None

        async def mock_generate(prompt, *args, **kwargs):
            nonlocal prompt_captured
            prompt_captured = prompt
            yield "ls -la | List\n"

        mock_llm.generate = mock_generate
        ctx = ContextState(
            cwd="/home/user",
            git_branch="main",
            recent_commands=["cd /tmp", "ls"],
        )
        await provider.suggest("ls", ctx, mock_llm)
        assert prompt_captured is not None
        assert "/home/user" in prompt_captured
        assert "main" in prompt_captured
        assert "cd /tmp" in prompt_captured

    @pytest.mark.asyncio
    async def test_suggest_all_have_ai_source(self):
        provider = AISuggestionProvider()
        mock_llm = MagicMock()

        async def mock_generate(*args, **kwargs):
            yield "ls -la | List\n"
            yield "cd /tmp | Change\n"

        mock_llm.generate = mock_generate
        ctx = ContextState()
        suggestions = await provider.suggest("ls", ctx, mock_llm)
        assert all(s.source == "ai" for s in suggestions)

    @pytest.mark.asyncio
    async def test_suggest_scoring_decreases(self):
        provider = AISuggestionProvider()
        mock_llm = MagicMock()

        async def mock_generate(*args, **kwargs):
            yield "cmd1 | Desc1\n"
            yield "cmd2 | Desc2\n"
            yield "cmd3 | Desc3\n"

        mock_llm.generate = mock_generate
        ctx = ContextState()
        suggestions = await provider.suggest("cmd", ctx, mock_llm, limit=3)
        assert suggestions[0].score > suggestions[1].score
        assert suggestions[1].score > suggestions[2].score

    @pytest.mark.asyncio
    async def test_suggest_empty_response(self):
        provider = AISuggestionProvider()
        mock_llm = MagicMock()

        async def mock_generate(*args, **kwargs):
            yield ""

        mock_llm.generate = mock_generate
        ctx = ContextState()
        suggestions = await provider.suggest("ls", ctx, mock_llm)
        assert suggestions == []

    @pytest.mark.asyncio
    async def test_suggest_whitespace_only(self):
        provider = AISuggestionProvider()
        mock_llm = MagicMock()

        async def mock_generate(*args, **kwargs):
            yield "   \n"
            yield "\n"

        mock_llm.generate = mock_generate
        ctx = ContextState()
        suggestions = await provider.suggest("ls", ctx, mock_llm)
        assert suggestions == []


class TestSuggestionEngine:
    def test_init(self):
        engine = SuggestionEngine()
        assert engine.history_provider is not None
        assert engine.context_provider is not None
        assert engine.ai_provider is not None
        assert engine.enabled_sources == ["history", "context", "ai"]

    def test_add_to_history(self):
        engine = SuggestionEngine()
        engine.add_to_history("ls -la")
        assert "ls -la" in engine.history_provider._history

    def test_add_to_history_multiple(self):
        engine = SuggestionEngine()
        engine.add_to_history("ls -la")
        engine.add_to_history("cd /tmp")
        assert len(engine.history_provider._history) == 2

    def test_get_context_cwd(self):
        engine = SuggestionEngine()
        ctx = engine.get_context()
        assert ctx.cwd != ""

    def test_get_context_directory_contents(self):
        engine = SuggestionEngine()
        ctx = engine.get_context()
        assert isinstance(ctx.directory_contents, list)

    @patch("subprocess.run")
    def test_get_context_git_branch(self, mock_run):
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="main\n",
        )
        engine = SuggestionEngine()
        ctx = engine.get_context()
        assert ctx.git_branch == "main"

    @patch("subprocess.run")
    def test_get_context_git_dirty(self, mock_run):
        def side_effect(*args, **kwargs):
            result = MagicMock()
            if "rev-parse" in args[0]:
                result.returncode = 0
                result.stdout = "main\n"
            elif "status" in args[0]:
                result.returncode = 0
                result.stdout = "M file.py\n"
            return result

        mock_run.side_effect = side_effect
        engine = SuggestionEngine()
        ctx = engine.get_context()
        assert ctx.git_dirty is True

    @patch("subprocess.run")
    def test_get_context_git_not_dirty(self, mock_run):
        def side_effect(*args, **kwargs):
            result = MagicMock()
            if "rev-parse" in args[0]:
                result.returncode = 0
                result.stdout = "main\n"
            elif "status" in args[0]:
                result.returncode = 0
                result.stdout = ""
            return result

        mock_run.side_effect = side_effect
        engine = SuggestionEngine()
        ctx = engine.get_context()
        assert ctx.git_dirty is False

    @patch("subprocess.run")
    def test_get_context_git_error(self, mock_run):
        mock_run.side_effect = Exception("Git not found")
        engine = SuggestionEngine()
        ctx = engine.get_context()
        assert ctx.git_branch == ""
        assert ctx.git_dirty is False

    @patch("os.getcwd")
    def test_get_context_cwd_error(self, mock_getcwd):
        mock_getcwd.side_effect = Exception("Permission denied")
        engine = SuggestionEngine()
        ctx = engine.get_context()
        assert ctx.cwd == ""

    @patch("os.listdir")
    def test_get_context_listdir_error(self, mock_listdir):
        mock_listdir.side_effect = Exception("Permission denied")
        engine = SuggestionEngine()
        ctx = engine.get_context()
        assert ctx.directory_contents == []

    @pytest.mark.asyncio
    async def test_suggest_short_input(self):
        engine = SuggestionEngine()
        suggestions = await engine.suggest("l")
        assert suggestions == []

    @pytest.mark.asyncio
    async def test_suggest_empty_input(self):
        engine = SuggestionEngine()
        suggestions = await engine.suggest("")
        assert suggestions == []

    @pytest.mark.asyncio
    async def test_suggest_combines_sources(self):
        engine = SuggestionEngine()
        engine.add_to_history("ls -la")
        mock_llm = MagicMock()

        async def mock_generate(*args, **kwargs):
            yield "ls -l | List\n"

        mock_llm.generate = mock_generate
        suggestions = await engine.suggest("ls", mock_llm)
        assert len(suggestions) >= 1

    @pytest.mark.asyncio
    async def test_suggest_deduplicates(self):
        engine = SuggestionEngine()
        engine.add_to_history("ls -la")
        engine.add_to_history("ls -la")
        suggestions = await engine.suggest("ls")
        commands = [s.command for s in suggestions]
        assert commands.count("ls -la") <= 1

    @pytest.mark.asyncio
    async def test_suggest_sorts_by_score(self):
        engine = SuggestionEngine()
        engine.add_to_history("ls -la")
        engine.add_to_history("ls -la")
        engine.add_to_history("ls -la")
        engine.add_to_history("ls -l")
        suggestions = await engine.suggest("ls")
        assert suggestions[0].score >= suggestions[-1].score

    @pytest.mark.asyncio
    async def test_suggest_respects_max_suggestions(self):
        engine = SuggestionEngine()
        for i in range(20):
            engine.add_to_history(f"cmd_{i}")
        suggestions = await engine.suggest("cmd", max_suggestions=3)
        assert len(suggestions) <= 3

    @pytest.mark.asyncio
    async def test_suggest_respects_enabled_sources_history_only(self):
        engine = SuggestionEngine()
        engine.enabled_sources = ["history"]
        engine.add_to_history("ls -la")
        suggestions = await engine.suggest("ls")
        assert all(s.source == "history" for s in suggestions)

    @pytest.mark.asyncio
    async def test_suggest_respects_enabled_sources_context_only(self):
        engine = SuggestionEngine()
        engine.enabled_sources = ["context"]
        with patch("os.listdir", return_value=["script.py"]):
            suggestions = await engine.suggest("python")
        assert all(s.source == "context" for s in suggestions)

    @pytest.mark.asyncio
    async def test_suggest_respects_enabled_sources_ai_only(self):
        engine = SuggestionEngine()
        engine.enabled_sources = ["ai"]
        mock_llm = MagicMock()

        async def mock_generate(*args, **kwargs):
            yield "ls -la | List\n"

        mock_llm.generate = mock_generate
        suggestions = await engine.suggest("ls", mock_llm)
        assert all(s.source == "ai" for s in suggestions)

    @pytest.mark.asyncio
    async def test_suggest_ai_provider_error_graceful(self):
        engine = SuggestionEngine()
        engine.add_to_history("ls -la")
        mock_llm = MagicMock()

        async def mock_generate(*args, **kwargs):
            raise Exception("API error")

        mock_llm.generate = mock_generate
        suggestions = await engine.suggest("ls", mock_llm)
        assert len(suggestions) >= 1
        assert suggestions[0].source == "history"

    @pytest.mark.asyncio
    async def test_suggest_no_ai_provider(self):
        engine = SuggestionEngine()
        engine.add_to_history("ls -la")
        suggestions = await engine.suggest("ls", ai_provider=None)
        assert len(suggestions) >= 1

    @pytest.mark.asyncio
    async def test_suggest_ai_disabled(self):
        engine = SuggestionEngine()
        engine.enabled_sources = ["history", "context"]
        mock_llm = MagicMock()

        async def mock_generate(*args, **kwargs):
            yield "ls -la | List\n"

        mock_llm.generate = mock_generate
        engine.add_to_history("ls -la")
        suggestions = await engine.suggest("ls", mock_llm)
        assert all(s.source != "ai" for s in suggestions)

    @pytest.mark.asyncio
    async def test_suggest_history_disabled(self):
        engine = SuggestionEngine()
        engine.enabled_sources = ["context", "ai"]
        engine.add_to_history("ls -la")
        suggestions = await engine.suggest("ls")
        assert all(s.source != "history" for s in suggestions)

    @pytest.mark.asyncio
    async def test_suggest_context_disabled(self):
        engine = SuggestionEngine()
        engine.enabled_sources = ["history", "ai"]
        with patch("os.listdir", return_value=["script.py"]):
            suggestions = await engine.suggest("python")
        assert all(s.source != "context" for s in suggestions)

    @pytest.mark.asyncio
    async def test_suggest_all_sources_disabled(self):
        engine = SuggestionEngine()
        engine.enabled_sources = []
        engine.add_to_history("ls -la")
        suggestions = await engine.suggest("ls")
        assert suggestions == []

    @pytest.mark.asyncio
    async def test_suggest_complex_scenario(self):
        engine = SuggestionEngine()
        engine.add_to_history("git status")
        engine.add_to_history("git status")
        engine.add_to_history("git diff")

        with patch("subprocess.run") as mock_run:

            def side_effect(*args, **kwargs):
                result = MagicMock()
                if "rev-parse" in args[0]:
                    result.returncode = 0
                    result.stdout = "main\n"
                elif "status" in args[0]:
                    result.returncode = 0
                    result.stdout = "M file.py\n"
                return result

            mock_run.side_effect = side_effect

            mock_llm = MagicMock()

            async def mock_generate(*args, **kwargs):
                yield "git add . | Stage changes\n"

            mock_llm.generate = mock_generate

            suggestions = await engine.suggest("git", mock_llm, max_suggestions=5)
            assert len(suggestions) >= 1
            assert all(s.command.startswith("git") for s in suggestions)

    @pytest.mark.asyncio
    async def test_suggest_returns_list(self):
        engine = SuggestionEngine()
        suggestions = await engine.suggest("ls")
        assert isinstance(suggestions, list)

    @pytest.mark.asyncio
    async def test_suggest_all_suggestions_have_required_fields(self):
        engine = SuggestionEngine()
        engine.add_to_history("ls -la")
        suggestions = await engine.suggest("ls")
        for sugg in suggestions:
            assert sugg.command
            assert sugg.description
            assert sugg.source
            assert sugg.icon
            assert sugg.score >= 0.0
