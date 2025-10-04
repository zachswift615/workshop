"""
Tests for Workshop CLI commands
"""
import tempfile
import shutil
from pathlib import Path
from click.testing import CliRunner
import pytest

from src.cli import main, note, decision, gotcha, preference, recent, search, context, info


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
