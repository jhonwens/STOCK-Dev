"""LLM 客户端 - 向后兼容层

历史接口（deprecated）：
- LLMClient: stock-analyst/scripts/llm_client.py 的旧版 LLMClient，不支持 tool calling
- load_llm_config(): 自实现的 config 加载

新版请使用 backend.ai.llm_client_v2.LLMClientV2
"""
import sys
import os
from pathlib import Path

# 复用 LLMClientV2 的 config 加载逻辑
from backend.ai.llm_client_v2 import LLMClientV2, _find_config_path  # noqa: F401

# 把 stock-analyst/scripts 加入 path，复用现有实现（仅用于兼容）
_SCRIPTS_DIR = Path(__file__).parent.parent / "stock-analyst" / "scripts"
sys.path.insert(0, str(_SCRIPTS_DIR))

# 导入现有 llm_client（向后兼容）
from llm_client import LLMClient  # noqa: E402


def load_llm_config():
    """加载当前激活的 LLM 配置（dict）

    委托给 LLMClientV2._load_config，避免重复实现。
    """
    return LLMClientV2._load_config()


__all__ = ["LLMClient", "LLMClientV2", "load_llm_config"]
