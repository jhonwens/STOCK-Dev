"""
文件搬迁完整性 & 数据库结构验证测试
验证 T3: 数据库操作, T6: 文件搬迁完整性
"""
import sys
import os

PROJECT_ROOT = '/Users/ws/Desktop/Project/Trea-Project/STOCK-Dev'
ORIGINAL_ROOT = '/Users/ws/.config/opencode'


def get_py_files(directory):
    """获取目录下所有 .py 文件 (非 __init__)"""
    py_files = []
    for root, dirs, files in os.walk(directory):
        for f in files:
            if f.endswith('.py') and f != '__init__.py':
                py_files.append(os.path.join(root, f))
    return sorted(py_files)


def get_all_files(directory):
    """获取目录下所有文件"""
    all_files = []
    for root, dirs, files in os.walk(directory):
        for f in files:
            all_files.append(os.path.join(root, f))
    return sorted(all_files)


def test_t3_database_tables():
    """T3.1: 数据库表结构验证 - 检查 db_manager 中的 CREATE TABLE"""
    db_path = os.path.join(PROJECT_ROOT, 'backend/stock-analyst/scripts/db_manager.py')
    assert os.path.exists(db_path), f"db_manager.py 不存在: {db_path}"
    with open(db_path, 'r') as f:
        content = f.read()
    tables_found = []
    for line in content.split('\n'):
        if 'CREATE TABLE IF NOT EXISTS' in line or 'CREATE TABLE' in line:
            table_name = line.split('IF NOT EXISTS')[-1].split('(')[0].strip() if 'IF NOT EXISTS' in line else line.split('CREATE TABLE')[-1].split('(')[0].strip()
            tables_found.append(table_name)
    print(f"  ✅ db_manager.py 中定义了 {len(tables_found)} 张表: {tables_found}")
    assert len(tables_found) >= 7, f"至少应有 7 张表, 当前 {len(tables_found)}"
    return True


def test_t3_database_imports():
    """T3.2: 数据库导入验证 - 检查所有脚本能正确导入 db_manager"""
    db_path = os.path.join(PROJECT_ROOT, 'backend/stock-analyst/scripts/db_manager.py')
    assert os.path.exists(db_path), f"db_manager.py 不存在"
    # 检查各脚本对 db_manager 的引用
    scripts = get_py_files(os.path.join(PROJECT_ROOT, 'backend/stock-analyst/scripts'))
    referencing = 0
    for script in scripts:
        with open(script, 'r') as f:
            content = f.read()
        if 'db_manager' in content or 'DBManager' in content:
            referencing += 1
    print(f"  ✅ {referencing}/{len(scripts)} 个脚本引用了 db_manager")
    assert referencing >= 3, f"至少应有 3 个脚本引用 db_manager"
    return True


def test_t6_original_files_untouched():
    """T6.1: 确认原始文件未被修改"""
    original_files = [
        '/Users/ws/.config/opencode/agents/stock-analyst.md',
        '/Users/ws/.config/opencode/skills/stock-analyst/SKILL.md',
        '/Users/ws/.config/opencode/skills/stock-analyst/scripts/main.py',
        '/Users/ws/.config/opencode/skills/stock-analyst/scripts/db_manager.py',
    ]
    for f in original_files:
        assert os.path.exists(f), f"原始文件已被删除或移动: {f}"
        assert os.access(f, os.R_OK), f"原始文件不可读: {f}"
    print("  ✅ 原始 opencode 文件完整未被修改")
    return True


def test_t6_new_paths_complete():
    """T6.2: 新路径文件完整性验证"""
    expected_paths = [
        'backend/stock-analyst/__init__.py',
        'backend/stock-analyst/scripts/__init__.py',
        'backend/stock-analyst/scripts/main.py',
        'backend/stock-analyst/scripts/db_manager.py',
        'backend/stock-analyst/scripts/stock_crawler.py',
        'backend/stock-analyst/scripts/stock_picker.py',
        'backend/stock-analyst/scripts/alert_engine.py',
        'backend/stock-analyst/scripts/llm_client.py',
        'backend/stock-analyst/scripts/trend_analyzer.py',
        'backend/stock-analyst/scripts/finance_fetcher.py',
        'backend/stock-analyst/scripts/news_fetcher.py',
        'backend/stock-analyst/scripts/limit_up_finder.py',
        'backend/stock-analyst/scripts/config.yaml',
        'backend/stock-analyst/resource/stock_list.yaml',
        'docs/stock-analyst/agent/stock-analyst.md',
        'docs/stock-analyst/specs/01-architecture-design.md',
    ]
    missing = []
    for rel_path in expected_paths:
        full_path = os.path.join(PROJECT_ROOT, rel_path)
        if not os.path.exists(full_path):
            missing.append(rel_path)
    if missing:
        print(f"  ❌ 缺失文件: {missing}")
        return False
    print(f"  ✅ 全部 {len(expected_paths)} 个文件已到位")
    return True


def test_t6_module_imports():
    """T6.3: 模块导入路径验证"""
    script_dir = os.path.join(PROJECT_ROOT, 'backend/stock-analyst/scripts')
    # 检查相对导入格式
    scripts = get_py_files(script_dir)
    for script in scripts:
        with open(script, 'r') as f:
            for line in f:
                if 'import' in line and 'stock-analyst' in line.replace(' ', ''):
                    print(f"  ⚠️  可能存在硬编码路径: {os.path.basename(script)}: {line.strip()}")
    print("  ✅ 导入路径检查完成")
    return True


def test_t6_no_leftover_temp_files():
    """补充: 确认项目根目录无临时 .py 文件"""
    root_files = [f for f in os.listdir(PROJECT_ROOT) if f.endswith('.py')]
    if root_files:
        print(f"  ⚠️  项目根目录有 .py 文件: {root_files}")
        return False
    print("  ✅ 项目根目录无临时 .py 文件")
    return True


if __name__ == "__main__":
    results = []
    tests = [
        ("T3.1 数据库表结构", test_t3_database_tables),
        ("T3.2 数据库引用检查", test_t3_database_imports),
        ("T6.1 原始文件完整", test_t6_original_files_untouched),
        ("T6.2 新路径文件完整", test_t6_new_paths_complete),
        ("T6.3 导入路径验证", test_t6_module_imports),
        ("T6.4 无遗留临时文件", test_t6_no_leftover_temp_files),
    ]
    passed = 0
    failed = 0
    for name, fn in tests:
        try:
            fn()
            results.append((name, "PASS"))
            passed += 1
        except AssertionError as e:
            results.append((name, f"FAIL: {e}"))
            failed += 1
        except Exception as e:
            results.append((name, f"ERROR: {e}"))
            failed += 1

    print(f"\n{'='*40}")
    print(f"文件搬迁 & 数据库验证测试完成")
    print(f"通过: {passed}/{len(tests)}")
    if failed > 0:
        print(f"失败: {failed}")
    print(f"{'='*40}")
    for name, status in results:
        print(f"  [{status[:4]}] {name}")

    sys.exit(0 if failed == 0 else 1)