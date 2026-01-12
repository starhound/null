from pathlib import Path
from unittest.mock import patch

from nullrc import NullrcManager, ProjectConfig, get_nullrc_manager, get_project_config


class TestProjectConfig:
    def test_default_values(self):
        config = ProjectConfig()
        assert config.provider is None
        assert config.model is None
        assert config.system_prompt is None
        assert config.temperature is None
        assert config.shell is None
        assert config.env == {}
        assert config.context_files == []
        assert config.ignore_patterns == []
        assert config.aliases == {}
        assert config.on_start == []

    def test_to_dict_filters_none_and_empty(self):
        config = ProjectConfig(provider="ollama", model="llama3")
        result = config.to_dict()
        assert result == {"provider": "ollama", "model": "llama3"}
        assert "env" not in result
        assert "context_files" not in result

    def test_to_dict_includes_populated_values(self):
        config = ProjectConfig(
            provider="openai",
            model="gpt-4",
            env={"API_KEY": "secret"},
            context_files=["README.md"],
        )
        result = config.to_dict()
        assert result["provider"] == "openai"
        assert result["model"] == "gpt-4"
        assert result["env"] == {"API_KEY": "secret"}
        assert result["context_files"] == ["README.md"]

    def test_from_dict_creates_config(self):
        data = {
            "provider": "anthropic",
            "model": "claude-3",
            "temperature": 0.7,
            "aliases": {"test": "pytest"},
        }
        config = ProjectConfig.from_dict(data)
        assert config.provider == "anthropic"
        assert config.model == "claude-3"
        assert config.temperature == 0.7
        assert config.aliases == {"test": "pytest"}

    def test_from_dict_ignores_unknown_keys(self):
        data = {"provider": "ollama", "unknown_field": "value"}
        config = ProjectConfig.from_dict(data)
        assert config.provider == "ollama"
        assert not hasattr(config, "unknown_field")


class TestNullrcManager:
    def test_init(self):
        manager = NullrcManager()
        assert manager._cache == {}
        assert manager._file_cache == {}

    def test_nullrc_names(self):
        assert ".nullrc" in NullrcManager.NULLRC_NAMES
        assert ".nullrc.json" in NullrcManager.NULLRC_NAMES
        assert "nullrc.json" in NullrcManager.NULLRC_NAMES

    def test_find_nullrc_in_current_dir(self, tmp_path):
        nullrc_path = tmp_path / ".nullrc"
        nullrc_path.write_text('{"provider": "test"}')
        manager = NullrcManager()
        result = manager.find_nullrc(tmp_path)
        assert result == nullrc_path

    def test_find_nullrc_json_variant(self, tmp_path):
        nullrc_path = tmp_path / ".nullrc.json"
        nullrc_path.write_text('{"provider": "test"}')
        manager = NullrcManager()
        result = manager.find_nullrc(tmp_path)
        assert result == nullrc_path

    def test_find_nullrc_in_parent_dir(self, tmp_path):
        nullrc_path = tmp_path / ".nullrc"
        nullrc_path.write_text('{"provider": "test"}')
        child_dir = tmp_path / "subdir"
        child_dir.mkdir()
        manager = NullrcManager()
        result = manager.find_nullrc(child_dir)
        assert result == nullrc_path

    def test_find_nullrc_returns_none_when_not_found(self, tmp_path):
        manager = NullrcManager()
        with patch.object(Path, "home", return_value=tmp_path):
            result = manager.find_nullrc(tmp_path)
        assert result is None

    def test_load_returns_none_when_no_file(self, tmp_path):
        manager = NullrcManager()
        with patch.object(Path, "home", return_value=tmp_path):
            result = manager.load(tmp_path)
        assert result is None

    def test_load_parses_valid_json(self, tmp_path):
        nullrc_path = tmp_path / ".nullrc"
        nullrc_path.write_text('{"provider": "ollama", "model": "llama3"}')
        manager = NullrcManager()
        result = manager.load(tmp_path)
        assert result is not None
        assert result.provider == "ollama"
        assert result.model == "llama3"

    def test_load_caches_result(self, tmp_path):
        nullrc_path = tmp_path / ".nullrc"
        nullrc_path.write_text('{"provider": "test"}')
        manager = NullrcManager()
        result1 = manager.load(tmp_path)
        result2 = manager.load(tmp_path)
        assert result1 is result2

    def test_load_returns_none_on_invalid_json(self, tmp_path):
        nullrc_path = tmp_path / ".nullrc"
        nullrc_path.write_text("not valid json")
        manager = NullrcManager()
        result = manager.load(tmp_path)
        assert result is None

    def test_get_project_root(self, tmp_path):
        nullrc_path = tmp_path / ".nullrc"
        nullrc_path.write_text('{"provider": "test"}')
        manager = NullrcManager()
        result = manager.get_project_root(tmp_path)
        assert result == tmp_path

    def test_get_project_root_returns_none_when_no_nullrc(self, tmp_path):
        manager = NullrcManager()
        with patch.object(Path, "home", return_value=tmp_path):
            result = manager.get_project_root(tmp_path)
        assert result is None

    def test_create_default(self, tmp_path):
        manager = NullrcManager()
        result = manager.create_default(tmp_path)
        assert result == tmp_path / ".nullrc"
        assert result.exists()
        content = result.read_text()
        assert "context_files" in content
        assert "aliases" in content

    def test_apply_to_config_provider(self):
        manager = NullrcManager()
        base = {}
        project = ProjectConfig(provider="ollama")
        result = manager.apply_to_config(base, project)
        assert result["ai"]["provider"] == "ollama"

    def test_apply_to_config_model(self):
        manager = NullrcManager()
        base = {"ai": {"provider": "openai"}}
        project = ProjectConfig(model="gpt-4")
        result = manager.apply_to_config(base, project)
        assert result["ai"]["model"] == "gpt-4"
        assert result["ai"]["provider"] == "openai"

    def test_apply_to_config_shell(self):
        manager = NullrcManager()
        base = {}
        project = ProjectConfig(shell="/bin/zsh")
        result = manager.apply_to_config(base, project)
        assert result["shell"] == "/bin/zsh"

    def test_apply_to_config_temperature(self):
        manager = NullrcManager()
        base = {}
        project = ProjectConfig(temperature=0.5)
        result = manager.apply_to_config(base, project)
        assert result["ai"]["temperature"] == 0.5

    def test_apply_to_config_does_not_modify_original(self):
        manager = NullrcManager()
        base = {"existing": "value"}
        project = ProjectConfig(provider="test")
        result = manager.apply_to_config(base, project)
        assert "ai" not in base
        assert "ai" in result

    def test_get_context_files_with_direct_paths(self, tmp_path):
        nullrc_path = tmp_path / ".nullrc"
        nullrc_path.write_text('{"context_files": ["README.md"]}')
        readme = tmp_path / "README.md"
        readme.write_text("# Test")
        manager = NullrcManager()
        config = manager.load(tmp_path)
        assert config is not None
        with patch.object(manager, "get_project_root", return_value=tmp_path):
            files = manager.get_context_files(config)
        assert readme in files

    def test_get_context_files_with_glob_patterns(self, tmp_path):
        nullrc_path = tmp_path / ".nullrc"
        nullrc_path.write_text('{"context_files": ["*.py"]}')
        py_file = tmp_path / "test.py"
        py_file.write_text("# Python")
        manager = NullrcManager()
        config = manager.load(tmp_path)
        assert config is not None
        with patch.object(manager, "get_project_root", return_value=tmp_path):
            files = manager.get_context_files(config)
        assert py_file in files

    def test_get_context_files_skips_missing(self, tmp_path):
        nullrc_path = tmp_path / ".nullrc"
        nullrc_path.write_text('{"context_files": ["missing.md"]}')
        manager = NullrcManager()
        config = manager.load(tmp_path)
        assert config is not None
        with patch.object(manager, "get_project_root", return_value=tmp_path):
            files = manager.get_context_files(config)
        assert files == []

    def test_reload_clears_cache(self, tmp_path):
        nullrc_path = tmp_path / ".nullrc"
        nullrc_path.write_text('{"provider": "test"}')
        manager = NullrcManager()
        manager.load(tmp_path)
        assert len(manager._cache) > 0
        manager.reload()
        assert manager._cache == {}
        assert manager._file_cache == {}


class TestSingletonFunctions:
    def test_get_nullrc_manager_returns_singleton(self):
        import nullrc

        nullrc._nullrc_manager = None
        manager1 = get_nullrc_manager()
        manager2 = get_nullrc_manager()
        assert manager1 is manager2

    def test_get_project_config_delegates_to_manager(self, tmp_path):
        import nullrc

        nullrc._nullrc_manager = None
        nullrc_path = tmp_path / ".nullrc"
        nullrc_path.write_text('{"provider": "singleton_test"}')
        with patch("nullrc.NullrcManager.find_nullrc", return_value=nullrc_path):
            result = get_project_config()
        assert result is not None
        assert result.provider == "singleton_test"
