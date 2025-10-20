"""
Tests for storage/base.py workspace detection and database initialization
"""
import tempfile
import shutil
from pathlib import Path
import pytest
from unittest.mock import patch, MagicMock

from src.storage.base import DatabaseManager


@pytest.fixture
def temp_dir():
    """Create a temporary directory for testing"""
    temp = Path(tempfile.mkdtemp())
    yield temp
    shutil.rmtree(temp, ignore_errors=True)


class TestDatabaseManagerSQLite:
    """Tests for SQLite (OSS) mode database manager"""

    def test_init_with_explicit_workspace(self, temp_dir):
        """Test initialization with explicit workspace directory"""
        workspace = temp_dir / ".workshop"
        workspace.mkdir()

        db_manager = DatabaseManager(workspace_dir=workspace)

        assert db_manager.workspace_dir == workspace
        assert db_manager.db_file == workspace / "workshop.db"
        assert not db_manager.multi_tenant_mode
        assert db_manager.user_id is None
        assert db_manager.project_id is None

    def test_init_creates_workspace(self, temp_dir):
        """Test that initialization creates workspace if it doesn't exist"""
        workspace = temp_dir / ".workshop"
        # Don't create it beforehand

        db_manager = DatabaseManager(workspace_dir=workspace)

        assert workspace.exists()
        assert db_manager.db_file.parent == workspace

    def test_workspace_detection_with_env_var(self, temp_dir, monkeypatch):
        """Test workspace detection uses WORKSHOP_DIR environment variable"""
        workspace = temp_dir / "custom_workspace"
        workspace.mkdir()
        monkeypatch.setenv('WORKSHOP_DIR', str(workspace))

        # Don't provide workspace_dir to trigger detection
        with patch('src.storage.base.find_project_root') as mock_find:
            # Make find_project_root return None to use env var path
            mock_find.return_value = (None, "No project detected", 0)

            db_manager = DatabaseManager()

            # Should use the env var path (resolve both for comparison due to macOS symlinks)
            assert db_manager.workspace_dir.resolve() == workspace.resolve()

    def test_database_file_created(self, temp_dir):
        """Test that database file is created on initialization"""
        workspace = temp_dir / ".workshop"
        workspace.mkdir()

        db_manager = DatabaseManager(workspace_dir=workspace)

        # Database file should exist after init
        assert db_manager.db_file.exists()

    def test_session_creation(self, temp_dir):
        """Test that we can create database sessions"""
        workspace = temp_dir / ".workshop"
        workspace.mkdir()

        db_manager = DatabaseManager(workspace_dir=workspace)
        session = db_manager.get_session()

        assert session is not None
        session.close()


class TestDatabaseManagerPostgreSQL:
    """Tests for PostgreSQL (Cloud) mode database manager"""

    def test_multi_tenant_mode_requires_credentials(self):
        """Test that multi-tenant mode requires user_id and project_name"""
        with pytest.raises(ValueError, match="user_id and project_name required"):
            DatabaseManager(
                connection_string="postgresql://localhost/test",
                user_id=None,
                project_name="test"
            )

        with pytest.raises(ValueError, match="user_id and project_name required"):
            DatabaseManager(
                connection_string="postgresql://localhost/test",
                user_id="user123",
                project_name=None
            )

    @patch('src.storage.base.create_engine')
    @patch('src.storage.base.DatabaseManager._init_db')
    @patch('src.storage.base.DatabaseManager._ensure_user_and_project')
    def test_multi_tenant_mode_initialization(self, mock_ensure, mock_init, mock_engine):
        """Test multi-tenant mode sets up correctly"""
        mock_engine_instance = MagicMock()
        mock_engine.return_value = mock_engine_instance

        db_manager = DatabaseManager(
            connection_string="postgresql://localhost/testdb",
            user_id="user123",
            project_name="my_project"
        )

        assert db_manager.multi_tenant_mode
        assert db_manager.user_id == "user123"
        assert db_manager.project_name == "my_project"
        assert db_manager.workspace_dir is None

        # Should have called ensure_user_and_project
        mock_ensure.assert_called_once()


class TestWorkspaceDetection:
    """Tests for workspace detection logic"""

    def test_env_var_override(self, temp_dir, monkeypatch):
        """Test WORKSHOP_DIR environment variable overrides other detection"""
        workspace = temp_dir / "env_workspace"
        workspace.mkdir()
        monkeypatch.setenv('WORKSHOP_DIR', str(workspace))

        with patch('src.storage.base.find_project_root') as mock_find:
            mock_find.return_value = (temp_dir, "Test project", 100)

            db_manager = DatabaseManager()

            # Should use env var, not project root (resolve both for macOS symlinks)
            assert db_manager.workspace_dir.resolve() == workspace.resolve()

    def test_auto_init_mode(self, temp_dir, monkeypatch):
        """Test auto-init mode (non-interactive) creates workspace automatically"""
        project_root = temp_dir
        monkeypatch.setenv('WORKSHOP_AUTO_INIT', '1')

        with patch('src.storage.base.find_project_root') as mock_find:
            mock_find.return_value = (project_root, "Test project", 100)

            with patch('src.storage.base.WorkshopConfig') as mock_config:
                mock_config_instance = MagicMock()
                mock_config.return_value = mock_config_instance
                mock_config_instance.get_project_config.return_value = None

                db_manager = DatabaseManager()

                # Should create workspace at project root
                expected_workspace = project_root / ".workshop"
                assert db_manager.workspace_dir == expected_workspace
                assert expected_workspace.exists()

                # Should register in config
                mock_config_instance.register_project.assert_called_once()

    def test_existing_config_used(self, temp_dir, monkeypatch):
        """Test that existing config database path is used"""
        workspace = temp_dir / "configured_workspace"
        workspace.mkdir()
        db_file = workspace / "workshop.db"

        with patch('src.storage.base.find_project_root') as mock_find:
            mock_find.return_value = (temp_dir, "Test project", 100)

            with patch('src.storage.base.WorkshopConfig') as mock_config:
                mock_config_instance = MagicMock()
                mock_config.return_value = mock_config_instance
                mock_config_instance.get_project_config.return_value = {
                    'database': str(db_file)
                }

                db_manager = DatabaseManager()

                # Should use the configured workspace
                assert db_manager.workspace_dir == workspace

    def test_no_project_detected_uses_global(self, monkeypatch):
        """Test that when no project is detected, uses global workspace"""
        with patch('src.storage.base.find_project_root') as mock_find:
            mock_find.return_value = (None, "No project", 0)

            # Remove WORKSHOP_DIR if set
            monkeypatch.delenv('WORKSHOP_DIR', raising=False)

            db_manager = DatabaseManager()

            # Should use global workspace
            expected = Path.home() / ".workshop" / "global"
            assert db_manager.workspace_dir == expected


class TestDatabaseInitialization:
    """Tests for database schema initialization"""

    def test_schema_version_set(self, temp_dir):
        """Test that schema version is set during initialization"""
        workspace = temp_dir / ".workshop"
        workspace.mkdir()

        db_manager = DatabaseManager(workspace_dir=workspace)

        # Query schema version from config table
        from src.models import Config
        with db_manager.get_session() as session:
            version_config = session.query(Config).filter_by(key='schema_version').first()
            assert version_config is not None
            assert version_config.value == '4'  # SQLAlchemy version (v4 adds raw_messages)

    def test_tables_created(self, temp_dir):
        """Test that all required tables are created"""
        workspace = temp_dir / ".workshop"
        workspace.mkdir()

        db_manager = DatabaseManager(workspace_dir=workspace)

        # Tables should exist
        from sqlalchemy import inspect
        inspector = inspect(db_manager.engine)
        tables = inspector.get_table_names()

        # Should have key tables
        assert 'entries' in tables
        assert 'preferences' in tables
        assert 'sessions' in tables
        assert 'config' in tables
