#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 千问 LLM 客户端 - 调用 Qwen3.5-35B-A3B

import os
import json
import yaml
from openai import OpenAI


class LLMClient:
    def __init__(self):
        self.base_dir = os.path.dirname(os.path.abspath(__file__))
        self.config = self._load_config()
        self.client = None
        if self.config:
            self.client = OpenAI(
                api_key=self.config.get('api_key'),
                base_url=self.config.get('api_base')
            )

    def _load_config(self):
        config = self._load_project_config()
        if config:
            return config
        config = self._load_secrets()
        if config:
            return config
        return None

    def _load_project_config(self):
        project_root = os.path.abspath(os.path.join(self.base_dir, '..', '..', '..'))
        json_path = os.path.join(project_root, 'config', 'llm_config.json')
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
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

    def chat(self, prompt, system_prompt=None, temperature=None, max_tokens=None):
        """调用千问 API"""
        if not self.client:
            return None, "LLM 客户端未初始化"

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        try:
            response = self.client.chat.completions.create(
                model=self.config.get('model', 'qwen3.5-35b-a3b'),
                messages=messages,
                temperature=temperature or self.config.get('temperature', 0.7),
                max_tokens=max_tokens or self.config.get('max_tokens', 2000)
            )
            return response.choices[0].message.content, None
        except Exception as e:
            return None, str(e)

    def is_available(self):
        """检查客户端是否可用"""
        return self.client is not None


def chat(prompt, system_prompt=None):
    """便捷函数：单次对话"""
    client = LLMClient()
    if not client.is_available():
        return "LLM 客户端未初始化，请检查 secrets.yaml 配置"
    result, error = client.chat(prompt, system_prompt)
    if error:
        return f"调用失败: {error}"
    return result


if __name__ == "__main__":
    # 测试
    client = LLMClient()
    if client.is_available():
        print("✅ LLM 客户端初始化成功")
        result, _ = client.chat("你好，请介绍一下你自己")
        print(f"测试结果: {result[:200]}...")
    else:
        print("❌ LLM 客户端初始化失败")