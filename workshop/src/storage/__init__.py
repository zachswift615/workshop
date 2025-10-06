"""
Workshop Storage - Fully migrated to SQLAlchemy!

This module provides a modern storage layer that:
- Uses SQLAlchemy ORM for all database operations
- Supports both SQLite (OSS) and PostgreSQL (Cloud)
- Maintains backward compatibility with existing code
- Provides multi-tenant isolation for cloud deployments

Migration Status:
✅ entries.py - Fully migrated to SQLAlchemy
✅ preferences_state.py - Fully migrated to SQLAlchemy
✅ sessions.py - Fully migrated to SQLAlchemy
✅ import_history.py - Fully migrated to SQLAlchemy
"""
from pathlib import Path
from typing import Optional

from .base import DatabaseManager
from .entries import EntriesManager
from .preferences_state import PreferencesStateManager
from .sessions import SessionsManager
from .import_history import ImportHistoryManager

# Re-export for convenience
__all__ = [
    'WorkshopStorage',
    'DatabaseManager',
    'EntriesManager',
    'PreferencesStateManager',
    'SessionsManager',
    'ImportHistoryManager',
]


class WorkshopStorage:
    """
    Main storage facade that composes all storage modules.

    This class provides a unified interface while internally delegating
    to specialized managers (some using SQLAlchemy, some using raw SQL).
    """

    def __init__(
        self,
        workspace_dir: Optional[Path] = None,
        connection_string: Optional[str] = None,
        user_id: Optional[str] = None,
        project_name: Optional[str] = None,
        echo: bool = False
    ):
        """
        Initialize Workshop storage.

        Args:
            workspace_dir: For OSS mode - workspace directory
            connection_string: For Cloud mode - database URL
            user_id: For Cloud mode - user identifier
            project_name: For Cloud mode - project name
            echo: Echo SQL queries (debug mode)
        """
        # Initialize database manager
        self.db_manager = DatabaseManager(
            workspace_dir=workspace_dir,
            connection_string=connection_string,
            user_id=user_id,
            project_name=project_name,
            echo=echo
        )

        # Get SQLAlchemy session
        self._session = self.db_manager.get_session()

        # Initialize module managers (all using SQLAlchemy now!)
        self.entries = EntriesManager(self._session, self.db_manager.project_id)
        self.prefs_state = PreferencesStateManager(self._session, self.db_manager.project_id)
        self.sessions = SessionsManager(self._session, self.db_manager.project_id)
        self.import_history = ImportHistoryManager(self._session, self.db_manager.project_id)

    # ========================================================================
    # Entry Management (Delegated to EntriesManager)
    # ========================================================================

    def add_entry(self, *args, **kwargs):
        """Add a new entry."""
        return self.entries.add_entry(*args, **kwargs)

    def get_entries(self, *args, **kwargs):
        """Get entries with optional filtering."""
        return self.entries.get_entries(*args, **kwargs)

    def get_entry_by_id(self, *args, **kwargs):
        """Get a single entry by ID."""
        return self.entries.get_entry_by_id(*args, **kwargs)

    def get_last_entry(self, *args, **kwargs):
        """Get the most recent entry."""
        return self.entries.get_last_entry(*args, **kwargs)

    def update_entry(self, *args, **kwargs):
        """Update an existing entry."""
        return self.entries.update_entry(*args, **kwargs)

    def delete_entry(self, *args, **kwargs):
        """Delete an entry by ID."""
        return self.entries.delete_entry(*args, **kwargs)

    def delete_entries_by_type(self, *args, **kwargs):
        """Delete all entries of a specific type."""
        return self.entries.delete_entries_by_type(*args, **kwargs)

    def delete_entries_before(self, *args, **kwargs):
        """Delete entries before a specific date."""
        return self.entries.delete_entries_before(*args, **kwargs)

    def search(self, *args, **kwargs):
        """Search entries."""
        return self.entries.search(*args, **kwargs)

    def why_search(self, *args, **kwargs):
        """Smart search for 'why' queries."""
        return self.entries.why_search(*args, **kwargs)

    # ========================================================================
    # Preferences (Delegated to PreferencesStateManager)
    # ========================================================================

    def add_preference(self, *args, **kwargs):
        """Add a preference."""
        return self.prefs_state.add_preference(*args, **kwargs)

    def get_preferences(self, *args, **kwargs):
        """Get all preferences."""
        return self.prefs_state.get_preferences(*args, **kwargs)

    # ========================================================================
    # Current State (Delegated to PreferencesStateManager)
    # ========================================================================

    def add_goal(self, *args, **kwargs):
        """Add a goal."""
        return self.prefs_state.add_goal(*args, **kwargs)

    def add_next_step(self, *args, **kwargs):
        """Add a next step."""
        return self.prefs_state.add_next_step(*args, **kwargs)

    def get_current_state(self, *args, **kwargs):
        """Get current state."""
        return self.prefs_state.get_current_state(*args, **kwargs)

    def clear_goals(self, *args, **kwargs):
        """Clear all goals."""
        return self.prefs_state.clear_goals(*args, **kwargs)

    def clear_next_steps(self, *args, **kwargs):
        """Clear all next steps."""
        return self.prefs_state.clear_next_steps(*args, **kwargs)

    def complete_goal(self, *args, **kwargs):
        """Mark a goal as completed."""
        return self.prefs_state.complete_goal(*args, **kwargs)

    def complete_next_step(self, *args, **kwargs):
        """Mark a next step as completed."""
        return self.prefs_state.complete_next_step(*args, **kwargs)

    def clear_completed_goals(self, *args, **kwargs):
        """Remove completed goals."""
        return self.prefs_state.clear_completed_goals(*args, **kwargs)

    def clear_completed_next_steps(self, *args, **kwargs):
        """Remove completed next steps."""
        return self.prefs_state.clear_completed_next_steps(*args, **kwargs)

    # ========================================================================
    # Session Management (Delegated to SessionsManager)
    # ========================================================================

    def add_session(self, *args, **kwargs):
        """Add a session record."""
        return self.sessions.add_session(*args, **kwargs)

    def get_sessions(self, *args, **kwargs):
        """Get sessions."""
        return self.sessions.get_sessions(*args, **kwargs)

    def get_session_by_id(self, *args, **kwargs):
        """Get a session by ID."""
        return self.sessions.get_session_by_id(*args, **kwargs)

    def get_last_session(self, *args, **kwargs):
        """Get the most recent session."""
        return self.sessions.get_last_session(*args, **kwargs)

    # ========================================================================
    # Import History (Delegated to ImportHistoryManager)
    # ========================================================================

    def record_import(self, *args, **kwargs):
        """Record a JSONL import."""
        return self.import_history.record_import(*args, **kwargs)

    def get_last_import(self, *args, **kwargs):
        """Get last import record for a JSONL file."""
        return self.import_history.get_last_import(*args, **kwargs)

    def get_import_history(self, *args, **kwargs):
        """Get recent import history."""
        return self.import_history.get_import_history(*args, **kwargs)

    def is_message_imported(self, *args, **kwargs):
        """Check if a message UUID has been imported."""
        return self.import_history.is_message_imported(*args, **kwargs)

    # ========================================================================
    # Properties
    # ========================================================================

    @property
    def workspace_dir(self) -> Optional[Path]:
        """Get workspace directory (OSS mode only)."""
        return self.db_manager.workspace_dir

    @property
    def backend_type(self) -> str:
        """Get backend type identifier."""
        return "cloud" if self.db_manager.multi_tenant_mode else "local"

    def __del__(self):
        """Cleanup connections."""
        if hasattr(self, '_session'):
            self._session.close()
