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
    display_why_results,
    success, error, info as display_info
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

        # Add Workshop custom instructions
        workshop_instructions = """## Workshop CLI - Persistent Context Tool

If the `workshop` CLI is available in this project, use it liberally to maintain context across sessions.

**Check for Workshop at session start:**
- Run `workshop context` to load existing project context
- If Workshop is not installed, continue normally

**Use Workshop throughout sessions to:**
- Record decisions: `workshop decision "<text>" -r "<reasoning>"`
- Document gotchas: `workshop gotcha "<text>" -t tag1 -t tag2`
- Add notes: `workshop note "<text>"`
- Track preferences: `workshop preference "<text>" --category code_style`
- Manage state: `workshop goal add "<text>"` and `workshop next "<text>"`

**Query context when needed (use these frequently!):**
- `workshop why "<topic>"` - THE KILLER FEATURE! Answers "why did we do X?" - prioritizes decisions with reasoning
- `workshop context` - Current session summary
- `workshop search "<query>"` - Find relevant entries
- `workshop recent` - Recent activity
- `workshop summary` - Activity overview

**Important:** Workshop helps maintain continuity across sessions. Document:
- Architectural decisions with reasoning
- Failed approaches and why they didn't work
- User preferences and coding style
- Gotchas and constraints
- Current goals and next steps

**Best Practice:** When you wonder "why did we choose X?" or "why is this implemented this way?", run `workshop why "X"` first before asking the user!

**Note:** Only use Workshop if it's installed in the project. Check with `command -v workshop` or try running a workshop command."""

        # Append to existing custom instructions or create new
        existing_instructions = settings.get('customInstructions', '')
        if 'Workshop CLI' not in existing_instructions:
            if existing_instructions:
                settings['customInstructions'] = existing_instructions + '\n\n' + workshop_instructions
            else:
                settings['customInstructions'] = workshop_instructions

            # Write back
            with open(global_settings_path, 'w') as f:
                json.dump(settings, f, indent=2)

            success_messages.append(f"✓ Global configuration updated: {global_settings_path}")
        else:
            success_messages.append(f"ℹ Global configuration already contains Workshop instructions")

    # Local configuration
    if local_config:
        local_claude_dir = Path.cwd() / ".claude"

        # Get the template .claude directory from workshop package
        try:
            workshop_root = Path(__file__).parent.parent.parent
            template_dir = workshop_root / ".claude"

            if not template_dir.exists():
                error("Workshop .claude template directory not found")
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

                    # Merge settings
                    if 'hooks' not in existing:
                        existing['hooks'] = template_settings.get('hooks', {})
                        files_copied.append('settings.json (hooks added)')

                    if 'customInstructions' not in existing:
                        existing['customInstructions'] = template_settings.get('customInstructions', '')
                        files_copied.append('settings.json (instructions added)')

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
                success_messages.append(f"✓ Local configuration created: .claude/")
                for file in files_copied:
                    success_messages.append(f"  • {file}")
            else:
                success_messages.append("ℹ Local configuration already exists")

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


if __name__ == '__main__':
    main()
