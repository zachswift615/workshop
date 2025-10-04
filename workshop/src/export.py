"""
Export Workshop context for use in web chat conversations.
"""
from datetime import datetime, timedelta
from typing import Optional, List, Dict
from pathlib import Path


def format_export(
    recent_entries: List[Dict],
    current_state: Dict,
    preferences: Dict,
    workspace_dir: Path,
    mode: str = "default"
) -> str:
    """
    Format Workshop context for export to web chat.

    Args:
        recent_entries: Recent Workshop entries
        current_state: Current goals, blockers, next steps
        preferences: User preferences
        workspace_dir: Workshop workspace directory
        mode: Export mode (default, full, context, recent)

    Returns:
        Formatted markdown string
    """
    lines = []

    # Header
    lines.append("# Workshop Context Export")
    lines.append("")
    project_name = workspace_dir.parent.name
    lines.append(f"**Project:** {project_name}")
    lines.append(f"**Exported:** {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    lines.append("")
    lines.append("---")
    lines.append("")

    # Current State (always include)
    goals = current_state.get("goals", [])
    next_steps = current_state.get("next_steps", [])

    if goals or next_steps:
        lines.append("## 🎯 Current State")
        lines.append("")

        if goals:
            lines.append("**Active Goals:**")
            for goal in goals[:5]:  # Limit to 5
                lines.append(f"- {goal['content']}")
            lines.append("")

        if next_steps:
            lines.append("**Next Steps:**")
            for step in next_steps[:5]:  # Limit to 5
                lines.append(f"- {step['content']}")
            lines.append("")

    # Recent Decisions
    decisions = [e for e in recent_entries if e.get("type") == "decision"]
    if decisions:
        lines.append("## 💡 Recent Decisions")
        lines.append("")

        for decision in decisions[:10]:  # Show last 10 decisions
            # Format timestamp
            try:
                ts = datetime.fromisoformat(decision['timestamp'])
                time_ago = _format_time_ago(ts)
            except:
                time_ago = "recently"

            lines.append(f"### {decision['content']}")
            lines.append(f"*{time_ago}*")
            lines.append("")

            if decision.get("reasoning"):
                lines.append(f"**Why:** {decision['reasoning']}")
                lines.append("")

            if decision.get("tags"):
                tags = " ".join([f"`{tag}`" for tag in decision["tags"]])
                lines.append(f"Tags: {tags}")
                lines.append("")

    # Gotchas & Constraints
    gotchas = [e for e in recent_entries if e.get("type") == "gotcha"]
    if gotchas:
        lines.append("## ⚠️ Gotchas & Constraints")
        lines.append("")

        for gotcha in gotchas[:10]:
            lines.append(f"- {gotcha['content']}")

        lines.append("")

    # Antipatterns (things to avoid)
    antipatterns = [e for e in recent_entries if e.get("type") == "antipattern"]
    if antipatterns:
        lines.append("## 🚫 Antipatterns (Avoid These)")
        lines.append("")

        for ap in antipatterns[:10]:
            lines.append(f"- {ap['content']}")

        lines.append("")

    # User Preferences
    if preferences and any(preferences.values()):
        lines.append("## 👤 User Preferences")
        lines.append("")

        for category, prefs in preferences.items():
            if prefs:
                category_name = category.replace('_', ' ').title()
                lines.append(f"**{category_name}:**")
                for pref in prefs[:5]:  # Limit per category
                    lines.append(f"- {pref['content']}")
                lines.append("")

    # Recent Notes (if mode is full)
    if mode == "full":
        notes = [e for e in recent_entries if e.get("type") == "note"]
        if notes:
            lines.append("## 📝 Recent Notes")
            lines.append("")

            for note in notes[:10]:
                try:
                    ts = datetime.fromisoformat(note['timestamp'])
                    time_ago = _format_time_ago(ts)
                except:
                    time_ago = "recently"

                lines.append(f"- {note['content']} *({time_ago})*")

            lines.append("")

    # Footer with usage instructions
    lines.append("---")
    lines.append("")
    lines.append("*This context export helps Claude understand your project's history and preferences.*")
    lines.append("*Paste this into a web chat to give Claude continuity with your Claude Code sessions.*")
    lines.append("")

    return "\n".join(lines)


def _format_time_ago(dt: datetime) -> str:
    """Format datetime as relative time."""
    now = datetime.now()
    diff = now - dt

    if diff.days > 0:
        if diff.days == 1:
            return "yesterday"
        elif diff.days < 7:
            return f"{diff.days} days ago"
        elif diff.days < 30:
            weeks = diff.days // 7
            return f"{weeks} week{'s' if weeks != 1 else ''} ago"
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
