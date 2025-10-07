"""
Basic tests for Workshop storage layer
"""
import tempfile
import shutil
from pathlib import Path
from datetime import datetime
import pytest

from src.storage_sqlite import WorkshopStorageSQLite


@pytest.fixture
def temp_workspace():
    """Create a temporary workspace for testing"""
    temp_dir = Path(tempfile.mkdtemp())
    yield temp_dir
    # Windows-friendly cleanup: ignore errors if files are locked
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def storage(temp_workspace):
    """Create a storage instance with temporary workspace"""
    return WorkshopStorageSQLite(temp_workspace)


def test_init_creates_database(temp_workspace):
    """Test that initializing storage creates the database"""
    storage = WorkshopStorageSQLite(temp_workspace)
    db_file = temp_workspace / "workshop.db"
    assert db_file.exists()
    assert db_file.name == "workshop.db"


def test_add_entry(storage):
    """Test adding a basic entry"""
    entry = storage.add_entry(
        entry_type="note",
        content="Test note",
        tags=["test"],
        files=["test.py"]
    )

    assert entry["id"] is not None
    assert entry["type"] == "note"
    assert entry["content"] == "Test note"
    assert "test" in entry["tags"]
    assert "test.py" in entry["files"]


def test_add_decision_with_reasoning(storage):
    """Test adding a decision with reasoning"""
    entry = storage.add_entry(
        entry_type="decision",
        content="Use SQLite for storage",
        reasoning="Better performance than JSON"
    )

    assert entry["reasoning"] == "Better performance than JSON"


def test_get_entries(storage):
    """Test retrieving entries"""
    # Add some entries
    storage.add_entry("note", "Note 1")
    storage.add_entry("decision", "Decision 1", reasoning="Because")
    storage.add_entry("note", "Note 2")

    # Get all entries
    entries = storage.get_entries()
    assert len(entries) == 3

    # Get only notes
    notes = storage.get_entries(entry_type="note")
    assert len(notes) == 2
    assert all(e["type"] == "note" for e in notes)


def test_search(storage):
    """Test full-text search"""
    storage.add_entry("note", "Testing SQLite database")
    storage.add_entry("note", "Testing search functionality")
    storage.add_entry("note", "Something else entirely")

    results = storage.search("sqlite")
    assert len(results) == 1
    assert "SQLite" in results[0]["content"]

    results = storage.search("testing")
    assert len(results) == 2


def test_why_search(storage):
    """Test smart 'why' search"""
    # Add decision with reasoning (high priority)
    storage.add_entry(
        "decision",
        "Use Python for backend",
        reasoning="Fast development and great libraries"
    )

    # Add note (lower priority)
    storage.add_entry("note", "Python is great")

    results = storage.why_search("python")
    assert len(results) >= 1
    # Decision should be first (higher priority)
    assert results[0]["type"] == "decision"


def test_preferences(storage):
    """Test preference management"""
    storage.add_preference("code_style", "Use type hints everywhere")
    storage.add_preference("code_style", "Prefer f-strings over .format()")

    prefs = storage.get_preferences()
    assert "code_style" in prefs
    assert len(prefs["code_style"]) == 2


def test_goals(storage):
    """Test goal management"""
    storage.add_goal("Implement authentication")
    storage.add_goal("Add payment processing")

    state = storage.get_current_state()
    assert len(state["goals"]) == 2

    storage.clear_goals()
    state = storage.get_current_state()
    assert len(state["goals"]) == 0


def test_sessions(storage):
    """Test session tracking"""
    from uuid import uuid4
    test_session_id = str(uuid4())

    session = storage.add_session(
        session_id=test_session_id,
        start_time=datetime.now().isoformat(),
        end_time=datetime.now().isoformat(),
        duration_minutes=30,
        files_modified=["file1.py", "file2.py"],
        commands_run=["pip install click"],
        workshop_entries={"decisions": 2, "notes": 5},
        user_requests=["Add feature X"],
        summary="Test session",
        branch="main",
        reason="test"
    )

    assert session["id"] == test_session_id
    assert len(session["files_modified"]) == 2
    assert session["workshop_entries"]["decisions"] == 2

    # Retrieve sessions
    sessions = storage.get_sessions()


def test_sessions_with_z_suffix_timestamps(storage):
    """
    Regression test for sessions with 'Z' suffix timestamps from Claude Code.

    This tests the fix for the bug where session timestamps with 'Z' suffix
    would cause ValueError during import.
    """
    from uuid import uuid4
    test_session_id = str(uuid4())

    # Claude Code uses timestamps with Z suffix
    session = storage.add_session(
        session_id=test_session_id,
        start_time="2025-10-06T19:59:59.997Z",  # Z suffix format
        end_time="2025-10-06T20:30:00.123Z",
        duration_minutes=30,
        files_modified=["test.py"],
        commands_run=["workshop import --execute"],
        workshop_entries={"gotchas": 5},
        user_requests=["Import sessions from Claude Code"],
        summary="Testing Z-suffix timestamp handling",
        branch="main",
        reason="regression test"
    )

    # Should not raise ValueError anymore
    assert session["id"] == test_session_id
    assert session["summary"] == "Testing Z-suffix timestamp handling"

    # Verify session can be retrieved
    sessions = storage.get_sessions()
    assert len(sessions) == 1

    # Get by ID
    retrieved = storage.get_session_by_id(test_session_id)
    assert retrieved["id"] == test_session_id

    # Get last session
    last = storage.get_last_session()
    assert last["id"] == test_session_id


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
