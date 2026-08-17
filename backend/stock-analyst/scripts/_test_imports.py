#!/usr/bin/env python3
"""验证 PyInstaller 打包后哪些 backend.ai 模块可导入"""
import sys
import json

print("=" * 50)
print("MEIPASS:", getattr(sys, '_MEIPASS', 'N/A'))
print("sys.path:", json.dumps(sys.path, ensure_ascii=False))
print("sys.modules count:", len(sys.modules))
print("=" * 50)

for modname in [
    "backend", "backend.ai", "backend.ai.agent_bridge",
    "backend.ai.repository", "backend.ai.agent",
    "backend.ai.skill_impl", "backend.ai.intent"
]:
    try:
        mod = __import__(modname)
        file = getattr(mod, '__file__', 'N/A')
        print(f"  ✓ {modname} -> {file}")
    except Exception as e:
        print(f"  ✗ {modname}: {e}")

print("=" * 50)
print("All 'backend' modules in sys.modules:")
for m in sorted(sys.modules.keys()):
    if "backend" in m:
        print(f"  {m}")