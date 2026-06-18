#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# LLM 配置管理 CLI - 供 Rust 端通过 sidecar 调用
# 用法:
#   python3 llm_config_cli.py list                  # 列出所有模型
#   python3 llm_config_cli.py get-active            # 列出当前激活
#   python3 llm_config_cli.py save '<json>'         # 保存/更新模型
#   python3 llm_config_cli.py delete <id>           # 删除模型
#   python3 llm_config_cli.py set-active <id>       # 切换激活
#   python3 llm_config_cli.py test <base> <key> <model>  # 测试连接

import sys
import os
import json
import urllib.request
import urllib.error

# 切到项目根目录
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "..", "..", ".."))
os.chdir(PROJECT_ROOT)
sys.path.insert(0, SCRIPT_DIR)

from llm_client import LLMClient


def cmd_list():
    """列出所有模型（JSON 数组字符串）"""
    c = LLMClient()
    print(c.get_all_models())


def cmd_get_active():
    """返回当前激活模型（单 JSON 对象）"""
    c = LLMClient()
    if c.config:
        print(json.dumps(c.config, ensure_ascii=False))
    else:
        print("{}")


def cmd_save(model_json: str):
    c = LLMClient()
    print(c.save_model(model_json))


def cmd_delete(model_id: str):
    c = LLMClient()
    print(c.delete_model(model_id))


def cmd_set_active(model_id: str):
    c = LLMClient()
    print(c.set_active_model(model_id))


def cmd_test(api_base: str, api_key: str, model: str):
    """测试 LLM 连接（不入库配置）"""
    try:
        req = urllib.request.Request(
            f"{api_base.rstrip('/')}/chat/completions",
            data=json.dumps({
                "model": model,
                "messages": [{"role": "user", "content": "hi"}],
                "max_tokens": 5,
            }).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}",
            },
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            if resp.status == 200:
                print("✅ 连接成功")
            else:
                body = resp.read().decode("utf-8", errors="replace")
                print(f"❌ HTTP {resp.status}: {body[:120]}")
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        print(f"❌ HTTP {e.code}: {body[:120]}")
    except Exception as e:
        print(f"❌ 连接失败: {e}")


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    cmd = sys.argv[1]

    if cmd == "list":
        cmd_list()
    elif cmd == "get-active":
        cmd_get_active()
    elif cmd == "save":
        if len(sys.argv) < 3:
            print("用法: save '<json>'")
            sys.exit(1)
        cmd_save(sys.argv[2])
    elif cmd == "delete":
        if len(sys.argv) < 3:
            print("用法: delete <id>")
            sys.exit(1)
        cmd_delete(sys.argv[2])
    elif cmd == "set-active":
        if len(sys.argv) < 3:
            print("用法: set-active <id>")
            sys.exit(1)
        cmd_set_active(sys.argv[2])
    elif cmd == "test":
        if len(sys.argv) < 5:
            print("用法: test <api_base> <api_key> <model>")
            sys.exit(1)
        cmd_test(sys.argv[2], sys.argv[3], sys.argv[4])
    else:
        print(f"未知命令: {cmd}")
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main()
