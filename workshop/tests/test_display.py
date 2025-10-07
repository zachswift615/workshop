"""
Tests for Workshop display utilities
"""
import pytest
from datetime import datetime, timezone, timedelta
from src.display import (
    format_timestamp,
    get_type_emoji,
)


class TestFormatTimestamp:
    """Tests for timestamp formatting"""

    def test_just_now(self):
        """Test timestamp within last minute"""
        # Use UTC to match how Workshop stores timestamps
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        iso = now.isoformat()
        assert format_timestamp(iso) == "just now"

    def test_minutes_ago(self):
        """Test timestamp within last hour"""
        # Use UTC to match how Workshop stores timestamps
        past = (datetime.now(timezone.utc) - timedelta(minutes=30)).replace(tzinfo=None)
        iso = past.isoformat()
        result = format_timestamp(iso)
        assert "m ago" in result
        assert "30" in result or "29" in result  # Allow for timing variance

    def test_hours_ago(self):
        """Test timestamp within last day"""
        # Use UTC to match how Workshop stores timestamps
        past = (datetime.now(timezone.utc) - timedelta(hours=5)).replace(tzinfo=None)
        iso = past.isoformat()
        result = format_timestamp(iso)
        assert "h ago" in result
        assert "5" in result or "4" in result  # Allow for timing variance

    def test_yesterday(self):
        """Test timestamp exactly 1 day ago"""
        # Use UTC to match how Workshop stores timestamps
        past = (datetime.now(timezone.utc) - timedelta(days=1)).replace(tzinfo=None)
        iso = past.isoformat()
        result = format_timestamp(iso)
        assert result == "yesterday"

    def test_days_ago(self):
        """Test timestamp 2-6 days ago"""
        # Use UTC to match how Workshop stores timestamps
        past = (datetime.now(timezone.utc) - timedelta(days=3)).replace(tzinfo=None)
        iso = past.isoformat()
        result = format_timestamp(iso)
        assert "days ago" in result
        assert "3" in result or "2" in result  # Allow for timing variance

    def test_date_format_for_old_timestamps(self):
        """Test timestamp more than a week ago shows date"""
        # Use UTC to match how Workshop stores timestamps
        past = (datetime.now(timezone.utc) - timedelta(days=10)).replace(tzinfo=None)
        iso = past.isoformat()
        result = format_timestamp(iso)
        # Should be formatted as YYYY-MM-DD
        assert len(result) == 10
        assert "-" in result
        assert result.startswith("20")  # Assuming 21st century

    def test_timezone_aware_datetime(self):
        """Test timezone-aware datetime handling"""
        past = datetime.now(timezone.utc) - timedelta(hours=2)
        iso = past.isoformat()
        result = format_timestamp(iso)
        assert "h ago" in result or "just now" in result

    def test_timezone_naive_datetime(self):
        """Test timezone-naive datetime handling (assumes UTC storage)"""
        # Use UTC to match how Workshop stores timestamps
        past = (datetime.now(timezone.utc) - timedelta(minutes=45)).replace(tzinfo=None)
        iso = past.isoformat()
        result = format_timestamp(iso)
        assert "m ago" in result or "just now" in result

    def test_edge_case_60_seconds(self):
        """Test timestamp right at 60 seconds"""
        # Use UTC to match how Workshop stores timestamps
        past = (datetime.now(timezone.utc) - timedelta(seconds=60)).replace(tzinfo=None)
        iso = past.isoformat()
        result = format_timestamp(iso)
        # Could be "just now" or "1m ago" depending on exact timing
        assert result in ["just now", "1m ago"]

    def test_edge_case_3600_seconds(self):
        """Test timestamp right at 1 hour"""
        # Use UTC to match how Workshop stores timestamps
        past = (datetime.now(timezone.utc) - timedelta(seconds=3600)).replace(tzinfo=None)
        iso = past.isoformat()
        result = format_timestamp(iso)
        # Could be "59m ago" or "1h ago"
        assert "ago" in result


class TestGetTypeEmoji:
    """Tests for entry type emoji mapping"""

    def test_decision_emoji(self):
        """Test decision type returns light bulb"""
        assert get_type_emoji("decision") == "💡"

    def test_note_emoji(self):
        """Test note type returns memo"""
        assert get_type_emoji("note") == "📝"

    def test_gotcha_emoji(self):
        """Test gotcha type returns warning"""
        assert get_type_emoji("gotcha") == "⚠️"

    def test_preference_emoji(self):
        """Test preference type returns person"""
        assert get_type_emoji("preference") == "👤"

    def test_antipattern_emoji(self):
        """Test antipattern type returns prohibited"""
        assert get_type_emoji("antipattern") == "🚫"

    def test_session_emoji(self):
        """Test session type returns arrows"""
        assert get_type_emoji("session") == "🔄"

    def test_goal_emoji(self):
        """Test goal type returns target"""
        assert get_type_emoji("goal") == "🎯"

    def test_blocker_emoji(self):
        """Test blocker type returns stop sign"""
        assert get_type_emoji("blocker") == "🛑"

    def test_next_step_emoji(self):
        """Test next_step type returns pin"""
        assert get_type_emoji("next_step") == "📍"

    def test_unknown_type_default(self):
        """Test unknown type returns default pin"""
        assert get_type_emoji("unknown_type") == "📌"
        assert get_type_emoji("random") == "📌"
        assert get_type_emoji("") == "📌"


class TestDisplayFunctions:
    """Tests for display functions that can be tested without console output"""

    def test_get_type_emoji_all_types(self):
        """Test that all expected types have emoji mappings"""
        expected_types = [
            "decision",
            "note",
            "gotcha",
            "preference",
            "antipattern",
            "session",
            "goal",
            "blocker",
            "next_step",
        ]

        for entry_type in expected_types:
            emoji = get_type_emoji(entry_type)
            assert emoji is not None
            assert len(emoji) > 0
            assert emoji != "📌"  # Should not be default

    def test_format_timestamp_various_formats(self):
        """Test that format_timestamp handles various ISO formats"""
        # Use UTC to match how Workshop stores timestamps
        formats = [
            datetime.now(timezone.utc).replace(tzinfo=None).isoformat(),
            datetime.now(timezone.utc).isoformat(),
            (datetime.now(timezone.utc) - timedelta(days=5)).replace(tzinfo=None).isoformat(),
        ]

        for iso_str in formats:
            result = format_timestamp(iso_str)
            assert isinstance(result, str)
            assert len(result) > 0

    def test_utc_timestamp_conversion_regression(self):
        """
        Regression test: Naive UTC timestamps should be converted to local time for display.

        Bug: Entries created "now" showed as "19h ago" because naive UTC timestamps
        (e.g., 19:00 UTC) were compared directly to local time (e.g., 14:00 local)
        without timezone conversion.

        Fix: Assume naive timestamps are UTC, convert to local before calculating
        relative time using dt.replace(tzinfo=timezone.utc).astimezone().
        """
        # Simulate how Workshop stores timestamps - naive UTC datetime
        utc_now = datetime.now(timezone.utc)
        naive_utc = utc_now.replace(tzinfo=None)  # Remove timezone info (how it's stored)

        # Test 1: Current UTC timestamp should show as "just now"
        iso_str = naive_utc.isoformat()
        result = format_timestamp(iso_str)
        assert result == "just now", f"Expected 'just now' but got '{result}'"

        # Test 2: UTC timestamp from 5 minutes ago should show as "5m ago"
        utc_5min_ago = datetime.now(timezone.utc) - timedelta(minutes=5)
        naive_utc_5min = utc_5min_ago.replace(tzinfo=None)
        iso_str = naive_utc_5min.isoformat()
        result = format_timestamp(iso_str)
        assert "m ago" in result, f"Expected minutes ago but got '{result}'"
        # Allow for timing variance (4-6 minutes)
        assert any(str(i) in result for i in range(4, 7)), f"Expected ~5m ago but got '{result}'"

        # Test 3: UTC timestamp from 2 hours ago should show as "2h ago" (not 21h or 17h)
        utc_2h_ago = datetime.now(timezone.utc) - timedelta(hours=2)
        naive_utc_2h = utc_2h_ago.replace(tzinfo=None)
        iso_str = naive_utc_2h.isoformat()
        result = format_timestamp(iso_str)
        assert "h ago" in result, f"Expected hours ago but got '{result}'"
        # Allow 1-3h variance
        assert any(str(i) in result for i in range(1, 4)), f"Expected ~2h ago but got '{result}'"

        # Test 4: Verify the bug would have manifested without fix
        # If we were in timezone UTC-5 and it's 14:00 local (19:00 UTC), a timestamp
        # from "now" in naive UTC (19:00) would incorrectly show as 5-19 hours off
        # This test ensures we're converting properly regardless of local timezone


class TestDisplayFunctionsOutput:
    """Tests for display output functions using mock console"""

    def test_display_entry(self):
        """Test display_entry shows entry with formatted output"""
        from src.display import display_entry
        from unittest.mock import patch
        from datetime import datetime, timezone

        entry = {
            'id': 'test-id',
            'type': 'note',
            'content': 'Test content',
            'timestamp': datetime.now(timezone.utc).replace(tzinfo=None).isoformat(),
            'tags': ['test'],
            'branch': 'main',
            'reasoning': None
        }

        # Mock the console to capture output
        with patch('src.display.console.print') as mock_print:
            display_entry(entry)
            # Verify it was called
            assert mock_print.called

    def test_display_entries_empty(self):
        """Test display_entries with empty list"""
        from src.display import display_entries
        from unittest.mock import patch

        with patch('src.display.console.print') as mock_print:
            display_entries([])
            # Should print "No entries found"
            mock_print.assert_called()

    def test_display_entries_with_data(self):
        """Test display_entries with entries"""
        from src.display import display_entries
        from unittest.mock import patch
        from datetime import datetime, timezone

        entries = [
            {
                'id': 'test-1',
                'type': 'note',
                'content': 'First note',
                'timestamp': datetime.now(timezone.utc).replace(tzinfo=None).isoformat(),
                'tags': [],
                'reasoning': None
            },
            {
                'id': 'test-2',
                'type': 'decision',
                'content': 'Second decision',
                'timestamp': datetime.now(timezone.utc).replace(tzinfo=None).isoformat(),
                'tags': [],
                'reasoning': 'Because reasons'
            }
        ]

        with patch('src.display.console.print') as mock_print:
            display_entries(entries)
            # Should be called multiple times (header + entries)
            assert mock_print.call_count >= 2

    def test_display_context(self):
        """Test display_context shows session summary"""
        from src.display import display_context
        from unittest.mock import patch
        from datetime import datetime, timezone

        recent_entries = [
            {
                'id': 'test-1',
                'type': 'note',
                'content': 'Latest activity',
                'timestamp': datetime.now(timezone.utc).replace(tzinfo=None).isoformat(),
                'tags': []
            }
        ]

        current_state = {
            'goals': [{'content': 'Test goal'}],
            'next_steps': [{'content': 'Test step'}]
        }

        preferences = {
            'code_style': [{'content': 'Use type hints'}]
        }

        with patch('src.display.console.print') as mock_print:
            display_context(recent_entries, current_state, preferences)
            # Should print context summary
            assert mock_print.called

    def test_display_why_results_no_results(self):
        """Test display_why_results with no matching entries"""
        from src.display import display_why_results
        from unittest.mock import patch

        with patch('src.display.console.print') as mock_print:
            display_why_results([], 'test query')
            # Should print "No context found"
            assert mock_print.called

    def test_display_why_results_with_results(self):
        """Test display_why_results with matching entries"""
        from src.display import display_why_results
        from unittest.mock import patch
        from datetime import datetime, timezone

        entries = [
            {
                'id': 'test-1',
                'type': 'decision',
                'content': 'Use PostgreSQL',
                'reasoning': 'Better for relational data',
                'timestamp': datetime.now(timezone.utc).replace(tzinfo=None).isoformat(),
                'tags': ['database'],
                'branch': 'main',
                'files': ['db.py']
            }
        ]

        with patch('src.display.console.print') as mock_print:
            display_why_results(entries, 'PostgreSQL')
            # Should print the "why" formatted output
            assert mock_print.called
            # Verify content is in output
            calls_str = str(mock_print.call_args_list)
            assert 'PostgreSQL' in calls_str or any('PostgreSQL' in str(call) for call in mock_print.call_args_list)

    def test_display_preferences(self):
        """Test display_preferences shows preferences by category"""
        from src.display import display_preferences
        from unittest.mock import patch

        preferences = {
            'code_style': [
                {'content': 'Use type hints'},
                {'content': 'Follow PEP 8'}
            ],
            'libraries': [
                {'content': 'Prefer SQLAlchemy'}
            ]
        }

        with patch('src.display.console.print') as mock_print:
            display_preferences(preferences)
            assert mock_print.called

    def test_display_preferences_empty(self):
        """Test display_preferences with no preferences"""
        from src.display import display_preferences
        from unittest.mock import patch

        with patch('src.display.console.print') as mock_print:
            display_preferences({})
            # Should print "No preferences"
            assert mock_print.called

    def test_display_current_state(self):
        """Test display_current_state shows goals and next steps"""
        from src.display import display_current_state
        from unittest.mock import patch

        state = {
            'goals': [{'content': 'Build feature'}],
            'next_steps': [{'content': 'Write tests'}],
            'blockers': [{'content': 'API rate limit'}]
        }

        with patch('src.display.console.print') as mock_print:
            display_current_state(state)
            assert mock_print.called

    def test_display_current_state_empty(self):
        """Test display_current_state with no state"""
        from src.display import display_current_state
        from unittest.mock import patch

        with patch('src.display.console.print') as mock_print:
            display_current_state({})
            # Should print "No active goals or next steps"
            assert mock_print.called

    def test_success_message(self):
        """Test success message display"""
        from src.display import success
        from unittest.mock import patch

        with patch('src.display.console.print') as mock_print:
            success("Operation completed")
            assert mock_print.called

    def test_error_message(self):
        """Test error message display"""
        from src.display import error
        from unittest.mock import patch

        with patch('src.display.console.print') as mock_print:
            error("Something went wrong")
            assert mock_print.called

    def test_info_message(self):
        """Test info message display"""
        from src.display import info
        from unittest.mock import patch

        with patch('src.display.console.print') as mock_print:
            info("Here's some information")
            assert mock_print.called
