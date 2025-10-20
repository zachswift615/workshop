"""
SQLAlchemy models for Workshop storage.

Supports both single-tenant (OSS SQLite) and multi-tenant (Cloud PostgreSQL) modes.
"""
from datetime import datetime
from typing import Optional
from uuid import uuid4

from sqlalchemy import (
    Column, String, Text, Integer, Boolean, DateTime, ForeignKey,
    Index, UniqueConstraint, event, text
)
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.types import TypeDecorator, CHAR
import uuid

Base = declarative_base()


class GUID(TypeDecorator):
    """Platform-independent GUID type.

    Uses PostgreSQL's UUID type, otherwise uses CHAR(36), storing as stringified hex values.
    """
    impl = CHAR
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == 'postgresql':
            return dialect.type_descriptor(PG_UUID())
        else:
            return dialect.type_descriptor(CHAR(36))

    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        elif dialect.name == 'postgresql':
            return str(value)
        else:
            if not isinstance(value, uuid.UUID):
                return str(uuid.UUID(value))
            else:
                return str(value)

    def process_result_value(self, value, dialect):
        if value is None:
            return value
        else:
            if not isinstance(value, uuid.UUID):
                return uuid.UUID(value)
            return value


class User(Base):
    """User/API key for multi-tenant mode (Cloud only)."""
    __tablename__ = 'users'

    id = Column(GUID(), primary_key=True, default=uuid4)
    api_key = Column(String(255), unique=True, nullable=False, index=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    # Relationships
    projects = relationship('Project', back_populates='user', cascade='all, delete-orphan')

    def __repr__(self):
        return f"<User(id={self.id}, api_key={self.api_key[:8]}...)>"


class Project(Base):
    """Project for organizing entries (Cloud multi-tenant mode)."""
    __tablename__ = 'projects'

    id = Column(GUID(), primary_key=True, default=uuid4)
    user_id = Column(GUID(), ForeignKey('users.id'), nullable=True, index=True)  # Nullable for OSS mode
    name = Column(String(255), nullable=False)
    path = Column(Text, nullable=True)  # Optional project root path
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    # Relationships
    user = relationship('User', back_populates='projects')
    entries = relationship('Entry', back_populates='project', cascade='all, delete-orphan')
    sessions = relationship('Session', back_populates='project', cascade='all, delete-orphan')

    # Unique constraint for multi-tenant mode
    __table_args__ = (
        UniqueConstraint('user_id', 'name', name='uix_user_project'),
        Index('idx_projects_user_id', 'user_id'),
    )

    def __repr__(self):
        return f"<Project(id={self.id}, name={self.name})>"


class Entry(Base):
    """Workshop entry (decision, note, gotcha, etc.)."""
    __tablename__ = 'entries'

    id = Column(GUID(), primary_key=True, default=uuid4)
    project_id = Column(GUID(), ForeignKey('projects.id'), nullable=True, index=True)  # Nullable for OSS mode
    type = Column(String(50), nullable=False, index=True)
    content = Column(Text, nullable=False)
    reasoning = Column(Text, nullable=True)
    timestamp = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    branch = Column(String(255), nullable=True, index=True)
    commit_hash = Column(String(40), nullable=True)
    entry_metadata = Column(Text, nullable=True)  # JSON blob (renamed from 'metadata' which is reserved)

    # Relationships
    project = relationship('Project', back_populates='entries')
    tags = relationship('Tag', back_populates='entry', cascade='all, delete-orphan')
    files = relationship('File', back_populates='entry', cascade='all, delete-orphan')

    __table_args__ = (
        Index('idx_entries_project_type', 'project_id', 'type'),
        Index('idx_entries_project_timestamp', 'project_id', 'timestamp'),
    )

    def __repr__(self):
        return f"<Entry(id={self.id}, type={self.type}, content={self.content[:50]}...)>"


class Tag(Base):
    """Tags for entries (many-to-many)."""
    __tablename__ = 'tags'

    entry_id = Column(GUID(), ForeignKey('entries.id', ondelete='CASCADE'), primary_key=True)
    tag = Column(String(100), primary_key=True, index=True)

    # Relationships
    entry = relationship('Entry', back_populates='tags')

    def __repr__(self):
        return f"<Tag(entry_id={self.entry_id}, tag={self.tag})>"


class File(Base):
    """Files associated with entries (many-to-many)."""
    __tablename__ = 'files'

    entry_id = Column(GUID(), ForeignKey('entries.id', ondelete='CASCADE'), primary_key=True)
    file_path = Column(Text, primary_key=True, index=True)

    # Relationships
    entry = relationship('Entry', back_populates='files')

    def __repr__(self):
        return f"<File(entry_id={self.entry_id}, path={self.file_path})>"


class Preference(Base):
    """User preferences."""
    __tablename__ = 'preferences'

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(GUID(), ForeignKey('projects.id'), nullable=True, index=True)  # Nullable for OSS mode
    category = Column(String(100), nullable=False, index=True)
    content = Column(Text, nullable=False)
    timestamp = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)

    def __repr__(self):
        return f"<Preference(id={self.id}, category={self.category})>"


class CurrentState(Base):
    """Current state: goals, blockers, next steps."""
    __tablename__ = 'current_state'

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(GUID(), ForeignKey('projects.id'), nullable=True, index=True)  # Nullable for OSS mode
    type = Column(String(50), nullable=False, index=True)  # 'goal', 'blocker', 'next_step'
    content = Column(Text, nullable=False)
    timestamp = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    completed = Column(Boolean, default=False)  # For task tracking

    __table_args__ = (
        Index('idx_current_state_project_type', 'project_id', 'type'),
    )

    def __repr__(self):
        return f"<CurrentState(id={self.id}, type={self.type})>"


class Session(Base):
    """Claude Code sessions."""
    __tablename__ = 'sessions'

    id = Column(GUID(), primary_key=True, default=uuid4)
    project_id = Column(GUID(), ForeignKey('projects.id'), nullable=True, index=True)  # Nullable for OSS mode
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=False, index=True)
    duration_minutes = Column(Integer, nullable=False)
    summary = Column(Text, nullable=True)
    branch = Column(String(255), nullable=True, index=True)
    reason = Column(Text, nullable=True)
    session_metadata = Column(Text, nullable=True)  # JSON blob (renamed from 'metadata' which is reserved)

    # Relationships
    project = relationship('Project', back_populates='sessions')
    files = relationship('SessionFile', back_populates='session', cascade='all, delete-orphan')
    commands = relationship('SessionCommand', back_populates='session', cascade='all, delete-orphan')
    workshop_entries = relationship('SessionWorkshopEntry', back_populates='session', cascade='all, delete-orphan')
    user_requests = relationship('SessionUserRequest', back_populates='session', cascade='all, delete-orphan')

    def __repr__(self):
        return f"<Session(id={self.id}, start={self.start_time})>"


class SessionFile(Base):
    """Files modified in a session (many-to-many)."""
    __tablename__ = 'session_files'

    session_id = Column(GUID(), ForeignKey('sessions.id', ondelete='CASCADE'), primary_key=True)
    file_path = Column(Text, primary_key=True, index=True)

    # Relationships
    session = relationship('Session', back_populates='files')

    def __repr__(self):
        return f"<SessionFile(session_id={self.session_id}, path={self.file_path})>"


class SessionCommand(Base):
    """Commands run in a session."""
    __tablename__ = 'session_commands'

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(GUID(), ForeignKey('sessions.id', ondelete='CASCADE'), nullable=False, index=True)
    command = Column(Text, nullable=False)

    # Relationships
    session = relationship('Session', back_populates='commands')

    def __repr__(self):
        return f"<SessionCommand(id={self.id}, command={self.command[:50]}...)>"


class SessionWorkshopEntry(Base):
    """Workshop entries created during a session (counts by type)."""
    __tablename__ = 'session_workshop_entries'

    session_id = Column(GUID(), ForeignKey('sessions.id', ondelete='CASCADE'), primary_key=True)
    entry_type = Column(String(50), primary_key=True)
    count = Column(Integer, nullable=False)

    # Relationships
    session = relationship('Session', back_populates='workshop_entries')

    def __repr__(self):
        return f"<SessionWorkshopEntry(session_id={self.session_id}, type={self.entry_type}, count={self.count})>"


class SessionUserRequest(Base):
    """User requests during a session."""
    __tablename__ = 'session_user_requests'

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(GUID(), ForeignKey('sessions.id', ondelete='CASCADE'), nullable=False, index=True)
    request = Column(Text, nullable=False)

    # Relationships
    session = relationship('Session', back_populates='user_requests')

    def __repr__(self):
        return f"<SessionUserRequest(id={self.id}, request={self.request[:50]}...)>"


class Config(Base):
    """Configuration key-value store."""
    __tablename__ = 'config'

    key = Column(String(100), primary_key=True)
    value = Column(Text, nullable=False)

    def __repr__(self):
        return f"<Config(key={self.key}, value={self.value})>"


class ImportHistory(Base):
    """Track JSONL imports for incremental updates."""
    __tablename__ = 'import_history'

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(GUID(), ForeignKey('projects.id'), nullable=True, index=True)  # Nullable for OSS mode
    jsonl_path = Column(Text, nullable=False, unique=True, index=True)
    jsonl_hash = Column(String(64), nullable=True)
    last_message_uuid = Column(String(36), nullable=True)
    last_message_timestamp = Column(String(50), nullable=True)
    messages_imported = Column(Integer, nullable=True)
    entries_created = Column(Integer, nullable=True)
    import_timestamp = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)

    def __repr__(self):
        return f"<ImportHistory(id={self.id}, path={self.jsonl_path})>"


class RawMessage(Base):
    """Raw conversation messages from JSONL imports."""
    __tablename__ = 'raw_messages'

    id = Column(GUID(), primary_key=True, default=uuid4)
    project_id = Column(GUID(), ForeignKey('projects.id'), nullable=True, index=True)  # Nullable for OSS mode
    session_id = Column(String(255), nullable=True, index=True)  # From JSONL sessionId
    message_uuid = Column(String(36), nullable=False, unique=True, index=True)  # From JSONL uuid
    message_type = Column(String(50), nullable=False, index=True)  # user/assistant/system/tool_result
    timestamp = Column(DateTime, nullable=False, index=True)
    parent_uuid = Column(String(36), nullable=True)  # For threading
    content = Column(Text, nullable=True)  # Extracted text/JSON content
    raw_json = Column(Text, nullable=False)  # Complete JSONL line for full fidelity
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    __table_args__ = (
        Index('idx_raw_messages_session_time', 'session_id', 'timestamp'),
        Index('idx_raw_messages_project_time', 'project_id', 'timestamp'),
    )

    def __repr__(self):
        return f"<RawMessage(uuid={self.message_uuid}, type={self.message_type})>"
