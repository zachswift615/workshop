"""
Tests for Workshop JSONL parser
"""
import pytest
import json
from pathlib import Path
from datetime import datetime
from src.jsonl_parser import JSONLParser, ExtractedEntry


@pytest.fixture
def temp_jsonl(tmp_path):
    """Create a temporary JSONL file for testing"""
    jsonl_path = tmp_path / "test_session.jsonl"
    return jsonl_path


def write_jsonl_messages(jsonl_path, messages):
    """Helper to write messages to JSONL file"""
    with open(jsonl_path, 'w') as f:
        for msg in messages:
            f.write(json.dumps(msg) + '\n')


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


def test_parse_assistant_decision(temp_jsonl):
    """Test extracting decisions from assistant messages"""
    messages = [
        {
            "uuid": "test-uuid-1",
            "conversation": [
                {
                    "role": "assistant",
                    "message": "I've decided to use PostgreSQL for the database.",
                    "created_at": "2025-01-01T12:00:00Z"
                }
            ]
        }
    ]
    write_jsonl_messages(temp_jsonl, messages)

    parser = JSONLParser()
    result = parser.parse_jsonl_file(temp_jsonl)

    decision_entries = [e for e in result.entries if e.type == 'decision']
    assert len(decision_entries) > 0


def test_parse_gotcha(temp_jsonl):
    """Test extracting gotchas/constraints"""
    messages = [
        {
            "uuid": "test-uuid-3",
            "conversation": [
                {
                    "role": "assistant",
                    "message": "Important gotcha: the API rate limit is 100 requests per minute.",
                    "created_at": "2025-01-01T14:00:00Z"
                }
            ]
        }
    ]
    write_jsonl_messages(temp_jsonl, messages)

    parser = JSONLParser()
    result = parser.parse_jsonl_file(temp_jsonl)

    gotcha_entries = [e for e in result.entries if e.type == 'gotcha']
    assert len(gotcha_entries) > 0
    assert "rate limit" in gotcha_entries[0].content.lower()


def test_parse_preference(temp_jsonl):
    """Test extracting user preferences"""
    messages = [
        {
            "uuid": "test-uuid-4",
            "conversation": [
                {
                    "role": "user",
                    "message": "I prefer using tabs over spaces for indentation.",
                    "created_at": "2025-01-01T15:00:00Z"
                }
            ]
        }
    ]
    write_jsonl_messages(temp_jsonl, messages)

    parser = JSONLParser()
    result = parser.parse_jsonl_file(temp_jsonl)

    pref_entries = [e for e in result.entries if e.type == 'preference']
    assert len(pref_entries) > 0


def test_parse_compaction_summary(temp_jsonl):
    """Test extracting compaction summaries"""
    messages = [
        {
            "uuid": "test-uuid-5",
            "conversation": [
                {
                    "role": "user",
                    "message": "This session is being continued from a previous conversation that ran out of context.\n\nAnalysis:\nLet me chronologically analyze this conversation:\n\n**Session Start Context:**\nUser was working on Workshop v0.2.0 with the following features:\n- SQLite storage with FTS5 search\n- JSONL import from Claude sessions\n- CLI commands for notes, decisions, gotchas\n\n**Main Work:**\n1. Added import feature for Claude JSONL files\n2. Implemented deduplication using MD5 hashes\n3. Created comprehensive README documentation\n\n**Technical Details:**\n- Database location: .workshop/workshop.db\n- JSONL location: ~/.claude/projects/\n- Path normalization: /Users/name/project → -Users-name-project",
                    "created_at": "2025-01-01T16:00:00Z"
                }
            ]
        }
    ]
    write_jsonl_messages(temp_jsonl, messages)

    parser = JSONLParser()
    result = parser.parse_jsonl_file(temp_jsonl)

    # Should find compaction summary
    summary_entries = [e for e in result.entries if "Session Continuation Summary" in e.content]
    assert len(summary_entries) > 0
    assert len(summary_entries[0].content) > 500  # Should be substantial


def test_timestamp_extraction(temp_jsonl):
    """Test that timestamps are correctly extracted"""
    timestamp = "2025-01-01T20:00:00Z"
    messages = [
        {
            "uuid": "test-uuid-11",
            "conversation": [
                {
                    "role": "assistant",
                    "message": "I've decided to use React for the frontend.",
                    "created_at": timestamp
                }
            ]
        }
    ]
    write_jsonl_messages(temp_jsonl, messages)

    parser = JSONLParser()
    result = parser.parse_jsonl_file(temp_jsonl)

    assert result.last_message_timestamp == timestamp


def test_source_uuid_tracking(temp_jsonl):
    """Test that source UUIDs are tracked"""
    uuid = "test-uuid-12"
    messages = [
        {
            "uuid": uuid,
            "conversation": [
                {
                    "role": "assistant",
                    "message": "I'm noting that TypeScript is preferred for this project.",
                    "created_at": "2025-01-01T21:00:00Z"
                }
            ]
        }
    ]
    write_jsonl_messages(temp_jsonl, messages)

    parser = JSONLParser()
    result = parser.parse_jsonl_file(temp_jsonl)

    assert result.last_message_uuid == uuid
    if len(result.entries) > 0:
        assert result.entries[0].source_uuid == uuid


def test_multiple_messages_in_conversation(temp_jsonl):
    """Test parsing multiple messages within a conversation"""
    messages = [
        {
            "uuid": "test-uuid-14",
            "conversation": [
                {
                    "role": "user",
                    "message": "What should we use for authentication?",
                    "created_at": "2025-01-01T23:00:00Z"
                },
                {
                    "role": "assistant",
                    "message": "I recommend using JWT tokens for authentication.",
                    "created_at": "2025-01-01T23:01:00Z"
                },
                {
                    "role": "assistant",
                    "message": "Important gotcha: JWT tokens should have short expiration times.",
                    "created_at": "2025-01-01T23:02:00Z"
                }
            ]
        }
    ]
    write_jsonl_messages(temp_jsonl, messages)

    parser = JSONLParser()
    result = parser.parse_jsonl_file(temp_jsonl)

    # Should process multiple messages
    assert result.messages_processed >= 3


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
    from src.jsonl_parser import SessionImportResult

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
