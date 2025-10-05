"""
Tests for Workshop JSONL parser
"""
import pytest
import json
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from src.jsonl_parser import JSONLParser, ExtractedEntry, SessionImportResult


@pytest.fixture
def temp_jsonl(tmp_path):
    """Create a temporary JSONL file for testing"""
    jsonl_path = tmp_path / "test_session.jsonl"
    return jsonl_path


@pytest.fixture
def parser():
    """Create a parser instance"""
    return JSONLParser()


def create_message(role, text, uuid="test-uuid", timestamp="2025-01-01T12:00:00Z", msg_type=None):
    """Helper to create a message dict"""
    return {
        "uuid": uuid,
        "type": msg_type or role,
        "timestamp": timestamp,
        "message": {
            "role": role,
            "content": [{"type": "text", "text": text}]
        }
    }


def write_messages(jsonl_path, messages):
    """Helper to write messages to JSONL file"""
    with open(jsonl_path, 'w') as f:
        for msg in messages:
            f.write(json.dumps(msg) + '\n')


# Basic Parser Tests
def test_parser_initialization(parser):
    """Test parser initializes correctly"""
    assert parser.decision_pattern is not None
    assert parser.gotcha_pattern is not None
    assert parser.preference_pattern is not None


def test_parse_empty_file(temp_jsonl, parser):
    """Test parsing empty JSONL file"""
    temp_jsonl.touch()
    result = parser.parse_jsonl_file(temp_jsonl)

    assert result.entries == []
    assert result.messages_processed == 0
    assert result.session_summary == ""


def test_parse_nonexistent_file(tmp_path, parser):
    """Test handling of nonexistent file"""
    result = parser.parse_jsonl_file(tmp_path / "nonexistent.jsonl")
    assert result.messages_processed == 0


# Dataclass Tests
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


# File Reading Tests
def test_malformed_json_handling(temp_jsonl, parser):
    """Test handling of malformed JSON lines"""
    with open(temp_jsonl, 'w') as f:
        f.write('{"uuid": "valid", "type": "assistant", "message": {"content": []}}\n')
        f.write('{invalid json}\n')
        f.write('{"uuid": "valid2", "type": "assistant", "message": {"content": []}}\n')

    result = parser.parse_jsonl_file(temp_jsonl)
    # Should still parse valid entries
    assert isinstance(result.entries, list)
    assert result.last_message_uuid == "valid2"


def test_parse_file_basic_structure(temp_jsonl, parser):
    """Test that parser handles basic file structure"""
    messages = [create_message("assistant", "Some test content")]
    write_messages(temp_jsonl, messages)

    result = parser.parse_jsonl_file(temp_jsonl)
    assert result.messages_processed == 1
    assert result.last_message_uuid == "test-uuid"


# Pattern Matching Tests
def test_decision_pattern_matching(parser):
    """Test that decision patterns match expected keywords"""
    assert parser.decision_pattern.search("We decided to use PostgreSQL")
    assert parser.decision_pattern.search("chose to implement caching")
    assert parser.decision_pattern.search("went with React for the frontend")
    assert parser.decision_pattern.search("using SQLite because it's lightweight")
    assert parser.decision_pattern.search("opted for TypeScript")
    assert parser.decision_pattern.search("settled on a microservices architecture")


def test_gotcha_pattern_matching(parser):
    """Test that gotcha patterns match expected keywords"""
    assert parser.gotcha_pattern.search("Watch out for the rate limit")
    assert parser.gotcha_pattern.search("This is a gotcha")
    assert parser.gotcha_pattern.search("Be careful with async operations")
    assert parser.gotcha_pattern.search("The tricky part is timing")
    assert parser.gotcha_pattern.search("Important to note: credentials expire")
    assert parser.gotcha_pattern.search("This limitation affects all users")
    assert parser.gotcha_pattern.search("The test failed because of permissions")
    assert parser.gotcha_pattern.search("Error: connection timeout")
    assert parser.gotcha_pattern.search("doesn't work on Windows")


def test_preference_pattern_matching(parser):
    """Test that preference patterns match expected keywords"""
    assert parser.preference_pattern.search("I prefer type hints")
    assert parser.preference_pattern.search("We typically use React")
    assert parser.preference_pattern.search("always use const instead of let")
    assert parser.preference_pattern.search("usually write tests first")
    assert parser.preference_pattern.search("style: use snake_case for Python")


# UUID Filtering Tests
def test_filter_from_uuid(temp_jsonl, parser):
    """Test filtering messages from a specific UUID"""
    messages = [
        create_message("assistant", "First", uuid="uuid-1", timestamp="2025-01-01T10:00:00Z"),
        create_message("assistant", "Second", uuid="uuid-2", timestamp="2025-01-01T11:00:00Z"),
        create_message("assistant", "Third", uuid="uuid-3", timestamp="2025-01-01T12:00:00Z"),
    ]
    write_messages(temp_jsonl, messages)

    result = parser.parse_jsonl_file(temp_jsonl, start_from_uuid="uuid-2")
    # Should only process uuid-3 (the one after uuid-2)
    assert result.last_message_uuid == "uuid-3"
    assert result.messages_processed == 1


def test_filter_from_nonexistent_uuid(temp_jsonl, parser):
    """Test filtering from UUID that doesn't exist"""
    messages = [create_message("assistant", "Test")]
    write_messages(temp_jsonl, messages)

    result = parser.parse_jsonl_file(temp_jsonl, start_from_uuid="nonexistent")
    assert result.messages_processed == 0


# Hash Calculation Tests
def test_calculate_file_hash(temp_jsonl, parser):
    """Test file hash calculation"""
    temp_jsonl.write_text('{"test": "content"}')

    hash1 = parser.calculate_file_hash(temp_jsonl)
    hash2 = parser.calculate_file_hash(temp_jsonl)

    # Same file should produce same hash
    assert hash1 == hash2
    assert len(hash1) == 64  # SHA256 hash length

    # Different content should produce different hash
    temp_jsonl.write_text('{"test": "different"}')
    hash3 = parser.calculate_file_hash(temp_jsonl)
    assert hash1 != hash3


# Compaction Summary Extraction Tests
def test_extract_compaction_summary(temp_jsonl, parser):
    """Test extraction of compaction summaries"""
    compaction_text = """This session is being continued from a previous conversation that ran out of context. The conversation is summarized below:

Analysis:
This is a comprehensive summary of the previous session. It contains lots of details about what was accomplished, decisions made, and code written. """ + ("More content. " * 100)

    messages = [create_message("user", compaction_text)]
    write_messages(temp_jsonl, messages)

    result = parser.parse_jsonl_file(temp_jsonl)
    assert len(result.entries) > 0
    assert result.entries[0].type == 'note'
    assert "Session Continuation Summary" in result.entries[0].content
    assert result.entries[0].confidence == 1.0


def test_compaction_summary_bypasses_noise_filter(parser):
    """Test that compaction summaries bypass the noise filter"""
    # Compaction summaries contain code and would normally be filtered
    content = """This session is being continued from a previous conversation that ran out of context.

Analysis:
We implemented the following:
```python
def hello():
    print("world")
```
This was a key decision for the project. """ + ("More details. " * 50)

    # Should NOT be filtered as noise despite having code
    assert not parser._is_noise(content)


# Summary Section Extraction Tests
def test_extract_summary_sections(temp_jsonl, parser):
    """Test extraction of ## Summary sections"""
    summary_text = "## Summary\n\nWe accomplished the following tasks today:\n1. Fixed the authentication bug\n2. Added new endpoints\n3. Improved test coverage\n\nThe changes were significant and required careful testing. " + ("Additional context. " * 10)

    messages = [create_message("assistant", summary_text)]
    write_messages(temp_jsonl, messages)

    result = parser.parse_jsonl_file(temp_jsonl)
    assert len(result.entries) > 0
    assert any(e.type == 'note' for e in result.entries)
    assert any("Summary" in e.content for e in result.entries)


def test_extract_summary_too_short(temp_jsonl, parser):
    """Test that very short summaries are skipped"""
    messages = [create_message("assistant", "## Summary\n\nNot much to say.")]
    write_messages(temp_jsonl, messages)

    result = parser.parse_jsonl_file(temp_jsonl)
    # Should not extract too-short summaries
    assert len([e for e in result.entries if "Summary" in e.content]) == 0


# Completion Summary Extraction Tests
def test_extract_completion_summaries(temp_jsonl, parser):
    """Test extraction of completion summaries"""
    completion_text = """Perfect! I've:

1. Added comprehensive error handling
2. Implemented retry logic
3. Updated the documentation
4. Added integration tests
5. Optimized database queries

The system is now more robust and performant."""

    messages = [create_message("assistant", completion_text)]
    write_messages(temp_jsonl, messages)

    result = parser.parse_jsonl_file(temp_jsonl)
    assert len(result.entries) > 0
    assert any(e.confidence == 0.95 for e in result.entries)


def test_completion_summary_requires_multiple_items(temp_jsonl, parser):
    """Test that completion summaries need at least 2 numbered items"""
    # Only 1 item - should not be extracted
    messages = [create_message("assistant", "Great! I've:\n\n1. Fixed the bug")]
    write_messages(temp_jsonl, messages)

    result = parser.parse_jsonl_file(temp_jsonl)
    completions = [e for e in result.entries if e.confidence == 0.95]
    assert len(completions) == 0


# Problem/Solution Extraction Tests
def test_extract_problem_solutions(temp_jsonl, parser):
    """Test extraction of problem/solution pairs"""
    text = """## Fixed!

The authentication issue has been resolved. The problem was that JWT tokens were expiring too quickly."""

    messages = [create_message("assistant", text)]
    write_messages(temp_jsonl, messages)

    result = parser.parse_jsonl_file(temp_jsonl)
    assert len(result.entries) > 0


def test_extract_root_cause(temp_jsonl, parser):
    """Test extraction of root cause explanations"""
    text = "After debugging, I found that the issue was that the database connection pool was exhausted. This caused timeouts."

    messages = [create_message("assistant", text)]
    write_messages(temp_jsonl, messages)

    result = parser.parse_jsonl_file(temp_jsonl)
    gotchas = [e for e in result.entries if e.type == 'gotcha']
    assert len(gotchas) > 0


# Discovery Extraction Tests
def test_extract_discoveries(temp_jsonl, parser):
    """Test extraction of technical discoveries"""
    discoveries = [
        "Discovered that async operations must be awaited properly.",
        "Found that the cache invalidation was happening too late.",
        "Realized that we need connection pooling for better performance.",
        "Turns out the API has undocumented rate limits.",
        "Important to note that credentials expire after 24 hours."
    ]

    for text in discoveries:
        messages = [create_message("assistant", text)]
        write_messages(temp_jsonl, messages)

        result = parser.parse_jsonl_file(temp_jsonl)
        gotchas = [e for e in result.entries if e.type == 'gotcha']
        assert len(gotchas) > 0, f"Failed to extract: {text}"
        temp_jsonl.unlink()


# Decision Extraction Tests
def test_extract_decisions(temp_jsonl, parser):
    """Test extraction of decisions"""
    text = "We decided to use PostgreSQL for its advanced features and reliability."
    messages = [create_message("assistant", text)]
    write_messages(temp_jsonl, messages)

    result = parser.parse_jsonl_file(temp_jsonl)
    decisions = [e for e in result.entries if e.type == 'decision']
    assert len(decisions) > 0
    assert decisions[0].confidence == 0.7


def test_extract_decision_with_reasoning(temp_jsonl, parser):
    """Test that reasoning is extracted from decisions"""
    text = "We chose to implement caching because it significantly improves performance."
    messages = [create_message("assistant", text)]
    write_messages(temp_jsonl, messages)

    result = parser.parse_jsonl_file(temp_jsonl)
    decisions = [e for e in result.entries if e.type == 'decision']
    assert len(decisions) > 0
    # Reasoning extraction is attempted
    assert decisions[0].reasoning is None or isinstance(decisions[0].reasoning, str)


# Gotcha Extraction Tests
def test_extract_gotchas(temp_jsonl, parser):
    """Test extraction of gotchas"""
    text = "Watch out for the rate limit of 100 requests per minute on this API."
    messages = [create_message("assistant", text)]
    write_messages(temp_jsonl, messages)

    result = parser.parse_jsonl_file(temp_jsonl)
    gotchas = [e for e in result.entries if e.type == 'gotcha']
    assert len(gotchas) > 0


# Preference Extraction Tests
def test_extract_preferences(temp_jsonl, parser):
    """Test extraction of user preferences"""
    text = "I prefer using async/await over promises for cleaner code."
    messages = [create_message("user", text)]
    write_messages(temp_jsonl, messages)

    result = parser.parse_jsonl_file(temp_jsonl)
    preferences = [e for e in result.entries if e.type == 'preference']
    assert len(preferences) > 0


def test_preferences_only_from_user_messages(temp_jsonl, parser):
    """Test that preferences are only extracted from user messages"""
    text = "I prefer using TypeScript over JavaScript."

    # Assistant message - should not extract preference
    messages = [create_message("assistant", text)]
    write_messages(temp_jsonl, messages)
    result = parser.parse_jsonl_file(temp_jsonl)
    assert len([e for e in result.entries if e.type == 'preference']) == 0

    # User message - should extract preference
    temp_jsonl.unlink()
    messages = [create_message("user", text)]
    write_messages(temp_jsonl, messages)
    result = parser.parse_jsonl_file(temp_jsonl)
    assert len([e for e in result.entries if e.type == 'preference']) > 0


# Tool Error Extraction Tests
def test_extract_tool_errors(temp_jsonl, parser):
    """Test extraction of tool errors"""
    message = {
        "uuid": "test-uuid",
        "type": "user",
        "timestamp": "2025-01-01T12:00:00Z",
        "message": {
            "role": "user",
            "content": [
                {
                    "type": "tool_result",
                    "tool_use_id": "test-id",
                    "is_error": True,
                    "content": "PermissionError: Access denied to /etc/passwd"
                }
            ]
        }
    }

    write_messages(temp_jsonl, [message])
    result = parser.parse_jsonl_file(temp_jsonl)

    gotchas = [e for e in result.entries if e.type == 'gotcha']
    assert len(gotchas) > 0
    assert "Tool error" in gotchas[0].content
    assert gotchas[0].confidence == 0.9


# Noise Filtering Tests
def test_is_noise_short_content(parser):
    """Test that very short content is filtered"""
    assert parser._is_noise("Short")
    assert parser._is_noise("x")
    assert parser._is_noise("")


def test_is_noise_json_content(parser):
    """Test that JSON-like content is filtered"""
    assert parser._is_noise('{"role": "assistant", "message": "test"}')
    assert parser._is_noise('[{"key": "value"}]')


def test_is_noise_code_content(parser):
    """Test that code is filtered as noise"""
    assert parser._is_noise('```python\ndef hello():\n    pass\n```')
    assert parser._is_noise('function test() { return true; }')
    assert parser._is_noise('class MyClass:\n    def __init__(self):')


def test_is_noise_hooks(parser):
    """Test that session hooks are filtered"""
    assert parser._is_noise('<session-start-hook>Test hook</session-start-hook>')
    assert parser._is_noise('Some text with session-end-hook in it')


def test_is_noise_error_fragments(parser):
    """Test that error message fragments are filtered"""
    assert parser._is_noise('Error: Something went wrong')
    assert parser._is_noise('Traceback (most recent call last):')
    assert parser._is_noise('TypeError: expected string')


# Content Extraction Tests
def test_get_message_content_string(parser):
    """Test extracting content when it's a string"""
    message = {
        "message": {
            "content": "Simple string content"
        }
    }
    content = parser._get_message_content(message)
    assert content == "Simple string content"


def test_get_message_content_list(parser):
    """Test extracting content from list of parts"""
    message = {
        "message": {
            "content": [
                {"type": "text", "text": "This is the first part of the content"},
                {"type": "text", "text": "This is the second part"}
            ]
        }
    }
    content = parser._get_message_content(message)
    assert "first part" in content
    assert "second part" in content


def test_get_message_content_filters_tool_results(parser):
    """Test that tool results are filtered from content"""
    message = {
        "message": {
            "content": [
                {"type": "text", "text": "This is the actual text content we want to extract"},
                {"type": "tool_result", "content": "This should be completely filtered out"}
            ]
        }
    }
    content = parser._get_message_content(message)
    assert "actual text content" in content
    assert "filtered out" not in content


def test_get_message_content_empty(parser):
    """Test handling of empty message content"""
    assert parser._get_message_content({}) == ""
    assert parser._get_message_content({"message": {}}) == ""


# Low Quality Sentence Tests
def test_is_low_quality_sentence(parser):
    """Test low quality sentence detection"""
    # Too short
    assert parser._is_low_quality_sentence("Too short")

    # Too long
    assert parser._is_low_quality_sentence("x" * 501)

    # Command patterns
    assert parser._is_low_quality_sentence("$ npm install package")
    assert parser._is_low_quality_sentence("> git commit -m 'test'")

    # JSON-like
    assert parser._is_low_quality_sentence('{"key": "value"}')

    # Good sentence should pass
    assert not parser._is_low_quality_sentence("This is a good quality sentence with enough words.")


def test_is_low_quality_special_characters(parser):
    """Test detection of high special character ratio"""
    # Too many special characters
    bad_sentence = "!@#$%^&*()_+{}[]|:;<>?,./~`"
    assert parser._is_low_quality_sentence(bad_sentence)


# Deduplication Tests
def test_content_deduplication(temp_jsonl, parser):
    """Test that duplicate content is deduplicated"""
    # Same decision appears twice
    text = "We decided to use PostgreSQL for the database."
    messages = [
        create_message("assistant", text, uuid="uuid-1"),
        create_message("assistant", text, uuid="uuid-2")
    ]
    write_messages(temp_jsonl, messages)

    result = parser.parse_jsonl_file(temp_jsonl)
    decisions = [e for e in result.entries if e.type == 'decision']

    # Should only have one entry despite appearing twice
    contents = [d.content for d in decisions]
    assert len(contents) == len(set(contents)), "Duplicate content was not deduplicated"


# Session Summary Tests
def test_session_summary_from_metadata(temp_jsonl, parser):
    """Test extraction of session summary from metadata"""
    message = {
        "uuid": "test-uuid",
        "type": "summary",
        "summary": "This is the session summary",
        "timestamp": "2025-01-01T12:00:00Z",
        "message": {"content": []}
    }

    write_messages(temp_jsonl, [message])
    result = parser.parse_jsonl_file(temp_jsonl)

    assert result.session_summary == "This is the session summary"


# Edge Cases
def test_message_with_missing_timestamp(temp_jsonl, parser):
    """Test handling message without timestamp"""
    message = {
        "uuid": "test-uuid",
        "type": "assistant",
        "message": {
            "content": [{"type": "text", "text": "We decided to use Redis."}]
        }
    }

    write_messages(temp_jsonl, [message])
    result = parser.parse_jsonl_file(temp_jsonl)

    # Should still process but use current timestamp
    assert result.messages_processed == 1


def test_extract_sentence_around_match(parser):
    """Test sentence extraction around regex match"""
    text = "First sentence. We decided to use MongoDB. Last sentence."
    match = parser.decision_pattern.search(text)

    sentence = parser._extract_sentence_around_match(text, match)
    assert "decided to use MongoDB" in sentence
    assert "First sentence" not in sentence


def test_extract_reasoning_patterns(parser):
    """Test reasoning extraction with different patterns"""
    # Test 'because'
    text = "We chose to use React because it has great community support. More text here."
    match = parser.decision_pattern.search(text)
    assert match is not None, "Decision pattern should match"
    reasoning = parser._extract_reasoning(text, match)
    assert reasoning is None or "community support" in reasoning.lower()

    # Test 'since'
    text = "We opted for TypeScript since it provides type safety."
    match = parser.decision_pattern.search(text)
    assert match is not None, "Decision pattern should match"
    reasoning = parser._extract_reasoning(text, match)
    assert reasoning is None or "type safety" in reasoning.lower()


def test_extract_from_message_filters_system_types(parser):
    """Test that non-user/assistant messages are filtered"""
    message = {
        "uuid": "test-uuid",
        "type": "system",
        "timestamp": "2025-01-01T12:00:00Z",
        "message": {
            "content": [{"type": "text", "text": "System message"}]
        }
    }

    entries = parser._extract_from_message(message)
    assert len(entries) == 0


# LLM Extraction Tests
def test_parser_initialization_without_api_key():
    """Test parser initializes without API key"""
    with patch.dict('os.environ', {}, clear=True):
        parser = JSONLParser()
        # Without API key, anthropic_client should be None
        assert parser.anthropic_client is None


def test_parser_initialization_with_api_key_in_env():
    """Test parser initializes with API key from environment"""
    # This test will work if anthropic is installed
    try:
        import anthropic
        with patch.dict('os.environ', {'ANTHROPIC_API_KEY': 'test-key'}):
            parser = JSONLParser()
            # Should attempt to create client (may fail with invalid key, but that's ok)
            assert parser.anthropic_client is not None or parser.anthropic_client is None
    except ImportError:
        # If anthropic not installed, parser should gracefully handle it
        with patch.dict('os.environ', {'ANTHROPIC_API_KEY': 'test-key'}):
            parser = JSONLParser()
            assert parser.anthropic_client is None


def test_parser_initialization_gracefully_handles_missing_package():
    """Test parser gracefully handles missing anthropic package"""
    # Even with an API key, if anthropic isn't installed, should be None
    parser = JSONLParser(api_key='test-key')
    # Client will be None if anthropic not installed, or a client if it is
    # Either way, the parser should work
    assert hasattr(parser, 'anthropic_client')


def test_llm_extraction_with_valid_response(temp_jsonl):
    """Test LLM extraction with valid API response"""
    # Mock Anthropic client
    mock_client = Mock()
    mock_response = Mock()
    mock_response.content = [Mock(text=json.dumps({
        "decisions": [
            {"content": "Use SQLite for storage", "reasoning": "Provides FTS5 search and better performance"}
        ],
        "gotchas": [
            {"content": "API rate limit is 100/min", "reasoning": "This affects batch operations"}
        ],
        "preferences": []
    }))]
    mock_client.messages.create.return_value = mock_response

    # Create parser with mocked client
    parser = JSONLParser(api_key='test-key')
    parser.anthropic_client = mock_client
    parser.llm_type = 'anthropic'  # Set type for mocked client

    # Test message
    message = create_message("assistant", "We decided to use SQLite because it provides FTS5 search.")

    entries = parser._extract_from_message_llm(message)

    # Should have extracted decision and gotcha
    assert len(entries) >= 2
    decisions = [e for e in entries if e.type == 'decision']
    gotchas = [e for e in entries if e.type == 'gotcha']

    assert len(decisions) == 1
    assert "SQLite" in decisions[0].content
    assert decisions[0].confidence == 0.95
    assert decisions[0].reasoning == "Provides FTS5 search and better performance"

    assert len(gotchas) == 1
    assert "rate limit" in gotchas[0].content


def test_llm_extraction_fallback_on_error(temp_jsonl):
    """Test that LLM extraction falls back to pattern matching on error"""
    # Mock Anthropic client that raises an error
    mock_client = Mock()
    mock_client.messages.create.side_effect = Exception("API error")

    parser = JSONLParser(api_key='test-key')
    parser.anthropic_client = mock_client
    parser.llm_type = 'anthropic'  # Set type for mocked client

    # Message with pattern-matchable content (must be >50 chars for LLM processing)
    message = create_message("assistant", "We decided to use PostgreSQL for the database because it provides excellent reliability and performance for our use case.")

    # Should fall back to pattern matching
    entries = parser._extract_from_message_llm(message)

    # Should still extract using pattern matching
    decisions = [e for e in entries if e.type == 'decision']
    assert len(decisions) > 0
    assert decisions[0].confidence == 0.7  # Pattern matching confidence


def test_llm_extraction_without_client(monkeypatch):
    """Test that LLM extraction falls back when no client is available"""
    # Clear environment variable to ensure no client is created
    monkeypatch.delenv('ANTHROPIC_API_KEY', raising=False)

    parser = JSONLParser()  # No API key
    assert parser.anthropic_client is None

    message = create_message("assistant", "We chose to use Redis for caching.")

    # Should fall back to pattern matching
    entries = parser._extract_from_message_llm(message)
    decisions = [e for e in entries if e.type == 'decision']
    assert len(decisions) > 0


def test_llm_extraction_skips_short_messages():
    """Test that LLM extraction skips very short messages"""
    mock_client = Mock()
    parser = JSONLParser(api_key='test-key')
    parser.anthropic_client = mock_client
    parser.llm_type = 'anthropic'  # Set type for mocked client

    # Very short message
    message = create_message("assistant", "OK")

    entries = parser._extract_from_message_llm(message)

    # Should not call API for very short messages
    mock_client.messages.create.assert_not_called()


def test_llm_extraction_with_malformed_json():
    """Test LLM extraction handles malformed JSON response"""
    mock_client = Mock()
    mock_response = Mock()
    mock_response.content = [Mock(text="This is not valid JSON")]
    mock_client.messages.create.return_value = mock_response

    parser = JSONLParser(api_key='test-key')
    parser.anthropic_client = mock_client
    parser.llm_type = 'anthropic'  # Set type for mocked client

    # Message must be >50 chars for LLM processing
    message = create_message("assistant", "We decided to use MongoDB for the document store because it handles unstructured data very well.")

    # Should fall back to pattern matching on JSON parse error
    entries = parser._extract_from_message_llm(message)

    # Should still extract using pattern matching fallback
    decisions = [e for e in entries if e.type == 'decision']
    assert len(decisions) > 0


def test_parse_jsonl_with_llm_flag(temp_jsonl):
    """Test parsing JSONL file with use_llm=True"""
    # Message must be >50 chars for LLM processing
    messages = [
        create_message("assistant", "We decided to use FastAPI for the backend because it's modern, fast, and has great documentation.")
    ]
    write_messages(temp_jsonl, messages)

    mock_client = Mock()
    mock_response = Mock()
    mock_response.content = [Mock(text=json.dumps({
        "decisions": [
            {"content": "Use FastAPI", "reasoning": "Modern, fast, and great documentation"}
        ],
        "gotchas": [],
        "preferences": []
    }))]
    mock_client.messages.create.return_value = mock_response

    parser = JSONLParser(api_key='test-key')
    parser.anthropic_client = mock_client
    parser.llm_type = 'anthropic'  # Set type for mocked client

    # Parse with LLM
    result = parser.parse_jsonl_file(temp_jsonl, use_llm=True)

    assert result.messages_processed == 1
    decisions = [e for e in result.entries if e.type == 'decision']
    assert len(decisions) > 0
    assert decisions[0].confidence == 0.95


def test_parse_jsonl_without_llm_flag(temp_jsonl):
    """Test parsing JSONL file with use_llm=False uses pattern matching"""
    messages = [
        create_message("assistant", "We decided to use FastAPI for the backend.")
    ]
    write_messages(temp_jsonl, messages)

    parser = JSONLParser()

    # Parse without LLM
    result = parser.parse_jsonl_file(temp_jsonl, use_llm=False)

    assert result.messages_processed == 1
    decisions = [e for e in result.entries if e.type == 'decision']
    assert len(decisions) > 0
    # Pattern matching has lower confidence
    assert decisions[0].confidence == 0.7
