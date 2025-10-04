"""
Tests for Workshop configuration management
"""
import pytest
import json
from pathlib import Path
from src.config import WorkshopConfig


@pytest.fixture
def temp_config(tmp_path):
    """Create a temporary config file"""
    config_path = tmp_path / "config.json"
    return WorkshopConfig(config_path)


def test_create_default_config(temp_config):
    """Test creating default configuration"""
    assert temp_config._config["version"] == "1.0"
    assert "projects" in temp_config._config
    assert "global" in temp_config._config
    assert temp_config._config["default_mode"] == "per-project"


def test_config_file_created(tmp_path):
    """Test that config file is created on disk"""
    config_path = tmp_path / "config.json"
    config = WorkshopConfig(config_path)

    assert config_path.exists()

    with open(config_path) as f:
        data = json.load(f)
        assert data["version"] == "1.0"


def test_register_project(temp_config, tmp_path):
    """Test registering a new project"""
    project_path = tmp_path / "test_project"
    project_path.mkdir()

    result = temp_config.register_project(project_path)

    assert "database" in result
    assert "jsonl_path" in result
    assert "auto_import" in result

    projects = temp_config.list_projects()
    assert str(project_path.resolve()) in projects


def test_register_project_with_custom_paths(temp_config, tmp_path):
    """Test registering project with custom database and JSONL paths"""
    project_path = tmp_path / "test_project"
    db_path = tmp_path / "custom.db"
    jsonl_path = tmp_path / "jsonl"

    result = temp_config.register_project(
        project_path,
        database_path=db_path,
        jsonl_path=jsonl_path
    )

    assert result["database"] == str(db_path)
    assert result["jsonl_path"] == str(jsonl_path)


def test_get_project_config(temp_config, tmp_path):
    """Test retrieving project configuration"""
    project_path = tmp_path / "test_project"
    temp_config.register_project(project_path)

    config = temp_config.get_project_config(project_path)

    assert config is not None
    assert "database" in config
    assert "jsonl_path" in config


def test_get_nonexistent_project(temp_config, tmp_path):
    """Test getting config for non-registered project"""
    project_path = tmp_path / "nonexistent"

    config = temp_config.get_project_config(project_path)

    assert config is None


def test_unregister_project(temp_config, tmp_path):
    """Test removing a project"""
    project_path = tmp_path / "test_project"
    temp_config.register_project(project_path)

    result = temp_config.unregister_project(project_path)

    assert result is True
    assert str(project_path.resolve()) not in temp_config.list_projects()


def test_unregister_nonexistent_project(temp_config, tmp_path):
    """Test removing a project that doesn't exist"""
    project_path = tmp_path / "nonexistent"

    result = temp_config.unregister_project(project_path)

    assert result is False


def test_list_projects_empty(temp_config):
    """Test listing projects when none registered"""
    projects = temp_config.list_projects()

    assert projects == {}


def test_list_multiple_projects(temp_config, tmp_path):
    """Test listing multiple registered projects"""
    project1 = tmp_path / "project1"
    project2 = tmp_path / "project2"

    temp_config.register_project(project1)
    temp_config.register_project(project2)

    projects = temp_config.list_projects()

    assert len(projects) == 2
    assert str(project1.resolve()) in projects
    assert str(project2.resolve()) in projects


def test_global_config(temp_config):
    """Test global configuration"""
    global_config = temp_config.get_global_config()

    assert "database" in global_config
    assert "enabled" in global_config
    assert global_config["enabled"] is False


def test_set_global_enabled(temp_config):
    """Test enabling/disabling global mode"""
    temp_config.set_global_enabled(True)

    assert temp_config.get_global_config()["enabled"] is True

    temp_config.set_global_enabled(False)

    assert temp_config.get_global_config()["enabled"] is False


def test_validate_valid_config(temp_config, tmp_path):
    """Test validating a valid configuration"""
    project_path = tmp_path / "project"
    project_path.mkdir()
    (project_path / ".workshop").mkdir()

    temp_config.register_project(project_path)

    result = temp_config.validate()

    assert result["valid"] is True
    assert len(result["errors"]) == 0


def test_validate_nonexistent_project_path(temp_config, tmp_path):
    """Test validation warns about nonexistent project paths"""
    project_path = tmp_path / "nonexistent"
    temp_config.register_project(project_path)

    result = temp_config.validate()

    assert len(result["warnings"]) > 0
    assert any("does not exist" in w for w in result["warnings"])


def test_get_raw_config(temp_config):
    """Test getting raw config dictionary"""
    raw = temp_config.get_raw_config()

    assert isinstance(raw, dict)
    assert "version" in raw
    assert "projects" in raw


def test_update_from_dict(temp_config):
    """Test updating config from dictionary"""
    new_config = {
        "version": "1.0",
        "default_mode": "global",
        "projects": {},
        "global": {"enabled": True, "database": "/custom/path.db"}
    }

    temp_config.update_from_dict(new_config)

    assert temp_config._config["default_mode"] == "global"
    assert temp_config._config["global"]["enabled"] is True


def test_update_from_dict_invalid(temp_config):
    """Test that invalid config raises error"""
    invalid_config = {"no_version": "oops"}

    with pytest.raises(ValueError, match="version"):
        temp_config.update_from_dict(invalid_config)


def test_update_from_dict_invalid_projects_type(temp_config):
    """Test that invalid projects type raises error"""
    invalid_config = {
        "version": "1.0",
        "projects": "not a dict"
    }

    with pytest.raises(ValueError, match="projects"):
        temp_config.update_from_dict(invalid_config)


def test_corrupted_config_file_recovery(tmp_path):
    """Test that corrupted config file is backed up and recreated"""
    config_path = tmp_path / "config.json"

    # Write corrupted JSON
    with open(config_path, 'w') as f:
        f.write("{invalid json")

    # Should create backup and new config
    config = WorkshopConfig(config_path)

    assert config_path.exists()
    assert (tmp_path / "config.json.backup").exists()
    assert config._config["version"] == "1.0"


def test_config_persistence(tmp_path):
    """Test that config persists across instances"""
    config_path = tmp_path / "config.json"
    project_path = tmp_path / "project"

    # First instance
    config1 = WorkshopConfig(config_path)
    config1.register_project(project_path)

    # Second instance should load same data
    config2 = WorkshopConfig(config_path)

    assert str(project_path.resolve()) in config2.list_projects()
