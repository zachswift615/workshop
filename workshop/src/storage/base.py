"""
Base database connection and initialization for Workshop storage.

Supports both SQLite (OSS) and PostgreSQL (Cloud) via SQLAlchemy.
"""
import os
from pathlib import Path
from typing import Optional
import click

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Import models
import sys
models_path = Path(__file__).parent.parent
sys.path.insert(0, str(models_path))
from models import Base

from ..config import WorkshopConfig
from ..project_detection import find_project_root, validate_workspace_path


class DatabaseManager:
    """Manages database connections for both SQLite and PostgreSQL."""

    def __init__(
        self,
        workspace_dir: Optional[Path] = None,
        connection_string: Optional[str] = None,
        user_id: Optional[str] = None,
        project_name: Optional[str] = None,
        echo: bool = False
    ):
        """
        Initialize database connection.

        Args:
            workspace_dir: For OSS mode - workspace directory (auto-detects if None)
            connection_string: For Cloud mode - database URL (e.g., postgresql://...)
            user_id: For Cloud mode - user identifier (API key)
            project_name: For Cloud mode - project name
            echo: Echo SQL queries (debug mode)
        """
        self.multi_tenant_mode = connection_string is not None

        if self.multi_tenant_mode:
            # Cloud mode: PostgreSQL multi-tenant
            if not user_id or not project_name:
                raise ValueError("user_id and project_name required for multi-tenant mode")

            self.engine = create_engine(connection_string, echo=echo)
            self.user_id = user_id
            self.project_name = project_name
            self.project_id = None  # Will be set after ensuring project exists
            self._workspace_dir = None

        else:
            # OSS mode: SQLite file per project
            self._workspace_dir = Path(workspace_dir) if workspace_dir else self._find_workspace()
            self.db_file = self._workspace_dir / "workshop.db"

            # Ensure workspace exists
            self._workspace_dir.mkdir(parents=True, exist_ok=True)

            # Auto-migrate schema if needed (for backward compatibility)
            from ..migrate import auto_migrate_if_needed
            auto_migrate_if_needed(self._workspace_dir)

            # Create SQLite engine with proper settings
            self.engine = create_engine(
                f"sqlite:///{self.db_file}",
                echo=echo,
                connect_args={"check_same_thread": False},
                poolclass=StaticPool
            )

            # Enable foreign keys for SQLite
            @event.listens_for(self.engine, "connect")
            def set_sqlite_pragma(dbapi_conn, connection_record):
                cursor = dbapi_conn.cursor()
                cursor.execute("PRAGMA foreign_keys=ON")
                cursor.close()

            self.user_id = None
            self.project_name = None
            self.project_id = None  # Single-tenant mode

        # Create session factory
        self.SessionLocal = sessionmaker(bind=self.engine, expire_on_commit=False)

        # Initialize database schema
        self._init_db()

        # For multi-tenant mode, ensure user and project exist
        if self.multi_tenant_mode:
            self._ensure_user_and_project()

    def _find_workspace(self) -> Path:
        """
        Find or create the appropriate workspace directory.

        Priority order:
        1. WORKSHOP_DIR environment variable (override)
        2. Config file (~/.workshop/config.json) for this project
        3. Existing .workshop/ directory (backward compatibility)
        4. Prompt user for workspace location
        """
        # Check for override
        if env_dir := os.getenv("WORKSHOP_DIR"):
            return Path(env_dir).expanduser().resolve()

        # Try to find project root
        project_root, detection_reason, confidence = find_project_root()
        if not project_root:
            # No project detected, use global
            return Path.home() / ".workshop" / "global"

        # Check config for registered database
        config = WorkshopConfig()
        project_config = config.get_project_config(project_root)
        if project_config and 'database' in project_config:
            db_path = Path(project_config['database'])
            return db_path.parent

        # Check for existing .workshop in parent directories
        existing = self._find_existing_workshop(project_root)
        if existing:
            return existing

        # Prompt user for workspace location
        return self._prompt_for_workspace(project_root, detection_reason, confidence)

    def _find_existing_workshop(self, project_root: Path) -> Optional[Path]:
        """Check for existing .workshop directory in parent directories."""
        current = Path.cwd()
        while current != current.parent:
            if current == project_root:
                break
            current = current.parent

        if current != project_root and (current / ".workshop").exists():
            return current / ".workshop"

        return None

    def _prompt_for_workspace(self, project_root: Path, detection_reason: str, confidence: int) -> Path:
        """Interactive prompt for workspace location (or auto-select if non-interactive)."""
        import sys
        import os

        # Check for non-interactive mode (env var or no TTY)
        auto_mode = os.getenv('WORKSHOP_AUTO_INIT') == '1' or not sys.stdin.isatty()

        if auto_mode:
            # Non-interactive: auto-select project root
            workspace = project_root / ".workshop"
            workspace.mkdir(parents=True, exist_ok=True)

            # Register in config
            db_path = workspace / "workshop.db"
            config = WorkshopConfig()
            config.register_project(project_root, database_path=db_path)

            return workspace

        # Interactive mode - show prompts
        current = Path.cwd()

        click.echo(f"\n📝 Workshop Setup")
        click.echo(f"\n   Detected project root: {project_root}")
        click.echo(f"   Reason: {detection_reason}")
        if confidence > 0:
            click.echo(f"   Confidence: {confidence} points")
        click.echo(f"   Current directory: {current}\n")

        click.echo("Where should Workshop store data for this project?")
        click.echo(f"  1. {project_root}/.workshop (at project root - recommended)")

        if current != project_root:
            click.echo(f"  2. {current}/.workshop (in current directory)")
            click.echo(f"  3. Custom path")
            max_choice = 3
        else:
            click.echo(f"  2. Custom path")
            max_choice = 2

        choice = click.prompt("\nSelect", type=str, default="1")

        if choice == "1":
            workspace = project_root / ".workshop"
        elif choice == "2" and max_choice == 3:
            workspace = current / ".workshop"
        elif (choice == "2" and max_choice == 2) or choice == "3":
            custom = click.prompt("Enter workspace path")
            workspace = Path(custom).expanduser().resolve()
        else:
            click.echo(f"Invalid choice, using default: {project_root}/.workshop")
            workspace = project_root / ".workshop"

        # Validate the path
        is_valid, error_msg = validate_workspace_path(workspace)
        if not is_valid:
            click.echo(f"\n❌ Error: {error_msg}")
            click.echo("Falling back to project root...")
            workspace = project_root / ".workshop"

        # Create workspace directory
        workspace.mkdir(parents=True, exist_ok=True)

        # Register in config
        db_path = workspace / "workshop.db"
        config = WorkshopConfig()
        config.register_project(project_root, database_path=db_path)

        click.echo(f"\n✓ Workspace configured: {workspace}")
        click.echo(f"✓ Registered for project: {project_root}\n")

        return workspace

    def _init_db(self):
        """Initialize database schema using SQLAlchemy models."""
        Base.metadata.create_all(self.engine)

        # Set schema version
        from ..models import Config
        with self.SessionLocal() as session:
            version = session.query(Config).filter_by(key='schema_version').first()
            if not version:
                session.add(Config(key='schema_version', value='4'))  # SQLAlchemy version
                session.commit()

    def _ensure_user_and_project(self):
        """Ensure user and project exist in multi-tenant mode."""
        from ..models import User, Project

        with self.SessionLocal() as session:
            # Get or create user (using api_key as identifier)
            user = session.query(User).filter_by(api_key=str(self.user_id)).first()
            if not user:
                user = User(api_key=str(self.user_id))
                session.add(user)
                session.flush()

            # Get or create project
            project = session.query(Project).filter_by(
                user_id=user.id,
                name=self.project_name
            ).first()
            if not project:
                project = Project(
                    user_id=user.id,
                    name=self.project_name
                )
                session.add(project)
                session.flush()

            self.project_id = project.id
            session.commit()

    def get_session(self):
        """Get a new database session."""
        return self.SessionLocal()

    @property
    def workspace_dir(self) -> Optional[Path]:
        """Get workspace directory (OSS mode only)."""
        return self._workspace_dir
