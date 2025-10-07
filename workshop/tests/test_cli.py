"""
Tests for Workshop CLI commands
"""
import tempfile
import shutil
from pathlib import Path
from click.testing import CliRunner
import pytest
from unittest.mock import patch, MagicMock

from src.cli import (
    main, note, decision, gotcha, preference, recent, search, context, info, web,
    goal, next as next_cmd, antipattern, why, export, delete, clean, sessions, session,
    summary, state, preferences, read, clear
)


@pytest.fixture
def temp_workspace(monkeypatch):
    """Create a temporary workspace for testing"""
    import src.cli
    import os
    # Reset global storage before each test
    src.cli.storage = None

    temp_dir = Path(tempfile.mkdtemp())
    # Create .workshop directory
    workshop_dir = temp_dir / ".workshop"
    workshop_dir.mkdir(exist_ok=True)

    # Set WORKSHOP_DIR environment variable to avoid workspace prompts
    monkeypatch.setenv('WORKSHOP_DIR', str(workshop_dir))

    yield temp_dir
    shutil.rmtree(temp_dir, ignore_errors=True)

    # Reset global storage after test
    src.cli.storage = None


@pytest.fixture
def runner():
    """Create a Click CLI runner"""
    return CliRunner()


def test_note_command(runner, temp_workspace, monkeypatch):
    """Test adding a note via CLI"""
    monkeypatch.chdir(temp_workspace)
    result = runner.invoke(note, ['Test note content'])
    assert result.exit_code == 0
    assert 'Note added' in result.output or 'added' in result.output.lower()


def test_decision_command(runner, temp_workspace, monkeypatch):
    """Test adding a decision via CLI"""
    monkeypatch.chdir(temp_workspace)
    result = runner.invoke(decision, ['Use SQLite', '-r', 'Better performance'])
    assert result.exit_code == 0, f"Command failed with: {result.output}"
    assert 'added' in result.output.lower() or 'decision' in result.output.lower()


def test_gotcha_command(runner, temp_workspace, monkeypatch):
    """Test adding a gotcha via CLI"""
    monkeypatch.chdir(temp_workspace)
    result = runner.invoke(gotcha, ['Watch out for rate limits'])
    assert result.exit_code == 0, f"Command failed with: {result.output}"


def test_preference_command(runner, temp_workspace, monkeypatch):
    """Test adding a preference via CLI"""
    monkeypatch.chdir(temp_workspace)
    result = runner.invoke(preference, ['Use type hints everywhere'])
    assert result.exit_code == 0, f"Command failed with: {result.output}"


def test_recent_command(runner, temp_workspace, monkeypatch):
    """Test listing recent entries"""
    monkeypatch.chdir(temp_workspace)
    # Add an entry first
    runner.invoke(note, ['Sample note'])
    # Then list recent
    result = runner.invoke(recent, [])
    assert result.exit_code == 0, f"Command failed with: {result.output}"


def test_search_command(runner, temp_workspace, monkeypatch):
    """Test searching entries"""
    monkeypatch.chdir(temp_workspace)
    # Add an entry first
    runner.invoke(note, ['PostgreSQL database'])
    # Search for it
    result = runner.invoke(search, ['PostgreSQL'])
    assert result.exit_code == 0, f"Command failed with: {result.output}"


def test_context_command(runner, temp_workspace, monkeypatch):
    """Test showing context"""
    monkeypatch.chdir(temp_workspace)
    result = runner.invoke(context, [])
    assert result.exit_code == 0, f"Command failed with: {result.output}"


def test_info_command(runner, temp_workspace, monkeypatch):
    """Test showing workspace info"""
    monkeypatch.chdir(temp_workspace)
    result = runner.invoke(info, [])
    assert result.exit_code == 0, f"Command failed with: {result.output}"
    assert 'Workshop' in result.output or 'Database' in result.output


def test_main_help(runner):
    """Test main help command"""
    result = runner.invoke(main, ['--help'])
    assert result.exit_code == 0
    assert 'Workshop' in result.output or 'Usage' in result.output


def test_note_with_tags(runner, temp_workspace, monkeypatch):
    """Test adding a note with tags"""
    monkeypatch.chdir(temp_workspace)
    result = runner.invoke(note, ['Test note', '-t', 'backend', '-t', 'api'])
    assert result.exit_code == 0, f"Command failed with: {result.output}"


def test_decision_without_reasoning(runner, temp_workspace, monkeypatch):
    """Test adding a decision without reasoning"""
    monkeypatch.chdir(temp_workspace)
    result = runner.invoke(decision, ['Use React'])
    assert result.exit_code == 0, f"Command failed with: {result.output}"


def test_changes_to_project_root(runner, temp_workspace, monkeypatch):
    """Test that CLI changes to project root when run from nested directory"""
    import src.cli
    import os

    # Reset global storage
    src.cli.storage = None

    # Create nested directory structure
    nested_dir = temp_workspace / "deep" / "nested" / "dir"
    nested_dir.mkdir(parents=True)

    # Set WORKSHOP_DIR to avoid interactive prompt
    monkeypatch.setenv('WORKSHOP_DIR', str(temp_workspace / '.workshop'))

    # Change to nested directory
    monkeypatch.chdir(nested_dir)
    assert Path.cwd().resolve() == nested_dir.resolve()

    # Run a workshop command
    result = runner.invoke(note, ['Test from nested dir'])
    assert result.exit_code == 0, f"Command failed with: {result.output}"

    # After command, we should have changed to project root
    # (parent of .workshop directory)
    expected_root = temp_workspace.resolve()
    actual_cwd = Path.cwd().resolve()
    assert actual_cwd == expected_root, f"Expected to be in {expected_root}, but in {actual_cwd}"

    # Reset storage for other tests
    src.cli.storage = None


@patch('src.cli.get_storage')
def test_web_command_passes_workspace(mock_get_storage, runner, temp_workspace, monkeypatch):
    """
    Regression test: Web UI should use workspace from where command was run.

    Bug: When running 'workshop web' in project A, then cd to project B and running
    'workshop web' again, the UI showed project A's data instead of project B's.

    Fix: CLI now explicitly passes workspace_dir to Flask app.run()
    """
    pytest.importorskip("flask", reason="Flask not installed")

    # Mock storage to return our temp workspace
    mock_store = MagicMock()
    mock_store.workspace_dir = temp_workspace / ".workshop"
    mock_get_storage.return_value = mock_store

    # Mock Flask's run to prevent actual server startup and capture arguments
    with patch('src.web.app.run') as mock_flask_run:
        mock_flask_run.return_value = None

        # Run the web command
        result = runner.invoke(web, [])

        # Should succeed
        assert result.exit_code == 0, f"Command failed with: {result.output}"

        # Verify Flask run was called with the correct workspace_dir
        mock_flask_run.assert_called_once()
        call_kwargs = mock_flask_run.call_args[1]

        # The workspace_dir should be set and point to our temp workspace
        assert 'workspace_dir' in call_kwargs, "workspace_dir not passed to Flask app.run()"
        assert call_kwargs['workspace_dir'] is not None, "workspace_dir is None"
        assert str(temp_workspace) in str(call_kwargs['workspace_dir']), \
            f"workspace_dir {call_kwargs['workspace_dir']} doesn't match expected {temp_workspace}"


# ============================================================================
# GOAL MANAGEMENT TESTS
# ============================================================================

def test_goal_add(runner, temp_workspace, monkeypatch):
    """Test adding a goal"""
    monkeypatch.chdir(temp_workspace)
    result = runner.invoke(goal, ['add', 'Build authentication system'])
    assert result.exit_code == 0, f"Command failed with: {result.output}"
    assert 'Goal added' in result.output or 'added' in result.output.lower()


def test_goal_list_empty(runner, temp_workspace, monkeypatch):
    """Test listing goals when none exist"""
    monkeypatch.chdir(temp_workspace)
    result = runner.invoke(goal, ['list'])
    assert result.exit_code == 0, f"Command failed with: {result.output}"
    assert 'No active goals' in result.output or 'no' in result.output.lower()


def test_goal_list_with_goals(runner, temp_workspace, monkeypatch):
    """Test listing goals"""
    monkeypatch.chdir(temp_workspace)
    # Add goals
    runner.invoke(goal, ['add', 'First goal'])
    runner.invoke(goal, ['add', 'Second goal'])
    # List them
    result = runner.invoke(goal, ['list'])
    assert result.exit_code == 0, f"Command failed with: {result.output}"
    assert 'First goal' in result.output
    assert 'Second goal' in result.output


def test_goal_done(runner, temp_workspace, monkeypatch):
    """Test marking a goal as done"""
    monkeypatch.chdir(temp_workspace)
    # Add a goal
    runner.invoke(goal, ['add', 'Implement user login'])
    # Mark it done
    result = runner.invoke(goal, ['done', 'Implement user login'])
    assert result.exit_code == 0, f"Command failed with: {result.output}"
    assert 'completed' in result.output.lower() or 'done' in result.output.lower()


def test_goal_done_not_found(runner, temp_workspace, monkeypatch):
    """Test marking a non-existent goal as done"""
    monkeypatch.chdir(temp_workspace)
    result = runner.invoke(goal, ['done', 'Nonexistent goal'])
    assert result.exit_code == 0, f"Command failed with: {result.output}"
    assert 'No matching' in result.output or 'not found' in result.output.lower()


def test_goal_clean(runner, temp_workspace, monkeypatch):
    """Test cleaning completed goals"""
    monkeypatch.chdir(temp_workspace)
    # Add and complete a goal
    runner.invoke(goal, ['add', 'Test goal'])
    runner.invoke(goal, ['done', 'Test goal'])
    # Clean completed goals
    result = runner.invoke(goal, ['clean'])
    assert result.exit_code == 0, f"Command failed with: {result.output}"
    assert 'Removed' in result.output or 'removed' in result.output.lower()


def test_goal_clear(runner, temp_workspace, monkeypatch):
    """Test clearing all goals"""
    monkeypatch.chdir(temp_workspace)
    # Add some goals
    runner.invoke(goal, ['add', 'Goal 1'])
    runner.invoke(goal, ['add', 'Goal 2'])
    # Clear them
    result = runner.invoke(goal, ['clear'])
    assert result.exit_code == 0, f"Command failed with: {result.output}"
    assert 'cleared' in result.output.lower()


# ============================================================================
# NEXT STEPS TESTS
# ============================================================================

def test_next_add(runner, temp_workspace, monkeypatch):
    """Test adding a next step"""
    monkeypatch.chdir(temp_workspace)
    result = runner.invoke(next_cmd, ['add', 'Write unit tests'])
    assert result.exit_code == 0, f"Command failed with: {result.output}"
    assert 'Next step added' in result.output or 'added' in result.output.lower()


def test_next_done(runner, temp_workspace, monkeypatch):
    """Test marking a next step as done"""
    monkeypatch.chdir(temp_workspace)
    # Add a next step
    runner.invoke(next_cmd, ['add', 'Review pull request'])
    # Mark it done
    result = runner.invoke(next_cmd, ['done', 'Review pull request'])
    assert result.exit_code == 0, f"Command failed with: {result.output}"
    assert 'completed' in result.output.lower()


def test_next_done_not_found(runner, temp_workspace, monkeypatch):
    """Test marking a non-existent next step as done"""
    monkeypatch.chdir(temp_workspace)
    result = runner.invoke(next_cmd, ['done', 'Nonexistent step'])
    assert result.exit_code == 0, f"Command failed with: {result.output}"
    assert 'No matching' in result.output or 'not found' in result.output.lower()


def test_next_clean(runner, temp_workspace, monkeypatch):
    """Test cleaning completed next steps"""
    monkeypatch.chdir(temp_workspace)
    # Add and complete a step
    runner.invoke(next_cmd, ['add', 'Test step'])
    runner.invoke(next_cmd, ['done', 'Test step'])
    # Clean completed steps
    result = runner.invoke(next_cmd, ['clean'])
    assert result.exit_code == 0, f"Command failed with: {result.output}"
    assert 'Removed' in result.output or 'removed' in result.output.lower()


# ============================================================================
# OTHER ENTRY TYPE TESTS
# ============================================================================

def test_antipattern_command(runner, temp_workspace, monkeypatch):
    """Test adding an antipattern"""
    monkeypatch.chdir(temp_workspace)
    result = runner.invoke(antipattern, ['Using global variables'])
    assert result.exit_code == 0, f"Command failed with: {result.output}"
    assert 'Antipattern' in result.output or 'recorded' in result.output.lower()


def test_antipattern_with_tags(runner, temp_workspace, monkeypatch):
    """Test adding an antipattern with tags"""
    monkeypatch.chdir(temp_workspace)
    result = runner.invoke(antipattern, ['Circular imports', '-t', 'python', '-t', 'imports'])
    assert result.exit_code == 0, f"Command failed with: {result.output}"


# ============================================================================
# SEARCH AND QUERY TESTS
# ============================================================================

def test_why_command(runner, temp_workspace, monkeypatch):
    """Test why command"""
    monkeypatch.chdir(temp_workspace)
    # Add a decision with reasoning
    runner.invoke(decision, ['Use PostgreSQL', '-r', 'Better for relational data'])
    # Query why
    result = runner.invoke(why, ['PostgreSQL'])
    assert result.exit_code == 0, f"Command failed with: {result.output}"


def test_why_command_no_results(runner, temp_workspace, monkeypatch):
    """Test why command with no matching entries"""
    monkeypatch.chdir(temp_workspace)
    result = runner.invoke(why, ['nonexistent topic'])
    assert result.exit_code == 0, f"Command failed with: {result.output}"


def test_search_with_type_filter(runner, temp_workspace, monkeypatch):
    """Test search command with type filter"""
    monkeypatch.chdir(temp_workspace)
    # Add different types
    runner.invoke(note, ['Test note'])
    runner.invoke(decision, ['Test decision'])
    # Search for decisions only
    result = runner.invoke(search, ['Test', '--type', 'decision'])
    assert result.exit_code == 0, f"Command failed with: {result.output}"


def test_search_with_limit(runner, temp_workspace, monkeypatch):
    """Test search command with limit"""
    monkeypatch.chdir(temp_workspace)
    # Add multiple entries
    for i in range(5):
        runner.invoke(note, [f'Test note {i}'])
    # Search with limit
    result = runner.invoke(search, ['Test', '--limit', '2'])
    assert result.exit_code == 0, f"Command failed with: {result.output}"


def test_read_command(runner, temp_workspace, monkeypatch):
    """Test read command"""
    monkeypatch.chdir(temp_workspace)
    # Add entries
    runner.invoke(note, ['Sample note'])
    runner.invoke(decision, ['Sample decision'])
    # Read all
    result = runner.invoke(read, [])
    assert result.exit_code == 0, f"Command failed with: {result.output}"


def test_read_with_type_filter(runner, temp_workspace, monkeypatch):
    """Test read command with type filter"""
    monkeypatch.chdir(temp_workspace)
    runner.invoke(note, ['Note entry'])
    result = runner.invoke(read, ['--type', 'note'])
    assert result.exit_code == 0, f"Command failed with: {result.output}"


# ============================================================================
# STATE AND SUMMARY TESTS
# ============================================================================

def test_state_command(runner, temp_workspace, monkeypatch):
    """Test state command showing goals and next steps"""
    monkeypatch.chdir(temp_workspace)
    # Add some state
    runner.invoke(goal, ['add', 'Test goal'])
    runner.invoke(next_cmd, ['add', 'Test step'])
    # View state
    result = runner.invoke(state, [])
    assert result.exit_code == 0, f"Command failed with: {result.output}"


def test_preferences_command(runner, temp_workspace, monkeypatch):
    """Test preferences command"""
    monkeypatch.chdir(temp_workspace)
    # Add a preference
    runner.invoke(preference, ['Use type hints', '--category', 'code_style'])
    # View preferences
    result = runner.invoke(preferences, [])
    assert result.exit_code == 0, f"Command failed with: {result.output}"


def test_summary_command(runner, temp_workspace, monkeypatch):
    """Test summary command"""
    monkeypatch.chdir(temp_workspace)
    # Add various entries
    runner.invoke(note, ['Test note'])
    runner.invoke(decision, ['Test decision'])
    runner.invoke(gotcha, ['Test gotcha'])
    # Get summary
    result = runner.invoke(summary, [])
    assert result.exit_code == 0, f"Command failed with: {result.output}"


def test_summary_with_days(runner, temp_workspace, monkeypatch):
    """Test summary command with days limit"""
    monkeypatch.chdir(temp_workspace)
    runner.invoke(note, ['Recent note'])
    result = runner.invoke(summary, ['--days', '7'])
    assert result.exit_code == 0, f"Command failed with: {result.output}"


# ============================================================================
# EXPORT AND DELETE TESTS
# ============================================================================

def test_export_command(runner, temp_workspace, monkeypatch):
    """Test export command"""
    monkeypatch.chdir(temp_workspace)
    # Add some data
    runner.invoke(note, ['Export test note'])
    runner.invoke(decision, ['Export test decision'])
    # Export
    result = runner.invoke(export, [])
    assert result.exit_code == 0, f"Command failed with: {result.output}"


def test_export_with_output_file(runner, temp_workspace, monkeypatch):
    """Test export to file"""
    monkeypatch.chdir(temp_workspace)
    runner.invoke(note, ['Test note'])
    output_file = temp_workspace / "export.json"
    result = runner.invoke(export, ['--output', str(output_file)])
    assert result.exit_code == 0, f"Command failed with: {result.output}"
    assert output_file.exists(), "Export file was not created"


def test_delete_command(runner, temp_workspace, monkeypatch):
    """Test delete command"""
    monkeypatch.chdir(temp_workspace)
    import src.cli
    src.cli.storage = None
    # Add an entry and get its ID
    from src.storage_sqlite import WorkshopStorageSQLite
    monkeypatch.setenv('WORKSHOP_DIR', str(temp_workspace / '.workshop'))
    store = WorkshopStorageSQLite(workspace_dir=temp_workspace / '.workshop')
    entry = store.add_entry(entry_type='note', content='To be deleted')
    entry_id = entry['id']
    src.cli.storage = None

    # Delete it
    result = runner.invoke(delete, [entry_id])
    assert result.exit_code == 0, f"Command failed with: {result.output}"


def test_clean_command_old_entries(runner, temp_workspace, monkeypatch):
    """Test clean command to remove old entries"""
    monkeypatch.chdir(temp_workspace)
    # This should succeed even with no old entries
    result = runner.invoke(clean, ['--days', '365'])
    assert result.exit_code == 0, f"Command failed with: {result.output}"


def test_clean_command_by_type(runner, temp_workspace, monkeypatch):
    """Test clean command with type filter"""
    monkeypatch.chdir(temp_workspace)
    result = runner.invoke(clean, ['--type', 'note', '--days', '365'])
    assert result.exit_code == 0, f"Command failed with: {result.output}"


# ============================================================================
# SESSION TESTS
# ============================================================================

def test_sessions_command(runner, temp_workspace, monkeypatch):
    """Test sessions command"""
    monkeypatch.chdir(temp_workspace)
    result = runner.invoke(sessions, [])
    assert result.exit_code == 0, f"Command failed with: {result.output}"


def test_sessions_with_limit(runner, temp_workspace, monkeypatch):
    """Test sessions command with limit"""
    monkeypatch.chdir(temp_workspace)
    result = runner.invoke(sessions, ['--limit', '5'])
    assert result.exit_code == 0, f"Command failed with: {result.output}"


def test_session_command_last(runner, temp_workspace, monkeypatch):
    """Test viewing last session"""
    monkeypatch.chdir(temp_workspace)
    result = runner.invoke(session, ['last'])
    assert result.exit_code == 0, f"Command failed with: {result.output}"


# ============================================================================
# PREFERENCE CATEGORY TESTS
# ============================================================================

def test_preference_code_style(runner, temp_workspace, monkeypatch):
    """Test preference with code_style category"""
    monkeypatch.chdir(temp_workspace)
    result = runner.invoke(preference, ['Use 4 spaces for indentation', '--category', 'code_style'])
    assert result.exit_code == 0, f"Command failed with: {result.output}"


def test_preference_libraries(runner, temp_workspace, monkeypatch):
    """Test preference with libraries category"""
    monkeypatch.chdir(temp_workspace)
    result = runner.invoke(preference, ['Prefer SQLAlchemy over raw SQL', '--category', 'libraries'])
    assert result.exit_code == 0, f"Command failed with: {result.output}"


def test_preference_communication(runner, temp_workspace, monkeypatch):
    """Test preference with communication category"""
    monkeypatch.chdir(temp_workspace)
    result = runner.invoke(preference, ['Keep responses concise', '--category', 'communication'])
    assert result.exit_code == 0, f"Command failed with: {result.output}"


def test_preference_testing(runner, temp_workspace, monkeypatch):
    """Test preference with testing category"""
    monkeypatch.chdir(temp_workspace)
    result = runner.invoke(preference, ['Write tests for all new features', '--category', 'testing'])
    assert result.exit_code == 0, f"Command failed with: {result.output}"


# ============================================================================
# ADDITIONAL COVERAGE TESTS
# ============================================================================

def test_read_with_limit(runner, temp_workspace, monkeypatch):
    """Test read command with limit parameter"""
    monkeypatch.chdir(temp_workspace)
    for i in range(5):
        runner.invoke(note, [f'Note {i}'])
    result = runner.invoke(read, ['--limit', '3'])
    assert result.exit_code == 0, f"Command failed with: {result.output}"


def test_read_with_tags(runner, temp_workspace, monkeypatch):
    """Test read command with tag filter"""
    monkeypatch.chdir(temp_workspace)
    runner.invoke(note, ['Tagged note', '-t', 'important'])
    result = runner.invoke(read, ['--tags', 'important'])
    assert result.exit_code == 0, f"Command failed with: {result.output}"


def test_read_full_details(runner, temp_workspace, monkeypatch):
    """Test read command with full details flag"""
    monkeypatch.chdir(temp_workspace)
    runner.invoke(note, ['Sample note'])
    result = runner.invoke(read, ['--full'])
    assert result.exit_code == 0, f"Command failed with: {result.output}"


def test_clear_command_by_date(runner, temp_workspace, monkeypatch):
    """Test clear command with before date"""
    monkeypatch.chdir(temp_workspace)
    from datetime import datetime, timedelta
    past_date = (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')
    result = runner.invoke(clear, [past_date])
    assert result.exit_code == 0, f"Command failed with: {result.output}"


def test_clear_command_by_type(runner, temp_workspace, monkeypatch):
    """Test clear command filtered by entry type"""
    monkeypatch.chdir(temp_workspace)
    from datetime import datetime, timedelta
    past_date = (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')
    result = runner.invoke(clear, [past_date, '--type', 'note'])
    assert result.exit_code == 0, f"Command failed with: {result.output}"


def test_context_with_days_limit(runner, temp_workspace, monkeypatch):
    """Test context command with days parameter"""
    monkeypatch.chdir(temp_workspace)
    runner.invoke(note, ['Context test'])
    result = runner.invoke(context, ['--days', '30'])
    assert result.exit_code == 0, f"Command failed with: {result.output}"


def test_search_compact_format(runner, temp_workspace, monkeypatch):
    """Test search with compact output format"""
    monkeypatch.chdir(temp_workspace)
    runner.invoke(note, ['Searchable note'])
    result = runner.invoke(search, ['Searchable', '--format', 'compact'])
    assert result.exit_code == 0, f"Command failed with: {result.output}"


def test_search_full_format(runner, temp_workspace, monkeypatch):
    """Test search with full output format"""
    monkeypatch.chdir(temp_workspace)
    runner.invoke(note, ['Searchable note'])
    result = runner.invoke(search, ['Searchable', '--format', 'full'])
    assert result.exit_code == 0, f"Command failed with: {result.output}"


def test_export_full_flag(runner, temp_workspace, monkeypatch):
    """Test export with full details flag"""
    monkeypatch.chdir(temp_workspace)
    runner.invoke(note, ['Export test'])
    result = runner.invoke(export, ['--full'])
    assert result.exit_code == 0, f"Command failed with: {result.output}"


def test_export_recent_flag(runner, temp_workspace, monkeypatch):
    """Test export with recent flag"""
    monkeypatch.chdir(temp_workspace)
    runner.invoke(note, ['Recent export test'])
    result = runner.invoke(export, ['--recent'])
    assert result.exit_code == 0, f"Command failed with: {result.output}"


def test_export_context_flag(runner, temp_workspace, monkeypatch):
    """Test export with context flag"""
    monkeypatch.chdir(temp_workspace)
    runner.invoke(goal, ['add', 'Test goal'])
    result = runner.invoke(export, ['--context'])
    assert result.exit_code == 0, f"Command failed with: {result.output}"


def test_note_with_files(runner, temp_workspace, monkeypatch):
    """Test adding note with related files"""
    monkeypatch.chdir(temp_workspace)
    result = runner.invoke(note, ['Note with files', '-f', 'test.py', '-f', 'main.py'])
    assert result.exit_code == 0, f"Command failed with: {result.output}"


def test_decision_with_files(runner, temp_workspace, monkeypatch):
    """Test adding decision with related files"""
    monkeypatch.chdir(temp_workspace)
    result = runner.invoke(decision, ['Use feature flags', '-r', 'Safer rollout', '-f', 'config.py'])
    assert result.exit_code == 0, f"Command failed with: {result.output}"


def test_gotcha_with_files(runner, temp_workspace, monkeypatch):
    """Test adding gotcha with files"""
    monkeypatch.chdir(temp_workspace)
    result = runner.invoke(gotcha, ['Race condition in handler', '-f', 'handler.py', '-t', 'concurrency'])
    assert result.exit_code == 0, f"Command failed with: {result.output}"
