"""Tests for HistoryIndex."""

import pytest

from config.history_index import HistoryEntry, HistoryIndex


@pytest.fixture
def index():
    return HistoryIndex()


@pytest.fixture
def populated_index():
    idx = HistoryIndex()
    entries = [
        HistoryEntry(1, "ls -la", "2024-01-01 10:00:00", 0),
        HistoryEntry(2, "cd /home/user", "2024-01-01 10:01:00", 0),
        HistoryEntry(3, "git status", "2024-01-01 10:02:00", 0),
        HistoryEntry(4, "git commit -m 'fix'", "2024-01-01 10:03:00", 0),
        HistoryEntry(5, "python main.py", "2024-01-01 10:04:00", 0),
        HistoryEntry(6, "docker ps", "2024-01-01 10:05:00", 0),
        HistoryEntry(7, "git push origin main", "2024-01-01 10:06:00", 0),
    ]
    for entry in entries:
        idx._add_to_index(entry)
    return idx


class TestHistoryIndex:
    def test_empty_index(self, index):
        assert index.count == 0
        assert index.search("foo") == []

    def test_add_to_index(self, index):
        entry = HistoryEntry(1, "ls -la", "2024-01-01", 0)
        index._add_to_index(entry)
        assert index.count == 1
        assert index._entries[1] == entry

    def test_search_exact_match(self, populated_index):
        results = populated_index.search("git status")
        assert len(results) == 1
        assert results[0].command == "git status"

    def test_search_partial_match(self, populated_index):
        results = populated_index.search("git")
        assert len(results) == 3
        commands = [r.command for r in results]
        assert "git push origin main" in commands
        assert "git commit -m 'fix'" in commands
        assert "git status" in commands

    def test_search_case_insensitive(self, populated_index):
        results = populated_index.search("GIT")
        assert len(results) == 3

    def test_search_empty_query(self, populated_index):
        results = populated_index.search("")
        assert len(results) == 7

    def test_search_no_match(self, populated_index):
        results = populated_index.search("nonexistent")
        assert results == []

    def test_search_limit(self, populated_index):
        results = populated_index.search("", limit=3)
        assert len(results) == 3

    def test_search_returns_newest_first(self, populated_index):
        results = populated_index.search("git")
        ids = [r.id for r in results]
        assert ids == sorted(ids, reverse=True)

    def test_search_prefix(self, populated_index):
        results = populated_index.search_prefix("git")
        assert len(results) == 3
        for r in results:
            assert r.command.startswith("git")

    def test_search_prefix_case_insensitive(self, populated_index):
        results = populated_index.search_prefix("GIT")
        assert len(results) == 3

    def test_search_prefix_no_match(self, populated_index):
        results = populated_index.search_prefix("xyz")
        assert results == []

    def test_get_recent(self, populated_index):
        results = populated_index.get_recent(limit=3)
        assert len(results) == 3
        assert results[-1].id == 7

    def test_get_recent_oldest_first(self, populated_index):
        results = populated_index.get_recent(limit=3)
        ids = [r.id for r in results]
        assert ids == sorted(ids)

    def test_clear(self, populated_index):
        populated_index.clear()
        assert populated_index.count == 0
        assert populated_index.search("git") == []

    def test_tokenize(self, index):
        tokens = index._tokenize("git commit -m message")
        assert "git" in tokens
        assert "commit" in tokens
        assert "message" in tokens

    def test_tokenize_paths(self, index):
        tokens = index._tokenize("cd /home/user/projects")
        assert "home" in tokens
        assert "user" in tokens
        assert "projects" in tokens


class TestHistoryIndexWithStorage:
    @pytest.fixture
    def storage(self, mock_home, tmp_path):
        from config.storage import StorageManager

        db_path = tmp_path / "test.db"
        return StorageManager(db_path=db_path)

    @pytest.fixture
    def index_with_storage(self, storage):
        storage.add_history("ls -la")
        storage.add_history("git status")
        storage.add_history("python main.py")
        return HistoryIndex.from_storage(storage)

    def test_from_storage(self, index_with_storage):
        assert index_with_storage.count == 3

    def test_rebuild_index(self, storage):
        storage.add_history("echo hello")
        index = HistoryIndex(_storage=storage)
        count = index.rebuild_index()
        assert count == 1
        assert index.count == 1

    def test_add_entry(self, storage):
        index = HistoryIndex.from_storage(storage)
        initial_count = index.count
        entry_id = index.add_entry("new command")
        assert entry_id is not None
        assert index.count == initial_count + 1
        results = index.search("new command")
        assert len(results) == 1

    def test_add_entry_empty(self, storage):
        index = HistoryIndex.from_storage(storage)
        entry_id = index.add_entry("   ")
        assert entry_id is None

    def test_add_entry_no_storage(self, index):
        entry_id = index.add_entry("test")
        assert entry_id is None

    def test_search_synced_with_storage(self, index_with_storage):
        results = index_with_storage.search("git")
        assert len(results) == 1
        assert results[0].command == "git status"
