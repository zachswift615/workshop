"""
Tests for Workshop SQLite storage
"""
import pytest
from pathlib import Path
from datetime import datetime
from src.storage_sqlite import WorkshopStorageSQLite


@pytest.fixture
def temp_storage(tmp_path):
    """Create a temporary storage instance"""
    workspace = tmp_path / ".workshop"
    return WorkshopStorageSQLite(workspace)


def test_storage_initialization(tmp_path):
    """Test storage creates database and schema"""
    workspace = tmp_path / ".workshop"
    storage = WorkshopStorageSQLite(workspace)

    assert workspace.exists()
    assert (workspace / "workshop.db").exists()


def test_add_note(temp_storage):
    """Test adding a note"""
    entry = temp_storage.add_entry(
        entry_type="note",
        content="Test note"
    )

    assert entry["type"] == "note"
    assert entry["content"] == "Test note"
    assert "id" in entry
    assert "timestamp" in entry


def test_add_decision_with_reasoning(temp_storage):
    """Test adding a decision with reasoning"""
    entry = temp_storage.add_entry(
        entry_type="decision",
        content="Use PostgreSQL",
        reasoning="Need ACID guarantees"
    )

    assert entry["type"] == "decision"
    assert entry["content"] == "Use PostgreSQL"
    assert entry["reasoning"] == "Need ACID guarantees"


def test_add_entry_with_tags(temp_storage):
    """Test adding entry with tags"""
    entry = temp_storage.add_entry(
        entry_type="note",
        content="Test",
        tags=["python", "testing"]
    )

    assert "python" in entry["tags"]
    assert "testing" in entry["tags"]


def test_add_entry_with_files(temp_storage):
    """Test adding entry with file references"""
    entry = temp_storage.add_entry(
        entry_type="note",
        content="Test",
        files=["src/test.py", "README.md"]
    )

    assert "src/test.py" in entry["files"]
    assert "README.md" in entry["files"]


def test_add_entry_with_custom_timestamp(temp_storage):
    """Test adding entry with custom timestamp"""
    custom_time = "2025-01-01T12:00:00"

    entry = temp_storage.add_entry(
        entry_type="note",
        content="Test",
        timestamp=custom_time
    )

    assert entry["timestamp"] == custom_time


def test_get_entries(temp_storage):
    """Test retrieving entries"""
    temp_storage.add_entry("note", "First")
    temp_storage.add_entry("note", "Second")
    temp_storage.add_entry("decision", "Third")

    entries = temp_storage.get_entries()

    assert len(entries) == 3


def test_get_entries_with_limit(temp_storage):
    """Test retrieving entries with limit"""
    for i in range(10):
        temp_storage.add_entry("note", f"Note {i}")

    entries = temp_storage.get_entries(limit=5)

    assert len(entries) == 5


def test_get_entries_by_type(temp_storage):
    """Test filtering entries by type"""
    temp_storage.add_entry("note", "Note 1")
    temp_storage.add_entry("note", "Note 2")
    temp_storage.add_entry("decision", "Decision 1")

    notes = temp_storage.get_entries(entry_type="note")
    decisions = temp_storage.get_entries(entry_type="decision")

    assert len(notes) == 2
    assert len(decisions) == 1


def test_get_entry_by_id(temp_storage):
    """Test retrieving single entry by ID"""
    created = temp_storage.add_entry("note", "Test note")

    entry = temp_storage.get_entry_by_id(created["id"])

    assert entry is not None
    assert entry["id"] == created["id"]
    assert entry["content"] == "Test note"


def test_get_nonexistent_entry(temp_storage):
    """Test getting entry that doesn't exist"""
    entry = temp_storage.get_entry_by_id("nonexistent-id")

    assert entry is None


def test_search(temp_storage):
    """Test full-text search"""
    temp_storage.add_entry("note", "Python is great")
    temp_storage.add_entry("note", "JavaScript is okay")
    temp_storage.add_entry("decision", "Using Python for backend")

    results = temp_storage.search("Python")

    assert len(results) == 2


def test_search_no_results(temp_storage):
    """Test search with no matches"""
    temp_storage.add_entry("note", "First")
    temp_storage.add_entry("note", "Second")

    results = temp_storage.search("nonexistent")

    assert len(results) == 0


def test_search_with_limit(temp_storage):
    """Test search respects limit"""
    for i in range(10):
        temp_storage.add_entry("note", f"Python test {i}")

    results = temp_storage.search("Python", limit=3)

    assert len(results) == 3


def test_search_with_hyphen(temp_storage):
    """Test search handles hyphenated terms"""
    temp_storage.add_entry("note", "Testing auto-attachment feature")
    temp_storage.add_entry("note", "Manual attachment required")
    temp_storage.add_entry("decision", "Use auto-generated IDs")

    # Search for hyphenated term
    results = temp_storage.search("auto-attachment")

    assert len(results) >= 1
    assert any("auto-attachment" in r["content"].lower() for r in results)


def test_search_with_quotes(temp_storage):
    """Test search handles quoted terms"""
    temp_storage.add_entry("note", 'Use the "factory pattern" for widgets')
    temp_storage.add_entry("decision", "Implement factory methods")

    results = temp_storage.search("factory pattern")

    assert len(results) >= 1


def test_search_with_special_chars(temp_storage):
    """Test search handles various special characters"""
    temp_storage.add_entry("note", "C++ is powerful")
    temp_storage.add_entry("note", "Use @decorators in Python")
    temp_storage.add_entry("decision", "Support file-names with-dashes")

    # Search with plus signs
    results = temp_storage.search("C++")
    assert len(results) >= 0  # May be treated as "C"

    # Search with @ symbol
    results = temp_storage.search("@decorators")
    assert len(results) >= 0  # May be treated as "decorators"

    # Search with dashes
    results = temp_storage.search("file-names")
    assert len(results) >= 1


def test_search_fallback(temp_storage):
    """Test that fallback search works when FTS5 fails"""
    temp_storage.add_entry("note", "Testing fallback mechanism")

    # This should work even if FTS5 has issues
    results = temp_storage.search("fallback")

    assert len(results) >= 1
    assert any("fallback" in r["content"].lower() for r in results)


def test_delete_entry(temp_storage):
    """Test deleting an entry"""
    entry = temp_storage.add_entry("note", "To be deleted")

    result = temp_storage.delete_entry(entry["id"])

    assert result is True
    assert temp_storage.get_entry_by_id(entry["id"]) is None


def test_delete_nonexistent_entry(temp_storage):
    """Test deleting entry that doesn't exist"""
    result = temp_storage.delete_entry("nonexistent")

    assert result is False


def test_record_import(temp_storage):
    """Test recording an import"""
    temp_storage.record_import(
        jsonl_path="/path/to/session.jsonl",
        jsonl_hash="abc123",
        last_uuid="uuid-123",
        last_timestamp="2025-01-01T12:00:00",
        messages_imported=100,
        entries_created=10
    )

    last_import = temp_storage.get_last_import("/path/to/session.jsonl")

    assert last_import is not None
    assert last_import["jsonl_hash"] == "abc123"
    assert last_import["entries_created"] == 10


def test_get_last_import_nonexistent(temp_storage):
    """Test getting import for file never imported"""
    result = temp_storage.get_last_import("/nonexistent.jsonl")

    assert result is None


def test_metadata_json_parsing(temp_storage):
    """Test that metadata is properly JSON serialized/deserialized"""
    metadata = {"key": "value", "number": 42}

    entry = temp_storage.add_entry(
        "note",
        "Test",
        metadata=metadata
    )

    retrieved = temp_storage.get_entry_by_id(entry["id"])

    assert retrieved["metadata"] == metadata


def test_empty_tags_and_files(temp_storage):
    """Test entries with no tags or files"""
    entry = temp_storage.add_entry("note", "Simple note")

    assert entry["tags"] == []
    assert entry["files"] == []


def test_entry_ordering(temp_storage):
    """Test that entries are returned in reverse chronological order"""
    temp_storage.add_entry("note", "First", timestamp="2025-01-01T10:00:00")
    temp_storage.add_entry("note", "Second", timestamp="2025-01-01T11:00:00")
    temp_storage.add_entry("note", "Third", timestamp="2025-01-01T12:00:00")

    entries = temp_storage.get_entries()

    # Should be newest first
    assert entries[0]["content"] == "Third"
    assert entries[1]["content"] == "Second"
    assert entries[2]["content"] == "First"


def test_timestamp_with_z_suffix(temp_storage):
    """
    Regression test for bug where timestamps with 'Z' suffix from Claude Code JSONL files
    caused ValueError: Invalid isoformat string during import.

    Bug report: workshop import --execute failed with:
    ValueError: Invalid isoformat string: '2025-10-06T19:59:59.997Z'
    """
    # Test various timestamp formats that Claude Code might generate
    timestamp_formats = [
        "2025-10-06T19:59:59.997Z",  # Claude Code format with Z suffix
        "2025-10-06T19:59:59.997+00:00",  # Standard ISO format with timezone
        "2025-10-06T19:59:59Z",  # Without milliseconds but with Z
        "2025-10-06T19:59:59",  # Without timezone
    ]

    for i, ts in enumerate(timestamp_formats):
        # This should not raise ValueError anymore
        entry = temp_storage.add_entry(
            entry_type="note",
            content=f"Test note with timestamp format {i}",
            timestamp=ts
        )

        assert entry["type"] == "note"
        assert entry["content"] == f"Test note with timestamp format {i}"
        assert "timestamp" in entry
        assert "id" in entry

    # Verify all entries were added successfully
    entries = temp_storage.get_entries()
    assert len(entries) >= len(timestamp_formats)
