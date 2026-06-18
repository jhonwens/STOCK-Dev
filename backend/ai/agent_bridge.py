"""Python 端 Rust 调用入口"""
import sys
import json
import os
from datetime import datetime
from pathlib import Path
from backend.ai.repository import SessionRepository, MessageRepository


def export_message(db_path: str, session_id: str, message_id: int, format: str, output_dir: str = None) -> dict:
    """导出消息为 MD 或 HTML"""
    s_repo = SessionRepository(db_path)
    m_repo = MessageRepository(db_path)

    msg = m_repo.get(message_id)
    session = s_repo.get(session_id)

    if not msg or not session:
        return {"error": "Message or session not found"}

    if not output_dir:
        output_dir = os.path.expanduser("~/Documents/衡势价值/智能分析报告")
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_title = "".join(c for c in session["title"] if c.isalnum() or c in "_-")[:20]
    filename = f"{safe_title}_msg{message_id}_{timestamp}.{format}"
    file_path = Path(output_dir) / filename

    if format == "md":
        content = build_markdown(session, msg)
    elif format == "html":
        content = build_html(session, msg)
    else:
        return {"error": f"Unknown format: {format}"}

    file_path.write_text(content, encoding="utf-8")
    return {"file_path": str(file_path)}


def build_markdown(session, msg) -> str:
    """生成 Markdown 内容"""
    tool_calls = msg.get("tool_calls") or []
    tc_section = ""
    if tool_calls:
        tc_section = "\n## 工具调用\n\n"
        for tc in tool_calls:
            tc_section += f"- **{tc.get('name')}** ({json.dumps(tc.get('args', {}), ensure_ascii=False)})\n"
            if tc.get("resultPreview"):
                tc_section += f"  - 结果: {tc['resultPreview'][:200]}...\n"

    return f"""# 智能分析报告

**会话**: {session['title']}
**生成时间**: {msg.get('created_at', '')}
**消息 ID**: {msg['id']}
**耗时**: {msg.get('duration_ms', 0)}ms

---

## Agent 回答

{msg.get('content', '')}
{tc_section}
"""


def build_html(session, msg) -> str:
    """生成 HTML 内容（带样式）"""
    content = msg.get("content", "").replace("\n", "<br>")
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <title>智能分析报告 - {session['title']}</title>
  <style>
    body {{ font-family: -apple-system, "Helvetica Neue", sans-serif; max-width: 800px; margin: 0 auto; padding: 24px; background: #fafafa; color: #333; }}
    .card {{ background: #fff; border-radius: 8px; padding: 24px; margin: 16px 0; box-shadow: 0 1px 4px rgba(0,0,0,0.06); }}
    h1 {{ color: #1e40af; }}
    .meta {{ color: #666; font-size: 14px; }}
    .answer {{ line-height: 1.7; }}
  </style>
</head>
<body>
  <h1>🤖 智能分析报告</h1>
  <div class="card">
    <div class="meta">
      <strong>会话</strong>: {session['title']}<br>
      <strong>生成时间</strong>: {msg.get('created_at', '')}<br>
      <strong>消息 ID</strong>: {msg['id']}
    </div>
  </div>
  <div class="card">
    <h2>Agent 回答</h2>
    <div class="answer">{content}</div>
  </div>
</body>
</html>"""


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
    elif action == "export_message":
        return export_message(args[0], args[1], args[2], kwargs["format"], kwargs.get("output_dir"))
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
