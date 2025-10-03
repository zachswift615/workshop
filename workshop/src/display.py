# -*- coding: utf-8 -*-
"""
Display utilities for Workshop - pretty terminal output using rich
"""
from datetime import datetime
from typing import List, Dict
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.markdown import Markdown
from rich import box
from rich.text import Text


console = Console()


def format_timestamp(iso_timestamp: str) -> str:
    """Format ISO timestamp to relative time (e.g., '2 hours ago')"""
    dt = datetime.fromisoformat(iso_timestamp)
    now = datetime.now()
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
