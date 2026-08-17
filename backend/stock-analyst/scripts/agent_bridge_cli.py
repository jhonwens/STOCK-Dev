#!/usr/bin/env python3
"""agent_bridge CLI — 专供 PyInstaller 打包模式调用

Rust 端通过 backend-runner 调此脚本：
  backend-runner script agent_bridge_cli.py <json_request>
  backend-runner script agent_bridge_cli.py streaming <db_path> <session_id> <text>

设计说明：
  PyInstaller 冻结模式下，PYZ 中的 backend.ai 子模块 import 存在限制。
  本脚本直接用 runpy.run_path 加载 backend/ai/agent_bridge.py 和
  backend/ai/repository.py，避免依赖子包导入链。
"""
import sys
import json
import os
import importlib.util
import traceback


# ---- 工具函数：在冻结模式下直接加载 Python 模块文件 ----

def _load_module_from_path(filepath: str, modname: str):
    """从文件路径加载一个 Python 模块（绕过 import 系统）"""
    spec = importlib.util.spec_from_file_location(modname, filepath)
    if spec is None:
        return None
    mod = importlib.util.module_from_spec(spec)
    sys.modules[modname] = mod
    spec.loader.exec_module(mod)
    return mod


def _ensure_backend_ai_importable():
    """确保 backend.ai 包在冻结模式下可被 import"""
    if not hasattr(sys, '_MEIPASS'):
        from backend.ai import agent_bridge
        return

    meipass = sys._MEIPASS
    ai_dir = os.path.join(meipass, "backend", "ai")

    backend_init = os.path.join(meipass, "backend", "__init__.py")
    if os.path.isfile(backend_init) and 'backend' not in sys.modules:
        _load_module_from_path(backend_init, 'backend')

    ai_init = os.path.join(ai_dir, "__init__.py")
    if os.path.isfile(ai_init) and 'backend.ai' not in sys.modules:
        _load_module_from_path(ai_init, 'backend.ai')

    if ai_dir not in sys.path:
        sys.path.insert(0, ai_dir)

        deps = {
            'backend.ai.repository': os.path.join(ai_dir, "repository.py"),
            'backend.ai.skills': os.path.join(ai_dir, "skills.py"),
            'backend.ai.llm_client_v2': os.path.join(ai_dir, "llm_client_v2.py"),
            'backend.ai.agent': os.path.join(ai_dir, "agent.py"),
            'backend.ai.agent_bridge': os.path.join(ai_dir, "agent_bridge.py"),
        }
        for modname, path in deps.items():
            if os.path.isfile(path) and modname not in sys.modules:
                _load_module_from_path(path, modname)


def _emit_error(msg: str):
    """向 stdout 输出错误事件，确保前端能收到错误信息"""
    payload = json.dumps({
        "event": "error",
        "data": {"content": msg}
    }, ensure_ascii=False)
    print(payload, flush=True)


def main() -> None:
    try:
        if len(sys.argv) < 2:
            _emit_error("缺少参数")
            sys.exit(1)

        _ensure_backend_ai_importable()
        from backend.ai.agent_bridge import handle_request

        mode = sys.argv[1]

        if mode == "streaming":
            db_path = sys.argv[2]
            session_id = sys.argv[3]
            text = sys.argv[4]

            from backend.ai.agent import StockAgent
            from backend.ai.repository import SessionRepository, MessageRepository

            s_repo = SessionRepository(db_path)
            m_repo = MessageRepository(db_path)

            m_repo.save(session_id, "user", text)
            s_repo.touch(session_id, text[:100])

            # 尽早输出首次 thinking 事件，让用户感知消息已收到
            print(json.dumps({
                "event": "thinking",
                "data": {"step": 0, "content": "正在初始化 AI 分析引擎..."}
            }, ensure_ascii=False), flush=True)

            history = m_repo.list(session_id, limit=20)
            if history and history[-1].get("role") == "user" and history[-1].get("content") == text:
                history = history[:-1]

            try:
                agent = StockAgent()
            except Exception as e:
                _emit_error(f"Agent 初始化失败: {e}，请在设置页检查 LLM 配置")
                return

            final_content = ""
            try:
                for event in agent.run(text, history, session_id):
                    payload = json.dumps({
                        "event": event.event,
                        "data": event.data
                    }, ensure_ascii=False)
                    print(payload, flush=True)
                    if event.event == "final_answer":
                        final_content = event.data.get("content", "")
            except Exception as e:
                _emit_error(f"Agent 运行出错: {e}")

            if final_content:
                msg_id = m_repo.save(session_id, "assistant", final_content)
                s_repo.touch(session_id, final_content[:100])
                print(json.dumps({
                    "event": "assistant_saved",
                    "data": {"message_id": msg_id, "session_id": session_id}
                }, ensure_ascii=False), flush=True)
        else:
            request_json = sys.argv[1]
            req = json.loads(request_json)
            result = handle_request(req)
            print(json.dumps(result, ensure_ascii=False))

    except Exception as e:
        _emit_error(f"内部错误: {e}")
        traceback.print_exc()


if __name__ == "__main__":
    main()