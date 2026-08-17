#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# LLM 客户端 - 支持多模型配置和动态切换

import os
import json
from openai import OpenAI


def extract_json(text):
    """从 LLM 返回中提取 JSON。容忍多种格式：
    1. 纯 JSON
    2. ```json ... ``` 代码块
    3. ``` ... ``` 任意代码块
    4. 嵌入在中文文本中的 JSON（用花括号定位）
    提取失败返回空字符串，让上层走错误处理。
    """
    if not text:
        return ""
    text = text.strip()
    if not text:
        return ""

    # 1. 剥代码块（```json ... ``` 或 ``` ... ```）
    if text.startswith("```"):
        lines = text.split("\n")
        start = 0
        for i, line in enumerate(lines):
            if line.strip().startswith("```"):
                start = i + 1
                break
        end = len(lines)
        for i in range(len(lines) - 1, start - 1, -1):
            if lines[i].strip().startswith("```"):
                end = i
                break
        text = "\n".join(lines[start:end]).strip()

    # 2. 如果首字符是 { 或 [，尝试直接解析
    if text.startswith(("{", "[")):
        return text

    # 3. 嵌入文本：找最外层 { ... } 块
    first = text.find("{")
    last = text.rfind("}")
    if first != -1 and last != -1 and last > first:
        return text[first:last + 1]

    return ""


# 配置路径（使用 __file__ 推导，不依赖 cwd）
# __file__ = backend/stock-analyst/scripts/llm_client.py
# 需要 3 次 dirname 回到项目根 STOCK-Dev/
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
# 优先用 STOCK_PROJECT_ROOT 环境变量（Rust 注入 = .app/Contents/Resources）
# 否则从 __file__ 推导：scripts/llm_client.py → scripts/ → project_root（2 次 dirname）
_PROJECT_ROOT = os.environ.get("STOCK_PROJECT_ROOT") or os.path.dirname(os.path.dirname(_SCRIPT_DIR))

# 可写配置目录（打包模式下为应用数据目录，开发模式下为项目根目录/config）
_CONFIG_WRITE_DIR = os.environ.get("STOCK_CONFIG_DIR") or os.path.join(_PROJECT_ROOT, "config")

# 候选配置路径列表（按优先级查找）
# 1. 用户显式配置的 STOCK_CONFIG_DIR
# 2. app_data_dir 直系下（早期版本保存位置，向后兼容）
# 3. app_data_dir/衡势价值/config/（当前 main.rs 设置的 STOCK_CONFIG_DIR 路径）
# 4. 项目根 config/（开发模式 / 资源包）
_CANDIDATE_DIRS = [
    _CONFIG_WRITE_DIR,
    os.path.join(os.path.expanduser("~"), "Library", "Application Support", "com.hengshi-value.app"),
    os.path.join(os.path.expanduser("~"), "Library", "Application Support", "com.hengshi-value.app", "衡势价值", "config"),
    os.path.join(_PROJECT_ROOT, "config"),
]


def _find_config_path():
    """查找配置路径 - 优先可写目录，回退到所有候选位置"""
    # 优先在已知位置找已存在的 llm_config.json
    for d in _CANDIDATE_DIRS:
        candidate = os.path.join(d, "llm_config.json")
        if os.path.exists(candidate):
            return candidate
    # 最终回退到 STOCK_CONFIG_DIR
    return os.path.join(_CONFIG_WRITE_DIR, "llm_config.json")


def _write_config_path():
    """获取可写的配置保存路径（始终写到当前 STOCK_CONFIG_DIR）"""
    return os.path.join(_CONFIG_WRITE_DIR, "llm_config.json")


def _legacy_single_config_path():
    """旧版单配置路径（用于迁移）"""
    return os.path.join(_PROJECT_ROOT, "config", "llm_config.json")


class LLMClient:
    def __init__(self):
        self.base_dir = os.path.dirname(os.path.abspath(__file__))
        self.config = self._load_active_config()
        self._client = None

    def _ensure_client(self):
        """惰性创建 OpenAI 客户端（仅 chat 需要）"""
        if self._client is not None:
            return self._client
        if not self.config:
            return None
        api_key = self.config.get('api_key')
        if not api_key:
            return None
        self._client = OpenAI(
            api_key=api_key,
            base_url=self.config.get('api_base')
        )
        return self._client

    # ----------------------------------------------------------------
    # 配置加载
    # ----------------------------------------------------------------
    def _load_active_config(self):
        """加载当前激活的模型配置（单数）"""
        # 优先读多模型配置
        models = self._load_all_models()
        if models:
            active = next((m for m in models if m.get("enabled")), None)
            if active:
                return active
            # 没有 enabled 的，取第一个
            return models[0] if models else None

        # 回退到旧版单配置
        cfg = self._load_legacy_single()
        if cfg:
            return cfg

        # 再回退到 secrets.yaml
        return self._load_secrets()

    def _load_all_models(self):
        """加载所有模型配置（数组格式）"""
        path = _find_config_path()
        if not os.path.exists(path):
            return None
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            # 数组格式（新）
            if isinstance(data, list):
                return data
            # 单对象格式（旧，自动迁移）
            if isinstance(data, dict) and data.get("api_base"):
                migrated = [{
                    "id": "m_legacy",
                    "name": "默认模型",
                    "provider": "unknown",
                    "api_base": data["api_base"],
                    "api_key": data["api_key"],
                    "model": data["model"],
                    "temperature": data.get("temperature", 0.7),
                    "enabled": True,
                    "created_at": data.get("created_at", ""),
                }]
                # 写回新格式
                self._save_all_models(migrated)
                return migrated
        except Exception as e:
            print(f"加载 llm_config.json 失败: {e}")
        return None

    def _load_legacy_single(self):
        """加载旧版单对象配置（仅在主路径为对象时）"""
        path = _legacy_single_config_path()
        if not os.path.exists(path):
            return None
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            if isinstance(data, dict) and data.get("api_base"):
                return data
        except Exception:
            pass
        return None

    def _load_secrets(self):
        secrets_path = os.path.expanduser("~/.config/opencode/secrets.yaml")
        try:
            with open(secrets_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
                return config.get('llm', {})
        except Exception as e:
            print(f"加载 secrets.yaml 失败: {e}")
            return None

    # ----------------------------------------------------------------
    # 多模型管理（供 Rust/Python 双向调用）
    # ----------------------------------------------------------------
    def get_all_models(self):
        """返回所有模型（数组 JSON 字符串）"""
        models = self._load_all_models() or []
        return json.dumps(models, ensure_ascii=False)

    def save_model(self, model_json: str) -> str:
        """保存/更新单条模型配置。
        入参是 JSON 字符串（含 id/name/api_base/api_key/model/temperature/enabled 等）
        规则:
          1. 如果有同 id → 覆盖更新
          2. 如果 enabled=true → 同时把其他所有 enabled 置为 false（单选激活）
          3. 如果是新增（无 id）→ 自动生成 id
        """
        try:
            new_model = json.loads(model_json)
        except Exception as e:
            return f"❌ 无效的 JSON: {e}"

        if not new_model.get("id"):
            new_model["id"] = "m_" + os.urandom(4).hex()
        if not new_model.get("created_at"):
            new_model["created_at"] = ""

        models = self._load_all_models() or []
        existing_idx = next((i for i, m in enumerate(models) if m.get("id") == new_model["id"]), None)
        if existing_idx is not None:
            models[existing_idx] = new_model
        else:
            models.append(new_model)

        # 单选激活
        if new_model.get("enabled"):
            for m in models:
                if m.get("id") != new_model["id"]:
                    m["enabled"] = False

        self._save_all_models(models)
        return f"✅ 模型 '{new_model.get('name', new_model['id'])}' 已保存"

    def delete_model(self, model_id: str) -> str:
        models = self._load_all_models() or []
        before = len(models)
        models = [m for m in models if m.get("id") != model_id]
        if len(models) == before:
            return f"⚠️ 未找到 id={model_id}"
        self._save_all_models(models)
        return f"✅ 模型已删除（剩余 {len(models)} 个）"

    def set_active_model(self, model_id: str) -> str:
        models = self._load_all_models() or []
        target = next((m for m in models if m.get("id") == model_id), None)
        if not target:
            return f"⚠️ 未找到 id={model_id}"
        for m in models:
            m["enabled"] = (m.get("id") == model_id)
        self._save_all_models(models)
        return f"✅ 已切换到 '{target.get('name', model_id)}'"

    def _save_all_models(self, models):
        path = _write_config_path()
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(models, f, ensure_ascii=False, indent=2)

    # ----------------------------------------------------------------
    # 聊天接口（不变）
    # ----------------------------------------------------------------
    def chat(self, prompt, system_prompt=None, temperature=None, max_tokens=None, json_mode=False, _retry_on_truncate=True):
        """调用激活模型的 API

        Args:
            json_mode: 启用后会在请求中加 response_format={"type": "json_object"}，
                       强制 LLM 输出合法 JSON（Qwen/DeepSeek/OpenAI 均支持）。
            _retry_on_truncate: 内部参数 — 检测到 finish_reason=length（被 max_tokens 截断）
                                时是否自动用 2x max_tokens 重试一次。
        """
        client = self._ensure_client()
        if not client:
            return None, "LLM 客户端未初始化（请先在设置中配置模型）"

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        try:
            effective_max = max_tokens or self.config.get('max_tokens', 16000)
            kwargs = {
                "model": self.config.get('model', 'qwen3.5-35b-a3b'),
                "messages": messages,
                "temperature": temperature or self.config.get('temperature', 0.7),
                "max_tokens": effective_max,
            }
            # 强制 JSON 模式（如果用户开启）
            if json_mode:
                kwargs["response_format"] = {"type": "json_object"}

            response = client.chat.completions.create(**kwargs)
            content = response.choices[0].message.content or ""
            finish_reason = getattr(response.choices[0], "finish_reason", None)

            # 自动重试：被 max_tokens 截断时用 2x 重试一次
            if finish_reason == "length" and _retry_on_truncate:
                kwargs["max_tokens"] = effective_max * 2
                response2 = client.chat.completions.create(**kwargs)
                content2 = response2.choices[0].message.content or ""
                if content2 and len(content2) > len(content):
                    content = content2
                    finish_reason = getattr(response2.choices[0], "finish_reason", None)

            # 把 finish_reason 透传给调用方（如果调用方想用）
            if finish_reason == "length" and not content.rstrip().endswith(("}", "]", "`", "。", "！", "？", "\"", "'")):
                return content, "⚠️ LLM 输出被截断（finish_reason=length），JSON 可能不完整"

            return content, None
        except Exception as e:
            return None, str(e)

    def is_available(self):
        return self._ensure_client() is not None

    def get_active_model_name(self):
        if self.config:
            return self.config.get("name") or self.config.get("model", "未知")
        return "未配置"


def chat(prompt, system_prompt=None):
    """便捷函数：单次对话"""
    client = LLMClient()
    if not client.is_available():
        return "LLM 客户端未初始化，请在设置中配置模型"
    result, error = client.chat(prompt, system_prompt)
    if error:
        return f"调用失败: {error}"
    return result


if __name__ == "__main__":
    client = LLMClient()
    if client.is_available():
        print(f"✅ LLM 客户端初始化成功（当前激活: {client.get_active_model_name()}）")
        result, _ = client.chat("你好，请介绍一下你自己")
        if result:
            print(f"测试结果: {result[:200]}...")
        else:
            print("❌ 调用失败")
    else:
        print("❌ LLM 客户端初始化失败，请先在设置中配置模型")
