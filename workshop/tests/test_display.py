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
        now = datetime.now()
        iso = now.isoformat()
        assert format_timestamp(iso) == "just now"

    def test_minutes_ago(self):
        """Test timestamp within last hour"""
        past = datetime.now() - timedelta(minutes=30)
        iso = past.isoformat()
        result = format_timestamp(iso)
        assert "m ago" in result
        assert "30" in result or "29" in result  # Allow for timing variance

    def test_hours_ago(self):
        """Test timestamp within last day"""
        past = datetime.now() - timedelta(hours=5)
        iso = past.isoformat()
        result = format_timestamp(iso)
        assert "h ago" in result
        assert "5" in result or "4" in result  # Allow for timing variance

    def test_yesterday(self):
        """Test timestamp exactly 1 day ago"""
        past = datetime.now() - timedelta(days=1)
        iso = past.isoformat()
        result = format_timestamp(iso)
        assert result == "yesterday"

    def test_days_ago(self):
        """Test timestamp 2-6 days ago"""
        past = datetime.now() - timedelta(days=3)
        iso = past.isoformat()
        result = format_timestamp(iso)
        assert "days ago" in result
        assert "3" in result or "2" in result  # Allow for timing variance

    def test_date_format_for_old_timestamps(self):
        """Test timestamp more than a week ago shows date"""
        past = datetime.now() - timedelta(days=10)
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
        """Test timezone-naive datetime handling"""
        past = datetime.now() - timedelta(minutes=45)
        iso = past.isoformat()
        result = format_timestamp(iso)
        assert "m ago" in result or "just now" in result

    def test_edge_case_60_seconds(self):
        """Test timestamp right at 60 seconds"""
        past = datetime.now() - timedelta(seconds=60)
        iso = past.isoformat()
        result = format_timestamp(iso)
        # Could be "just now" or "1m ago" depending on exact timing
        assert result in ["just now", "1m ago"]

    def test_edge_case_3600_seconds(self):
        """Test timestamp right at 1 hour"""
        past = datetime.now() - timedelta(seconds=3600)
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
        formats = [
            datetime.now().isoformat(),
            datetime.now(timezone.utc).isoformat(),
            (datetime.now() - timedelta(days=5)).isoformat(),
        ]

        for iso_str in formats:
            result = format_timestamp(iso_str)
            assert isinstance(result, str)
            assert len(result) > 0
