-- Workshop SQLite Schema
-- Migration from JSON to SQLite for better performance and querying

-- Entries table: decisions, notes, gotchas, preferences, antipatterns
CREATE TABLE IF NOT EXISTS entries (
    id TEXT PRIMARY KEY,
    type TEXT NOT NULL,
    content TEXT NOT NULL,
    reasoning TEXT,
    timestamp TEXT NOT NULL,
    branch TEXT,
    commit_hash TEXT,
    metadata TEXT  -- JSON blob for additional fields
);

CREATE INDEX IF NOT EXISTS idx_entries_type ON entries(type);
CREATE INDEX IF NOT EXISTS idx_entries_timestamp ON entries(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_entries_branch ON entries(branch);

-- Tags table (many-to-many with entries)
CREATE TABLE IF NOT EXISTS tags (
    entry_id TEXT NOT NULL,
    tag TEXT NOT NULL,
    PRIMARY KEY (entry_id, tag),
    FOREIGN KEY (entry_id) REFERENCES entries(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_tags_tag ON tags(tag);
CREATE INDEX IF NOT EXISTS idx_tags_entry_id ON tags(entry_id);

-- Files table (many-to-many with entries)
CREATE TABLE IF NOT EXISTS files (
    entry_id TEXT NOT NULL,
    file_path TEXT NOT NULL,
    PRIMARY KEY (entry_id, file_path),
    FOREIGN KEY (entry_id) REFERENCES entries(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_files_path ON files(file_path);
CREATE INDEX IF NOT EXISTS idx_files_entry_id ON files(entry_id);

-- Full-text search virtual table for entries
CREATE VIRTUAL TABLE IF NOT EXISTS entries_fts USING fts5(
    id UNINDEXED,
    content,
    reasoning,
    content=entries,
    content_rowid=rowid
);

-- Triggers to keep FTS table in sync
CREATE TRIGGER IF NOT EXISTS entries_fts_insert AFTER INSERT ON entries BEGIN
    INSERT INTO entries_fts(rowid, id, content, reasoning)
    VALUES (new.rowid, new.id, new.content, new.reasoning);
END;

CREATE TRIGGER IF NOT EXISTS entries_fts_delete AFTER DELETE ON entries BEGIN
    DELETE FROM entries_fts WHERE rowid = old.rowid;
END;

CREATE TRIGGER IF NOT EXISTS entries_fts_update AFTER UPDATE ON entries BEGIN
    DELETE FROM entries_fts WHERE rowid = old.rowid;
    INSERT INTO entries_fts(rowid, id, content, reasoning)
    VALUES (new.rowid, new.id, new.content, new.reasoning);
END;

-- Preferences table
CREATE TABLE IF NOT EXISTS preferences (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    category TEXT NOT NULL,
    content TEXT NOT NULL,
    timestamp TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_preferences_category ON preferences(category);
CREATE INDEX IF NOT EXISTS idx_preferences_timestamp ON preferences(timestamp DESC);

-- Current state: goals, blockers, next steps
CREATE TABLE IF NOT EXISTS current_state (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    type TEXT NOT NULL,  -- 'goal', 'blocker', 'next_step'
    content TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    completed INTEGER DEFAULT 0  -- For future task tracking
);

CREATE INDEX IF NOT EXISTS idx_current_state_type ON current_state(type);
CREATE INDEX IF NOT EXISTS idx_current_state_timestamp ON current_state(timestamp DESC);

-- Sessions table
CREATE TABLE IF NOT EXISTS sessions (
    id TEXT PRIMARY KEY,
    start_time TEXT NOT NULL,
    end_time TEXT NOT NULL,
    duration_minutes INTEGER NOT NULL,
    summary TEXT,
    branch TEXT,
    reason TEXT,
    metadata TEXT  -- JSON blob for additional fields
);

CREATE INDEX IF NOT EXISTS idx_sessions_end_time ON sessions(end_time DESC);
CREATE INDEX IF NOT EXISTS idx_sessions_branch ON sessions(branch);

-- Session files (many-to-many)
CREATE TABLE IF NOT EXISTS session_files (
    session_id TEXT NOT NULL,
    file_path TEXT NOT NULL,
    PRIMARY KEY (session_id, file_path),
    FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_session_files_session_id ON session_files(session_id);
CREATE INDEX IF NOT EXISTS idx_session_files_path ON session_files(file_path);

-- Session commands
CREATE TABLE IF NOT EXISTS session_commands (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    command TEXT NOT NULL,
    FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_session_commands_session_id ON session_commands(session_id);

-- Session workshop entries (counts by type)
CREATE TABLE IF NOT EXISTS session_workshop_entries (
    session_id TEXT NOT NULL,
    entry_type TEXT NOT NULL,
    count INTEGER NOT NULL,
    PRIMARY KEY (session_id, entry_type),
    FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_session_workshop_entries_session_id ON session_workshop_entries(session_id);

-- Session user requests
CREATE TABLE IF NOT EXISTS session_user_requests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    request TEXT NOT NULL,
    FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_session_user_requests_session_id ON session_user_requests(session_id);

-- Config table for workspace settings
CREATE TABLE IF NOT EXISTS config (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

-- Import history: track JSONL imports for incremental updates
CREATE TABLE IF NOT EXISTS import_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    jsonl_path TEXT NOT NULL,
    jsonl_hash TEXT,  -- File hash to detect changes
    last_message_uuid TEXT,  -- Last message UUID imported
    last_message_timestamp TEXT,
    messages_imported INTEGER,
    entries_created INTEGER,
    import_timestamp TEXT NOT NULL,
    UNIQUE(jsonl_path)
);

CREATE INDEX IF NOT EXISTS idx_import_history_path ON import_history(jsonl_path);
CREATE INDEX IF NOT EXISTS idx_import_history_timestamp ON import_history(import_timestamp DESC);

-- Schema version for future migrations
INSERT OR REPLACE INTO config (key, value) VALUES ('schema_version', '2');
