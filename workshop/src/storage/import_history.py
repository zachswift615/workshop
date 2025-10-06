"""
Import history management using SQLAlchemy.

Tracks JSONL imports for incremental updates.
"""
from datetime import datetime
from typing import Dict, List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import ImportHistory, Entry


class ImportHistoryManager:
    """Manages JSONL import tracking using SQLAlchemy."""

    def __init__(self, db_session: Session, project_id: Optional[UUID] = None):
        """
        Initialize import history manager.

        Args:
            db_session: SQLAlchemy session
            project_id: Project ID for multi-tenant isolation (None for OSS mode)
        """
        self.session = db_session
        self.project_id = project_id

    def record_import(
        self,
        jsonl_path: str,
        jsonl_hash: str,
        last_uuid: str,
        last_timestamp: str,
        messages_imported: int,
        entries_created: int
    ) -> None:
        """
        Record a JSONL import for incremental tracking.

        Args:
            jsonl_path: Path to JSONL file
            jsonl_hash: SHA256 hash of file
            last_uuid: UUID of last message imported
            last_timestamp: Timestamp of last message
            messages_imported: Number of messages processed
            entries_created: Number of entries created
        """
        # Check if record exists
        existing = self.session.query(ImportHistory).filter_by(
            jsonl_path=jsonl_path
        ).first()

        if existing:
            # Update existing record
            existing.jsonl_hash = jsonl_hash
            existing.last_message_uuid = last_uuid
            existing.last_message_timestamp = last_timestamp
            existing.messages_imported = messages_imported
            existing.entries_created = entries_created
            existing.import_timestamp = datetime.utcnow()
        else:
            # Create new record
            record = ImportHistory(
                project_id=self.project_id,
                jsonl_path=jsonl_path,
                jsonl_hash=jsonl_hash,
                last_message_uuid=last_uuid,
                last_message_timestamp=last_timestamp,
                messages_imported=messages_imported,
                entries_created=entries_created
            )
            self.session.add(record)

        self.session.commit()

    def get_last_import(self, jsonl_path: str) -> Optional[Dict]:
        """
        Get last import record for a JSONL file.

        Args:
            jsonl_path: Path to JSONL file

        Returns:
            Import record dict or None if never imported
        """
        query = select(ImportHistory).where(ImportHistory.jsonl_path == jsonl_path)

        # Apply project filter
        if self.project_id:
            query = query.where(ImportHistory.project_id == self.project_id)

        record = self.session.execute(query).scalar_one_or_none()

        if not record:
            return None

        return {
            'id': record.id,
            'jsonl_path': record.jsonl_path,
            'jsonl_hash': record.jsonl_hash,
            'last_message_uuid': record.last_message_uuid,
            'last_message_timestamp': record.last_message_timestamp,
            'messages_imported': record.messages_imported,
            'entries_created': record.entries_created,
            'import_timestamp': record.import_timestamp.isoformat()
        }

    def get_import_history(self, limit: int = 50) -> List[Dict]:
        """
        Get recent import history.

        Args:
            limit: Maximum number of records to return

        Returns:
            List of import records
        """
        query = select(ImportHistory)

        # Apply project filter
        if self.project_id:
            query = query.where(ImportHistory.project_id == self.project_id)

        # Order by import time descending
        query = query.order_by(ImportHistory.import_timestamp.desc()).limit(limit)

        records = self.session.execute(query).scalars().all()

        return [
            {
                'id': r.id,
                'jsonl_path': r.jsonl_path,
                'jsonl_hash': r.jsonl_hash,
                'last_message_uuid': r.last_message_uuid,
                'last_message_timestamp': r.last_message_timestamp,
                'messages_imported': r.messages_imported,
                'entries_created': r.entries_created,
                'import_timestamp': r.import_timestamp.isoformat()
            }
            for r in records
        ]

    def is_message_imported(self, uuid: str) -> bool:
        """
        Check if a message UUID has been imported.

        Args:
            uuid: Message UUID to check

        Returns:
            True if message was already imported
        """
        try:
            entry_uuid = UUID(uuid)
        except ValueError:
            return False

        query = select(Entry).where(Entry.id == entry_uuid)

        # Apply project filter
        if self.project_id:
            query = query.where(Entry.project_id == self.project_id)

        entry = self.session.execute(query).scalar_one_or_none()
        return entry is not None
