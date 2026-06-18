"""Skill 实现 - 复用现有 stock-analyst 脚本"""
import sys
import subprocess
import json
import sqlite3
import os
from pathlib import Path

# 现有 stock-analyst 路径
SCRIPTS_DIR = Path(__file__).parent.parent / "stock-analyst" / "scripts"
DB_PATH = Path(__file__).parent.parent / "stock-analyst" / "data" / "stock_data.db"
STOCK_LIST_YAML = Path(__file__).parent.parent / "stock-analyst" / "resource" / "stock_list.yaml"


def _run_script(script_name: str, *args, timeout: int = 60) -> str:
    """运行 stock-analyst 脚本并返回 stdout"""
    cmd = ["python3", str(SCRIPTS_DIR / script_name), *args]
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout, check=True
        )
        return result.stdout
    except subprocess.CalledProcessError as e:
        return f"Script error: {e.stderr}"
    except subprocess.TimeoutExpired:
        return f"Script timeout ({timeout}s)"
    except FileNotFoundError:
        return f"Script not found: {script_name}"


def _search_stock_db(query: str) -> list:
    """直接通过 SQLite 搜索股票（search_stock.py 不存在，回退到 DB）"""
    if not DB_PATH.exists():
        return []
    conn = sqlite3.connect(str(DB_PATH))
    try:
        cursor = conn.execute(
            """SELECT code, name FROM stock_realtime
               WHERE code = ? OR name LIKE ?
               ORDER BY code LIMIT 10""",
            (query, f"%{query}%"),
        )
        return [{"code": r[0], "name": r[1]} for r in cursor.fetchall()]
    finally:
        conn.close()


def search_stock(query: str) -> str:
    """查询股票 - 直接查询 SQLite（search_stock.py 不存在）"""
    results = _search_stock_db(query)
    if not results:
        return f"未找到股票: {query}"
    # 取前 3 个
    lines = [f"找到 {len(results)} 只相关股票（前 3 只）："]
    for r in results[:3]:
        lines.append(f"- {r.get('code', '?')} {r.get('name', '?')}")
    return "\n".join(lines)


def analyze_stock(code: str) -> str:
    """个股深度分析 - 复用 stock_insight.py（run_stock_insight.py 不存在）"""
    return _run_script("stock_insight.py", code, timeout=120)


def analyze_portfolio() -> str:
    """持仓分析 - 复用 portfolio_analysis.py"""
    return _run_script("portfolio_analysis.py", timeout=120)


def recommend_candidates() -> str:
    """候选推荐 - 复用 candidate_recommend.py"""
    return _run_script("candidate_recommend.py", timeout=180)


def analyze_market() -> str:
    """大盘分析 - 基于 stock_realtime + stock_fund_flow 聚合"""
    if not DB_PATH.exists():
        return "错误: 数据库不存在"

    conn = sqlite3.connect(str(DB_PATH))
    try:
        # 大盘指数（用 plan 中的代码：000001/399001/399006，注：000001 实际是平安银行）
        cursor = conn.execute("""
            SELECT code, name, price, change_pct
            FROM stock_realtime
            WHERE code IN ('000001', '399001', '399006')
            ORDER BY code
        """)
        indices = cursor.fetchall()

        # 涨跌停统计
        cursor = conn.execute("""
            SELECT
                SUM(CASE WHEN change_pct > 9.5 THEN 1 ELSE 0 END) as limit_up,
                SUM(CASE WHEN change_pct < -9.5 THEN 1 ELSE 0 END) as limit_down,
                COUNT(*) as total
            FROM stock_realtime
        """)
        up_down = cursor.fetchone()

        # 资金净流入（修正：表用 main_inflow 和 update_date）
        cursor = conn.execute("""
            SELECT SUM(main_inflow) as total_inflow
            FROM stock_fund_flow
            WHERE update_date = (SELECT MAX(update_date) FROM stock_fund_flow)
        """)
        inflow = cursor.fetchone()

        lines = ["## A 股大盘概况"]
        for code, name, price, pct in indices:
            lines.append(f"- **{name}** ({code}): {price:.2f} ({pct:+.2f}%)")

        if up_down and up_down[2] and up_down[2] > 0:
            lines.append(f"\n**涨跌停**: 涨停 {up_down[0] or 0} / 跌停 {up_down[1] or 0} / 总 {up_down[2]}")

        if inflow and inflow[0] is not None:
            lines.append(f"**资金净流入**: {inflow[0]:.2f} 元")

        return "\n".join(lines)
    finally:
        conn.close()


def _load_stock_list_yaml() -> list:
    """加载 stock_list.yaml（plan 中 stock_list 表不存在，回退到 YAML）"""
    if not STOCK_LIST_YAML.exists():
        return []
    try:
        import yaml
        with open(STOCK_LIST_YAML, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        return data.get("stocks", [])
    except Exception:
        return []


def analyze_industry(industry_name: str) -> str:
    """行业分析 - 基于 stock_list.yaml + stock_realtime + stock_finance 聚合"""
    if not DB_PATH.exists():
        return "错误: 数据库不存在"

    # 从 YAML 找行业相关股票（plan 中 stock_list 表不存在）
    stocks_meta = _load_stock_list_yaml()
    matched = [s for s in stocks_meta if industry_name in (s.get("industry") or "")][:10]

    if not matched:
        return f"未找到行业: {industry_name}"

    conn = sqlite3.connect(str(DB_PATH))
    try:
        codes = [s["code"] for s in matched]
        placeholders = ",".join("?" * len(codes))

        # pe/pb 来自 stock_realtime
        cursor = conn.execute(
            f"""SELECT code, pe, pb FROM stock_realtime
                WHERE code IN ({placeholders})""",
            codes,
        )
        rt_data = {row[0]: row for row in cursor.fetchall()}

        # roe 来自 stock_finance
        cursor = conn.execute(
            f"""SELECT code, roe FROM stock_finance
                WHERE code IN ({placeholders})""",
            codes,
        )
        fin_data = {row[0]: row for row in cursor.fetchall()}

        lines = [f"## {industry_name} 行业分析（{len(matched)} 只相关股票）"]
        for s in matched:
            code = s["code"]
            name = s["name"]
            rt_row = rt_data.get(code)
            fin_row = fin_data.get(code)
            pe = rt_row[1] if rt_row else None
            pb = rt_row[2] if rt_row else None
            roe = fin_row[1] if fin_row else None

            pe_s = f"PE={pe:.1f}" if isinstance(pe, (int, float)) and pe else "PE=?"
            pb_s = f"PB={pb:.1f}" if isinstance(pb, (int, float)) and pb else "PB=?"
            roe_s = f"ROE={roe:.1f}%" if isinstance(roe, (int, float)) and roe else "ROE=?"
            lines.append(f"- **{name}** ({code}): {pe_s}, {pb_s}, {roe_s}")

        return "\n".join(lines)
    finally:
        conn.close()
