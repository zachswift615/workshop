"""
Tests for Workshop CLI commands
"""
import tempfile
import shutil
from pathlib import Path
from click.testing import CliRunner
import pytest
from unittest.mock import patch, MagicMock

from src.cli import main, note, decision, gotcha, preference, recent, search, context, info, web


@pytest.fixture
def temp_workspace():
    """Create a temporary workspace for testing"""
    import src.cli
    # Reset global storage before each test
    src.cli.storage = None

    temp_dir = Path(tempfile.mkdtemp())
    # Create .workshop directory
    workshop_dir = temp_dir / ".workshop"
    workshop_dir.mkdir(exist_ok=True)
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
