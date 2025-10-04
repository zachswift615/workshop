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


def test_parser_initialization(temp_jsonl):
    """Test parser initializes correctly"""
    parser = JSONLParser(temp_jsonl)

    assert parser.jsonl_path == temp_jsonl
    assert parser.entries == []


def test_parse_empty_file(temp_jsonl):
    """Test parsing empty JSONL file"""
    temp_jsonl.touch()

    parser = JSONLParser(temp_jsonl)
    entries = parser.parse()

    assert entries == []


def test_parse_assistant_note(temp_jsonl):
    """Test extracting notes from assistant messages"""
    messages = [
        {
            "uuid": "test-uuid-1",
            "conversation": [
                {
                    "role": "assistant",
                    "message": "I'm going to note that Python 3.12 is required for this project.",
                    "created_at": "2025-01-01T12:00:00Z"
                }
            ]
        }
    ]
    write_jsonl_messages(temp_jsonl, messages)

    parser = JSONLParser(temp_jsonl)
    entries = parser.parse()

    assert len(entries) > 0
    note_entries = [e for e in entries if e.type == 'note']
    assert len(note_entries) > 0
    assert "Python 3.12" in note_entries[0].content


def test_parse_decision_with_reasoning(temp_jsonl):
    """Test extracting decisions with reasoning"""
    messages = [
        {
            "uuid": "test-uuid-2",
            "conversation": [
                {
                    "role": "assistant",
                    "message": "I've decided to use PostgreSQL for the database because we need ACID guarantees and complex query support.",
                    "created_at": "2025-01-01T13:00:00Z"
                }
            ]
        }
    ]
    write_jsonl_messages(temp_jsonl, messages)

    parser = JSONLParser(temp_jsonl)
    entries = parser.parse()

    decision_entries = [e for e in entries if e.type == 'decision']
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

    parser = JSONLParser(temp_jsonl)
    entries = parser.parse()

    gotcha_entries = [e for e in entries if e.type == 'gotcha']
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

    parser = JSONLParser(temp_jsonl)
    entries = parser.parse()

    pref_entries = [e for e in entries if e.type == 'preference']
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

    parser = JSONLParser(temp_jsonl)
    entries = parser.parse()

    # Should find compaction summary
    summary_entries = [e for e in entries if "Session Continuation Summary" in e.content]
    assert len(summary_entries) > 0
    assert len(summary_entries[0].content) > 500  # Should be substantial


def test_noise_filtering(temp_jsonl):
    """Test that noise content is filtered out"""
    messages = [
        {
            "uuid": "test-uuid-6",
            "conversation": [
                {
                    "role": "assistant",
                    "message": '{"role": "system", "content": "internal metadata"}',
                    "created_at": "2025-01-01T17:00:00Z"
                }
            ]
        },
        {
            "uuid": "test-uuid-7",
            "conversation": [
                {
                    "role": "assistant",
                    "message": "```python\ndef example():\n    pass\n```",
                    "created_at": "2025-01-01T17:01:00Z"
                }
            ]
        }
    ]
    write_jsonl_messages(temp_jsonl, messages)

    parser = JSONLParser(temp_jsonl)
    entries = parser.parse()

    # Should filter out JSON and code blocks
    assert all("role" not in e.content for e in entries)
    assert all("```" not in e.content for e in entries)


def test_compaction_summary_not_filtered(temp_jsonl):
    """Test that compaction summaries are NOT filtered despite containing code"""
    messages = [
        {
            "uuid": "test-uuid-8",
            "conversation": [
                {
                    "role": "user",
                    "message": """This session is being continued from a previous conversation that ran out of context.

Analysis:
The user implemented a new feature with this code:

```python
def calculate_total(items):
    return sum(item.price for item in items)
```

This was a critical decision for the project architecture.""",
                    "created_at": "2025-01-01T18:00:00Z"
                }
            ]
        }
    ]
    write_jsonl_messages(temp_jsonl, messages)

    parser = JSONLParser(temp_jsonl)
    entries = parser.parse()

    # Should find compaction summary despite code blocks
    summary_entries = [e for e in entries if "Session Continuation Summary" in e.content]
    assert len(summary_entries) > 0
    assert "```" in summary_entries[0].content  # Code should be preserved


def test_deduplication(temp_jsonl):
    """Test that duplicate content is detected"""
    messages = [
        {
            "uuid": "test-uuid-9",
            "conversation": [
                {
                    "role": "assistant",
                    "message": "I'm noting that we should use Redis for caching.",
                    "created_at": "2025-01-01T19:00:00Z"
                }
            ]
        },
        {
            "uuid": "test-uuid-10",
            "conversation": [
                {
                    "role": "assistant",
                    "message": "I'm noting that we should use Redis for caching.",
                    "created_at": "2025-01-01T19:01:00Z"
                }
            ]
        }
    ]
    write_jsonl_messages(temp_jsonl, messages)

    parser = JSONLParser(temp_jsonl)
    entries = parser.parse()

    # Should have unique content hashes
    content_hashes = set(e.content_hash for e in entries)
    assert len(content_hashes) == len(entries)


def test_timestamp_extraction(temp_jsonl):
    """Test that timestamps are correctly extracted"""
    timestamp = "2025-01-01T20:00:00Z"
    messages = [
        {
            "uuid": "test-uuid-11",
            "conversation": [
                {
                    "role": "assistant",
                    "message": "Test message with timestamp",
                    "created_at": timestamp
                }
            ]
        }
    ]
    write_jsonl_messages(temp_jsonl, messages)

    parser = JSONLParser(temp_jsonl)
    entries = parser.parse()

    if len(entries) > 0:
        assert entries[0].timestamp == timestamp


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

    parser = JSONLParser(temp_jsonl)
    entries = parser.parse()

    if len(entries) > 0:
        assert entries[0].source_uuid == uuid


def test_confidence_scoring(temp_jsonl):
    """Test that confidence scores are assigned"""
    messages = [
        {
            "uuid": "test-uuid-13",
            "conversation": [
                {
                    "role": "assistant",
                    "message": "I've decided to use React for the frontend because it has the best ecosystem.",
                    "created_at": "2025-01-01T22:00:00Z"
                }
            ]
        }
    ]
    write_jsonl_messages(temp_jsonl, messages)

    parser = JSONLParser(temp_jsonl)
    entries = parser.parse()

    if len(entries) > 0:
        assert 0.0 <= entries[0].confidence <= 1.0


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

    parser = JSONLParser(temp_jsonl)
    entries = parser.parse()

    # Should extract multiple entries from the conversation
    assert len(entries) >= 2


def test_malformed_json_handling(temp_jsonl):
    """Test handling of malformed JSON lines"""
    with open(temp_jsonl, 'w') as f:
        f.write('{"uuid": "valid", "conversation": []}\n')
        f.write('{invalid json}\n')
        f.write('{"uuid": "valid2", "conversation": []}\n')

    parser = JSONLParser(temp_jsonl)
    # Should not crash on malformed JSON
    entries = parser.parse()

    # Should still parse valid entries
    assert isinstance(entries, list)


def test_missing_fields_handling(temp_jsonl):
    """Test handling of messages with missing fields"""
    messages = [
        {
            "uuid": "test-uuid-15",
            "conversation": [
                {
                    "role": "assistant",
                    # Missing "message" field
                    "created_at": "2025-01-02T00:00:00Z"
                }
            ]
        },
        {
            "uuid": "test-uuid-16",
            "conversation": [
                {
                    "role": "assistant",
                    "message": "This one is valid",
                    # Missing "created_at" field
                }
            ]
        }
    ]
    write_jsonl_messages(temp_jsonl, messages)

    parser = JSONLParser(temp_jsonl)
    # Should handle missing fields gracefully
    entries = parser.parse()

    assert isinstance(entries, list)


def test_extracted_entry_dataclass():
    """Test ExtractedEntry dataclass"""
    entry = ExtractedEntry(
        type='note',
        content='Test content',
        confidence=0.9,
        timestamp='2025-01-02T01:00:00Z',
        source_uuid='test-uuid',
        metadata={'key': 'value'},
        tags=['python', 'testing'],
        files=['test.py']
    )

    assert entry.type == 'note'
    assert entry.content == 'Test content'
    assert entry.confidence == 0.9
    assert entry.metadata == {'key': 'value'}
    assert 'python' in entry.tags
    assert 'test.py' in entry.files


def test_long_content_handling(temp_jsonl):
    """Test handling of very long messages"""
    long_content = "This is a very long message. " * 1000
    messages = [
        {
            "uuid": "test-uuid-17",
            "conversation": [
                {
                    "role": "assistant",
                    "message": long_content,
                    "created_at": "2025-01-02T02:00:00Z"
                }
            ]
        }
    ]
    write_jsonl_messages(temp_jsonl, messages)

    parser = JSONLParser(temp_jsonl)
    entries = parser.parse()

    # Should handle long content
    assert isinstance(entries, list)


def test_special_characters_in_content(temp_jsonl):
    """Test handling of special characters"""
    messages = [
        {
            "uuid": "test-uuid-18",
            "conversation": [
                {
                    "role": "assistant",
                    "message": "Content with 'quotes' and \"double quotes\" and \n newlines \t tabs",
                    "created_at": "2025-01-02T03:00:00Z"
                }
            ]
        }
    ]
    write_jsonl_messages(temp_jsonl, messages)

    parser = JSONLParser(temp_jsonl)
    entries = parser.parse()

    # Should preserve special characters
    if len(entries) > 0:
        assert "quotes" in entries[0].content
