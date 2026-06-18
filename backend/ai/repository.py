"""Session / Message 仓储层"""
import json
import uuid
import sqlite3
from typing import List, Dict, Any, Optional
from datetime import datetime


def _row_to_dict(row: sqlite3.Row) -> Dict[str, Any]:
    return {k: row[k] for k in row.keys()}


class SessionRepository:
    def __init__(self, db_path: str):
        self.db_path = db_path

    def _conn(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def create(self, title: str = "新会话") -> Dict[str, Any]:
        sid = str(uuid.uuid4())
        with self._conn() as conn:
            conn.execute(
                "INSERT INTO agent_session (id, title) VALUES (?, ?)",
                (sid, title)
            )
            conn.commit()
        return self.get(sid)

    def get(self, session_id: str) -> Optional[Dict[str, Any]]:
        with self._conn() as conn:
            cursor = conn.execute(
                "SELECT * FROM agent_session WHERE id = ?", (session_id,)
            )
            row = cursor.fetchone()
            return _row_to_dict(row) if row else None

    def list(self) -> List[Dict[str, Any]]:
        with self._conn() as conn:
            cursor = conn.execute("""
                SELECT * FROM agent_session
                ORDER BY is_pinned DESC, updated_at DESC
            """)
            return [_row_to_dict(row) for row in cursor.fetchall()]

    def rename(self, session_id: str, title: str) -> None:
        with self._conn() as conn:
            conn.execute(
                "UPDATE agent_session SET title = ?, updated_at = datetime('now', 'localtime') WHERE id = ?",
                (title, session_id)
            )
            conn.commit()

    def delete(self, session_id: str) -> None:
        with self._conn() as conn:
            conn.execute("DELETE FROM agent_session WHERE id = ?", (session_id,))
            conn.commit()

    def pin(self, session_id: str, pinned: bool) -> None:
        with self._conn() as conn:
            conn.execute(
                "UPDATE agent_session SET is_pinned = ? WHERE id = ?",
                (1 if pinned else 0, session_id)
            )
            conn.commit()

    def touch(self, session_id: str, last_message: str = "") -> None:
        """更新 updated_at 和 last_message"""
        with self._conn() as conn:
            conn.execute("""
                UPDATE agent_session
                SET updated_at = datetime('now', 'localtime'),
                    message_count = message_count + 1,
                    last_message = ?
                WHERE id = ?
            """, (last_message[:100], session_id))
            conn.commit()


class MessageRepository:
    def __init__(self, db_path: str):
        self.db_path = db_path

    def _conn(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def save(
        self, session_id: str, role: str, content: str,
        tool_calls: Optional[List[Dict]] = None,
        token_count: Optional[int] = None,
        duration_ms: Optional[int] = None,
    ) -> int:
        """保存消息，返回 message id"""
        tc_json = json.dumps(tool_calls, ensure_ascii=False) if tool_calls else None
        with self._conn() as conn:
            cursor = conn.execute(
                """INSERT INTO agent_message
                   (session_id, role, content, tool_calls, token_count, duration_ms)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (session_id, role, content, tc_json, token_count, duration_ms)
            )
            msg_id = cursor.lastrowid
            conn.commit()
        return msg_id

    def get(self, message_id: int) -> Optional[Dict[str, Any]]:
        with self._conn() as conn:
            cursor = conn.execute("SELECT * FROM agent_message WHERE id = ?", (message_id,))
            row = cursor.fetchone()
            if not row:
                return None
            d = _row_to_dict(row)
            if d.get("tool_calls"):
                d["tool_calls"] = json.loads(d["tool_calls"])
            return d

    def list(self, session_id: str, limit: int = 100) -> List[Dict[str, Any]]:
        """列出某会话的所有消息（限制 100 条）"""
        with self._conn() as conn:
            cursor = conn.execute("""
                SELECT * FROM agent_message
                WHERE session_id = ?
                ORDER BY created_at ASC
                LIMIT ?
            """, (session_id, limit))
            messages = []
            for row in cursor.fetchall():
                d = _row_to_dict(row)
                if d.get("tool_calls"):
                    d["tool_calls"] = json.loads(d["tool_calls"])
                messages.append(d)
            return messages
