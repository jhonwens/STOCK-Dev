#!/usr/bin/env python3
"""统一入口点 — Rust 通过此脚本调用所有 Python 后端功能。

设计目标：
  - 将所有 Python 调用统一到一个入口点
  - PyInstaller 将其编译为独立可执行文件，随 APP 分发
  - 用户不需要安装 Python 和 pip 依赖

用法（供 Rust 调用）：
  backend-runner module <module_name> [args...]      → python3 -m <module_name> [args...]
  backend-runner script <script_name> [args...]       → python3 <script_path> [args...]

示例：
  backend-runner module backend.ai.agent_bridge '{"action":"list"}'
  backend-runner module backend.ai.agent_bridge streaming /path/to/db session_id text
  backend-runner script main.py --mode quick
  backend-runner script candidate_recommend.py
  backend-runner script portfolio_analysis.py 000001
  backend-runner script stock_insight.py --code 000001
  backend-runner script llm_config_cli.py list
"""
import os
import sys
import runpy


# ---------------------------------------------------------------------------
# 路径解析（兼容 PyInstaller 打包模式和开发模式）
# ---------------------------------------------------------------------------

def _is_frozen() -> bool:
    """判断是否在 PyInstaller 打包的可执行文件中运行"""
    return hasattr(sys, "frozen")


# ---------------------------------------------------------------------------
# SSL 证书修复（PyInstaller 打包后必须）
# ---------------------------------------------------------------------------
# 原因：certifi 默认从系统 Python 安装目录读取 cacert.pem，但 PyInstaller
# 不会把系统的 CA bundle 一起打包。结果就是 urllib3 / openai / httpx 在
# HTTPS 请求时报 "certificate verify failed: unable to get local issuer
# certificate"。这里把 certifi 自带的 cacert.pem 路径注入到环境变量，
# 让所有使用 ssl 的库都走这个文件。

def _setup_ssl_certs() -> None:
    """SSL 证书修复 — 让 urllib3/openai/httpx 在 PyInstaller 打包后能找到 CA bundle

    优先级：
      1. PyInstaller 解压目录 sys._MEIPASS/certifi/cacert.pem（打包模式）
      2. certifi 库默认位置（开发模式）
    """
    candidate_paths = []
    if _is_frozen():
        candidate_paths.append(
            os.path.join(sys._MEIPASS, "certifi", "cacert.pem")  # type: ignore[attr-defined]
        )
    try:
        import certifi
        candidate_paths.append(certifi.where())
    except Exception:
        pass

    for ca_path in candidate_paths:
        if ca_path and os.path.isfile(ca_path):
            os.environ["SSL_CERT_FILE"] = ca_path
            os.environ["REQUESTS_CA_BUNDLE"] = ca_path
            os.environ["CURL_CA_BUNDLE"] = ca_path
            return


_setup_ssl_certs()


def _get_base_dir() -> str:
    """获取基础目录：
    - 打包模式：sys._MEIPASS（PyInstaller 提取 data 文件的临时目录）
    - 开发模式：项目根（由 STOCK_PROJECT_ROOT 环境变量指定，或从 __file__ 推导）
    """
    if _is_frozen():
        return sys._MEIPASS  # type: ignore[attr-defined]
    return os.environ.get(
        "STOCK_PROJECT_ROOT",
        os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")),
    )


def _get_scripts_dir(base_dir: str) -> str:
    """获取 stock-analyst 脚本目录：
    - 打包模式：data 文件映射到 sys._MEIPASS/scripts/
    - 开发模式：backend/stock-analyst/scripts/
    """
    if _is_frozen():
        return os.path.join(sys._MEIPASS, "scripts")  # type: ignore[attr-defined]
    return os.path.join(base_dir, "backend", "stock-analyst", "scripts")


# ---------------------------------------------------------------------------
# sys.path 设置
# ---------------------------------------------------------------------------

def _setup_sys_path(base_dir: str) -> None:
    """设置 sys.path 使所有导入可解析"""
    # scripts 目录 — 使 from llm_client import LLMClient 等可解析
    scripts_dir = _get_scripts_dir(base_dir)
    if scripts_dir not in sys.path and os.path.isdir(scripts_dir):
        sys.path.insert(0, scripts_dir)

    if _is_frozen():
        # 打包模式：sys._MEIPASS 下放了 backend/、config/ 等 data 目录
        # 添加 sys._MEIPASS 到 path 使 import backend.ai.* 可解析
        if base_dir not in sys.path:
            sys.path.insert(0, base_dir)
        # 也加 backend 二级目录（部分模块用 from backend.ai.repository 导入）
        backend_dir = os.path.join(base_dir, "backend")
        if os.path.isdir(backend_dir) and backend_dir not in sys.path:
            sys.path.insert(0, backend_dir)
    else:
        # 非打包模式还需要项目根目录和 backend 目录
        if base_dir not in sys.path:
            sys.path.insert(0, base_dir)
        # backend 目录
        backend_dir = os.path.join(base_dir, "backend")
        if os.path.isdir(backend_dir) and backend_dir not in sys.path:
            sys.path.insert(0, backend_dir)


# ---------------------------------------------------------------------------
# 调度
# ---------------------------------------------------------------------------

def _run_module(mod_name: str, mod_args: list[str]) -> None:
    """模拟 python3 -m <module> <args...>"""
    sys.argv = [mod_name] + mod_args
    runpy.run_module(mod_name, run_name="__main__", alter_sys=True)


def _run_script(script_name: str, script_args: list[str]) -> None:
    """模拟 python3 <script_path> <args...>"""
    base_dir = _get_base_dir()
    scripts_dir = _get_scripts_dir(base_dir)
    script_path = os.path.join(scripts_dir, script_name)

    if not os.path.isfile(script_path):
        print(f"[entry.py] 脚本未找到: {script_path}", file=sys.stderr)
        sys.exit(1)

    sys.argv = [script_path] + script_args
    runpy.run_path(script_path, run_name="__main__")


# ---------------------------------------------------------------------------
# 主入口
# ---------------------------------------------------------------------------

def main() -> None:
    if len(sys.argv) < 3:
        print("用法: backend-runner <module|script> <name> [args...]", file=sys.stderr)
        sys.exit(1)

    mode = sys.argv[1]
    name = sys.argv[2]
    rest = sys.argv[3:]

    base_dir = _get_base_dir()
    _setup_sys_path(base_dir)

    if mode == "module":
        _run_module(name, rest)
    elif mode == "script":
        _run_script(name, rest)
    else:
        print(f"[entry.py] 未知模式: {mode}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()