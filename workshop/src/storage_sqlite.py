"""
SQLite storage layer for Workshop - handles reading/writing to SQLite database
"""
import json
import sqlite3
import os
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any
import uuid


class WorkshopStorageSQLite:
    """Manages persistent storage of workshop data using SQLite"""

    def __init__(self, workspace_dir: Optional[Path] = None):
        """
        Initialize storage.

        Args:
            workspace_dir: Custom workspace directory. If None, auto-detects
                          project .workshop/ or falls back to ~/.workshop/
        """
        self.workspace_dir = workspace_dir or self._find_workspace()
        self.db_file = self.workspace_dir / "workshop.db"
        self.data_file = self.workspace_dir / "data.json"  # Legacy JSON file

        # Ensure workspace exists
        self.workspace_dir.mkdir(parents=True, exist_ok=True)

        # Initialize database
        self._init_db()

    def _find_workspace(self) -> Path:
        """
        Find or create the appropriate workspace directory.

        Priority order:
        1. WORKSHOP_DIR environment variable
        2. .workshop/ in current dir or parents (git root)
        3. ~/.workshop/ for global storage
        """
        # Check environment variable first
        env_dir = os.environ.get('WORKSHOP_DIR')
        if env_dir:
            return Path(env_dir).expanduser().resolve()

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

    def _get_connection(self) -> sqlite3.Connection:
        """Get a database connection with proper settings"""
        conn = sqlite3.connect(str(self.db_file))
        conn.row_factory = sqlite3.Row  # Enable dict-like access
        conn.execute("PRAGMA foreign_keys = ON")  # Enable foreign keys
        return conn

    def _init_db(self):
        """Initialize database schema"""
        schema_file = Path(__file__).parent / "schema.sql"

        with self._get_connection() as conn:
            with open(schema_file, 'r') as f:
                schema_sql = f.read()
                conn.executescript(schema_sql)
            conn.commit()

    # ========================================================================
    # Entry Management
    # ========================================================================

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

        entry_id = str(uuid.uuid4())
        timestamp = datetime.now().isoformat()

        # Get git info
        git_info = get_git_info()
        branch = git_info.get("branch", "")
        commit = git_info.get("commit", "")

        with self._get_connection() as conn:
            # Insert entry
            conn.execute("""
                INSERT INTO entries (id, type, content, reasoning, timestamp, branch, commit_hash, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (entry_id, entry_type, content, reasoning, timestamp, branch, commit,
                  json.dumps(metadata) if metadata else None))

            # Insert tags
            if tags:
                for tag in tags:
                    conn.execute("""
                        INSERT INTO tags (entry_id, tag) VALUES (?, ?)
                    """, (entry_id, tag))

            # Insert files
            if files:
                for file_path in files:
                    conn.execute("""
                        INSERT INTO files (entry_id, file_path) VALUES (?, ?)
                    """, (entry_id, file_path))

            conn.commit()

        # Build and return entry dict
        entry = {
            "id": entry_id,
            "type": entry_type,
            "content": content,
            "timestamp": timestamp,
            "tags": tags or [],
            "files": files or [],
            "metadata": metadata or {}
        }

        if reasoning:
            entry["reasoning"] = reasoning
        if branch:
            entry["branch"] = branch
        if commit:
            entry["commit"] = commit

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
        with self._get_connection() as conn:
            # Build query
            query = "SELECT * FROM entries WHERE 1=1"
            params = []

            if entry_type:
                query += " AND type = ?"
                params.append(entry_type)

            if since:
                query += " AND timestamp >= ?"
                params.append(since.isoformat())

            if tags:
                # Join with tags table to filter by tags
                placeholders = ','.join('?' * len(tags))
                query = f"""
                    SELECT DISTINCT e.* FROM entries e
                    JOIN tags t ON e.id = t.entry_id
                    WHERE t.tag IN ({placeholders})
                """
                params = tags

                if entry_type:
                    query += " AND e.type = ?"
                    params.append(entry_type)

                if since:
                    query += " AND e.timestamp >= ?"
                    params.append(since.isoformat())

            query += " ORDER BY timestamp DESC"

            if limit:
                query += " LIMIT ?"
                params.append(limit)

            cursor = conn.execute(query, params)
            rows = cursor.fetchall()

            # Convert rows to dicts with tags and files
            entries = []
            for row in rows:
                entry = dict(row)
                entry_id = entry['id']

                # Load tags
                tags_cursor = conn.execute(
                    "SELECT tag FROM tags WHERE entry_id = ?", (entry_id,)
                )
                entry['tags'] = [t['tag'] for t in tags_cursor.fetchall()]

                # Load files
                files_cursor = conn.execute(
                    "SELECT file_path FROM files WHERE entry_id = ?", (entry_id,)
                )
                entry['files'] = [f['file_path'] for f in files_cursor.fetchall()]

                # Parse metadata if present
                if entry.get('metadata'):
                    entry['metadata'] = json.loads(entry['metadata'])
                else:
                    entry['metadata'] = {}

                entries.append(entry)

            return entries

    def search(self, query: str, limit: Optional[int] = None) -> List[Dict]:
        """
        Search entries using full-text search.

        Args:
            query: Search query
            limit: Maximum results to return

        Returns:
            List of matching entries
        """
        with self._get_connection() as conn:
            # Use FTS5 for full-text search
            fts_query = " AND ".join(query.split())  # Convert to FTS5 AND query

            sql = """
                SELECT e.* FROM entries e
                JOIN entries_fts fts ON e.rowid = fts.rowid
                WHERE entries_fts MATCH ?
                ORDER BY rank
            """

            params = [fts_query]

            if limit:
                sql += " LIMIT ?"
                params.append(limit)

            cursor = conn.execute(sql, params)
            rows = cursor.fetchall()

            # Convert to dicts
            entries = []
            for row in rows:
                entry = dict(row)
                entry_id = entry['id']

                # Load tags
                tags_cursor = conn.execute(
                    "SELECT tag FROM tags WHERE entry_id = ?", (entry_id,)
                )
                entry['tags'] = [t['tag'] for t in tags_cursor.fetchall()]

                # Load files
                files_cursor = conn.execute(
                    "SELECT file_path FROM files WHERE entry_id = ?", (entry_id,)
                )
                entry['files'] = [f['file_path'] for f in files_cursor.fetchall()]

                # Parse metadata
                if entry.get('metadata'):
                    entry['metadata'] = json.loads(entry['metadata'])
                else:
                    entry['metadata'] = {}

                entries.append(entry)

            return entries

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
        # Use FTS for initial search, then score
        entries = self.search(query, limit=limit * 3)  # Get more candidates

        # Calculate relevance scores
        keywords = query.lower().split()
        results = []

        for entry in entries:
            score = 0

            # Type priority
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

            # Keyword matches
            content_lower = entry.get("content", "").lower()
            reasoning_lower = (entry.get("reasoning") or "").lower()

            for keyword in keywords:
                if keyword in content_lower:
                    score += 10
                if keyword in reasoning_lower:
                    score += 15

            # Recency bonus
            try:
                entry_date = datetime.fromisoformat(entry["timestamp"])
                days_old = (datetime.now() - entry_date).days
                recency_score = max(0, 10 - (days_old // 7))
                score += recency_score
            except:
                pass

            results.append((score, entry))

        # Sort by score
        results.sort(key=lambda x: (x[0], x[1]["timestamp"]), reverse=True)

        # Return top entries
        entries = [entry for score, entry in results[:limit]]
        return entries

    # ========================================================================
    # Preferences
    # ========================================================================

    def add_preference(self, category: str, content: str) -> None:
        """Add a preference to a specific category"""
        timestamp = datetime.now().isoformat()

        with self._get_connection() as conn:
            conn.execute("""
                INSERT INTO preferences (category, content, timestamp)
                VALUES (?, ?, ?)
            """, (category, content, timestamp))
            conn.commit()

    def get_preferences(self) -> Dict:
        """Get all preferences organized by category"""
        with self._get_connection() as conn:
            cursor = conn.execute("""
                SELECT category, content, timestamp
                FROM preferences
                ORDER BY category, timestamp DESC
            """)

            prefs = {}
            for row in cursor.fetchall():
                category = row['category']
                if category not in prefs:
                    prefs[category] = []
                prefs[category].append({
                    'content': row['content'],
                    'timestamp': row['timestamp']
                })

            return prefs

    # ========================================================================
    # Current State
    # ========================================================================

    def add_goal(self, goal: str) -> None:
        """Add a goal to current state"""
        timestamp = datetime.now().isoformat()

        with self._get_connection() as conn:
            conn.execute("""
                INSERT INTO current_state (type, content, timestamp)
                VALUES ('goal', ?, ?)
            """, (goal, timestamp))
            conn.commit()

    def add_next_step(self, step: str) -> None:
        """Add a next step to current state"""
        timestamp = datetime.now().isoformat()

        with self._get_connection() as conn:
            conn.execute("""
                INSERT INTO current_state (type, content, timestamp)
                VALUES ('next_step', ?, ?)
            """, (step, timestamp))
            conn.commit()

    def get_current_state(self) -> Dict:
        """Get current state (goals, blockers, next steps)"""
        with self._get_connection() as conn:
            state = {
                "goals": [],
                "blockers": [],
                "next_steps": []
            }

            # Get goals
            cursor = conn.execute("""
                SELECT content, timestamp FROM current_state
                WHERE type = 'goal' AND completed = 0
                ORDER BY timestamp DESC
            """)
            state["goals"] = [
                {"content": row['content'], "timestamp": row['timestamp']}
                for row in cursor.fetchall()
            ]

            # Get blockers
            cursor = conn.execute("""
                SELECT content, timestamp FROM current_state
                WHERE type = 'blocker' AND completed = 0
                ORDER BY timestamp DESC
            """)
            state["blockers"] = [
                {"content": row['content'], "timestamp": row['timestamp']}
                for row in cursor.fetchall()
            ]

            # Get next steps
            cursor = conn.execute("""
                SELECT content, timestamp FROM current_state
                WHERE type = 'next_step' AND completed = 0
                ORDER BY timestamp DESC
            """)
            state["next_steps"] = [
                {"content": row['content'], "timestamp": row['timestamp']}
                for row in cursor.fetchall()
            ]

            return state

    def clear_goals(self) -> None:
        """Clear all goals"""
        with self._get_connection() as conn:
            conn.execute("DELETE FROM current_state WHERE type = 'goal'")
            conn.commit()

    def clear_next_steps(self) -> None:
        """Clear all next steps"""
        with self._get_connection() as conn:
            conn.execute("DELETE FROM current_state WHERE type = 'next_step'")
            conn.commit()

    def complete_goal(self, goal_text: str) -> bool:
        """
        Mark a goal as completed by matching text.

        Args:
            goal_text: The goal text to match (case-insensitive, partial match)

        Returns:
            True if a goal was found and marked complete, False otherwise
        """
        with self._get_connection() as conn:
            # Find goal by partial text match
            cursor = conn.execute("""
                SELECT id FROM current_state
                WHERE type = 'goal' AND completed = 0
                AND LOWER(content) LIKE LOWER(?)
                ORDER BY timestamp DESC
                LIMIT 1
            """, (f"%{goal_text}%",))

            row = cursor.fetchone()
            if row:
                conn.execute("""
                    UPDATE current_state SET completed = 1
                    WHERE id = ?
                """, (row['id'],))
                conn.commit()
                return True
            return False

    def complete_next_step(self, step_text: str) -> bool:
        """
        Mark a next step as completed by matching text.

        Args:
            step_text: The step text to match (case-insensitive, partial match)

        Returns:
            True if a step was found and marked complete, False otherwise
        """
        with self._get_connection() as conn:
            # Find step by partial text match
            cursor = conn.execute("""
                SELECT id FROM current_state
                WHERE type = 'next_step' AND completed = 0
                AND LOWER(content) LIKE LOWER(?)
                ORDER BY timestamp DESC
                LIMIT 1
            """, (f"%{step_text}%",))

            row = cursor.fetchone()
            if row:
                conn.execute("""
                    UPDATE current_state SET completed = 1
                    WHERE id = ?
                """, (row['id'],))
                conn.commit()
                return True
            return False

    def clear_completed_goals(self) -> int:
        """
        Remove completed goals from database.

        Returns:
            Number of goals removed
        """
        with self._get_connection() as conn:
            cursor = conn.execute("""
                DELETE FROM current_state WHERE type = 'goal' AND completed = 1
            """)
            conn.commit()
            return cursor.rowcount

    def clear_completed_next_steps(self) -> int:
        """
        Remove completed next steps from database.

        Returns:
            Number of steps removed
        """
        with self._get_connection() as conn:
            cursor = conn.execute("""
                DELETE FROM current_state WHERE type = 'next_step' AND completed = 1
            """)
            conn.commit()
            return cursor.rowcount

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
        """Add a session summary"""
        with self._get_connection() as conn:
            # Insert session
            conn.execute("""
                INSERT INTO sessions (id, start_time, end_time, duration_minutes,
                                     summary, branch, reason, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (session_id, start_time, end_time, duration_minutes,
                  summary, branch, reason, json.dumps(metadata) if metadata else None))

            # Insert files
            if files_modified:
                for file_path in files_modified:
                    conn.execute("""
                        INSERT INTO session_files (session_id, file_path)
                        VALUES (?, ?)
                    """, (session_id, file_path))

            # Insert commands
            if commands_run:
                for command in commands_run:
                    conn.execute("""
                        INSERT INTO session_commands (session_id, command)
                        VALUES (?, ?)
                    """, (session_id, command))

            # Insert workshop entries
            if workshop_entries:
                for entry_type, count in workshop_entries.items():
                    if count > 0:
                        conn.execute("""
                            INSERT INTO session_workshop_entries (session_id, entry_type, count)
                            VALUES (?, ?, ?)
                        """, (session_id, entry_type, count))

            # Insert user requests
            if user_requests:
                for request in user_requests:
                    conn.execute("""
                        INSERT INTO session_user_requests (session_id, request)
                        VALUES (?, ?)
                    """, (session_id, request))

            conn.commit()

        # Build return dict
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

        return session

    def get_sessions(
        self,
        limit: Optional[int] = None,
        since: Optional[datetime] = None
    ) -> List[Dict]:
        """Retrieve sessions with optional filtering"""
        with self._get_connection() as conn:
            query = "SELECT * FROM sessions WHERE 1=1"
            params = []

            if since:
                query += " AND end_time >= ?"
                params.append(since.isoformat())

            query += " ORDER BY end_time DESC"

            if limit:
                query += " LIMIT ?"
                params.append(limit)

            cursor = conn.execute(query, params)
            rows = cursor.fetchall()

            sessions = []
            for row in rows:
                session = dict(row)
                session_id = session['id']

                # Load files
                files_cursor = conn.execute("""
                    SELECT file_path FROM session_files WHERE session_id = ?
                """, (session_id,))
                session['files_modified'] = [r['file_path'] for r in files_cursor.fetchall()]

                # Load commands
                commands_cursor = conn.execute("""
                    SELECT command FROM session_commands WHERE session_id = ?
                """, (session_id,))
                session['commands_run'] = [r['command'] for r in commands_cursor.fetchall()]

                # Load workshop entries
                entries_cursor = conn.execute("""
                    SELECT entry_type, count FROM session_workshop_entries WHERE session_id = ?
                """, (session_id,))
                session['workshop_entries'] = {
                    r['entry_type']: r['count'] for r in entries_cursor.fetchall()
                }

                # Load user requests
                requests_cursor = conn.execute("""
                    SELECT request FROM session_user_requests WHERE session_id = ?
                """, (session_id,))
                session['user_requests'] = [r['request'] for r in requests_cursor.fetchall()]

                # Parse metadata
                if session.get('metadata'):
                    session['metadata'] = json.loads(session['metadata'])
                else:
                    session['metadata'] = {}

                sessions.append(session)

            return sessions

    def get_session_by_id(self, session_id: str) -> Optional[Dict]:
        """Get a specific session by ID"""
        with self._get_connection() as conn:
            # Try as index first (1-based)
            try:
                index = int(session_id) - 1
                if index >= 0:
                    cursor = conn.execute("""
                        SELECT * FROM sessions ORDER BY end_time ASC LIMIT 1 OFFSET ?
                    """, (index,))
                    row = cursor.fetchone()
                    if row:
                        sessions = self.get_sessions()
                        sorted_sessions = sorted(sessions, key=lambda s: s['end_time'])
                        if index < len(sorted_sessions):
                            return sorted_sessions[index]
            except ValueError:
                pass

            # Try as session ID or prefix
            cursor = conn.execute("""
                SELECT * FROM sessions WHERE id = ? OR id LIKE ?
            """, (session_id, f"{session_id}%"))
            row = cursor.fetchone()

            if row:
                # Get full session with related data
                sessions = self.get_sessions()
                for session in sessions:
                    if session['id'] == row['id']:
                        return session

            return None

    def get_last_session(self) -> Optional[Dict]:
        """Get the most recent session"""
        sessions = self.get_sessions(limit=1)
        return sessions[0] if sessions else None
