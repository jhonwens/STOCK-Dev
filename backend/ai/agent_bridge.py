"""Python 端 Rust 调用入口"""
import sys
import json
from backend.ai.repository import SessionRepository, MessageRepository


def handle_request(req: dict) -> dict:
    action = req["action"]
    args = req["args"]
    kwargs = req.get("kwargs", {})

    db_path = args[0]
    s_repo = SessionRepository(db_path)
    m_repo = MessageRepository(db_path)

    if action == "session_create":
        session = s_repo.create(kwargs.get("title", "新会话"))
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
    else:
        return {"error": f"Unknown action: {action}"}


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(json.dumps({"error": "Missing args"}))
        sys.exit(1)

    mode = sys.argv[1]

    if mode == "streaming":
        # python -m backend.ai.agent_bridge streaming <db_path> <session_id> <text>
        db_path = sys.argv[2]
        session_id = sys.argv[3]
        text = sys.argv[4]

        from backend.ai.agent import StockAgent
        from backend.ai.repository import SessionRepository, MessageRepository

        s_repo = SessionRepository(db_path)
        m_repo = MessageRepository(db_path)

        # 1. 保存用户消息
        m_repo.save(session_id, "user", text)
        s_repo.touch(session_id, text[:100])

        # 2. 加载历史（排除刚保存的 user 消息，避免重复）
        history = m_repo.list(session_id, limit=20)
        if history and history[-1].get("role") == "user" and history[-1].get("content") == text:
            history = history[:-1]

        # 3. 运行 Agent，逐事件输出 JSON 行
        agent = StockAgent()
        final_content = ""
        for event in agent.run(text, history, session_id):
            print(json.dumps({
                "event": event.event,
                "data": event.data
            }, ensure_ascii=False), flush=True)

            if event.event == "final_answer":
                final_content = event.data.get("content", "")

        # 4. 保存 Agent 消息
        if final_content:
            msg_id = m_repo.save(session_id, "assistant", final_content)
            s_repo.touch(session_id, final_content[:100])
            # ⚠️ Plan 修订 (方案 A): 不再 emit "done" 事件
            # agent.py 已经 yield 过 done 事件（含 step + duration_ms）
            # 这里改 emit 专用的 "assistant_saved" 事件（含 message_id）
            # Rust 端识别这个事件后 emit agent_stream_done 给前端
            print(json.dumps({
                "event": "assistant_saved",
                "data": {"message_id": msg_id, "session_id": session_id}
            }, ensure_ascii=False), flush=True)
    else:
        # 原有 JSON 模式
        request_json = sys.argv[1]
        req = json.loads(request_json)
        result = handle_request(req)
        print(json.dumps(result, ensure_ascii=False))
