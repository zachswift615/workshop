"""
Workshop Web UI - Flask Application
Provides a web interface for browsing, editing, and managing Workshop entries.
"""
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from pathlib import Path
from datetime import datetime
import sys

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.storage_sqlite import WorkshopStorageSQLite
from src.config import WorkshopConfig

app = Flask(__name__)
app.secret_key = 'workshop-dev-key-change-in-production'

# Disable caching to prevent stale 403 errors when server restarts
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0

# Store the workspace directory that was active when server started
# This ensures the web UI shows the correct project's data
_startup_workspace = None

@app.after_request
def add_header(response):
    """
    Add headers to prevent caching.

    This prevents browsers from caching 403 errors when the server is stopped,
    which would otherwise persist even after restarting the server.
    """
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response

def get_store():
    """
    Get Workshop storage instance.

    Uses the workspace directory from when the server was launched.
    This ensures each server instance shows the correct project's data.
    """
    global _startup_workspace
    # Always use the startup workspace if it was set by run()
    if _startup_workspace is not None:
        return WorkshopStorageSQLite(workspace_dir=_startup_workspace)
    else:
        # Fallback: shouldn't happen if run() is called properly
        return WorkshopStorageSQLite()

def format_timestamp(timestamp_str):
    """
    Format timestamp as relative time.

    Timestamps are stored as UTC (naive datetime). This converts to local time for display.
    """
    try:
        dt = datetime.fromisoformat(timestamp_str)

        # Handle timezone-aware vs naive timestamps
        if dt.tzinfo is None:
            # Naive timestamp - assume UTC, convert to local
            from datetime import timezone
            dt_utc = dt.replace(tzinfo=timezone.utc)
            dt = dt_utc.astimezone()
            now = datetime.now().astimezone()
        else:
            # Timezone-aware timestamp
            from datetime import timezone
            now = datetime.now(timezone.utc)

        diff = now - dt

        if diff.days > 365:
            years = diff.days // 365
            return f"{years} year{'s' if years != 1 else ''} ago"
        elif diff.days > 30:
            months = diff.days // 30
            return f"{months} month{'s' if months != 1 else ''} ago"
        elif diff.days > 0:
            return f"{diff.days} day{'s' if diff.days != 1 else ''} ago"
        elif diff.seconds > 3600:
            hours = diff.seconds // 3600
            return f"{hours} hour{'s' if hours != 1 else ''} ago"
        elif diff.seconds > 60:
            mins = diff.seconds // 60
            return f"{mins} minute{'s' if mins != 1 else ''} ago"
        else:
            return "just now"
    except:
        return timestamp_str

app.jinja_env.filters['timeago'] = format_timestamp

@app.route('/')
def dashboard():
    """Main dashboard with stats and recent entries"""
    store = get_store()

    # Get stats
    all_entries = store.get_entries(limit=10000)  # Get more for stats
    stats = {
        'total': len(all_entries),
        'notes': len([e for e in all_entries if e['type'] == 'note']),
        'gotchas': len([e for e in all_entries if e['type'] == 'gotcha']),
        'decisions': len([e for e in all_entries if e['type'] == 'decision']),
        'preferences': len([e for e in all_entries if e['type'] == 'preference']),
    }

    # Get recent entries
    recent_entries = store.get_entries(limit=20)

    # Get workspace info
    workspace_path = store.workspace_dir
    # db_file is on db_manager for SQLite storage
    data_path = getattr(store.db_manager, 'db_file', None) if hasattr(store, 'db_manager') else None

    return render_template('dashboard.html',
                         stats=stats,
                         entries=recent_entries,
                         workspace_path=workspace_path,
                         db_path=data_path)

@app.route('/entries')
def list_entries():
    """Paginated list of entries with filters"""
    store = get_store()

    # Get filters from query params
    entry_type = request.args.get('type', '')
    search_query = request.args.get('q', '')
    page = int(request.args.get('page', 1))
    per_page = 50

    # Get entries
    if search_query:
        entries = store.search(search_query, limit=1000)
    else:
        entries = store.get_entries(limit=1000)

    # Filter by type
    if entry_type:
        entries = [e for e in entries if e['type'] == entry_type]

    # Pagination
    total = len(entries)
    start = (page - 1) * per_page
    end = start + per_page
    page_entries = entries[start:end]

    total_pages = (total + per_page - 1) // per_page

    return render_template('entries.html',
                         entries=page_entries,
                         entry_type=entry_type,
                         search_query=search_query,
                         page=page,
                         total_pages=total_pages,
                         total=total)

@app.route('/entries/<entry_id>')
def view_entry(entry_id):
    """View single entry"""
    store = get_store()
    entry = store.get_entry_by_id(entry_id)

    if not entry:
        flash('Entry not found', 'error')
        return redirect(url_for('dashboard'))

    return render_template('view.html', entry=entry)

@app.route('/entries/<entry_id>/edit', methods=['GET', 'POST'])
def edit_entry(entry_id):
    """Edit entry"""
    store = get_store()

    if request.method == 'POST':
        # Update entry
        content = request.form.get('content', '')
        reasoning = request.form.get('reasoning', '')
        entry_type = request.form.get('type', 'note')

        # Update using SQLAlchemy
        success = store.update_entry(
            entry_id=entry_id,
            content=content,
            reasoning=reasoning if reasoning else None,
            entry_type=entry_type
        )

        if success:
            flash('Entry updated successfully', 'success')
            return redirect(url_for('view_entry', entry_id=entry_id))
        else:
            flash('Entry not found', 'error')
            return redirect(url_for('dashboard'))

    # GET request - show form
    entry = store.get_entry_by_id(entry_id)
    if not entry:
        flash('Entry not found', 'error')
        return redirect(url_for('dashboard'))

    return render_template('edit.html', entry=entry)

@app.route('/entries/<entry_id>/delete', methods=['POST'])
def delete_entry(entry_id):
    """Delete entry"""
    store = get_store()

    # Delete using SQLAlchemy
    success = store.delete_entry(entry_id)

    if success:
        flash('Entry deleted successfully', 'success')
    else:
        flash('Entry not found', 'error')

    return redirect(url_for('dashboard'))

@app.route('/entries/new', methods=['GET', 'POST'])
def new_entry():
    """Create new entry"""
    store = get_store()

    if request.method == 'POST':
        content = request.form.get('content', '')
        reasoning = request.form.get('reasoning', '')
        entry_type = request.form.get('type', 'note')

        if content:
            store.add_entry(
                entry_type=entry_type,
                content=content,
                reasoning=reasoning if reasoning else None
            )
            flash('Entry created successfully', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Content is required', 'error')

    return render_template('new.html')

@app.route('/settings')
def settings():
    """Settings page"""
    config = WorkshopConfig()

    # Get config as pretty JSON
    import json
    config_json = json.dumps(config.get_raw_config(), indent=2)

    # Get projects list
    projects = config.list_projects()

    return render_template('settings.html',
                         config_json=config_json,
                         projects=projects)

@app.route('/api/config', methods=['GET'])
def api_get_config():
    """Get current configuration"""
    config = WorkshopConfig()
    return jsonify(config.get_raw_config())

@app.route('/api/config', methods=['POST'])
def api_save_config():
    """Save configuration"""
    try:
        new_config = request.get_json()

        config = WorkshopConfig()
        config.update_from_dict(new_config)

        return jsonify({'success': True, 'message': 'Configuration saved'})

    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': f'Failed to save: {str(e)}'}), 500

@app.route('/api/config/validate', methods=['POST'])
def api_validate_config():
    """Validate configuration"""
    try:
        test_config = request.get_json()

        # Create temp config to test validation
        config = WorkshopConfig()
        config._config = test_config

        result = config.validate()
        return jsonify(result)

    except Exception as e:
        return jsonify({
            'valid': False,
            'errors': [f'Validation failed: {str(e)}'],
            'warnings': []
        })

@app.route('/api/config/reset', methods=['POST'])
def api_reset_config():
    """Reset to default configuration"""
    try:
        config = WorkshopConfig()
        config._config = config._create_default_config()

        return jsonify({'success': True, 'message': 'Configuration reset'})

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/stats')
def api_stats():
    """API endpoint for stats"""
    store = get_store()
    all_entries = store.get_entries(limit=10000)

    stats = {
        'total': len(all_entries),
        'by_type': {},
        'by_date': {}
    }

    for entry in all_entries:
        # Count by type
        entry_type = entry['type']
        stats['by_type'][entry_type] = stats['by_type'].get(entry_type, 0) + 1

    return jsonify(stats)

def run(host='127.0.0.1', port=5000, debug=True, workspace_dir=None):
    """
    Run the Flask app

    Args:
        workspace_dir: Path to workspace directory. This is set by the CLI
                      and determines which project's data is shown.
    """
    global _startup_workspace
    if workspace_dir:
        _startup_workspace = workspace_dir
    app.run(host=host, port=port, debug=debug)

if __name__ == '__main__':
    run()
