import sqlite3
import tempfile
from pathlib import Path
from backend.ai.migrations.apply import apply_migrations

def test_apply_migrations_creates_tables():
    """测试 migration 后 3 张表都存在"""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        apply_migrations(str(db_path))

        conn = sqlite3.connect(str(db_path))
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name IN "
            "('agent_session', 'agent_message', 'agent_export') ORDER BY name"
        )
        tables = [row[0] for row in cursor.fetchall()]
        assert tables == ["agent_export", "agent_message", "agent_session"]
        conn.close()

def test_apply_migrations_idempotent():
    """测试重复执行 migration 不出错"""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        apply_migrations(str(db_path))
        apply_migrations(str(db_path))  # 第二次
        # 不应该报错
