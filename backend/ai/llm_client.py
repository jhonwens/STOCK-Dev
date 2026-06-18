"""LLM 客户端 - 复用 stock-analyst/scripts/llm_client.py"""
import sys
import json
import os
from pathlib import Path

# 把 stock-analyst/scripts 加入 path，复用现有实现
SCRIPTS_DIR = Path(__file__).parent.parent / "stock-analyst" / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

# 导入现有 llm_client
from llm_client import LLMClient  # noqa: E402


def load_llm_config():
    """加载当前激活的 LLM 配置（dict）

    现有 stock-analyst 的 LLMClient 把 config 加载封装在内部，
    我们这里简单复用：实例化后读取其 _load_active_config()。
    注意：原 LLMClient.__init__ 不接受参数，这里为了保持 plan 接口一致
    单独抽出 config 加载逻辑。
    """
    import yaml
    # 复用 LLMClient 内部的路径解析
    config_paths = [
        os.path.join(os.path.dirname(SCRIPTS_DIR), "config", "llm_config.json"),
        os.path.expanduser("~/.config/opencode/secrets.yaml"),
    ]
    for p in config_paths:
        if not os.path.exists(p):
            continue
        try:
            if p.endswith(".yaml"):
                with open(p, "r", encoding="utf-8") as f:
                    return yaml.safe_load(f).get("llm", {})
            else:
                with open(p, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data, list):
                    active = next((m for m in data if m.get("enabled")), None)
                    return active or (data[0] if data else None)
                return data
        except Exception:
            continue
    return None


__all__ = ["LLMClient", "load_llm_config"]
