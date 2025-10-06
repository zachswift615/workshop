"""
Tests for Workshop Web UI
"""
import tempfile
import shutil
from pathlib import Path
import pytest
from unittest.mock import patch, MagicMock
from click.testing import CliRunner

from src.cli import web
from src.storage import WorkshopStorage


@pytest.fixture
def temp_workspace():
    """Create a temporary workspace for testing"""
    temp_dir = Path(tempfile.mkdtemp())
    workshop_dir = temp_dir / ".workshop"
    workshop_dir.mkdir(exist_ok=True)

    yield workshop_dir
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def runner():
    """Create a Click CLI runner"""
    return CliRunner()


def test_web_dashboard_with_workshopstorage(temp_workspace):
    """
    Regression test: Ensure dashboard works with WorkshopStorage (db_file from db_manager)

    Issue: app.py tried to access store.db_file which doesn't exist directly on WorkshopStorage,
           only on store.db_manager.db_file
    Fix: Use getattr() to safely access db_file or data_file from either location.
    """
    # Import here to ensure Flask is available (or skip test)
    try:
        from src.web.app import app
        import src.web.app as app_module
    except ImportError:
        pytest.skip("Flask not installed")

    # Set up web app to use our temp workspace (convert Path to str)
    app_module._startup_workspace = str(temp_workspace)

    # Create a WorkshopStorage instance (uses db_file via db_manager)
    store = WorkshopStorage(workspace_dir=temp_workspace)

    # Add some test data
    store.add_entry(entry_type="note", content="Test note")
    store.add_entry(entry_type="decision", content="Test decision", reasoning="Because testing")

    # Verify store has db_file via db_manager
    assert hasattr(store.db_manager, 'db_file')
    assert store.db_manager.db_file.exists()

    # Create Flask test client
    app.config['TESTING'] = True

    with app.test_client() as client:
        # This should not raise AttributeError
        response = client.get('/')
        assert response.status_code == 200


def test_web_command_error_message():
    """
    Regression test: Verify the error message content for Flask not installed

    Issue: Error message said "pip install flask" instead of showing the extras syntax.
    Fix: Changed message to 'pip install "claude-workshop[web]"'

    This test verifies the actual error message string used in cli.py
    """
    # Read the cli.py source file directly with UTF-8 encoding for Windows compatibility
    from pathlib import Path
    cli_path = Path(__file__).parent.parent / "src" / "cli.py"
    cli_source = cli_path.read_text(encoding='utf-8')

    # Find the web function definition
    web_function_start = cli_source.find('def web(')
    assert web_function_start != -1, "web function not found in cli.py"

    # Extract a chunk of the web function (next 500 chars should include the error message)
    web_chunk = cli_source[web_function_start:web_function_start + 500]

    # Verify the error message contains the correct install command
    assert 'claude-workshop[web]' in web_chunk
    assert 'Flask is not installed' in web_chunk


def test_web_dashboard_data_path_fallback(temp_workspace):
    """
    Test that data_path correctly accesses db_file from db_manager
    """
    try:
        from src.web.app import app
        import src.web.app as app_module
    except ImportError:
        pytest.skip("Flask not installed")

    app_module._startup_workspace = str(temp_workspace)
    app.config['TESTING'] = True

    # Create store and add data
    store = WorkshopStorage(workspace_dir=temp_workspace)
    store.add_entry(entry_type="note", content="Test")

    with app.test_client() as client:
        response = client.get('/')
        assert response.status_code == 200

        # Check that the data path is displayed in the response
        data = response.data.decode('utf-8')
        # Should show workshop.db for SQLite storage
        assert 'workshop.db' in data or '.workshop' in data


def test_web_edit_entry(temp_workspace):
    """
    Regression test: Ensure edit functionality works with SQLAlchemy

    Issue: Web UI crashed when editing entries with:
    AttributeError: 'WorkshopStorage' object has no attribute '_get_connection'

    Root cause: edit_entry route used old raw SQL methods that don't exist
    Fix: Added update_entry() method and use SQLAlchemy API
    """
    try:
        from src.web.app import app
        import src.web.app as app_module
    except ImportError:
        pytest.skip("Flask not installed")

    app_module._startup_workspace = str(temp_workspace)
    app.config['TESTING'] = True

    # Create store and add an entry
    store = WorkshopStorage(workspace_dir=temp_workspace)
    entry = store.add_entry(entry_type="note", content="Original content")
    entry_id = entry['id']

    with app.test_client() as client:
        # Test GET edit page
        response = client.get(f'/entries/{entry_id}/edit')
        assert response.status_code == 200
        assert b'Original content' in response.data

        # Test POST update
        response = client.post(f'/entries/{entry_id}/edit', data={
            'content': 'Updated content',
            'reasoning': 'Updated reasoning',
            'type': 'decision'
        }, follow_redirects=True)
        assert response.status_code == 200
        assert b'Entry updated successfully' in response.data

    # Verify entry was actually updated
    updated_entry = store.get_entry_by_id(entry_id)
    assert updated_entry['content'] == 'Updated content'
    assert updated_entry['reasoning'] == 'Updated reasoning'
    assert updated_entry['type'] == 'decision'


def test_web_delete_entry(temp_workspace):
    """
    Regression test: Ensure delete functionality works with SQLAlchemy

    Issue: Web UI crashed when deleting entries with:
    AttributeError: 'WorkshopStorage' object has no attribute '_get_connection'

    Root cause: delete_entry route used old raw SQL methods that don't exist
    Fix: Use SQLAlchemy-based delete_entry() method
    """
    try:
        from src.web.app import app
        import src.web.app as app_module
    except ImportError:
        pytest.skip("Flask not installed")

    app_module._startup_workspace = str(temp_workspace)
    app.config['TESTING'] = True

    # Create store and add an entry
    store = WorkshopStorage(workspace_dir=temp_workspace)
    entry = store.add_entry(entry_type="note", content="To be deleted")
    entry_id = entry['id']

    # Verify entry exists
    assert store.get_entry_by_id(entry_id) is not None

    with app.test_client() as client:
        # Test POST delete
        response = client.post(f'/entries/{entry_id}/delete', follow_redirects=True)
        assert response.status_code == 200
        assert b'Entry deleted successfully' in response.data

    # Verify entry was actually deleted
    assert store.get_entry_by_id(entry_id) is None
