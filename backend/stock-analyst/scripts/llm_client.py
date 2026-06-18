#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# LLM 客户端 - 支持多模型配置和动态切换

import os
import json
import yaml
from openai import OpenAI


# 配置路径
DEFAULT_CONFIG_PATHS = [
    os.path.join(os.getcwd(), "config", "llm_config.json"),  # 新格式
    os.path.join(os.getcwd(), "config", "llm_models.json"),  # 别名
]


def _find_config_path():
    """查找第一个存在的配置文件"""
    for p in DEFAULT_CONFIG_PATHS:
        if os.path.exists(p):
            return p
    # 回退到旧路径
    return os.path.join(os.getcwd(), "config", "llm_config.json")


def _legacy_single_config_path():
    """旧版单配置路径（用于迁移）"""
    return os.path.join(os.getcwd(), "config", "llm_config.json")


class LLMClient:
    def __init__(self):
        self.base_dir = os.path.dirname(os.path.abspath(__file__))
        self.config = self._load_active_config()
        self.client = None
        if self.config:
            self.client = OpenAI(
                api_key=self.config.get('api_key'),
                base_url=self.config.get('api_base')
            )

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
        path = _find_config_path()
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(models, f, ensure_ascii=False, indent=2)

    # ----------------------------------------------------------------
    # 聊天接口（不变）
    # ----------------------------------------------------------------
    def chat(self, prompt, system_prompt=None, temperature=None, max_tokens=None, json_mode=False):
        """调用激活模型的 API

        Args:
            json_mode: 启用后会在请求中加 response_format={"type": "json_object"}，
                       强制 LLM 输出合法 JSON（Qwen/DeepSeek/OpenAI 均支持）。
        """
        if not self.client:
            return None, "LLM 客户端未初始化（请先在设置中配置模型）"

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        try:
            kwargs = {
                "model": self.config.get('model', 'qwen3.5-35b-a3b'),
                "messages": messages,
                "temperature": temperature or self.config.get('temperature', 0.7),
                "max_tokens": max_tokens or self.config.get('max_tokens', 16000),
            }
            # 强制 JSON 模式（如果用户开启）
            if json_mode:
                kwargs["response_format"] = {"type": "json_object"}

            response = self.client.chat.completions.create(**kwargs)
            return response.choices[0].message.content, None
        except Exception as e:
            return None, str(e)

    def is_available(self):
        return self.client is not None

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
