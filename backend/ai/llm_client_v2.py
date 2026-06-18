"""LLMClientV2 - 直接调用 openai SDK，支持 tool calling 协议

与 stock-analyst/scripts/llm_client.py 的 LLMClient 不同：
- 不返回 (content, error) 元组
- 返回 OpenAI 风格的 response 对象（含 choices[0].message.content 和 tool_calls）
- 支持 messages/tools/tool_choice 参数
- 不接受旧的 prompt/system_prompt 位置参数
"""
import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from openai import OpenAI


# 配置路径：__file__ = backend/ai/llm_client_v2.py
# 需要回退 2 次到项目根 STOCK-Dev/
_PROJECT_ROOT = Path(__file__).parent.parent.parent
DEFAULT_CONFIG_PATHS = [
    _PROJECT_ROOT / "config" / "llm_config.json",
    _PROJECT_ROOT / "config" / "llm_models.json",
]


def _find_config_path() -> Optional[Path]:
    """查找第一个存在的配置文件"""
    for p in DEFAULT_CONFIG_PATHS:
        if p.exists():
            return p
    return DEFAULT_CONFIG_PATHS[0]


class LLMClientV2:
    """OpenAI 风格 LLM 客户端，支持 tool calling"""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """初始化客户端

        Args:
            config: 可选，外部传入的模型配置 dict（用于测试 mock）。
                    如果不传，则从 config/llm_config.json 自动加载 enabled 模型。
        """
        if config is not None:
            self.config = config
        else:
            self.config = self._load_config()

        if not self.config:
            raise ValueError(
                "No enabled LLM model in config. "
                "请在 config/llm_config.json 中配置至少一个 enabled 模型"
            )

        self.client = OpenAI(
            api_key=self.config.get("api_key"),
            base_url=self.config.get("api_base"),
        )
        self.model = self.config.get("model", "qwen3.5-35b-a3b")

    @staticmethod
    def _load_config() -> Optional[Dict[str, Any]]:
        """从 config/llm_config.json 加载 enabled=true 的模型"""
        config_path = _find_config_path()
        if not config_path or not config_path.exists():
            return None
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            # 新格式：数组
            if isinstance(data, list):
                active = next((m for m in data if m.get("enabled")), None)
                if active:
                    return active
                return data[0] if data else None
            # 旧格式：单对象
            if isinstance(data, dict) and data.get("api_base"):
                return data
        except Exception as e:
            print(f"加载 {config_path} 失败: {e}")
        return None

    def chat(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        tool_choice: Union[str, Dict[str, Any]] = "auto",
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        stream: bool = False,
    ):
        """调用 LLM 聊天接口

        Args:
            messages: OpenAI 风格 messages 列表
            tools: OpenAI 风格 tools 列表（function calling 定义）
            tool_choice: 工具选择策略，'auto' / 'none' / 'required' / 指定函数
            temperature: 采样温度
            max_tokens: 最大 token 数
            stream: 是否流式输出

        Returns:
            OpenAI ChatCompletion 对象（stream=False 时）
            或 Stream 对象（stream=True 时）
        """
        kwargs: Dict[str, Any] = {
            "model": self.model,
            "messages": messages,
        }
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = tool_choice
        if temperature is not None:
            kwargs["temperature"] = temperature
        if max_tokens is not None:
            kwargs["max_tokens"] = max_tokens
        if stream:
            kwargs["stream"] = True

        return self.client.chat.completions.create(**kwargs)

    def is_available(self) -> bool:
        return self.client is not None and bool(self.model)

    def get_active_model_name(self) -> str:
        if self.config:
            return self.config.get("name") or self.config.get("model", "未知")
        return "未配置"


__all__ = ["LLMClientV2"]
