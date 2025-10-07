"""
Entry management using SQLAlchemy.

Handles CRUD operations for workshop entries (decisions, notes, gotchas, etc.)
"""
import json
from datetime import datetime
from typing import Dict, List, Optional
from uuid import uuid4, UUID

from dateutil import parser as date_parser
from sqlalchemy import select, or_, and_
from sqlalchemy.orm import Session

from ..models import Entry, Tag, File


class EntriesManager:
    """Manages workshop entries using SQLAlchemy."""

    def __init__(self, db_session: Session, project_id: Optional[UUID] = None):
        """
        Initialize entries manager.

        Args:
            db_session: SQLAlchemy session
            project_id: Project ID for multi-tenant isolation (None for OSS mode)
        """
        self.session = db_session
        self.project_id = project_id

    def add_entry(
        self,
        entry_type: str,
        content: str,
        reasoning: Optional[str] = None,
        tags: Optional[List[str]] = None,
        files: Optional[List[str]] = None,
        metadata: Optional[Dict] = None,
        timestamp: Optional[str] = None
    ) -> Dict:
        """
        Add a new entry to the workshop.

        Args:
            entry_type: Type of entry (decision, note, gotcha, etc.)
            content: Main content/text of the entry
            reasoning: Optional reasoning (mainly for decisions)
            tags: Optional list of tags
            files: Optional list of related files
            metadata: Optional additional metadata
            timestamp: Optional timestamp (ISO format). Defaults to now.

        Returns:
            The created entry dict
        """
        from ..git_utils import get_git_info

        # Get git info
        git_info = get_git_info()
        branch = git_info.get("branch", "")
        commit_hash = git_info.get("commit", "")

        # Create entry
        entry = Entry(
            project_id=self.project_id,
            type=entry_type,
            content=content,
            reasoning=reasoning,
            timestamp=date_parser.parse(timestamp) if timestamp else datetime.utcnow(),
            branch=branch or None,
            commit_hash=commit_hash or None,
            entry_metadata=json.dumps(metadata) if metadata else None
        )
        self.session.add(entry)
        self.session.flush()  # Get entry.id

        # Add tags
        if tags:
            for tag in tags:
                self.session.add(Tag(entry_id=entry.id, tag=tag))

        # Add files
        if files:
            for file_path in files:
                self.session.add(File(entry_id=entry.id, file_path=file_path))

        self.session.commit()

        return self._entry_to_dict(entry)

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
        query = select(Entry)

        # Apply project filter (multi-tenant mode)
        if self.project_id:
            query = query.where(Entry.project_id == self.project_id)

        # Filter by type
        if entry_type:
            query = query.where(Entry.type == entry_type)

        # Filter by timestamp
        if since:
            query = query.where(Entry.timestamp >= since)

        # Filter by tags (join with tags table)
        if tags:
            query = query.join(Tag).where(Tag.tag.in_(tags)).distinct()

        # Order by timestamp descending
        query = query.order_by(Entry.timestamp.desc())

        # Apply limit
        if limit:
            query = query.limit(limit)

        entries = self.session.execute(query).scalars().all()
        return [self._entry_to_dict(e) for e in entries]

    def get_entry_by_id(self, entry_id: str) -> Optional[Dict]:
        """
        Get a single entry by ID.

        Args:
            entry_id: Entry UUID

        Returns:
            Entry dict or None if not found
        """
        try:
            entry_uuid = UUID(entry_id)
        except ValueError:
            return None

        query = select(Entry).where(Entry.id == entry_uuid)

        # Apply project filter
        if self.project_id:
            query = query.where(Entry.project_id == self.project_id)

        entry = self.session.execute(query).scalar_one_or_none()
        return self._entry_to_dict(entry) if entry else None

    def get_last_entry(self) -> Optional[Dict]:
        """
        Get the most recent entry.

        Returns:
            Most recent entry or None if no entries exist
        """
        query = select(Entry)

        # Apply project filter
        if self.project_id:
            query = query.where(Entry.project_id == self.project_id)

        query = query.order_by(Entry.timestamp.desc()).limit(1)

        entry = self.session.execute(query).scalar_one_or_none()
        return self._entry_to_dict(entry) if entry else None

    def update_entry(
        self,
        entry_id: str,
        content: Optional[str] = None,
        reasoning: Optional[str] = None,
        entry_type: Optional[str] = None
    ) -> bool:
        """
        Update an existing entry.

        Args:
            entry_id: Entry ID to update
            content: New content (if provided)
            reasoning: New reasoning (if provided)
            entry_type: New type (if provided)

        Returns:
            True if entry was updated, False if not found
        """
        try:
            entry_uuid = UUID(entry_id)
        except ValueError:
            return False

        query = select(Entry).where(Entry.id == entry_uuid)

        # Apply project filter
        if self.project_id:
            query = query.where(Entry.project_id == self.project_id)

        entry = self.session.execute(query).scalar_one_or_none()
        if not entry:
            return False

        # Update fields if provided
        if content is not None:
            entry.content = content
        if reasoning is not None:
            entry.reasoning = reasoning
        if entry_type is not None:
            entry.type = entry_type

        self.session.commit()
        return True

    def delete_entry(self, entry_id: str) -> bool:
        """
        Delete an entry by ID.

        Args:
            entry_id: Entry ID to delete

        Returns:
            True if entry was deleted, False if not found
        """
        try:
            entry_uuid = UUID(entry_id)
        except ValueError:
            return False

        query = select(Entry).where(Entry.id == entry_uuid)

        # Apply project filter
        if self.project_id:
            query = query.where(Entry.project_id == self.project_id)

        entry = self.session.execute(query).scalar_one_or_none()
        if not entry:
            return False

        self.session.delete(entry)
        self.session.commit()
        return True

    def delete_entries_by_type(self, entry_type: str) -> int:
        """
        Delete all entries of a specific type.

        Args:
            entry_type: Type of entries to delete

        Returns:
            Number of entries deleted
        """
        query = select(Entry).where(Entry.type == entry_type)

        # Apply project filter
        if self.project_id:
            query = query.where(Entry.project_id == self.project_id)

        entries = self.session.execute(query).scalars().all()
        count = len(entries)

        for entry in entries:
            self.session.delete(entry)

        self.session.commit()
        return count

    def delete_entries_before(self, before_date: datetime) -> int:
        """
        Delete entries before a specific date.

        Args:
            before_date: Delete entries before this datetime

        Returns:
            Number of entries deleted
        """
        query = select(Entry).where(Entry.timestamp < before_date)

        # Apply project filter
        if self.project_id:
            query = query.where(Entry.project_id == self.project_id)

        entries = self.session.execute(query).scalars().all()
        count = len(entries)

        for entry in entries:
            self.session.delete(entry)

        self.session.commit()
        return count

    def search(self, query_text: str, limit: Optional[int] = None) -> List[Dict]:
        """
        Search entries using simple LIKE search.

        Note: Full-text search (FTS5 for SQLite, tsvector for PostgreSQL)
        will be implemented in a future iteration.

        Args:
            query_text: Search query
            limit: Maximum results to return

        Returns:
            List of matching entries with relevance scores
        """
        search_term = f"%{query_text}%"

        query = select(Entry).where(
            or_(
                Entry.content.like(search_term),
                Entry.reasoning.like(search_term)
            )
        )

        # Apply project filter
        if self.project_id:
            query = query.where(Entry.project_id == self.project_id)

        # Order by timestamp descending
        query = query.order_by(Entry.timestamp.desc())

        # Apply limit
        if limit:
            query = query.limit(limit)

        entries = self.session.execute(query).scalars().all()

        # Add relevance scores (simple: 1.0 for all matches for now)
        results = []
        for entry in entries:
            entry_dict = self._entry_to_dict(entry)
            entry_dict['relevance'] = 1.0
            results.append(entry_dict)

        return results

    def why_search(self, query_text: str, limit: int = 5) -> List[Dict]:
        """
        Smart search for "why" queries - prioritizes decisions and reasoning.

        Args:
            query_text: Search query (what you want to know why about)
            limit: Maximum results to return

        Returns:
            List of matching entries, prioritized by relevance
        """
        search_term = f"%{query_text}%"

        # Prioritize decisions, then other types
        query = select(Entry).where(
            or_(
                Entry.content.like(search_term),
                Entry.reasoning.like(search_term)
            )
        )

        # Apply project filter
        if self.project_id:
            query = query.where(Entry.project_id == self.project_id)

        # Order: decisions first, then by timestamp
        query = query.order_by(
            (Entry.type == 'decision').desc(),  # True DESC first, so decisions come first
            Entry.timestamp.desc()
        ).limit(limit)

        entries = self.session.execute(query).scalars().all()

        # Add relevance scores
        results = []
        for i, entry in enumerate(entries):
            entry_dict = self._entry_to_dict(entry)
            # Higher score for decisions and earlier results
            score = 1.0
            if entry.type == 'decision':
                score += 0.5
            score -= (i * 0.1)  # Decay score by position
            entry_dict['relevance'] = max(0.1, score)
            results.append(entry_dict)

        return results

    def _entry_to_dict(self, entry: Entry) -> Dict:
        """Convert Entry model to dictionary."""
        # Load tags
        tags = self.session.query(Tag).filter_by(entry_id=entry.id).all()

        # Load files
        files = self.session.query(File).filter_by(entry_id=entry.id).all()

        result = {
            'id': str(entry.id),
            'type': entry.type,
            'content': entry.content,
            'timestamp': entry.timestamp.isoformat(),
            'tags': [t.tag for t in tags],
            'files': [f.file_path for f in files],
        }

        # Optional fields
        if entry.reasoning:
            result['reasoning'] = entry.reasoning
        if entry.branch:
            result['branch'] = entry.branch
        if entry.commit_hash:
            result['commit'] = entry.commit_hash
        if entry.entry_metadata:
            result['metadata'] = json.loads(entry.entry_metadata)
        else:
            result['metadata'] = {}

        return result
