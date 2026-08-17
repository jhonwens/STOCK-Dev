#!/usr/bin/env python3
"""测试 backend.ai 子模块导入"""
import sys, json

# Add MEIPASS to path 
if hasattr(sys, '_MEIPASS'):
    meipass = sys._MEIPASS
    # Add backend directory
    backend_dir = meipass + '/backend'
    if backend_dir not in sys.path and __import__('os').path.isdir(backend_dir):
        sys.path.insert(0, backend_dir)
    print(f"MEIPASS: {meipass}")
else:
    print("Not frozen")

print(f"sys.path: {json.dumps(sys.path, ensure_ascii=False)}")

for modname in [
    "backend", "backend.ai", "backend.ai.agent_bridge",
    "backend.ai.repository",
]:
    try:
        mod = __import__(modname)
        print(f"  ✓ {modname}")
    except Exception as e:
        print(f"  ✗ {modname}: {e}")

# All backend modules in sys.modules
print("---")
for m in sorted(sys.modules):
    if m.startswith("backend"):
        print(f"  {m}")