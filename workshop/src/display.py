# -*- coding: utf-8 -*-
"""
Display utilities for Workshop - pretty terminal output using rich
"""
import sys
import platform
from datetime import datetime
from typing import List, Dict
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.markdown import Markdown
from rich import box
from rich.text import Text

# Fix for Windows: Force UTF-8 encoding to display emojis
if platform.system() == 'Windows' and hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

console = Console()


def format_timestamp(iso_timestamp: str) -> str:
    """
    Format ISO timestamp to relative time (e.g., '2 hours ago').

    Timestamps are stored as UTC (naive datetime). This converts to local time for display.
    """
    dt = datetime.fromisoformat(iso_timestamp)
    # Make both datetimes timezone-aware or both naive for comparison
    if dt.tzinfo is not None:
        # dt is timezone-aware, make now timezone-aware too
        from datetime import timezone
        now = datetime.now(timezone.utc)
    else:
        # dt is naive - assume it's UTC (standard storage practice)
        # Convert to local time for display
        from datetime import timezone
        dt_utc = dt.replace(tzinfo=timezone.utc)
        dt = dt_utc.astimezone()
        now = datetime.now().astimezone()

    diff = now - dt

    if diff.days > 0:
        if diff.days == 1:
            return "yesterday"
        elif diff.days < 7:
            return f"{diff.days} days ago"
        else:
            return dt.strftime("%Y-%m-%d")
    elif diff.seconds > 3600:
        hours = diff.seconds // 3600
        return f"{hours}h ago"
    elif diff.seconds > 60:
        minutes = diff.seconds // 60
        return f"{minutes}m ago"
    else:
        return "just now"


def get_type_emoji(entry_type: str) -> str:
    """Get emoji for entry type"""
    emoji_map = {
        "decision": "💡",
        "note": "📝",
        "gotcha": "⚠️",
        "preference": "👤",
        "antipattern": "🚫",
        "session": "🔄",
        "goal": "🎯",
        "blocker": "🛑",
        "next_step": "📍"
    }
    return emoji_map.get(entry_type, "📌")


def display_error(message: str):
    """Display an error message"""
    console.print(f"[red]✗ {message}[/red]")


def display_entry(entry: Dict, show_full: bool = False):
    """Display a single entry with rich formatting"""
    emoji = get_type_emoji(entry["type"])
    timestamp = format_timestamp(entry["timestamp"])

    # Build title
    title = f"{emoji} {entry['type'].upper()}"
    if entry.get("branch"):
        title += f" [dim]on {entry['branch']}[/dim]"

    # Build content
    content_lines = [f"[bold]{entry['content']}[/bold]"]

    if entry.get("reasoning"):
        content_lines.append(f"\n[dim]Why:[/dim] {entry['reasoning']}")

    if entry.get("tags"):
        tags_str = " ".join([f"[cyan]#{tag}[/cyan]" for tag in entry["tags"]])
        content_lines.append(f"\n{tags_str}")

    if show_full:
        if entry.get("files"):
            files_str = ", ".join([f"[blue]{f}[/blue]" for f in entry["files"]])
            content_lines.append(f"\n[dim]Files:[/dim] {files_str}")

        if entry.get("commit"):
            content_lines.append(f"\n[dim]Commit:[/dim] {entry['commit']}")

    content_lines.append(f"\n[dim]{timestamp}[/dim]")

    panel = Panel(
        "\n".join(content_lines),
        title=title,
        title_align="left",
        border_style="blue",
        box=box.ROUNDED
    )

    console.print(panel)


def display_entries(entries: List[Dict], show_full: bool = False):
    """Display multiple entries"""
    if not entries:
        console.print("[yellow]No entries found[/yellow]")
        return

    console.print(f"\n[bold]Found {len(entries)} entries:[/bold]\n")

    for entry in entries:
        display_entry(entry, show_full)
        console.print()


def display_why_results(entries: List[Dict], query: str):
    """
    Display results for 'why' queries with emphasis on reasoning.

    This is optimized for answering "why did we do X?" questions by:
    - Showing reasoning prominently
    - Highlighting the most relevant answer first
    - Providing context about when and where
    """
    if not entries:
        console.print(f"\n[yellow]🤷 No context found for:[/yellow] [bold]{query}[/bold]")
        console.print("\n[dim]Try:[/dim]")
        console.print("[dim]  • Different keywords[/dim]")
        console.print("[dim]  • Broader search terms[/dim]")
        console.print("[dim]  • Check what's recorded with `workshop recent`[/dim]\n")
        return

    # Show header
    console.print(f"\n[bold cyan]🔍 Why {query}?[/bold cyan]\n")

    # Display the top result with special emphasis
    top = entries[0]
    emoji = get_type_emoji(top["type"])

    console.print(f"[bold green]→ Primary Answer:[/bold green] {emoji} {top['type'].upper()}")
    console.print(f"  [bold]{top['content']}[/bold]")

    if top.get("reasoning"):
        console.print(f"\n  [bold cyan]Why:[/bold cyan]")
        console.print(f"  [italic]{top['reasoning']}[/italic]")

    # Show context
    context_parts = []
    if top.get("branch"):
        context_parts.append(f"[dim]on branch {top['branch']}[/dim]")
    if top.get("tags"):
        tags_str = " ".join([f"[cyan]#{tag}[/cyan]" for tag in top["tags"]])
        context_parts.append(tags_str)

    context_parts.append(f"[dim]{format_timestamp(top['timestamp'])}[/dim]")

    if context_parts:
        console.print(f"\n  {' · '.join(context_parts)}")

    if top.get("files"):
        files_str = ", ".join([f"[blue]{f}[/blue]" for f in top["files"]])
        console.print(f"  [dim]Related files:[/dim] {files_str}")

    # If there are more results, show them compactly
    if len(entries) > 1:
        console.print(f"\n[bold]Related context ({len(entries) - 1} more):[/bold]\n")

        for entry in entries[1:]:
            emoji = get_type_emoji(entry["type"])
            timestamp = format_timestamp(entry["timestamp"])

            console.print(f"  {emoji} {entry['content']}")

            if entry.get("reasoning"):
                # Show first 100 chars of reasoning
                reasoning_preview = entry["reasoning"][:100]
                if len(entry["reasoning"]) > 100:
                    reasoning_preview += "..."
                console.print(f"    [dim italic]{reasoning_preview}[/dim italic]")

            console.print(f"    [dim]{timestamp}[/dim]")
            console.print()

    console.print()


def display_context(
    recent_entries: List[Dict],
    current_state: Dict,
    preferences: Dict
):
    """
    Display session context summary.
    This is the killer feature - shown at session start.
    """
    console.print("\n[bold cyan]📝 Workshop Context[/bold cyan]\n")

    # Recent activity
    if recent_entries:
        latest = recent_entries[0]
        console.print(
            f"[bold]Last activity:[/bold] {latest['content']} "
            f"[dim]({format_timestamp(latest['timestamp'])})[/dim]"
        )

    # Current goals
    goals = current_state.get("goals", [])
    if goals:
        console.print("\n🎯 [bold]Active Goals:[/bold]")
        for goal in goals[-3:]:  # Show last 3 goals
            console.print(f"  • {goal['content']}")

    # Next steps
    next_steps = current_state.get("next_steps", [])
    if next_steps:
        console.print("\n📍 [bold]Next Steps:[/bold]")
        for step in next_steps[-3:]:  # Show last 3 steps
            console.print(f"  • {step['content']}")

    # Recent decisions
    decisions = [e for e in recent_entries if e["type"] == "decision"]
    if decisions:
        console.print("\n💡 [bold]Recent Decisions:[/bold]")
        for decision in decisions[:2]:  # Show last 2 decisions
            console.print(f"  • {decision['content']}")
            if decision.get("reasoning"):
                console.print(f"    [dim]{decision['reasoning']}[/dim]")

    # Recent gotchas
    gotchas = [e for e in recent_entries if e["type"] == "gotcha"]
    if gotchas:
        console.print("\n⚠️  [bold]Recent Gotchas:[/bold]")
        for gotcha in gotchas[:2]:
            console.print(f"  • {gotcha['content']}")

    # Preferences (just count for now, can expand later)
    if preferences:
        pref_count = sum(len(prefs) for prefs in preferences.values())
        if pref_count > 0:
            console.print(f"\n👤 [dim]{pref_count} user preferences recorded[/dim]")

    console.print()


def display_preferences(preferences: Dict):
    """Display all preferences organized by category"""
    if not preferences or all(not v for v in preferences.values()):
        console.print("[yellow]No preferences recorded yet[/yellow]")
        return

    console.print("\n👤 [bold]User Preferences[/bold]\n")

    for category, prefs in preferences.items():
        if prefs:
            console.print(f"[cyan]{category.replace('_', ' ').title()}:[/cyan]")
            for pref in prefs:
                console.print(f"  • {pref['content']}")
            console.print()


def display_current_state(state: Dict):
    """Display current goals, blockers, next steps"""
    console.print("\n🎯 [bold]Current State[/bold]\n")

    goals = state.get("goals", [])
    if goals:
        console.print("[cyan]Goals:[/cyan]")
        for goal in goals:
            console.print(f"  • {goal['content']}")
        console.print()

    blockers = state.get("blockers", [])
    if blockers:
        console.print("[red]Blockers:[/red]")
        for blocker in blockers:
            console.print(f"  • {blocker['content']}")
        console.print()

    next_steps = state.get("next_steps", [])
    if next_steps:
        console.print("[green]Next Steps:[/green]")
        for step in next_steps:
            console.print(f"  • {step['content']}")
        console.print()

    if not (goals or blockers or next_steps):
        console.print("[yellow]No active goals or next steps[/yellow]")


def success(message: str):
    """Display success message"""
    console.print(f"[green]✓[/green] {message}")


def error(message: str):
    """Display error message"""
    console.print(f"[red]✗[/red] {message}", style="bold red")


def info(message: str):
    """Display info message"""
    console.print(f"[blue]ℹ[/blue] {message}")


# ============================================================================
# Session Display Functions
# ============================================================================

def display_sessions(sessions: List[Dict]):
    """Display a list of sessions in summary format."""
    if not sessions:
        console.print("[yellow]No sessions recorded yet[/yellow]")
        return

    console.print(f"\n[bold cyan]🔄 Recent Sessions[/bold cyan] [dim]({len(sessions)} total)[/dim]\n")

    table = Table(show_header=True, header_style="bold cyan", box=box.ROUNDED)
    table.add_column("#", style="dim", width=4)
    table.add_column("When", style="cyan")
    table.add_column("Duration", style="green")
    table.add_column("Files", justify="right", style="blue")
    table.add_column("Entries", justify="right", style="yellow")
    table.add_column("Summary", style="white")

    for i, session in enumerate(sessions, 1):
        # Format timestamp
        try:
            end_dt = datetime.fromisoformat(session['end_time'].replace('Z', '+00:00'))
            when = format_timestamp(session['end_time'])
        except:
            when = "unknown"

        # Format duration
        duration_min = session.get('duration_minutes', 0)
        if duration_min < 60:
            duration = f"{duration_min}m"
        else:
            hours = duration_min // 60
            mins = duration_min % 60
            duration = f"{hours}h {mins}m" if mins > 0 else f"{hours}h"

        # Count files and entries
        files_count = len(session.get('files_modified', []))
        entries = session.get('workshop_entries', {})
        total_entries = sum(entries.values())

        # Get summary
        summary = session.get('summary', '')
        if len(summary) > 50:
            summary = summary[:47] + "..."

        table.add_row(
            str(i),
            when,
            duration,
            str(files_count),
            str(total_entries),
            summary
        )

    console.print(table)
    console.print()
    console.print("[dim]Use `workshop session <number>` or `workshop session last` to see details[/dim]\n")


def display_session_detail(session: Dict):
    """Display detailed information about a single session."""

    # Format timestamps
    try:
        start_dt = datetime.fromisoformat(session['start_time'].replace('Z', '+00:00'))
        end_dt = datetime.fromisoformat(session['end_time'].replace('Z', '+00:00'))
        start_str = start_dt.strftime('%Y-%m-%d %H:%M:%S')
        end_str = end_dt.strftime('%H:%M:%S')
    except:
        start_str = session.get('start_time', 'unknown')
        end_str = session.get('end_time', 'unknown')

    # Format duration
    duration_min = session.get('duration_minutes', 0)
    if duration_min < 60:
        duration = f"{duration_min} minutes"
    else:
        hours = duration_min // 60
        mins = duration_min % 60
        if mins > 0:
            duration = f"{hours} hour{'s' if hours != 1 else ''} {mins} minutes"
        else:
            duration = f"{hours} hour{'s' if hours != 1 else ''}"

    # Build header
    console.print(f"\n[bold cyan]🔄 Session Details[/bold cyan]\n")

    # Session info
    console.print(f"[bold]Session ID:[/bold] {session['id'][:12]}...")
    console.print(f"[bold]Started:[/bold] {start_str}")
    console.print(f"[bold]Ended:[/bold] {end_str}")
    console.print(f"[bold]Duration:[/bold] {duration}")

    if session.get('branch'):
        console.print(f"[bold]Branch:[/bold] {session['branch']}")

    if session.get('reason'):
        console.print(f"[bold]End Reason:[/bold] {session['reason']}")

    # Summary
    if session.get('summary'):
        console.print(f"\n[bold cyan]Summary:[/bold cyan]")
        console.print(f"  {session['summary']}")

    # Workshop entries
    entries = session.get('workshop_entries', {})
    total_entries = sum(entries.values())
    if total_entries > 0:
        console.print(f"\n[bold cyan]Workshop Entries:[/bold cyan]")
        for entry_type, count in entries.items():
            if count > 0:
                emoji = get_type_emoji(entry_type.rstrip('s'))  # Remove plural 's'
                console.print(f"  {emoji} {entry_type.capitalize()}: {count}")

    # Files modified
    files = session.get('files_modified', [])
    if files:
        console.print(f"\n[bold cyan]Files Modified:[/bold cyan] [dim]({len(files)} total)[/dim]")
        for file_path in files[:10]:  # Show first 10
            console.print(f"  [blue]{file_path}[/blue]")
        if len(files) > 10:
            console.print(f"  [dim]... and {len(files) - 10} more[/dim]")

    # Commands run
    commands = session.get('commands_run', [])
    if commands:
        console.print(f"\n[bold cyan]Commands Run:[/bold cyan] [dim]({len(commands)} total)[/dim]")
        for cmd in commands[:5]:  # Show first 5
            console.print(f"  [green]$[/green] [dim]{cmd}[/dim]")
        if len(commands) > 5:
            console.print(f"  [dim]... and {len(commands) - 5} more[/dim]")

    # User requests
    requests = session.get('user_requests', [])
    if requests:
        console.print(f"\n[bold cyan]User Requests:[/bold cyan] [dim]({len(requests)} total)[/dim]")
        for req in requests[:3]:  # Show first 3
            preview = req[:80] + "..." if len(req) > 80 else req
            console.print(f"  • {preview}")
        if len(requests) > 3:
            console.print(f"  [dim]... and {len(requests) - 3} more[/dim]")

    console.print()
