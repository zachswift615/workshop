"""
Storage layer for Workshop - handles reading/writing JSON data
"""
import json
import os
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any
import uuid


class WorkshopStorage:
    """Manages persistent storage of workshop data"""

    def __init__(self, workspace_dir: Optional[Path] = None):
        """
        Initialize storage.

        Args:
            workspace_dir: Custom workspace directory. If None, auto-detects
                          project .workshop/ or falls back to ~/.workshop/
        """
        self.workspace_dir = workspace_dir or self._find_workspace()
        self.data_file = self.workspace_dir / "data.json"
        self.config_file = self.workspace_dir / "config.json"

        # Ensure workspace exists
        self.workspace_dir.mkdir(parents=True, exist_ok=True)

        # Initialize data structure if needed
        self._init_data_file()

    def _find_workspace(self) -> Path:
        """
        Find or create the appropriate workspace directory.
        Looks for .workshop/ in current dir or parents (git root).
        Falls back to ~/.workshop/ for global storage.
        """
        current = Path.cwd()

        # Check current directory and parents for existing .workshop/
        for parent in [current] + list(current.parents):
            workshop_dir = parent / ".workshop"
            if workshop_dir.exists():
                return workshop_dir

            # Stop at git root
            if (parent / ".git").exists():
                # Create .workshop at git root
                workshop_dir = parent / ".workshop"
                return workshop_dir

        # No git repo found, use project-local .workshop
        return current / ".workshop"

    def _init_data_file(self):
        """Initialize data.json with default structure if it doesn't exist"""
        if not self.data_file.exists():
            default_data = {
                "entries": [],
                "preferences": {
                    "code_style": [],
                    "libraries": [],
                    "communication": [],
                    "testing": []
                },
                "current_state": {
                    "goals": [],
                    "blockers": [],
                    "next_steps": []
                },
                "sessions": []
            }
            self._write_data(default_data)

    def _read_data(self) -> Dict:
        """Read and parse data.json"""
        try:
            with open(self.data_file, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            # Return default structure if file is corrupted or missing
            return {
                "entries": [],
                "preferences": {},
                "current_state": {}
            }

    def _write_data(self, data: Dict):
        """Write data to data.json with pretty formatting"""
        with open(self.data_file, 'w') as f:
            json.dump(data, f, indent=2, default=str)

    def add_entry(
        self,
        entry_type: str,
        content: str,
        reasoning: Optional[str] = None,
        tags: Optional[List[str]] = None,
        files: Optional[List[str]] = None,
        metadata: Optional[Dict] = None
    ) -> Dict:
        """
        Add a new entry to the workshop.

        Args:
            entry_type: Type of entry (decision, note, gotcha, preference, etc.)
            content: Main content/text of the entry
            reasoning: Optional reasoning (mainly for decisions)
            tags: Optional list of tags
            files: Optional list of related files
            metadata: Optional additional metadata

        Returns:
            The created entry dict
        """
        from .git_utils import get_git_info

        data = self._read_data()

        entry = {
            "id": str(uuid.uuid4()),
            "type": entry_type,
            "content": content,
            "timestamp": datetime.now().isoformat(),
            "tags": tags or [],
            "files": files or [],
            "metadata": metadata or {}
        }

        # Add optional fields
        if reasoning:
            entry["reasoning"] = reasoning

        # Add git info if available
        git_info = get_git_info()
        if git_info.get("branch"):
            entry["branch"] = git_info["branch"]
        if git_info.get("commit"):
            entry["commit"] = git_info["commit"]

        data["entries"].append(entry)
        self._write_data(data)

        return entry

    def get_entries(
        self,
        entry_type: Optional[str] = None,
        tags: Optional[List[str]] = None,
        limit: Optional[int] = None,
        since: Optional[datetime] = None
    ) -> List[Dict]:
        """
        Retrieve entries with optional filtering.

        Args:
            entry_type: Filter by type
            tags: Filter by tags (entry must have at least one matching tag)
            limit: Maximum number of entries to return (most recent first)
            since: Only return entries after this datetime

        Returns:
            List of matching entries
        """
        data = self._read_data()
        entries = data["entries"]

        # Filter by type
        if entry_type:
            entries = [e for e in entries if e.get("type") == entry_type]

        # Filter by tags
        if tags:
            entries = [
                e for e in entries
                if any(tag in e.get("tags", []) for tag in tags)
            ]

        # Filter by date
        if since:
            entries = [
                e for e in entries
                if datetime.fromisoformat(e["timestamp"]) >= since
            ]

        # Sort by timestamp (newest first)
        entries.sort(key=lambda e: e["timestamp"], reverse=True)

        # Apply limit
        if limit:
            entries = entries[:limit]

        return entries

    def search(self, query: str, limit: Optional[int] = None) -> List[Dict]:
        """
        Search entries by keyword.
        Simple implementation: searches content, reasoning, tags, and files.

        Args:
            query: Search query (space-separated keywords)
            limit: Maximum results to return

        Returns:
            List of matching entries
        """
        data = self._read_data()
        entries = data["entries"]

        # Split query into keywords (lowercase for case-insensitive search)
        keywords = query.lower().split()

        results = []
        for entry in entries:
            # Build searchable text from entry
            searchable = " ".join([
                entry.get("content", ""),
                entry.get("reasoning", ""),
                " ".join(entry.get("tags", [])),
                " ".join(entry.get("files", []))
            ]).lower()

            # Check if all keywords match
            if all(keyword in searchable for keyword in keywords):
                results.append(entry)

        # Sort by timestamp (newest first)
        results.sort(key=lambda e: e["timestamp"], reverse=True)

        if limit:
            results = results[:limit]

        return results

    def why_search(self, query: str, limit: Optional[int] = 5) -> List[Dict]:
        """
        Smart search for "why" queries - prioritizes decisions and reasoning.

        This is optimized for answering "why did we do X?" questions by:
        - Prioritizing entries with reasoning (decisions)
        - Boosting gotchas and antipatterns
        - Scoring based on relevance

        Args:
            query: Search query (what you want to know why about)
            limit: Maximum results to return (default 5)

        Returns:
            List of matching entries, prioritized by relevance
        """
        data = self._read_data()
        entries = data["entries"]

        # Split query into keywords (lowercase for case-insensitive search)
        keywords = query.lower().split()

        results = []
        for entry in entries:
            # Build searchable text from entry
            searchable = " ".join([
                entry.get("content", ""),
                entry.get("reasoning", ""),
                " ".join(entry.get("tags", [])),
                " ".join(entry.get("files", []))
            ]).lower()

            # Check if all keywords match
            if all(keyword in searchable for keyword in keywords):
                # Calculate relevance score
                score = 0

                # Type priority (decisions are most important for "why")
                type_scores = {
                    "decision": 100,
                    "antipattern": 80,
                    "gotcha": 70,
                    "note": 50,
                    "preference": 40
                }
                score += type_scores.get(entry.get("type"), 30)

                # Boost if has reasoning
                if entry.get("reasoning"):
                    score += 50

                # Keyword match count (more matches = more relevant)
                content_lower = entry.get("content", "").lower()
                reasoning_lower = entry.get("reasoning", "").lower()
                for keyword in keywords:
                    if keyword in content_lower:
                        score += 10
                    if keyword in reasoning_lower:
                        score += 15  # Reasoning matches are extra valuable

                # Recency bonus (newer is slightly more relevant)
                # More recent entries get a small boost
                try:
                    entry_date = datetime.fromisoformat(entry["timestamp"])
                    days_old = (datetime.now() - entry_date).days
                    recency_score = max(0, 10 - (days_old // 7))  # Up to 10 points, decay weekly
                    score += recency_score
                except:
                    pass

                results.append((score, entry))

        # Sort by score (highest first), then by timestamp
        results.sort(key=lambda x: (x[0], x[1]["timestamp"]), reverse=True)

        # Extract just the entries (not the scores)
        results = [entry for score, entry in results]

        if limit:
            results = results[:limit]

        return results

    def add_preference(self, category: str, content: str) -> None:
        """Add a preference to a specific category"""
        data = self._read_data()

        if category not in data["preferences"]:
            data["preferences"][category] = []

        data["preferences"][category].append({
            "content": content,
            "timestamp": datetime.now().isoformat()
        })

        self._write_data(data)

    def get_preferences(self) -> Dict:
        """Get all preferences"""
        data = self._read_data()
        return data.get("preferences", {})

    def add_goal(self, goal: str) -> None:
        """Add a goal to current state"""
        data = self._read_data()
        data["current_state"]["goals"].append({
            "content": goal,
            "timestamp": datetime.now().isoformat()
        })
        self._write_data(data)

    def add_next_step(self, step: str) -> None:
        """Add a next step to current state"""
        data = self._read_data()
        data["current_state"]["next_steps"].append({
            "content": step,
            "timestamp": datetime.now().isoformat()
        })
        self._write_data(data)

    def get_current_state(self) -> Dict:
        """Get current state (goals, blockers, next steps)"""
        data = self._read_data()
        return data.get("current_state", {})

    def clear_goals(self) -> None:
        """Clear all goals"""
        data = self._read_data()
        data["current_state"]["goals"] = []
        self._write_data(data)

    def clear_next_steps(self) -> None:
        """Clear all next steps"""
        data = self._read_data()
        data["current_state"]["next_steps"] = []
        self._write_data(data)

    # ========================================================================
    # Session Management
    # ========================================================================

    def add_session(
        self,
        session_id: str,
        start_time: str,
        end_time: str,
        duration_minutes: int,
        files_modified: List[str] = None,
        commands_run: List[str] = None,
        workshop_entries: Dict[str, int] = None,
        user_requests: List[str] = None,
        summary: str = "",
        branch: str = "",
        reason: str = "",
        metadata: Dict[str, Any] = None
    ) -> Dict:
        """
        Add a session summary.

        Args:
            session_id: Unique session identifier
            start_time: ISO timestamp of session start
            end_time: ISO timestamp of session end
            duration_minutes: Session duration in minutes
            files_modified: List of file paths that were modified
            commands_run: List of commands that were executed
            workshop_entries: Dict of entry types created (e.g., {"decisions": 2, "notes": 3})
            user_requests: List of main user requests/questions
            summary: Auto-generated summary of session
            branch: Git branch name
            reason: Reason session ended (clear, logout, etc.)
            metadata: Additional metadata

        Returns:
            The created session dict
        """
        data = self._read_data()

        session = {
            "id": session_id,
            "start_time": start_time,
            "end_time": end_time,
            "duration_minutes": duration_minutes,
            "files_modified": files_modified or [],
            "commands_run": commands_run or [],
            "workshop_entries": workshop_entries or {},
            "user_requests": user_requests or [],
            "summary": summary,
            "branch": branch,
            "reason": reason,
            "metadata": metadata or {}
        }

        if "sessions" not in data:
            data["sessions"] = []

        data["sessions"].append(session)
        self._write_data(data)

        return session

    def get_sessions(
        self,
        limit: Optional[int] = None,
        since: Optional[datetime] = None
    ) -> List[Dict]:
        """
        Retrieve sessions with optional filtering.

        Args:
            limit: Maximum number of sessions to return (most recent first)
            since: Only return sessions after this datetime

        Returns:
            List of matching sessions
        """
        data = self._read_data()
        sessions = data.get("sessions", [])

        # Filter by date if provided
        if since:
            sessions = [
                s for s in sessions
                if datetime.fromisoformat(s["end_time"]) >= since
            ]

        # Sort by end time (newest first)
        sessions.sort(key=lambda s: s["end_time"], reverse=True)

        # Apply limit
        if limit:
            sessions = sessions[:limit]

        return sessions

    def get_session_by_id(self, session_id: str) -> Optional[Dict]:
        """
        Get a specific session by ID.

        Args:
            session_id: Session identifier (can be full ID or index like "1", "2")

        Returns:
            Session dict or None if not found
        """
        data = self._read_data()
        sessions = data.get("sessions", [])

        # Try as index first (1-based for user-friendliness)
        try:
            index = int(session_id) - 1
            if 0 <= index < len(sessions):
                # Return sessions in chronological order for indexing
                sorted_sessions = sorted(sessions, key=lambda s: s["end_time"])
                return sorted_sessions[index]
        except ValueError:
            pass

        # Try as session ID
        for session in sessions:
            if session["id"] == session_id or session["id"].startswith(session_id):
                return session

        return None

    def get_last_session(self) -> Optional[Dict]:
        """Get the most recent session."""
        sessions = self.get_sessions(limit=1)
        return sessions[0] if sessions else None
