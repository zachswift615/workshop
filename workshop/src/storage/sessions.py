"""
Session management using SQLAlchemy.

Handles tracking of Claude Code sessions with files, commands, and workshop entries.
"""
import json
from datetime import datetime
from typing import Dict, List, Optional, Any
from uuid import UUID

from dateutil import parser as date_parser
from sqlalchemy import select, String
from sqlalchemy.orm import Session as DBSession

from ..models import (
    Session as SessionModel,
    SessionFile,
    SessionCommand,
    SessionWorkshopEntry,
    SessionUserRequest
)


class SessionsManager:
    """Manages Claude Code sessions using SQLAlchemy."""

    def __init__(self, db_session: DBSession, project_id: Optional[UUID] = None):
        """
        Initialize sessions manager.

        Args:
            db_session: SQLAlchemy session
            project_id: Project ID for multi-tenant isolation (None for OSS mode)
        """
        self.session = db_session
        self.project_id = project_id

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
            start_time: Session start time (ISO format)
            end_time: Session end time (ISO format)
            duration_minutes: Duration in minutes
            files_modified: List of modified file paths
            commands_run: List of commands executed
            workshop_entries: Dict mapping entry types to counts
            user_requests: List of user requests
            summary: Session summary text
            branch: Git branch
            reason: Resume source/reason
            metadata: Additional metadata

        Returns:
            The created session dict
        """
        # Create session
        session_model = SessionModel(
            id=UUID(session_id),
            project_id=self.project_id,
            start_time=date_parser.parse(start_time),
            end_time=date_parser.parse(end_time),
            duration_minutes=duration_minutes,
            summary=summary or None,
            branch=branch or None,
            reason=reason or None,
            session_metadata=json.dumps(metadata) if metadata else None
        )
        self.session.add(session_model)
        self.session.flush()

        # Add files
        if files_modified:
            for file_path in files_modified:
                self.session.add(SessionFile(
                    session_id=session_model.id,
                    file_path=file_path
                ))

        # Add commands
        if commands_run:
            for command in commands_run:
                self.session.add(SessionCommand(
                    session_id=session_model.id,
                    command=command
                ))

        # Add workshop entries
        if workshop_entries:
            for entry_type, count in workshop_entries.items():
                if count > 0:
                    self.session.add(SessionWorkshopEntry(
                        session_id=session_model.id,
                        entry_type=entry_type,
                        count=count
                    ))

        # Add user requests
        if user_requests:
            for request in user_requests:
                self.session.add(SessionUserRequest(
                    session_id=session_model.id,
                    request=request
                ))

        self.session.commit()

        return self._session_to_dict(session_model)

    def get_sessions(
        self,
        limit: Optional[int] = None,
        since: Optional[datetime] = None
    ) -> List[Dict]:
        """
        Retrieve sessions with optional filtering.

        Args:
            limit: Maximum number of sessions to return
            since: Only return sessions after this datetime

        Returns:
            List of session dicts
        """
        query = select(SessionModel)

        # Apply project filter
        if self.project_id:
            query = query.where(SessionModel.project_id == self.project_id)

        # Filter by time
        if since:
            query = query.where(SessionModel.end_time >= since)

        # Order by end_time descending
        query = query.order_by(SessionModel.end_time.desc())

        # Apply limit
        if limit:
            query = query.limit(limit)

        sessions = self.session.execute(query).scalars().all()
        return [self._session_to_dict(s) for s in sessions]

    def get_session_by_id(self, session_id: str) -> Optional[Dict]:
        """
        Get a specific session by ID.

        Supports:
        - Full UUID
        - UUID prefix
        - Numeric index (1-based)

        Args:
            session_id: Session ID, prefix, or numeric index

        Returns:
            Session dict or None if not found
        """
        # Try as numeric index first (1-based)
        try:
            index = int(session_id) - 1
            if index >= 0:
                # Get all sessions sorted by end_time
                sessions = self.get_sessions()
                sessions_sorted = sorted(sessions, key=lambda s: s['end_time'])
                if index < len(sessions_sorted):
                    return sessions_sorted[index]
        except ValueError:
            pass

        # Try as UUID or UUID prefix
        try:
            # Try exact UUID match first
            session_uuid = UUID(session_id)
            query = select(SessionModel).where(SessionModel.id == session_uuid)
        except ValueError:
            # Try as prefix
            query = select(SessionModel).where(
                SessionModel.id.cast(String).like(f"{session_id}%")
            )

        # Apply project filter
        if self.project_id:
            query = query.where(SessionModel.project_id == self.project_id)

        session = self.session.execute(query).scalar_one_or_none()
        return self._session_to_dict(session) if session else None

    def get_last_session(self) -> Optional[Dict]:
        """
        Get the most recent session.

        Returns:
            Most recent session or None if no sessions exist
        """
        sessions = self.get_sessions(limit=1)
        return sessions[0] if sessions else None

    def _session_to_dict(self, session: SessionModel) -> Dict:
        """Convert Session model to dictionary."""
        # Load related data
        files = self.session.query(SessionFile).filter_by(session_id=session.id).all()
        commands = self.session.query(SessionCommand).filter_by(session_id=session.id).all()
        workshop_entries = self.session.query(SessionWorkshopEntry).filter_by(session_id=session.id).all()
        user_requests = self.session.query(SessionUserRequest).filter_by(session_id=session.id).all()

        result = {
            'id': str(session.id),
            'start_time': session.start_time.isoformat(),
            'end_time': session.end_time.isoformat(),
            'duration_minutes': session.duration_minutes,
            'files_modified': [f.file_path for f in files],
            'commands_run': [c.command for c in commands],
            'workshop_entries': {e.entry_type: e.count for e in workshop_entries},
            'user_requests': [r.request for r in user_requests],
        }

        # Optional fields
        if session.summary:
            result['summary'] = session.summary
        if session.branch:
            result['branch'] = session.branch
        if session.reason:
            result['reason'] = session.reason
        if session.session_metadata:
            result['metadata'] = json.loads(session.session_metadata)
        else:
            result['metadata'] = {}

        return result
