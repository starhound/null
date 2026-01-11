import pytest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch, MagicMock

from managers.profiles import AgentProfile, ProfileManager


class TestAgentProfile:
    def test_profile_creation_minimal(self):
        profile = AgentProfile(
            id="test",
            name="Test Profile",
            description="A test profile",
        )
        assert profile.id == "test"
        assert profile.name == "Test Profile"
        assert profile.icon == "\U0001f916"
        assert profile.temperature == 0.7
        assert profile.max_tokens is None
        assert profile.allowed_tools is None
        assert profile.blocked_tools == []
        assert profile.source == "local"

    def test_profile_creation_full(self):
        profile = AgentProfile(
            id="full",
            name="Full Profile",
            description="Full test",
            icon="\U0001f4a1",
            system_prompt="You are helpful",
            temperature=0.5,
            max_tokens=1000,
            allowed_tools=["read_file", "write_file"],
            blocked_tools=["run_command"],
            auto_include_files=["*.py"],
            context_instructions="Check imports",
            require_approval=["write_file"],
            max_iterations=5,
            tags=["python", "test"],
            source="builtin",
        )
        assert profile.id == "full"
        assert profile.temperature == 0.5
        assert profile.max_tokens == 1000
        assert profile.allowed_tools is not None
        assert "read_file" in profile.allowed_tools
        assert "run_command" in profile.blocked_tools
        assert profile.max_iterations == 5
        assert "python" in profile.tags

    def test_profile_to_dict(self):
        profile = AgentProfile(
            id="test",
            name="Test",
            description="Test",
            tags=["tag1"],
        )
        result = profile.to_dict()

        assert result["id"] == "test"
        assert result["name"] == "Test"
        assert isinstance(result["created_at"], str)
        assert "tag1" in result["tags"]

    def test_profile_from_dict(self):
        data = {
            "id": "from_dict",
            "name": "From Dict",
            "description": "Created from dict",
            "icon": "\U0001f916",
            "system_prompt": "",
            "temperature": 0.7,
            "max_tokens": None,
            "allowed_tools": None,
            "blocked_tools": [],
            "auto_include_files": [],
            "context_instructions": "",
            "require_approval": [],
            "max_iterations": 10,
            "created_at": "2025-01-10T10:00:00",
            "tags": [],
            "source": "local",
        }
        profile = AgentProfile.from_dict(data)

        assert profile.id == "from_dict"
        assert profile.name == "From Dict"
        assert isinstance(profile.created_at, datetime)


class TestProfileManager:
    @pytest.fixture
    def temp_profiles_dir(self, tmp_path):
        return tmp_path / "profiles"

    @pytest.fixture
    def manager(self, temp_profiles_dir):
        return ProfileManager(profiles_dir=temp_profiles_dir)

    def test_manager_initialization(self, manager, temp_profiles_dir):
        assert manager.profiles_dir == temp_profiles_dir
        assert manager.profiles == {}
        assert manager.active_profile_id is None

    def test_initialize_creates_directory(self, manager, temp_profiles_dir):
        assert not temp_profiles_dir.exists()
        manager.initialize()
        assert temp_profiles_dir.exists()

    def test_initialize_creates_builtin_profiles(self, manager):
        manager.initialize()
        assert "default" in manager.profiles
        assert "frontend" in manager.profiles
        assert "backend" in manager.profiles
        assert "devops" in manager.profiles
        assert "security" in manager.profiles

    def test_save_profile(self, manager, temp_profiles_dir):
        manager.initialize()
        profile = AgentProfile(
            id="custom",
            name="Custom Profile",
            description="A custom profile",
        )

        filepath = manager.save_profile(profile)

        assert filepath.exists()
        assert "custom" in manager.profiles
        assert manager.profiles["custom"].name == "Custom Profile"

    def test_get_profile(self, manager):
        manager.initialize()
        profile = manager.get_profile("default")
        assert profile is not None
        assert profile.name == "Default Assistant"

    def test_get_profile_not_found(self, manager):
        manager.initialize()
        profile = manager.get_profile("nonexistent")
        assert profile is None

    def test_activate_profile(self, manager):
        manager.initialize()
        result = manager.activate("frontend")
        assert result is True
        assert manager.active_profile_id == "frontend"

    def test_activate_nonexistent_profile(self, manager):
        manager.initialize()
        result = manager.activate("nonexistent")
        assert result is False
        assert manager.active_profile_id is None

    def test_active_profile_property(self, manager):
        manager.initialize()
        assert manager.active_profile is None

        manager.activate("backend")
        assert manager.active_profile is not None
        assert manager.active_profile.id == "backend"

    def test_list_profiles(self, manager):
        manager.initialize()
        profiles = manager.list_profiles()

        assert len(profiles) >= 5
        names = [p.name for p in profiles]
        assert "Default Assistant" in names
        assert "Frontend Developer" in names

    def test_list_profiles_with_tag_filter(self, manager):
        manager.initialize()
        profiles = manager.list_profiles(tags=["python"])
        assert len(profiles) >= 1
        assert all("python" in p.tags or "backend" in p.tags for p in profiles)

    def test_delete_profile_local(self, manager):
        manager.initialize()
        local_profile = AgentProfile(
            id="deleteme",
            name="Delete Me",
            description="To be deleted",
            source="local",
        )
        manager.save_profile(local_profile)

        result = manager.delete_profile("deleteme")

        assert result is True
        assert "deleteme" not in manager.profiles

    def test_delete_profile_builtin_fails(self, manager):
        manager.initialize()
        result = manager.delete_profile("default")
        assert result is False
        assert "default" in manager.profiles

    def test_delete_profile_nonexistent(self, manager):
        manager.initialize()
        result = manager.delete_profile("nonexistent")
        assert result is False

    def test_export_profile(self, manager):
        manager.initialize()
        yaml_content = manager.export_profile("default")

        assert yaml_content is not None
        assert "id: default" in yaml_content
        assert "name: Default Assistant" in yaml_content

    def test_export_nonexistent_profile(self, manager):
        manager.initialize()
        result = manager.export_profile("nonexistent")
        assert result is None

    def test_import_profile(self, manager):
        manager.initialize()
        yaml_content = """
id: imported
name: Imported Profile
description: An imported profile
icon: "\U0001f916"
system_prompt: ""
temperature: 0.7
max_tokens: null
allowed_tools: null
blocked_tools: []
auto_include_files: []
context_instructions: ""
require_approval: []
max_iterations: 10
created_at: "2025-01-10T10:00:00"
tags: []
source: local
"""
        profile = manager.import_profile(yaml_content)

        assert profile is not None
        assert profile.id == "imported"
        assert "imported" in manager.profiles

    def test_import_invalid_yaml(self, manager):
        manager.initialize()
        result = manager.import_profile("not: valid: yaml: {")

    def test_duplicate_profile(self, manager):
        manager.initialize()
        new_profile = manager.duplicate_profile(
            source_id="frontend",
            new_id="frontend_custom",
            new_name="Custom Frontend",
        )

        assert new_profile is not None
        assert new_profile.id == "frontend_custom"
        assert new_profile.name == "Custom Frontend"
        assert new_profile.source == "local"
        assert "frontend_custom" in manager.profiles

    def test_duplicate_nonexistent_profile(self, manager):
        manager.initialize()
        result = manager.duplicate_profile(
            source_id="nonexistent",
            new_id="new",
            new_name="New",
        )
        assert result is None

    def test_load_profiles_from_disk(self, manager, temp_profiles_dir):
        manager.initialize()
        profile = AgentProfile(
            id="ondisk",
            name="On Disk",
            description="Saved to disk",
        )
        manager.save_profile(profile)

        new_manager = ProfileManager(profiles_dir=temp_profiles_dir)
        new_manager.load_profiles()

        assert "ondisk" in new_manager.profiles
        assert new_manager.profiles["ondisk"].name == "On Disk"
