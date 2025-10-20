"""
Raw message storage management using SQLAlchemy.

Stores complete conversation history from JSONL imports.
"""
from datetime import datetime
from typing import Dict, List, Optional
from uuid import UUID, uuid4

from sqlalchemy import select, and_, or_, func
from sqlalchemy.orm import Session
from dateutil import parser as date_parser

from ..models import RawMessage


class RawMessagesManager:
    """Manages raw conversation messages using SQLAlchemy."""

    def __init__(self, db_session: Session, project_id: Optional[UUID] = None):
        """
        Initialize raw messages manager.

        Args:
            db_session: SQLAlchemy session
            project_id: Project ID for multi-tenant isolation (None for OSS mode)
        """
        self.session = db_session
        self.project_id = project_id

    def add_raw_message(
        self,
        message_uuid: str,
        message_type: str,
        timestamp: str,
        raw_json: str,
        session_id: Optional[str] = None,
        parent_uuid: Optional[str] = None,
        content: Optional[str] = None
    ) -> str:
        """
        Add a single raw message.

        Args:
            message_uuid: Unique message UUID from JSONL
            message_type: Type of message (user/assistant/system/tool_result)
            timestamp: ISO timestamp string
            raw_json: Complete JSONL line as JSON string
            session_id: Optional session ID from JSONL
            parent_uuid: Optional parent message UUID for threading
            content: Optional extracted text content

        Returns:
            Database ID of created message
        """
        # Parse timestamp
        try:
            ts = date_parser.parse(timestamp)
        except:
            ts = datetime.utcnow()

        message = RawMessage(
            id=uuid4(),
            project_id=self.project_id,
            session_id=session_id,
            message_uuid=message_uuid,
            message_type=message_type,
            timestamp=ts,
            parent_uuid=parent_uuid,
            content=content,
            raw_json=raw_json
        )

        self.session.add(message)
        self.session.commit()

        return str(message.id)

    def add_raw_messages_batch(self, messages: List[Dict]) -> int:
        """
        Add multiple raw messages in a batch for performance.

        Args:
            messages: List of message dicts with keys:
                - message_uuid: str
                - message_type: str
                - timestamp: str
                - raw_json: str
                - session_id: Optional[str]
                - parent_uuid: Optional[str]
                - content: Optional[str]

        Returns:
            Number of messages inserted
        """
        raw_message_objects = []

        for msg in messages:
            # Parse timestamp
            try:
                ts = date_parser.parse(msg['timestamp'])
            except:
                ts = datetime.utcnow()

            raw_message_objects.append(RawMessage(
                id=uuid4(),
                project_id=self.project_id,
                session_id=msg.get('session_id'),
                message_uuid=msg['message_uuid'],
                message_type=msg['message_type'],
                timestamp=ts,
                parent_uuid=msg.get('parent_uuid'),
                content=msg.get('content'),
                raw_json=msg['raw_json']
            ))

        self.session.bulk_save_objects(raw_message_objects)
        self.session.commit()

        return len(raw_message_objects)

    def get_message_by_uuid(self, message_uuid: str) -> Optional[Dict]:
        """
        Get a single message by its UUID.

        Args:
            message_uuid: Message UUID to lookup

        Returns:
            Message dict or None if not found
        """
        query = select(RawMessage).where(RawMessage.message_uuid == message_uuid)

        # Apply project filter
        if self.project_id:
            query = query.where(RawMessage.project_id == self.project_id)

        message = self.session.execute(query).scalar_one_or_none()

        if not message:
            return None

        return {
            'id': str(message.id),
            'message_uuid': message.message_uuid,
            'session_id': message.session_id,
            'message_type': message.message_type,
            'timestamp': message.timestamp.isoformat(),
            'parent_uuid': message.parent_uuid,
            'content': message.content,
            'raw_json': message.raw_json,
            'created_at': message.created_at.isoformat()
        }

    def get_conversation_context(
        self,
        message_uuid: str,
        before: int = 5,
        after: int = 5
    ) -> List[Dict]:
        """
        Get N messages before and after a specific message for context.

        Args:
            message_uuid: UUID of the anchor message
            before: Number of messages to get before
            after: Number of messages to get after

        Returns:
            List of messages in chronological order (before + anchor + after)
        """
        # First, get the anchor message to find its session and timestamp
        anchor = self.get_message_by_uuid(message_uuid)
        if not anchor:
            return []

        session_id = anchor['session_id']
        anchor_time = date_parser.parse(anchor['timestamp'])

        # Build query for messages in the same session
        query = select(RawMessage).where(RawMessage.session_id == session_id)

        # Apply project filter
        if self.project_id:
            query = query.where(RawMessage.project_id == self.project_id)

        # Get messages before
        before_query = query.where(RawMessage.timestamp < anchor_time).order_by(
            RawMessage.timestamp.desc()
        ).limit(before)
        before_messages = list(reversed(self.session.execute(before_query).scalars().all()))

        # Get anchor message
        anchor_query = query.where(RawMessage.message_uuid == message_uuid)
        anchor_message = self.session.execute(anchor_query).scalar_one_or_none()

        # Get messages after
        after_query = query.where(RawMessage.timestamp > anchor_time).order_by(
            RawMessage.timestamp.asc()
        ).limit(after)
        after_messages = list(self.session.execute(after_query).scalars().all())

        # Combine in chronological order
        all_messages = before_messages + ([anchor_message] if anchor_message else []) + after_messages

        return [
            {
                'id': str(m.id),
                'message_uuid': m.message_uuid,
                'session_id': m.session_id,
                'message_type': m.message_type,
                'timestamp': m.timestamp.isoformat(),
                'parent_uuid': m.parent_uuid,
                'content': m.content,
                'raw_json': m.raw_json,
                'created_at': m.created_at.isoformat()
            }
            for m in all_messages
        ]

    def get_session_messages(
        self,
        session_id: str,
        limit: int = 100,
        offset: int = 0,
        message_types: Optional[List[str]] = None
    ) -> List[Dict]:
        """
        Get all messages for a session, paginated.

        Args:
            session_id: Session ID to query
            limit: Maximum number of messages to return
            offset: Number of messages to skip (for pagination)
            message_types: Optional filter by message types (e.g., ['user', 'assistant'])

        Returns:
            List of messages in chronological order
        """
        query = select(RawMessage).where(RawMessage.session_id == session_id)

        # Apply project filter
        if self.project_id:
            query = query.where(RawMessage.project_id == self.project_id)

        # Filter by message types
        if message_types:
            query = query.where(RawMessage.message_type.in_(message_types))

        # Order by timestamp and paginate
        query = query.order_by(RawMessage.timestamp.asc()).offset(offset).limit(limit)

        messages = self.session.execute(query).scalars().all()

        return [
            {
                'id': str(m.id),
                'message_uuid': m.message_uuid,
                'session_id': m.session_id,
                'message_type': m.message_type,
                'timestamp': m.timestamp.isoformat(),
                'parent_uuid': m.parent_uuid,
                'content': m.content,
                'raw_json': m.raw_json,
                'created_at': m.created_at.isoformat()
            }
            for m in messages
        ]

    def search_messages(
        self,
        query_text: str,
        limit: int = 20,
        message_types: Optional[List[str]] = None
    ) -> List[Dict]:
        """
        Search messages by content (simple substring search).

        Args:
            query_text: Text to search for in content
            limit: Maximum number of results
            message_types: Optional filter by message types

        Returns:
            List of matching messages ordered by timestamp descending
        """
        query = select(RawMessage).where(
            RawMessage.content.ilike(f'%{query_text}%')
        )

        # Apply project filter
        if self.project_id:
            query = query.where(RawMessage.project_id == self.project_id)

        # Filter by message types
        if message_types:
            query = query.where(RawMessage.message_type.in_(message_types))

        # Order by most recent first
        query = query.order_by(RawMessage.timestamp.desc()).limit(limit)

        messages = self.session.execute(query).scalars().all()

        return [
            {
                'id': str(m.id),
                'message_uuid': m.message_uuid,
                'session_id': m.session_id,
                'message_type': m.message_type,
                'timestamp': m.timestamp.isoformat(),
                'parent_uuid': m.parent_uuid,
                'content': m.content,
                'raw_json': m.raw_json,
                'created_at': m.created_at.isoformat()
            }
            for m in messages
        ]

    def count_messages(
        self,
        session_id: Optional[str] = None,
        message_type: Optional[str] = None
    ) -> int:
        """
        Count messages with optional filters.

        Args:
            session_id: Optional filter by session
            message_type: Optional filter by message type

        Returns:
            Count of matching messages
        """
        query = select(func.count()).select_from(RawMessage)

        # Apply filters
        if self.project_id:
            query = query.where(RawMessage.project_id == self.project_id)

        if session_id:
            query = query.where(RawMessage.session_id == session_id)

        if message_type:
            query = query.where(RawMessage.message_type == message_type)

        count = self.session.execute(query).scalar()
        return count or 0

    def message_exists(self, message_uuid: str) -> bool:
        """
        Check if a message UUID already exists.

        Args:
            message_uuid: Message UUID to check

        Returns:
            True if message exists
        """
        query = select(func.count()).select_from(RawMessage).where(
            RawMessage.message_uuid == message_uuid
        )

        # Apply project filter
        if self.project_id:
            query = query.where(RawMessage.project_id == self.project_id)

        count = self.session.execute(query).scalar()
        return count > 0
