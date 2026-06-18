import tempfile
import uuid
from pathlib import Path
from backend.ai.migrations.apply import apply_migrations
from backend.ai.repository import SessionRepository, MessageRepository

def test_session_create_list_rename_delete():
    """测试会话 CRUD"""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        apply_migrations(str(db_path))
        repo = SessionRepository(str(db_path))

        # 创建
        session = repo.create("测试会话")
        assert session["title"] == "测试会话"
        assert session["message_count"] == 0

        # 列出
        sessions = repo.list()
        assert len(sessions) == 1
        assert sessions[0]["id"] == session["id"]

        # 重命名
        repo.rename(session["id"], "新名称")
        assert repo.get(session["id"])["title"] == "新名称"

        # 删除
        repo.delete(session["id"])
        assert repo.get(session["id"]) is None
        assert len(repo.list()) == 0

def test_message_save_and_list():
    """测试消息保存和列表"""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        apply_migrations(str(db_path))
        s_repo = SessionRepository(str(db_path))
        m_repo = MessageRepository(str(db_path))

        session = s_repo.create()
        m_repo.save(session["id"], "user", "你好")
        m_repo.save(session["id"], "assistant", "你好，我能帮你什么？")
        m_repo.save(session["id"], "assistant", "## 报告\n表格...", tool_calls=[
            {"name": "analyze_stock", "args": {"code": "000001"}, "status": "success"}
        ])

        messages = m_repo.list(session["id"])
        assert len(messages) == 3
        assert messages[0]["role"] == "user"
        assert messages[1]["content"] == "你好，我能帮你什么？"
        assert messages[2]["tool_calls"][0]["name"] == "analyze_stock"
