"""
Tests for Workshop JSONL parser
"""
import pytest
import json
from pathlib import Path
from src.jsonl_parser import JSONLParser, ExtractedEntry, SessionImportResult


@pytest.fixture
def temp_jsonl(tmp_path):
    """Create a temporary JSONL file for testing"""
    jsonl_path = tmp_path / "test_session.jsonl"
    return jsonl_path


def test_parser_initialization():
    """Test parser initializes correctly"""
    parser = JSONLParser()

    assert parser.decision_pattern is not None
    assert parser.gotcha_pattern is not None
    assert parser.preference_pattern is not None


def test_parse_empty_file(temp_jsonl):
    """Test parsing empty JSONL file"""
    temp_jsonl.touch()

    parser = JSONLParser()
    result = parser.parse_jsonl_file(temp_jsonl)

    assert result.entries == []
    assert result.messages_processed == 0


def test_extracted_entry_dataclass():
    """Test ExtractedEntry dataclass"""
    entry = ExtractedEntry(
        type='note',
        content='Test content',
        reasoning='Test reasoning',
        confidence=0.9,
        timestamp='2025-01-02T01:00:00Z',
        source_uuid='test-uuid'
    )

    assert entry.type == 'note'
    assert entry.content == 'Test content'
    assert entry.reasoning == 'Test reasoning'
    assert entry.confidence == 0.9
    assert entry.timestamp == '2025-01-02T01:00:00Z'
    assert entry.source_uuid == 'test-uuid'


def test_session_import_result():
    """Test SessionImportResult construction"""
    result = SessionImportResult(
        jsonl_path="/path/to/file.jsonl",
        session_summary="Test summary",
        entries=[],
        last_message_uuid="uuid-123",
        last_message_timestamp="2025-01-01T12:00:00Z",
        messages_processed=10
    )

    assert result.jsonl_path == "/path/to/file.jsonl"
    assert result.messages_processed == 10


def test_malformed_json_handling(temp_jsonl):
    """Test handling of malformed JSON lines"""
    with open(temp_jsonl, 'w') as f:
        f.write('{"uuid": "valid", "conversation": []}\n')
        f.write('{invalid json}\n')
        f.write('{"uuid": "valid2", "conversation": []}\n')

    parser = JSONLParser()
    # Should not crash on malformed JSON
    result = parser.parse_jsonl_file(temp_jsonl)

    # Should still parse valid entries
    assert isinstance(result.entries, list)


def test_parse_file_basic_structure(temp_jsonl):
    """Test that parser handles basic file structure"""
    messages = [
        {
            "uuid": "test-uuid-1",
            "conversation": [
                {
                    "role": "assistant",
                    "message": "Some test content",
                    "created_at": "2025-01-01T12:00:00Z"
                }
            ]
        }
    ]

    with open(temp_jsonl, 'w') as f:
        for msg in messages:
            f.write(json.dumps(msg) + '\n')

    parser = JSONLParser()
    result = parser.parse_jsonl_file(temp_jsonl)

    # Should process the message without crashing
    assert result.messages_processed >= 1
    assert result.last_message_uuid == "test-uuid-1"
    assert isinstance(result.entries, list)


def test_pattern_matching():
    """Test that patterns match expected keywords"""
    parser = JSONLParser()

    # Test decision pattern
    assert parser.decision_pattern.search("We decided to use PostgreSQL")
    assert parser.decision_pattern.search("chose to implement caching")

    # Test gotcha pattern
    assert parser.gotcha_pattern.search("Watch out for the rate limit")
    assert parser.gotcha_pattern.search("This is a gotcha")

    # Test preference pattern
    assert parser.preference_pattern.search("I prefer type hints")
    assert parser.preference_pattern.search("We typically use React")


def test_filter_from_uuid(temp_jsonl):
    """Test filtering messages from a specific UUID"""
    messages = [
        {"uuid": "uuid-1", "conversation": [], "timestamp": "2025-01-01T10:00:00Z"},
        {"uuid": "uuid-2", "conversation": [], "timestamp": "2025-01-01T11:00:00Z"},
        {"uuid": "uuid-3", "conversation": [], "timestamp": "2025-01-01T12:00:00Z"},
    ]

    with open(temp_jsonl, 'w') as f:
        for msg in messages:
            f.write(json.dumps(msg) + '\n')

    parser = JSONLParser()
    # Parse from uuid-2 onwards
    result = parser.parse_jsonl_file(temp_jsonl, start_from_uuid="uuid-2")

    # Should only process uuid-3 (the one after uuid-2)
    assert result.last_message_uuid == "uuid-3"


def test_calculate_file_hash(temp_jsonl):
    """Test file hash calculation"""
    temp_jsonl.write_text('{"test": "content"}')

    parser = JSONLParser()
    hash1 = parser.calculate_file_hash(temp_jsonl)
    hash2 = parser.calculate_file_hash(temp_jsonl)

    # Same file should produce same hash
    assert hash1 == hash2
    assert len(hash1) == 64  # SHA256 hash length


def test_session_summary_extraction(temp_jsonl):
    """Test extraction of session summary"""
    messages = [{
        "uuid": "test-uuid-1",
        "conversation": [{
            "role": "assistant",
            "message": "Let me summarize what we accomplished:\n\n1. Fixed the bug\n2. Added tests",
            "created_at": "2025-01-01T12:00:00Z"
        }]
    }]

    with open(temp_jsonl, 'w') as f:
        f.write(json.dumps(messages[0]) + '\n')

    parser = JSONLParser()
    result = parser.parse_jsonl_file(temp_jsonl)

    # Should have some summary
    assert result.session_summary is not None
