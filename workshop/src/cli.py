"""
CLI interface for Workshop
"""
import click
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional

from .storage import WorkshopStorage
from .display import (
    display_entry, display_entries, display_context,
    display_preferences, display_current_state,
    success, error, info
)


# Global storage instance
storage = None


def get_storage() -> WorkshopStorage:
    """Get or create storage instance"""
    global storage
    if storage is None:
        storage = WorkshopStorage()
    return storage


@click.group()
@click.option('--workspace', type=click.Path(), help='Custom workspace directory')
def main(workspace):
    """
    Workshop - Persistent context tool for Claude Code.

    Maintains decisions, notes, preferences, and context across sessions.
    """
    global storage
    if workspace:
        storage = WorkshopStorage(Path(workspace))
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
        info(f"Reasoning: {reasoning}")


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
        info("No active goals")
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


@main.command()
@click.argument('content')
def next(content):
    """Add a next step / TODO"""
    store = get_storage()
    store.add_next_step(content)
    success(f"Next step added: {content}")


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
def search(query, limit):
    """Search entries by keyword"""
    store = get_storage()
    results = store.search(query, limit=limit)
    display_entries(results, show_full=False)


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
        info(f"No activity in the last {days} days")
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
def info():
    """Show workspace information"""
    store = get_storage()
    click.echo(f"\n📁 Workshop workspace: {store.workspace_dir}")
    click.echo(f"📄 Data file: {store.data_file}")

    data = store._read_data()
    total_entries = len(data.get('entries', []))
    click.echo(f"📝 Total entries: {total_entries}")

    current_state = store.get_current_state()
    goals = len(current_state.get('goals', []))
    next_steps = len(current_state.get('next_steps', []))

    click.echo(f"🎯 Active goals: {goals}")
    click.echo(f"📍 Next steps: {next_steps}\n")


if __name__ == '__main__':
    main()
