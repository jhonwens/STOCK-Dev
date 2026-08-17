# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_data_files, collect_submodules
import os
import certifi

block_cipher = None

# 项目根目录（运行 pyinstaller 时的当前工作目录）
project_root = os.getcwd()

datas = [
    # stock-analyst 脚本目录（供 entry.py 的 _run_script 通过 sys._MEIPASS/scripts/ 加载）
    (os.path.join(project_root, 'backend', 'stock-analyst', 'scripts'), 'scripts'),
    # scripts/config.yaml（脚本运行时通过 os.path.dirname(__file__) 定位）
    (os.path.join(project_root, 'backend', 'stock-analyst', 'scripts', 'config.yaml'), 'scripts'),
    # stock-analyst resource 目录（stock_list.yaml 等配置文件，供 skill_impl.py 在运行时读取）
    (os.path.join(project_root, 'backend', 'stock-analyst', 'resource'), 'resource'),
    # backend.ai 完整目录（agent_bridge_cli.py 用 _load_module_from_path 加载子模块）
    (os.path.join(project_root, 'backend', 'ai'), 'backend/ai'),
    # certifi CA bundle（修复 PyInstaller 打包后 SSL 证书验证失败问题）
    (certifi.where(), 'certifi'),
]

# backend.ai 的所有子模块（确保 agent、skills、repository 等都打包）
ai_hidden_imports = collect_submodules('backend.ai')

# stock-analyst/scripts 下的模块
script_hidden_imports = [
    'llm_client', 'db_manager', 'stock_crawler', 'finance_fetcher',
    'news_fetcher', 'trend_analyzer', 'alert_engine', 'stock_picker',
]

hiddenimports = ai_hidden_imports + script_hidden_imports + [
    # backend 顶层包（agent_bridge 通过 import backend.ai.* 导入）
    'backend', 'backend.ai',
    # 显式列出第三方库
    'openai', 'requests', 'yaml', 'baostock',
    'dateutil', 'dateutil.relativedelta',
]

a = Analysis(
    [os.path.join(project_root, 'backend', 'pyentry', 'entry.py')],
    pathex=[project_root, os.path.join(project_root, 'backend', 'stock-analyst', 'scripts')],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # 排除不必要的重型库以减少体积
        'matplotlib', 'scipy', 'notebook', 'ipython',
        'setuptools._distutils', 'torch', 'tensorflow',
        'transformers', 'PIL', 'cv2',
    ],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='backend-runner',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)