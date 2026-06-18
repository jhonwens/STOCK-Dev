-- 1. 会话表
CREATE TABLE IF NOT EXISTS agent_session (
    id              TEXT PRIMARY KEY,
    title           TEXT NOT NULL,
    created_at      DATETIME DEFAULT (datetime('now', 'localtime')),
    updated_at      DATETIME DEFAULT (datetime('now', 'localtime')),
    message_count   INTEGER DEFAULT 0,
    is_pinned       INTEGER DEFAULT 0,
    last_message    TEXT
);
CREATE INDEX IF NOT EXISTS idx_session_updated ON agent_session(updated_at DESC);

-- 2. 消息表
CREATE TABLE IF NOT EXISTS agent_message (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id      TEXT NOT NULL,
    role            TEXT NOT NULL,
    content         TEXT,
    tool_calls      TEXT,
    created_at      DATETIME DEFAULT (datetime('now', 'localtime')),
    token_count     INTEGER,
    duration_ms     INTEGER,
    FOREIGN KEY (session_id) REFERENCES agent_session(id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_msg_session ON agent_message(session_id, created_at);

-- 3. 导出表
CREATE TABLE IF NOT EXISTS agent_export (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id      TEXT NOT NULL,
    message_id      INTEGER,
    format          TEXT NOT NULL,
    file_path       TEXT NOT NULL,
    created_at      DATETIME DEFAULT (datetime('now', 'localtime')),
    FOREIGN KEY (session_id) REFERENCES agent_session(id) ON DELETE CASCADE
);

-- 4. 迁移记录表（幂等性）
CREATE TABLE IF NOT EXISTS _migrations (
    id      INTEGER PRIMARY KEY,
    name    TEXT NOT NULL,
    applied_at DATETIME DEFAULT (datetime('now', 'localtime'))
);
