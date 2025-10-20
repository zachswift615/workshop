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

def extract_tool_content(raw_json_str):
    """
    Extract tool result or tool use content from raw JSON.

    Args:
        raw_json_str: JSON string from raw_messages.raw_json field

    Returns:
        List of dicts with type and content, or empty list if no tool content
    """
    import json

    try:
        data = json.loads(raw_json_str)
        message = data.get('message', {})
        content_parts = message.get('content', [])

        tool_contents = []

        if isinstance(content_parts, list):
            for part in content_parts:
                if isinstance(part, dict):
                    part_type = part.get('type')

                    # Tool result
                    if part_type == 'tool_result':
                        tool_contents.append({
                            'type': 'tool_result',
                            'tool_use_id': part.get('tool_use_id', ''),
                            'content': part.get('content', ''),
                            'is_error': part.get('is_error', False)
                        })

                    # Tool use
                    elif part_type == 'tool_use':
                        tool_contents.append({
                            'type': 'tool_use',
                            'id': part.get('id', ''),
                            'name': part.get('name', ''),
                            'input': part.get('input', {})
                        })

        return tool_contents
    except:
        return []

app.jinja_env.filters['extract_tool_content'] = extract_tool_content

@app.route('/')
def dashboard():
    """Main dashboard with stats and recent entries"""
    from src.storage.raw_messages import RawMessagesManager

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

    # Count raw messages
    with store.db_manager.get_session() as session:
        raw_msg_manager = RawMessagesManager(session, store.db_manager.project_id)
        stats['raw_messages'] = raw_msg_manager.count_messages()

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

@app.route('/messages')
def list_messages():
    """Raw conversation messages with search, filter, and sort"""
    from src.storage.raw_messages import RawMessagesManager
    from dateutil import parser as date_parser

    store = get_store()

    # Get filters from query params
    search_query = request.args.get('q', '')
    message_type = request.args.get('type', '')
    date_from = request.args.get('from', '')
    date_to = request.args.get('to', '')
    sort_order = request.args.get('sort', 'desc')  # desc = newest first, asc = oldest first
    page = int(request.args.get('page', 1))
    per_page = 50

    # Get messages using RawMessagesManager
    with store.db_manager.get_session() as session:
        raw_msg_manager = RawMessagesManager(session, store.db_manager.project_id)

        # Start with search if provided
        if search_query:
            messages = raw_msg_manager.search_messages(
                query_text=search_query,
                limit=1000,
                message_types=[message_type] if message_type else None
            )
        else:
            # Get all messages (we'll filter and paginate)
            from sqlalchemy import select, and_
            from src.models import RawMessage

            query = select(RawMessage)

            # Apply project filter
            if store.db_manager.project_id:
                query = query.where(RawMessage.project_id == store.db_manager.project_id)

            # Filter by message type
            if message_type:
                query = query.where(RawMessage.message_type == message_type)

            # Filter by date range
            if date_from:
                try:
                    from_dt = date_parser.parse(date_from)
                    query = query.where(RawMessage.timestamp >= from_dt)
                except:
                    pass

            if date_to:
                try:
                    to_dt = date_parser.parse(date_to)
                    query = query.where(RawMessage.timestamp <= to_dt)
                except:
                    pass

            # Sort by timestamp
            if sort_order == 'asc':
                query = query.order_by(RawMessage.timestamp.asc())
            else:
                query = query.order_by(RawMessage.timestamp.desc())

            # Get results
            results = session.execute(query.limit(1000)).scalars().all()

            messages = [
                {
                    'id': str(m.id),
                    'message_uuid': m.message_uuid,
                    'session_id': m.session_id,
                    'message_type': m.message_type,
                    'timestamp': m.timestamp.isoformat(),
                    'parent_uuid': m.parent_uuid,
                    'content': m.content,
                    'raw_json': m.raw_json,
                    'created_at': m.created_at.isoformat()
                }
                for m in results
            ]

    # Pagination
    total = len(messages)
    start = (page - 1) * per_page
    end = start + per_page
    page_messages = messages[start:end]

    total_pages = (total + per_page - 1) // per_page

    return render_template('messages.html',
                         messages=page_messages,
                         search_query=search_query,
                         message_type=message_type,
                         date_from=date_from,
                         date_to=date_to,
                         sort_order=sort_order,
                         page=page,
                         total_pages=total_pages,
                         total=total)

@app.route('/messages/<message_uuid>')
def view_message(message_uuid):
    """View single raw message with context"""
    from src.storage.raw_messages import RawMessagesManager

    store = get_store()

    with store.db_manager.get_session() as session:
        raw_msg_manager = RawMessagesManager(session, store.db_manager.project_id)

        # Get the message
        message = raw_msg_manager.get_message_by_uuid(message_uuid)

        if not message:
            flash('Message not found', 'error')
            return redirect(url_for('list_messages'))

        # Get conversation context (5 before, 5 after)
        context_messages = raw_msg_manager.get_conversation_context(
            message_uuid=message_uuid,
            before=5,
            after=5
        )

    return render_template('view_message.html',
                         message=message,
                         context_messages=context_messages)

@app.route('/messages/<message_uuid>/conversation')
def view_conversation(message_uuid):
    """View full conversation thread (Claude Code TUI style)"""
    from src.storage.raw_messages import RawMessagesManager
    from sqlalchemy import select
    from src.models import RawMessage

    store = get_store()

    # Get pagination params
    limit = int(request.args.get('limit', 25))  # Messages per page
    offset = int(request.args.get('offset', 0))  # Starting position

    # Get exclude_types as comma-separated list
    exclude_types_param = request.args.get('exclude_types', '')
    exclude_types = [t.strip() for t in exclude_types_param.split(',') if t.strip()]

    with store.db_manager.get_session() as session:
        raw_msg_manager = RawMessagesManager(session, store.db_manager.project_id)

        # Get the anchor message
        anchor_message = raw_msg_manager.get_message_by_uuid(message_uuid)

        if not anchor_message:
            flash('Message not found', 'error')
            return redirect(url_for('list_messages'))

        session_id = anchor_message['session_id']

        # Get all messages in this session, ordered by timestamp
        query = select(RawMessage).where(RawMessage.session_id == session_id)

        if store.db_manager.project_id:
            query = query.where(RawMessage.project_id == store.db_manager.project_id)

        # Filter out excluded message types
        if exclude_types:
            query = query.where(~RawMessage.message_type.in_(exclude_types))

        query = query.order_by(RawMessage.timestamp.asc())

        # Get total count
        all_messages = session.execute(query).scalars().all()
        total_messages = len(all_messages)

        # Find the anchor message position
        anchor_position = 0
        for i, msg in enumerate(all_messages):
            if msg.message_uuid == message_uuid:
                anchor_position = i
                break

        # Calculate offset if not provided (center on anchor message)
        if 'offset' not in request.args:
            offset = max(0, anchor_position - limit // 2)

        # Get paginated messages
        paginated_messages = all_messages[offset:offset + limit]

        messages = [
            {
                'id': str(m.id),
                'message_uuid': m.message_uuid,
                'session_id': m.session_id,
                'message_type': m.message_type,
                'timestamp': m.timestamp.isoformat(),
                'parent_uuid': m.parent_uuid,
                'content': m.content,
                'raw_json': m.raw_json,
                'created_at': m.created_at.isoformat(),
                'is_anchor': m.message_uuid == message_uuid
            }
            for m in paginated_messages
        ]

    # Calculate pagination info
    has_earlier = offset > 0
    has_later = (offset + limit) < total_messages
    current_page = (offset // limit) + 1
    total_pages = (total_messages + limit - 1) // limit

    return render_template('conversation.html',
                         messages=messages,
                         anchor_message=anchor_message,
                         session_id=session_id,
                         limit=limit,
                         offset=offset,
                         total_messages=total_messages,
                         has_earlier=has_earlier,
                         has_later=has_later,
                         current_page=current_page,
                         total_pages=total_pages,
                         anchor_uuid=message_uuid,
                         exclude_types=exclude_types)

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
