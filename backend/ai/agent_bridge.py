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
        print(json.dumps({"error": "Missing request JSON"}))
        sys.exit(1)

    request_json = sys.argv[1]
    req = json.loads(request_json)
    result = handle_request(req)
    print(json.dumps(result, ensure_ascii=False))
