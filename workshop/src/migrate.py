"""
Migration script to convert JSON data to SQLite and handle schema upgrades
"""
import json
import sqlite3
import shutil
from pathlib import Path
from typing import Optional
from datetime import datetime
from .storage import WorkshopStorage  # Old JSON storage
from .storage_sqlite import WorkshopStorageSQLite  # New SQLite storage


def migrate_json_to_sqlite(workspace_dir: Optional[Path] = None) -> bool:
    """
    Migrate data from JSON to SQLite.

    Args:
        workspace_dir: Workspace directory to migrate

    Returns:
        True if migration was performed, False if no migration needed
    """
    # Initialize both storage backends
    json_storage = WorkshopStorage(workspace_dir)
    sqlite_storage = WorkshopStorageSQLite(workspace_dir)

    # Check if JSON file exists and has data
    if not json_storage.data_file.exists():
        return False  # Nothing to migrate

    # Read JSON data
    try:
        data = json_storage._read_data()
    except Exception as e:
        print(f"Error reading JSON data: {e}")
        return False

    # Check if there's any data to migrate
    has_data = (
        len(data.get('entries', [])) > 0 or
        any(len(v) > 0 for v in data.get('preferences', {}).values()) or
        len(data.get('current_state', {}).get('goals', [])) > 0 or
        len(data.get('current_state', {}).get('next_steps', [])) > 0 or
        len(data.get('sessions', [])) > 0
    )

    if not has_data:
        return False  # No data to migrate

    print("Migrating Workshop data from JSON to SQLite...")

    # Migrate entries
    entries = data.get('entries', [])
    print(f"Migrating {len(entries)} entries...")
    for entry in entries:
        # Add entry directly to SQLite
        import sqlite3
        with sqlite_storage._get_connection() as conn:
            conn.execute("""
                INSERT INTO entries (id, type, content, reasoning, timestamp, branch, commit_hash, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                entry.get('id'),
                entry.get('type'),
                entry.get('content'),
                entry.get('reasoning'),
                entry.get('timestamp'),
                entry.get('branch'),
                entry.get('commit'),
                json.dumps(entry.get('metadata', {}))
            ))

            # Add tags
            for tag in entry.get('tags', []):
                conn.execute("""
                    INSERT INTO tags (entry_id, tag) VALUES (?, ?)
                """, (entry['id'], tag))

            # Add files
            for file_path in entry.get('files', []):
                conn.execute("""
                    INSERT INTO files (entry_id, file_path) VALUES (?, ?)
                """, (entry['id'], file_path))

            conn.commit()

    # Migrate preferences
    preferences = data.get('preferences', {})
    pref_count = sum(len(v) for v in preferences.values())
    print(f"Migrating {pref_count} preferences...")
    for category, prefs in preferences.items():
        for pref in prefs:
            with sqlite_storage._get_connection() as conn:
                conn.execute("""
                    INSERT INTO preferences (category, content, timestamp)
                    VALUES (?, ?, ?)
                """, (category, pref.get('content'), pref.get('timestamp')))
                conn.commit()

    # Migrate current state
    current_state = data.get('current_state', {})

    goals = current_state.get('goals', [])
    print(f"Migrating {len(goals)} goals...")
    for goal in goals:
        with sqlite_storage._get_connection() as conn:
            conn.execute("""
                INSERT INTO current_state (type, content, timestamp)
                VALUES ('goal', ?, ?)
            """, (goal.get('content'), goal.get('timestamp')))
            conn.commit()

    next_steps = current_state.get('next_steps', [])
    print(f"Migrating {len(next_steps)} next steps...")
    for step in next_steps:
        with sqlite_storage._get_connection() as conn:
            conn.execute("""
                INSERT INTO current_state (type, content, timestamp)
                VALUES ('next_step', ?, ?)
            """, (step.get('content'), step.get('timestamp')))
            conn.commit()

    # Migrate sessions
    sessions = data.get('sessions', [])
    print(f"Migrating {len(sessions)} sessions...")
    for session in sessions:
        sqlite_storage.add_session(
            session_id=session.get('id'),
            start_time=session.get('start_time'),
            end_time=session.get('end_time'),
            duration_minutes=session.get('duration_minutes', 0),
            files_modified=session.get('files_modified', []),
            commands_run=session.get('commands_run', []),
            workshop_entries=session.get('workshop_entries', {}),
            user_requests=session.get('user_requests', []),
            summary=session.get('summary', ''),
            branch=session.get('branch', ''),
            reason=session.get('reason', ''),
            metadata=session.get('metadata', {})
        )

    # Create backup of JSON file
    backup_path = json_storage.data_file.with_suffix('.json.backup')
    if not backup_path.exists():
        import shutil
        shutil.copy2(json_storage.data_file, backup_path)
        print(f"Created backup: {backup_path}")

    print("Migration complete!")
    return True


def should_migrate(workspace_dir: Optional[Path] = None) -> bool:
    """
    Check if migration is needed.

    Returns:
        True if JSON data exists but SQLite database doesn't exist yet
    """
    from .storage import WorkshopStorage

    # Find workspace directory
    if workspace_dir is None:
        from .storage_sqlite import WorkshopStorageSQLite
        temp_storage = WorkshopStorageSQLite.__new__(WorkshopStorageSQLite)
        workspace_dir = temp_storage._find_workspace()

    json_storage = WorkshopStorage(workspace_dir)
    db_file = workspace_dir / "workshop.db"

    # Check if JSON file exists and has data
    if not json_storage.data_file.exists():
        return False

    # Check if SQLite database doesn't exist yet
    if not db_file.exists():
        try:
            data = json_storage._read_data()
            return len(data.get('entries', [])) > 0
        except:
            return False

    return False


# ============================================================================
# Schema Version Migrations
# ============================================================================

def get_schema_version(db_path: Path) -> int:
    """
    Get current schema version from database.

    Args:
        db_path: Path to SQLite database

    Returns:
        Schema version number (default 1 if not found)
    """
    if not db_path.exists():
        return 0  # Database doesn't exist yet

    try:
        conn = sqlite3.connect(str(db_path))
        cursor = conn.execute("SELECT value FROM config WHERE key = 'schema_version'")
        row = cursor.fetchone()
        conn.close()
        return int(row[0]) if row else 1
    except:
        return 1  # Assume version 1 if table doesn't exist


def migrate_schema_to_v2(db_path: Path) -> bool:
    """
    Migrate schema from v1 to v2: Add import_history table.

    Args:
        db_path: Path to SQLite database

    Returns:
        True if migration succeeded
    """
    print("🔄 Migrating database schema to v2...")

    # Backup database before migration
    backup_path = db_path.with_suffix('.db.backup.v1')
    if not backup_path.exists():
        shutil.copy2(db_path, backup_path)
        print(f"  ✓ Created backup: {backup_path.name}")

    try:
        conn = sqlite3.connect(str(db_path))

        # Add import_history table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS import_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                jsonl_path TEXT NOT NULL,
                jsonl_hash TEXT,
                last_message_uuid TEXT,
                last_message_timestamp TEXT,
                messages_imported INTEGER,
                entries_created INTEGER,
                import_timestamp TEXT NOT NULL,
                UNIQUE(jsonl_path)
            )
        """)

        # Add indexes
        conn.execute("CREATE INDEX IF NOT EXISTS idx_import_history_path ON import_history(jsonl_path)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_import_history_timestamp ON import_history(import_timestamp DESC)")

        # Update schema version
        conn.execute("INSERT OR REPLACE INTO config (key, value) VALUES ('schema_version', '2')")

        conn.commit()
        conn.close()

        print("  ✓ Migration to v2 complete")
        return True

    except Exception as e:
        print(f"  ✗ Migration failed: {e}")
        # Restore from backup
        if backup_path.exists():
            shutil.copy2(backup_path, db_path)
            print(f"  ✓ Restored from backup")
        return False


def migrate_schema(db_path: Path, target_version: int = 2) -> bool:
    """
    Migrate schema to target version.

    Args:
        db_path: Path to SQLite database
        target_version: Target schema version (default 2)

    Returns:
        True if migration succeeded or not needed
    """
    current_version = get_schema_version(db_path)

    if current_version >= target_version:
        return True  # Already at or above target version

    if current_version == 0:
        return True  # New database, will be created with latest schema

    # Apply migrations sequentially
    if current_version < 2 and target_version >= 2:
        if not migrate_schema_to_v2(db_path):
            return False

    return True


def auto_migrate_if_needed(workspace_dir: Path) -> bool:
    """
    Automatically migrate schema if needed on first use.

    Args:
        workspace_dir: Workshop workspace directory

    Returns:
        True if migration succeeded or not needed
    """
    db_path = workspace_dir / "workshop.db"

    if not db_path.exists():
        return True  # New database, no migration needed

    current_version = get_schema_version(db_path)
    target_version = 2  # Current schema version

    if current_version < target_version:
        return migrate_schema(db_path, target_version)

    return True
