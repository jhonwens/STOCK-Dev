#!/usr/bin/env python3
"""Agent 处理器 — 专供 PyInstaller 打包模式

PyInstaller 冻结模式下，backend.ai.* 子模块的 import 链路存在限制，
无法通过 from backend.ai.agent_bridge import handle_request 调用。

本脚本将所有 agent 操作内联到 scripts 目录，通过 runpy.run_path
直接执行。

Rust 调用：
  backend-runner script agent_handler.py session_list <db_path>
  backend-runner script agent_handler.py session_create <db_path> [title]
  backend-runner script agent_handler.py session_rename <db_path> <id> <title>
  backend-runner script agent_handler.py session_delete <db_path> <id>
  backend-runner script agent_handler.py session_pin <db_path> <id> <pinned>
  backend-runner script agent_handler.py msg_list <db_path> <session_id>
  backend-runner script agent_handler.py export_msg <db_path> <session_id> <msg_id> <format>
"""
import sys
import json
import os
from datetime import datetime
from pathlib import Path


# ============================================================
# 内联依赖：从 backend.ai.repository 提取的数据库操作
# ============================================================

def _dict_factory(cursor, row):
    """SQLite row → dict"""
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d


class SessionRepository:
    def __init__(self, db_path: str):
        import sqlite3
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = _dict_factory

    def create(self, title: str = "新会话") -> dict:
        import sqlite3
        uid = os.urandom(8).hex()
        try:
            self.conn.execute(
                "INSERT INTO agent_session (id, title) VALUES (?, ?)",
                (uid, title),
            )
            self.conn.commit()
        except sqlite3.OperationalError:
            self._ensure_table()
            self.conn.execute(
                "INSERT INTO agent_session (id, title) VALUES (?, ?)",
                (uid, title),
            )
            self.conn.commit()
        return {"id": uid, "title": title, "pinned": 0}

    def list(self) -> list[dict]:
        try:
            cur = self.conn.execute(
                "SELECT id, title, pinned, created_at, updated_at FROM agent_session ORDER BY pinned DESC, updated_at DESC"
            )
            return cur.fetchall()
        except Exception:
            return []

    def get(self, session_id: str) -> dict | None:
        try:
            cur = self.conn.execute(
                "SELECT id, title, pinned, created_at, updated_at FROM agent_session WHERE id = ?",
                (session_id,),
            )
            return cur.fetchone()
        except Exception:
            return None

    def rename(self, session_id: str, title: str) -> None:
        self.conn.execute(
            "UPDATE agent_session SET title = ?, updated_at = datetime('now','localtime') WHERE id = ?",
            (title, session_id),
        )
        self.conn.commit()

    def delete(self, session_id: str) -> None:
        self.conn.execute("DELETE FROM agent_session WHERE id = ?", (session_id,))
        self.conn.execute("DELETE FROM agent_message WHERE session_id = ?", (session_id,))
        self.conn.commit()

    def pin(self, session_id: str, pinned: bool) -> None:
        self.conn.execute(
            "UPDATE agent_session SET pinned = ?, updated_at = datetime('now','localtime') WHERE id = ?",
            (1 if pinned else 0, session_id),
        )
        self.conn.commit()

    def touch(self, session_id: str, preview: str) -> None:
        self.conn.execute(
            "UPDATE agent_session SET updated_at = datetime('now','localtime'), preview = ? WHERE id = ?",
            (preview, session_id),
        )
        self.conn.commit()

    def _ensure_table(self) -> None:
        self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS agent_session (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL DEFAULT '新会话',
                pinned INTEGER DEFAULT 0,
                preview TEXT DEFAULT '',
                created_at DATETIME DEFAULT (datetime('now','localtime')),
                updated_at DATETIME DEFAULT (datetime('now','localtime'))
            );
            CREATE TABLE IF NOT EXISTS agent_message (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL DEFAULT '',
                tool_calls TEXT DEFAULT '[]',
                token_count INTEGER DEFAULT 0,
                duration_ms INTEGER DEFAULT 0,
                created_at DATETIME DEFAULT (datetime('now','localtime')),
                FOREIGN KEY (session_id) REFERENCES agent_session(id)
            );
        """)
        # 幂等迁移：老版本 db 里的 agent_message 表可能没有 token_count 列
        # MessageRepository.save 会写入该列，所以必须补齐
        try:
            self.conn.execute("ALTER TABLE agent_message ADD COLUMN token_count INTEGER DEFAULT 0")
        except Exception:
            pass
        self.conn.commit()


class MessageRepository:
    def __init__(self, db_path: str):
        import sqlite3
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = _dict_factory

    def list(self, session_id: str, limit: int = 100) -> list[dict]:
        try:
            cur = self.conn.execute(
                "SELECT id, session_id, role, content, tool_calls, duration_ms, created_at "
                "FROM agent_message WHERE session_id = ? ORDER BY id ASC LIMIT ?",
                (session_id, limit),
            )
            rows = cur.fetchall()
            for r in rows:
                if isinstance(r.get("tool_calls"), str):
                    try:
                        r["tool_calls"] = json.loads(r["tool_calls"])
                    except (json.JSONDecodeError, TypeError):
                        r["tool_calls"] = []
            return rows
        except Exception:
            return []

    def save(self, session_id: str, role: str, content: str) -> int:
        cur = self.conn.execute(
            "INSERT INTO agent_message (session_id, role, content) VALUES (?, ?, ?)",
            (session_id, role, content),
        )
        self.conn.commit()
        return cur.lastrowid

    def get(self, msg_id: int) -> dict | None:
        try:
            cur = self.conn.execute(
                "SELECT id, session_id, role, content, tool_calls, duration_ms, created_at "
                "FROM agent_message WHERE id = ?",
                (msg_id,),
            )
            row = cur.fetchone()
            if row and isinstance(row.get("tool_calls"), str):
                try:
                    row["tool_calls"] = json.loads(row["tool_calls"])
                except (json.JSONDecodeError, TypeError):
                    row["tool_calls"] = []
            return row
        except Exception:
            return None


# ============================================================
# Agent 操作分发
# ============================================================

def handle_action(action: str, args: list[str], kwargs: dict) -> dict | list[dict]:
    db_path = args[0]
    s_repo = SessionRepository(db_path)
    m_repo = MessageRepository(db_path)

    if action == "session_create":
        session = s_repo.create(kwargs.get("title") or "新会话")
        return session
    elif action == "session_list":
        return s_repo.list()
    elif action == "session_rename":
        s_repo.rename(args[1], kwargs["title"])
        return {"status": "ok"}
    elif action == "session_delete":
        s_repo.delete(args[1])
        return {"status": "ok"}
    elif action == "session_pin":
        s_repo.pin(args[1], kwargs["pinned"])
        return {"status": "ok"}
    elif action == "message_list":
        return m_repo.list(args[1])
    elif action == "export_message":
        return _export_message(db_path, args[1], int(args[2]), kwargs["format"], kwargs.get("output_dir"))
    else:
        return {"error": f"Unknown action: {action}"}


def _export_message(db_path: str, session_id: str, message_id: int, format: str, output_dir: str = None) -> dict:
    """导出消息"""
    s_repo = SessionRepository(db_path)
    m_repo = MessageRepository(db_path)
    msg = m_repo.get(message_id)
    session = s_repo.get(session_id)
    if not msg or not session:
        return {"error": "Message or session not found"}
    if not output_dir:
        output_dir = os.path.join(os.getcwd(), "exports")
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_title = "".join(c for c in session["title"] if c.isalnum() or c in "_-")[:20]
    filename = f"{safe_title}_msg{message_id}_{timestamp}.{format}"
    file_path = Path(output_dir) / filename
    content = msg.get("content", "")
    tool_calls = json.dumps(msg.get("tool_calls", []), ensure_ascii=False)
    if format == "md":
        md = f"# {session['title']}\n\n**生成时间**: {msg.get('created_at', '')}\n\n{content}\n"
        if tool_calls != "[]":
            md += f"\n## 工具调用\n\n{tool_calls}\n"
        file_path.write_text(md, encoding="utf-8")
    else:
        html = f"<!DOCTYPE html><html><body><h1>{session['title']}</h1><pre>{content}</pre></body></html>"
        file_path.write_text(html, encoding="utf-8")
    return {"file_path": str(file_path)}


def main() -> None:
    if len(sys.argv) < 3:
        print(json.dumps({"error": "用法: agent_handler.py <action> <db_path> [args...]"}))
        sys.exit(1)

    action = sys.argv[1]
    db_path = sys.argv[2]
    args = [db_path]
    kwargs = {}

    if action == "session_create":
        if len(sys.argv) > 3:
            kwargs["title"] = sys.argv[3]
    elif action == "session_rename":
        if len(sys.argv) > 4:
            args.append(sys.argv[3])
            kwargs["title"] = sys.argv[4]
    elif action == "session_pin":
        if len(sys.argv) > 4:
            args.append(sys.argv[3])
            kwargs["pinned"] = sys.argv[4].lower() == "true"
    elif action == "session_delete":
        if len(sys.argv) > 3:
            args.append(sys.argv[3])
    elif action == "message_list":
        if len(sys.argv) > 3:
            args.append(sys.argv[3])
    elif action == "export_message":
        if len(sys.argv) > 5:
            args.extend([sys.argv[3], sys.argv[4]])
            kwargs["format"] = sys.argv[5]
            if len(sys.argv) > 6:
                kwargs["output_dir"] = sys.argv[6]
    elif action == "streaming":
        # streaming 模式由 agent_bridge_cli.py 处理
        pass

    result = handle_action(action, args, kwargs)
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()