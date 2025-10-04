"""
CLI interface for Workshop
"""
import click
import os
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional

from .storage_sqlite import WorkshopStorageSQLite
from .migrate import should_migrate, migrate_json_to_sqlite
from .display import (
    display_entry, display_entries, display_context,
    display_preferences, display_current_state,
    display_why_results,
    success, error, info as display_info,
    display_error
)


# Global storage instance
storage = None


def _change_to_project_root(store: WorkshopStorageSQLite):
    """
    Change working directory to project root.

    This ensures workshop commands execute from the project root,
    preventing creation of nested .workshop directories.
    """
    project_root = store.workspace_dir.parent
    if project_root != Path.cwd():
        os.chdir(project_root)


def get_storage() -> WorkshopStorageSQLite:
    """Get or create storage instance, migrating from JSON if needed"""
    global storage
    if storage is None:
        # Check if migration is needed
        if should_migrate():
            migrate_json_to_sqlite()
        storage = WorkshopStorageSQLite()
        _change_to_project_root(storage)
    return storage


@click.group()
@click.option('--workspace', type=click.Path(), help='Custom workspace directory')
@click.version_option(version='0.3.0', prog_name='Workshop')
def main(workspace):
    """
    Workshop - Persistent context tool for Claude Code.

    Maintains decisions, notes, preferences, and context across sessions.
    """
    global storage
    if workspace:
        workspace_path = Path(workspace)
        # Check if migration is needed for custom workspace
        if should_migrate(workspace_path):
            migrate_json_to_sqlite(workspace_path)
        storage = WorkshopStorageSQLite(workspace_path)
        _change_to_project_root(storage)
    else:
        storage = get_storage()


# ============================================================================
# WRITE COMMANDS
# ============================================================================

@main.command()
@click.argument('content')
@click.option('--tags', '-t', multiple=True, help='Add tags to the note')
@click.option('--files', '-f', multiple=True, help='Related files')
def note(content, tags, files):
    """Add a note about what you're working on"""
    store = get_storage()
    entry = store.add_entry(
        entry_type="note",
        content=content,
        tags=list(tags),
        files=list(files)
    )
    success(f"Note added: {content}")


@main.command()
@click.argument('content')
@click.option('--reasoning', '-r', help='Why this decision was made')
@click.option('--tags', '-t', multiple=True, help='Add tags')
@click.option('--files', '-f', multiple=True, help='Related files')
def decision(content, reasoning, tags, files):
    """Record a decision with reasoning"""
    store = get_storage()
    entry = store.add_entry(
        entry_type="decision",
        content=content,
        reasoning=reasoning,
        tags=list(tags),
        files=list(files)
    )
    success(f"Decision recorded: {content}")
    if reasoning:
        display_info(f"Reasoning: {reasoning}")


@main.command()
@click.argument('content')
@click.option('--tags', '-t', multiple=True, help='Add tags')
@click.option('--files', '-f', multiple=True, help='Related files')
def gotcha(content, tags, files):
    """Record a gotcha or constraint"""
    store = get_storage()
    entry = store.add_entry(
        entry_type="gotcha",
        content=content,
        tags=list(tags),
        files=list(files)
    )
    success(f"Gotcha recorded: {content}")


@main.command()
@click.argument('content')
@click.option('--category', '-c',
              type=click.Choice(['code_style', 'libraries', 'communication', 'testing']),
              default='code_style',
              help='Preference category')
def preference(content, category):
    """Record a user preference"""
    store = get_storage()
    store.add_preference(category, content)
    success(f"Preference added to {category}: {content}")


@main.command()
@click.argument('content')
@click.option('--tags', '-t', multiple=True, help='Add tags')
@click.option('--files', '-f', multiple=True, help='Related files')
def antipattern(content, tags, files):
    """Record an antipattern to avoid"""
    store = get_storage()
    entry = store.add_entry(
        entry_type="antipattern",
        content=content,
        tags=list(tags),
        files=list(files)
    )
    success(f"Antipattern recorded: {content}")


# ============================================================================
# GOAL/STATE COMMANDS
# ============================================================================

@main.group()
def goal():
    """Manage goals"""
    pass


@goal.command('add')
@click.argument('content')
def goal_add(content):
    """Add a new goal"""
    store = get_storage()
    store.add_goal(content)
    success(f"Goal added: {content}")


@goal.command('list')
def goal_list():
    """List all goals"""
    store = get_storage()
    state = store.get_current_state()
    goals = state.get('goals', [])

    if not goals:
        display_info("No active goals")
        return

    click.echo("\n🎯 Active Goals:\n")
    for i, goal in enumerate(goals, 1):
        click.echo(f"  {i}. {goal['content']}")
    click.echo()


@goal.command('clear')
def goal_clear():
    """Clear all goals"""
    store = get_storage()
    store.clear_goals()
    success("All goals cleared")


@goal.command('done')
@click.argument('goal_text')
def goal_done(goal_text):
    """Mark a goal as completed"""
    store = get_storage()
    if store.complete_goal(goal_text):
        success(f"Goal completed: {goal_text}")
    else:
        display_error(f"No matching goal found for: {goal_text}")


@goal.command('clean')
def goal_clean():
    """Remove completed goals"""
    store = get_storage()
    count = store.clear_completed_goals()
    if count > 0:
        success(f"Removed {count} completed goal{'s' if count != 1 else ''}")
    else:
        display_info("No completed goals to remove")


@main.group()
def next():
    """Manage next steps / TODOs"""
    pass


@next.command('add')
@click.argument('content')
def next_add(content):
    """Add a next step / TODO"""
    store = get_storage()
    store.add_next_step(content)
    success(f"Next step added: {content}")


@next.command('done')
@click.argument('step_text')
def next_done(step_text):
    """Mark a next step as completed"""
    store = get_storage()
    if store.complete_next_step(step_text):
        success(f"Next step completed: {step_text}")
    else:
        display_error(f"No matching next step found for: {step_text}")


@next.command('clean')
def next_clean():
    """Remove completed next steps"""
    store = get_storage()
    count = store.clear_completed_next_steps()
    if count > 0:
        success(f"Removed {count} completed next step{'s' if count != 1 else ''}")
    else:
        display_info("No completed next steps to remove")


# ============================================================================
# READ COMMANDS
# ============================================================================

@main.command()
@click.option('--type', '-t', 'entry_type',
              type=click.Choice(['decision', 'note', 'gotcha', 'preference', 'antipattern']),
              help='Filter by type')
@click.option('--tags', multiple=True, help='Filter by tags')
@click.option('--limit', '-n', type=int, default=10, help='Number of entries to show')
@click.option('--full', is_flag=True, help='Show full details')
def read(entry_type, tags, limit, full):
    """Read entries with optional filters"""
    store = get_storage()
    entries = store.get_entries(
        entry_type=entry_type,
        tags=list(tags) if tags else None,
        limit=limit
    )
    display_entries(entries, show_full=full)


@main.command()
@click.option('--limit', '-n', type=int, default=5, help='Number of entries to show')
def recent(limit):
    """Show recent entries"""
    store = get_storage()
    entries = store.get_entries(limit=limit)
    display_entries(entries, show_full=False)


@main.command()
@click.argument('query')
@click.option('--limit', '-n', type=int, default=10, help='Number of results')
@click.option('--type', '-t', type=click.Choice(['note', 'decision', 'gotcha', 'preference', 'goal', 'next']), help='Filter by entry type')
@click.option('--format', '-f', type=click.Choice(['compact', 'full']), default='compact', help='Output format')
def search(query, limit, type, format):
    """Search entries by keyword"""
    try:
        store = get_storage()
        results = store.search(query, limit=limit)

        # Filter by type if specified
        if type:
            results = [e for e in results if e['type'] == type]

        # Display with appropriate format
        show_full = (format == 'full')
        display_entries(results, show_full=show_full)
    except Exception as e:
        display_error(f"Search failed: {str(e)}")
        return 1


@main.command()
@click.argument('query')
@click.option('--limit', '-n', type=int, default=5, help='Number of results')
def why(query, limit):
    """
    Answer "why" questions - find decisions and reasoning.

    Smart search that prioritizes decisions with reasoning.
    Perfect for understanding why things are the way they are.

    Examples:
        workshop why "using zustand"
        workshop why "authentication flow"
        workshop why "postgres instead of mongodb"
    """
    store = get_storage()
    results = store.why_search(query, limit=limit)
    display_why_results(results, query)


@main.command()
def preferences():
    """Show all preferences"""
    store = get_storage()
    prefs = store.get_preferences()
    display_preferences(prefs)


@main.command()
def state():
    """Show current state (goals, next steps)"""
    store = get_storage()
    current_state = store.get_current_state()
    display_current_state(current_state)


# ============================================================================
# CONTEXT/SUMMARY COMMANDS
# ============================================================================

@main.command()
@click.option('--days', '-d', type=int, default=7, help='Number of days to look back')
def context(days):
    """
    Show context summary for current session.
    This is the killer feature - shows what you need to know right now.
    """
    store = get_storage()

    # Get recent entries
    since = datetime.now() - timedelta(days=days)
    recent_entries = store.get_entries(limit=20, since=since)

    # Get current state
    current_state = store.get_current_state()

    # Get preferences
    prefs = store.get_preferences()

    display_context(recent_entries, current_state, prefs)


@main.command()
@click.option('--days', '-d', type=int, default=7, help='Number of days to summarize')
def summary(days):
    """Show a summary of recent activity"""
    store = get_storage()

    since = datetime.now() - timedelta(days=days)
    entries = store.get_entries(since=since)

    if not entries:
        display_info(f"No activity in the last {days} days")
        return

    # Group by type
    by_type = {}
    for entry in entries:
        entry_type = entry['type']
        by_type.setdefault(entry_type, []).append(entry)

    click.echo(f"\n📊 Summary (last {days} days):\n")
    click.echo(f"Total entries: {len(entries)}\n")

    for entry_type, type_entries in sorted(by_type.items()):
        click.echo(f"{entry_type.capitalize()}: {len(type_entries)}")

    click.echo("\nMost recent activity:")
    display_entries(entries[:5], show_full=False)


# ============================================================================
# UTILITY COMMANDS
# ============================================================================

@main.command()
@click.option('--full', is_flag=True, help='Export everything including notes')
@click.option('--recent', is_flag=True, help='Export only recent context (last 7 days)')
@click.option('--context', is_flag=True, help='Export only current state and goals')
@click.option('--output', '-o', type=click.Path(), help='Save to file instead of stdout')
def export(full, recent, context, output):
    """Export Workshop context for web chat conversations"""
    from .export import format_export

    store = get_storage()

    # Determine time range
    if recent:
        since = datetime.now() - timedelta(days=7)
    elif context:
        since = datetime.now() - timedelta(days=1)  # Just today
    else:
        since = datetime.now() - timedelta(days=30)  # Default: last month

    # Get data
    recent_entries = store.get_entries(limit=100, since=since)
    current_state = store.get_current_state()
    prefs = store.get_preferences()

    # Determine export mode
    if full:
        mode = "full"
    elif context:
        mode = "context"
    elif recent:
        mode = "recent"
    else:
        mode = "default"

    # Format export
    exported = format_export(
        recent_entries=recent_entries,
        current_state=current_state,
        preferences=prefs,
        workspace_dir=store.workspace_dir,
        mode=mode
    )

    # Output
    if output:
        output_path = Path(output)
        output_path.write_text(exported)
        success(f"Exported to {output_path}")
    else:
        click.echo(exported)


@main.command()
@click.argument('entry_id')
def delete(entry_id):
    """Delete an entry by ID or 'last' for most recent"""
    store = get_storage()

    if entry_id.lower() == 'last':
        last_entry = store.get_last_entry()
        if not last_entry:
            display_error("No entries to delete")
            return
        entry_id = last_entry['id']

        # Show what we're deleting
        click.echo(f"\n🗑️  Deleting: {last_entry['type']} - {last_entry['content'][:60]}...")
        if not click.confirm("Are you sure?"):
            display_info("Cancelled")
            return

    if store.delete_entry(entry_id):
        success(f"Deleted entry: {entry_id}")
    else:
        display_error(f"Entry not found: {entry_id}")


@main.command()
@click.option('--type', '-t', 'entry_type',
              type=click.Choice(['decision', 'note', 'gotcha', 'preference', 'antipattern']),
              help='Only show entries of this type')
@click.option('--days', '-d', type=int, default=7, help='Show entries from last N days')
def clean(entry_type, days):
    """Interactively delete entries"""
    from datetime import timedelta
    store = get_storage()

    # Get recent entries
    since = datetime.now() - timedelta(days=days)
    entries = store.get_entries(entry_type=entry_type, since=since, limit=50)

    if not entries:
        display_info("No entries to clean")
        return

    click.echo(f"\n🧹 Interactive Clean (last {days} days)\n")

    deleted_count = 0
    for i, entry in enumerate(entries, 1):
        # Format entry preview
        preview = entry['content'][:70]
        if len(entry['content']) > 70:
            preview += "..."

        click.echo(f"{i}. [{entry['type']}] {preview}")

        if click.confirm("  Delete this?", default=False):
            if store.delete_entry(entry['id']):
                click.echo("  ✓ Deleted")
                deleted_count += 1
            else:
                click.echo("  ✗ Failed")

        if i < len(entries):
            click.echo()  # Blank line between entries

    click.echo()
    success(f"Deleted {deleted_count} entries")


@main.command()
@click.argument('before_date')
@click.option('--type', '-t', 'entry_type',
              type=click.Choice(['decision', 'note', 'gotcha', 'preference', 'antipattern']),
              help='Only delete entries of this type')
def clear(before_date, entry_type):
    """Delete entries before a date (format: YYYY-MM-DD or '30 days ago')"""
    from datetime import timedelta
    from dateutil import parser

    store = get_storage()

    # Parse date
    try:
        # Try "N days ago" format
        if 'days ago' in before_date.lower():
            days = int(before_date.lower().split()[0])
            cutoff_date = datetime.now() - timedelta(days=days)
        # Try "N weeks ago" format
        elif 'weeks ago' in before_date.lower():
            weeks = int(before_date.lower().split()[0])
            cutoff_date = datetime.now() - timedelta(weeks=weeks)
        # Try "N months ago" format
        elif 'months ago' in before_date.lower():
            months = int(before_date.lower().split()[0])
            cutoff_date = datetime.now() - timedelta(days=months * 30)
        else:
            # Try parsing as date string
            cutoff_date = parser.parse(before_date)
    except (ValueError, AttributeError) as e:
        display_error(f"Invalid date format: {before_date}")
        click.echo("Examples: '2025-01-01', '30 days ago', '2 weeks ago'")
        return

    # Get count of entries that will be deleted
    if entry_type:
        entries = store.get_entries(entry_type=entry_type)
        entries_to_delete = [e for e in entries if datetime.fromisoformat(e['timestamp']) < cutoff_date]
        count = len(entries_to_delete)
    else:
        # Count all entries before date
        with store._get_connection() as conn:
            cursor = conn.execute(
                "SELECT COUNT(*) as count FROM entries WHERE timestamp < ?",
                (cutoff_date.isoformat(),)
            )
            count = cursor.fetchone()['count']

    if count == 0:
        display_info(f"No entries found before {cutoff_date.strftime('%Y-%m-%d')}")
        return

    # Confirm deletion
    type_str = f" {entry_type}" if entry_type else ""
    click.echo(f"\n⚠️  This will delete {count}{type_str} entries before {cutoff_date.strftime('%Y-%m-%d %H:%M')}")
    if not click.confirm("Are you sure?", default=False):
        display_info("Cancelled")
        return

    # Delete entries
    if entry_type:
        # Delete by type and date
        deleted = 0
        for entry in entries_to_delete:
            if store.delete_entry(entry['id']):
                deleted += 1
        success(f"Deleted {deleted} {entry_type} entries")
    else:
        deleted = store.delete_entries_before(cutoff_date)
        success(f"Deleted {deleted} entries")


@main.command()
def info():
    """Show workspace information"""
    store = get_storage()
    click.echo(f"\n🔧 Workshop version: 0.3.0")
    click.echo(f"📁 Workshop workspace: {store.workspace_dir}")
    click.echo(f"📄 Database file: {store.db_file}")

    # Count entries using SQLite
    with store._get_connection() as conn:
        cursor = conn.execute("SELECT COUNT(*) as count FROM entries")
        total_entries = cursor.fetchone()['count']
    click.echo(f"📝 Total entries: {total_entries}")

    current_state = store.get_current_state()
    goals = len(current_state.get('goals', []))
    next_steps = len(current_state.get('next_steps', []))

    click.echo(f"🎯 Active goals: {goals}")
    click.echo(f"📍 Next steps: {next_steps}\n")


# ============================================================================
# SESSION COMMANDS
# ============================================================================

@main.command()
@click.option('--limit', '-n', type=int, default=10, help='Number of sessions to show')
def sessions(limit):
    """List recent sessions"""
    from .display import display_sessions

    store = get_storage()
    session_list = store.get_sessions(limit=limit)
    display_sessions(session_list)


@main.command()
@click.argument('session_id', default='last')
def session(session_id):
    """Show details for a specific session (by ID or 'last')"""
    from .display import display_session_detail

    store = get_storage()

    if session_id == 'last':
        session_data = store.get_last_session()
        if not session_data:
            display_info("No sessions recorded yet")
            return
    else:
        session_data = store.get_session_by_id(session_id)
        if not session_data:
            error(f"Session not found: {session_id}")
            return

    display_session_detail(session_data)


@main.command()
@click.option('--global', 'global_config', is_flag=True, help='Set up global Claude Code integration')
@click.option('--local', 'local_config', is_flag=True, help='Set up local project integration')
def init(global_config, local_config):
    """Set up Claude Code integration for Workshop"""
    import json
    import shutil
    from pathlib import Path

    # If no flags specified, default to both
    if not global_config and not local_config:
        global_config = True
        local_config = True

    success_messages = []

    # Global configuration
    if global_config:
        global_settings_path = Path.home() / ".claude" / "settings.json"
        global_settings_path.parent.mkdir(parents=True, exist_ok=True)

        # Read existing settings or create new
        if global_settings_path.exists():
            with open(global_settings_path, 'r') as f:
                try:
                    settings = json.load(f)
                except json.JSONDecodeError:
                    settings = {}
        else:
            settings = {}

        # Add Workshop custom instructions with markers for easy replacement
        workshop_instructions = """## Workshop CLI - Persistent Context Tool

If the `workshop` CLI is available in this project, use it liberally to maintain context across sessions.

**Check for Workshop at session start:**
- Run `workshop context` to load existing project context
- If Workshop is not installed, continue normally

**Record information throughout sessions:**
- `workshop decision "<text>" -r "<reasoning>"` - Record decisions with why
- `workshop gotcha "<text>"` - Document gotchas and constraints
- `workshop note "<text>"` - Add general notes
- `workshop preference "<text>" --category <category>` - Save user preferences
- `workshop antipattern "<text>"` - Record patterns to avoid

**Manage goals and next steps:**
- `workshop goal add "<text>"` - Add a new goal
- `workshop goal done "<text>"` - Mark goal as completed
- `workshop goal list` - List active goals
- `workshop next add "<text>"` - Add a next step/TODO
- `workshop next done "<text>"` - Mark next step as completed
- Clean up: `workshop goal clean`, `workshop next clean`

**Query and search:**
- `workshop why "<query>"` - Smart search answering "why did we do X?"
- `workshop search "<query>"` - Full-text search across all entries
- `workshop context` - Current session summary
- `workshop recent` - Recent activity

**Clean up entries:**
- `workshop delete last` - Delete the most recent entry (if you made a mistake)
- `workshop clean` - Interactively delete entries (shows each, asks y/n)
- `workshop clean --type <type>` - Clean only specific type
- `workshop clear "30 days ago"` - Bulk delete old entries

**Important workflow:**
- Add new goals at session start: `workshop goal add "<what you're building>"`
- Mark goals/steps complete as you finish them to keep context clean
- Record decisions with reasoning as you make architectural choices
- Document gotchas and failed approaches as you discover them
- If you make a mistake, use `workshop delete last` to remove it

**Note:** Only use Workshop if it's installed. Check with `command -v workshop` or try running a command."""

        # Update custom instructions, replacing Workshop section if it exists
        existing_instructions = settings.get('customInstructions', '')

        import re
        # Look for Workshop section using flexible pattern
        workshop_pattern = r'## Workshop CLI - Persistent Context Tool.*?(?=\n##|\Z)'

        if re.search(workshop_pattern, existing_instructions, re.DOTALL):
            # Replace existing Workshop section
            settings['customInstructions'] = re.sub(
                workshop_pattern,
                workshop_instructions.strip(),
                existing_instructions,
                flags=re.DOTALL
            )
            success_messages.append(f"✓ Global configuration updated (Workshop section replaced)")
        else:
            # Append Workshop section
            if existing_instructions:
                settings['customInstructions'] = existing_instructions + '\n\n' + workshop_instructions
            else:
                settings['customInstructions'] = workshop_instructions
            success_messages.append(f"✓ Global configuration created with Workshop instructions")

        # Write back
        with open(global_settings_path, 'w') as f:
            json.dump(settings, f, indent=2)

    # Local configuration
    if local_config:
        local_claude_dir = Path.cwd() / ".claude"

        # Get the template .claude directory from workshop package
        try:
            # Get template directory from package
            template_dir = Path(__file__).parent / "claude_templates"

            if not template_dir.exists():
                error("Workshop claude_templates directory not found")
                click.echo("Please ensure Workshop is properly installed")
                return

            # Create .claude directory if it doesn't exist
            local_claude_dir.mkdir(parents=True, exist_ok=True)

            # Copy files
            files_copied = []

            # Copy settings.json (merge if exists)
            settings_src = template_dir / "settings.json"
            settings_dst = local_claude_dir / "settings.json"

            if settings_src.exists():
                with open(settings_src, 'r') as f:
                    template_settings = json.load(f)

                if settings_dst.exists():
                    with open(settings_dst, 'r') as f:
                        try:
                            existing = json.load(f)
                        except json.JSONDecodeError:
                            existing = {}

                    # Always update hooks from template
                    existing['hooks'] = template_settings.get('hooks', {})

                    # Always update customInstructions from template
                    existing['customInstructions'] = template_settings.get('customInstructions', '')

                    files_copied.append('settings.json (updated)')

                    with open(settings_dst, 'w') as f:
                        json.dump(existing, f, indent=2)
                else:
                    shutil.copy2(settings_src, settings_dst)
                    files_copied.append('settings.json')

            # Copy workshop-session-start.sh
            script_src = template_dir / "workshop-session-start.sh"
            script_dst = local_claude_dir / "workshop-session-start.sh"
            if script_src.exists() and not script_dst.exists():
                shutil.copy2(script_src, script_dst)
                script_dst.chmod(0o755)  # Make executable
                files_copied.append('workshop-session-start.sh')

            # Copy workshop-session-end.sh
            script_end_src = template_dir / "workshop-session-end.sh"
            script_end_dst = local_claude_dir / "workshop-session-end.sh"
            if script_end_src.exists() and not script_end_dst.exists():
                shutil.copy2(script_end_src, script_end_dst)
                script_end_dst.chmod(0o755)  # Make executable
                files_copied.append('workshop-session-end.sh')

            # Copy workshop-pre-compact.sh
            script_compact_src = template_dir / "workshop-pre-compact.sh"
            script_compact_dst = local_claude_dir / "workshop-pre-compact.sh"
            if script_compact_src.exists() and not script_compact_dst.exists():
                shutil.copy2(script_compact_src, script_compact_dst)
                script_compact_dst.chmod(0o755)  # Make executable
                files_copied.append('workshop-pre-compact.sh')

            # Copy commands directory
            commands_src = template_dir / "commands"
            commands_dst = local_claude_dir / "commands"
            if commands_src.exists() and not commands_dst.exists():
                shutil.copytree(commands_src, commands_dst)
                # Make scripts executable
                for script in commands_dst.glob("*.sh"):
                    script.chmod(0o755)
                files_copied.append('commands/')

            # Copy README
            readme_src = template_dir / "README.md"
            readme_dst = local_claude_dir / "README.md"
            if readme_src.exists() and not readme_dst.exists():
                shutil.copy2(readme_src, readme_dst)
                files_copied.append('README.md')

            if files_copied:
                success_messages.append(f"✓ Local configuration updated: .claude/")
                for file in files_copied:
                    success_messages.append(f"  • {file}")
            else:
                success_messages.append("✓ Local configuration up to date")

        except Exception as e:
            error(f"Failed to set up local configuration: {e}")
            return

    # Display results
    click.echo("\n📝 Workshop Claude Code Integration Setup\n")
    for msg in success_messages:
        click.echo(msg)

    click.echo("\n✨ Setup complete! Workshop will now be available in Claude Code sessions.")
    click.echo("\nNext steps:")
    if local_config:
        click.echo("  1. Start a new Claude Code session in this project")
        click.echo("  2. Workshop context will load automatically!")
    if global_config:
        click.echo("  • Claude will check for Workshop in all projects")
        click.echo("  • Install Workshop per-project to enable it")


# ============================================================================
# IMPORT COMMANDS
# ============================================================================

@main.command('import')
@click.argument('files', nargs=-1, type=click.Path(exists=True))
@click.option('--execute', is_flag=True, help='Execute import (default is dry-run preview)')
@click.option('--interactive', '-i', is_flag=True, help='Interactively review each extraction')
@click.option('--since', help='Only import after date (YYYY-MM-DD or "last-import")')
@click.option('--force', is_flag=True, help='Re-import even if already processed')
def import_sessions(files, execute, interactive, since, force):
    """
    Import historical sessions from JSONL transcripts.

    By default, imports current project's JSONL files incrementally.
    Use --execute to actually import (default is preview only).

    Examples:
      workshop import                    # Preview current project
      workshop import --execute          # Import current project
      workshop import file.jsonl -i      # Interactive review
      workshop import --since 2025-10-01 # Only import after date
    """
    from .jsonl_parser import JSONLParser
    from .storage_sqlite import WorkshopStorageSQLite
    from datetime import datetime
    from pathlib import Path
    import glob

    parser = JSONLParser()
    store = WorkshopStorageSQLite()

    # Determine which files to import
    if not files:
        # Smart default: current project's JSONL directory
        import os
        cwd = Path(os.getcwd())

        # Search upward for .claude/ directory to find the actual project root
        # This handles cases where git root != project root
        claude_root = None
        for parent in [cwd] + list(cwd.parents):
            if (parent / '.claude').exists():
                claude_root = parent
                break

        # Use .claude location if found, otherwise use cwd
        project_path = claude_root if claude_root else cwd

        # Normalize path for Claude's directory structure
        # Claude Code converts absolute paths to directory names like:
        # /Users/name/project -> -Users-name-project
        norm_path = str(project_path).replace('/', '-').replace('_', '-')

        claude_projects = Path.home() / '.claude' / 'projects' / norm_path

        if claude_projects.exists():
            jsonl_files = list(claude_projects.glob('*.jsonl'))
        else:
            error(f"No JSONL files found for current project")
            click.echo(f"\n💡 Expected location: {claude_projects}")
            if claude_root:
                click.echo(f"   (Using .claude/ location: {claude_root})")

            # Platform-specific help
            import platform
            system = platform.system()

            click.echo(f"\n📚 Claude Code JSONL locations by platform:")
            if system == "Darwin" or system == "Linux":
                click.echo(f"   • macOS/Linux: ~/.claude/projects/<normalized-project-path>/")
                click.echo(f"   • Project paths are normalized: /Users/name/project → -Users-name-project")
            elif system == "Windows":
                click.echo(f"   • Windows: %USERPROFILE%\\.claude\\projects\\<normalized-project-path>\\")
                click.echo(f"   • Project paths are normalized: C:\\Users\\name\\project → C-Users-name-project")
            else:
                click.echo(f"   • Check ~/.claude/projects/ for session files")

            click.echo(f"\n🔍 Troubleshooting:")
            click.echo(f"   1. Verify Claude Code has been run in this project")
            click.echo(f"   2. Check available sessions: ls ~/.claude/projects/")
            click.echo(f"   3. Manual import: workshop import <path-to-jsonl-file>")

            return
    else:
        # Expand globs and collect files
        jsonl_files = []
        for pattern in files:
            if '*' in pattern:
                jsonl_files.extend([Path(f) for f in glob.glob(pattern)])
            else:
                jsonl_files.append(Path(pattern))

    if not jsonl_files:
        display_info("No JSONL files to import")
        return

    click.echo(f"\n📊 Found {len(jsonl_files)} JSONL file{'s' if len(jsonl_files) != 1 else ''}\n")

    # Process each file
    total_entries = []
    files_processed = 0
    files_skipped = 0

    for jsonl_path in jsonl_files:
        click.echo(f"Analyzing {jsonl_path.name}...")

        # Check if already imported
        last_import = store.get_last_import(str(jsonl_path))

        if last_import and not force:
            # Incremental: resume from last UUID
            start_uuid = last_import['last_message_uuid']

            # Check if file changed
            current_hash = parser.calculate_file_hash(jsonl_path)
            if current_hash == last_import['jsonl_hash']:
                click.echo(f"  ⏭️  Skipped (no new messages)")
                files_skipped += 1
                continue
        else:
            start_uuid = None

        # Parse JSONL file
        try:
            result = parser.parse_jsonl_file(jsonl_path, start_from_uuid=start_uuid)
        except Exception as e:
            error(f"  ✗ Failed to parse: {e}")
            continue

        # Filter by confidence and date
        filtered_entries = []
        for entry in result.entries:
            # Skip low confidence
            if entry.confidence < 0.6:
                continue

            # Filter by date if specified
            if since:
                if since == "last-import" and last_import:
                    cutoff = datetime.fromisoformat(last_import['import_timestamp'])
                else:
                    try:
                        cutoff = datetime.fromisoformat(since)
                    except:
                        error(f"Invalid date format: {since}")
                        return

                entry_time = datetime.fromisoformat(entry.timestamp)
                if entry_time < cutoff:
                    continue

            filtered_entries.append(entry)

        if not filtered_entries:
            click.echo(f"  ⏭️  Skipped (no new entries)")
            files_skipped += 1
            continue

        # Show summary
        decisions = [e for e in filtered_entries if e.type == 'decision']
        gotchas = [e for e in filtered_entries if e.type == 'gotcha']
        preferences = [e for e in filtered_entries if e.type == 'preference']

        click.echo(f"  ✓ {len(decisions)} decisions")
        click.echo(f"  ✓ {len(gotchas)} gotchas")
        click.echo(f"  ✓ {len(preferences)} preferences")

        # Interactive review
        if interactive and not execute:
            click.echo("\n  💡 Use --execute with --interactive to review and import")

        # Store for batch import
        total_entries.extend([(jsonl_path, result, filtered_entries)])
        files_processed += 1

    # Summary
    total_count = sum(len(entries) for _, _, entries in total_entries)

    click.echo(f"\n📊 Import Summary:")
    click.echo(f"  Files processed: {files_processed}")
    click.echo(f"  Files skipped: {files_skipped}")
    click.echo(f"  Total entries: {total_count}")

    if not execute:
        click.echo(f"\n💡 This was a preview. Use --execute to import")
        return

    # Execute import
    click.echo(f"\n📥 Importing...")

    imported_count = 0
    for jsonl_path, result, entries in total_entries:
        # Interactive review mode
        if interactive:
            reviewed_entries = []
            for entry in entries:
                preview = entry.content[:70]
                if len(entry.content) > 70:
                    preview += "..."

                click.echo(f"\n[{entry.type}] {preview}")
                if entry.reasoning:
                    click.echo(f"  Reasoning: {entry.reasoning}")
                click.echo(f"  Confidence: {entry.confidence:.2f}")

                if click.confirm("  Import this?", default=True):
                    reviewed_entries.append(entry)

            entries = reviewed_entries

        # Import entries
        for entry in entries:
            store.add_entry(
                entry_type=entry.type,
                content=entry.content,
                reasoning=entry.reasoning,
                timestamp=entry.timestamp
            )
            imported_count += 1

        # Record import
        file_hash = parser.calculate_file_hash(jsonl_path)
        store.record_import(
            jsonl_path=str(jsonl_path),
            jsonl_hash=file_hash,
            last_uuid=result.last_message_uuid,
            last_timestamp=result.last_message_timestamp,
            messages_imported=result.messages_processed,
            entries_created=len(entries)
        )

    success(f"Imported {imported_count} entries from {files_processed} files")


@main.command('import-status')
def import_status():
    """Show import history and statistics"""
    from .storage_sqlite import WorkshopStorageSQLite
    from datetime import datetime

    store = WorkshopStorageSQLite()
    history = store.get_import_history(limit=10)

    if not history:
        display_info("No imports yet")
        click.echo("\nRun 'workshop import' to import JSONL sessions")
        return

    click.echo(f"\n📊 Import History\n")

    for record in history:
        jsonl_name = Path(record['jsonl_path']).name
        import_time = datetime.fromisoformat(record['import_timestamp'])
        time_ago = _format_time_ago(import_time)

        click.echo(f"• {jsonl_name}")
        click.echo(f"  Imported {time_ago}")
        click.echo(f"  {record['entries_created']} entries from {record['messages_imported']} messages")
        click.echo()

    # Show total stats
    total_files = len(history)
    total_entries = sum(r['entries_created'] for r in history)

    click.echo(f"Total: {total_entries} entries from {total_files} files")


@main.command()
@click.option('--host', default='127.0.0.1', help='Host to bind to (default: 127.0.0.1)')
@click.option('--port', '-p', default=5000, type=int, help='Port to run on (default: 5000)')
@click.option('--debug/--no-debug', default=False, help='Run in debug mode')
def web(host, port, debug):
    """Launch web UI for browsing and editing entries"""
    try:
        from .web.app import run
    except ImportError:
        display_error("Flask is not installed. Install with: pip install flask")
        return

    store = get_storage()
    workspace_path = store.workspace_dir

    click.echo(f"\n🌐 Starting Workshop Web UI...")
    click.echo(f"   Workspace: {workspace_path}")
    click.echo(f"   URL: http://{host}:{port}")
    click.echo(f"\n⚠️  Note: Web UI shows data from the workspace above.")
    click.echo(f"   To view a different project, stop this server and run 'workshop web' from that project.\n")
    click.echo(f"Press Ctrl+C to stop\n")

    run(host=host, port=port, debug=debug, workspace_dir=workspace_path)


def _format_time_ago(dt: datetime) -> str:
    """Format datetime as relative time"""
    from datetime import timedelta
    now = datetime.now()
    diff = now - dt

    if diff < timedelta(minutes=1):
        return "just now"
    elif diff < timedelta(hours=1):
        mins = int(diff.total_seconds() / 60)
        return f"{mins} minute{'s' if mins != 1 else ''} ago"
    elif diff < timedelta(days=1):
        hours = int(diff.total_seconds() / 3600)
        return f"{hours} hour{'s' if hours != 1 else ''} ago"
    elif diff < timedelta(days=7):
        days = diff.days
        return f"{days} day{'s' if days != 1 else ''} ago"
    else:
        return dt.strftime("%Y-%m-%d")


if __name__ == '__main__':
    main()
