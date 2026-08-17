"""Skill 实现 - 复用现有 stock-analyst 脚本"""
import sys
import subprocess
import json
import sqlite3
import os
from pathlib import Path

# 现有 stock-analyst 路径（支持 STOCK_PROJECT_ROOT 环境变量覆盖）
_IS_FROZEN = hasattr(sys, 'frozen') or hasattr(sys, '_MEIPASS')
_MEIPASS = Path(sys._MEIPASS) if hasattr(sys, '_MEIPASS') else None

if _IS_FROZEN and _MEIPASS:
    _PROJECT_ROOT = _MEIPASS
    SCRIPTS_DIR = _PROJECT_ROOT / "scripts"
    STOCK_LIST_YAML = _PROJECT_ROOT / "resource" / "stock_list.yaml"
else:
    _PROJECT_ROOT = Path(os.environ.get("STOCK_PROJECT_ROOT", str(Path(__file__).parent.parent.parent)))
    SCRIPTS_DIR = _PROJECT_ROOT / "backend" / "stock-analyst" / "scripts"
    STOCK_LIST_YAML = _PROJECT_ROOT / "backend" / "stock-analyst" / "resource" / "stock_list.yaml"

DB_PATH = Path(os.environ.get("STOCK_DB_PATH", str(_PROJECT_ROOT / "backend" / "stock-analyst" / "data" / "stock_data.db")))


def _run_script(script_name: str, *args, timeout: int = 60) -> str:
    """运行 stock-analyst 脚本并返回 stdout"""
    if _IS_FROZEN:
        # PyInstaller 冻结模式：通过 backend-runner script 运行
        cmd = [sys.executable, "script", script_name, *args]
    else:
        # 开发模式：直接 python3 运行
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
    """个股深度分析 - 复用 stock_insight.py"""
    raw = _run_script("stock_insight.py", "--code", code, timeout=120)
    try:
        data = json.loads(raw)
        if "error" in data:
            err = data["error"]
            if "LLM返回格式错误" in err:
                return f"⚠️ {code} 分析暂时不可用：AI 模型返回格式异常，这可能是模型临时问题，请稍后重试或换一只股票。"
            if "超时" in err:
                return f"⏱️ {code} 分析超时（AI 响应较慢），请稍后重试。"
            return f"⚠️ {code} 分析异常: {err}"
        info = data.get("basic_info", {})
        bpa = data.get("buy_point_analysis", {})
        risk = data.get("risk_warning", "")
        dims = data.get("analysis_12dim", {})
        lines = [
            f"## {info.get('name', '?')}（{info.get('code', '?')}）",
            "",
            "| 指标 | 数值 |",
            "|------|------|",
            f"| 价格 | {info.get('price', '?')}元 |",
            f"| 涨跌幅 | {info.get('change_pct', '?')}% |",
            f"| PE | {info.get('pe', '?')} |",
            f"| PB | {info.get('pb', '?')} |",
            "",
        if bpa.get("summary"):
            lines.append("")
            lines.append("**综合判断**: " + str(bpa["summary"]))
        for k, label in [("short_term","短期 (1-4 周)"),("mid_term","中期 (1-3 月)"),("long_term","长期 (6 月+)")]:
            p_ = bpa.get(k) or {}
            if not p_: continue
            lines.append("")
            lines.append("#### " + label)
            lines.append("")
            lines.append("| 字段 | 内容 |")
            lines.append("|------|------|")
            if p_.get("point"):
                lines.append("| **买入信号** | " + str(p_["point"]) + " |")
            pr = p_.get("price_range")
            if isinstance(pr, list) and len(pr) == 2:
                lines.append("| **建议价格区间** | " + str(pr[0]) + " - " + str(pr[1]) + " 元 |")
            if p_.get("confidence"):
                lines.append("| **置信度** | " + str(p_["confidence"]) + " |")
            if p_.get("detail"):
                lines.append("| **详细理由** | " + str(p_["detail"]) + " |")
        ki = bpa.get("key_indicators") or {}
        if ki:
            lines.append("")
            lines.append("#### 关键价位")
            lines.append("")
            lines.append("| 指标 | 价位 |")
            lines.append("|------|------|")
            for kk in ["support_level","resistance_level","stop_loss"]:
                if ki.get(kk) is not None:
                    lines.append("| " + kk + " | **" + str(ki[kk]) + "** 元 |")
        if bpa.get("position_suggestion"):
            lines.append("")
            lines.append("> **建仓建议**: " + str(bpa["position_suggestion"]))
        ]
        if dims:
            lines.append("")
            lines.append("### 12 维分析")
            lines.append("")
            lines.append("| 维度 | 分析内容 |")
            lines.append("|------|----------|")
            for k, v in dims.items():
                if v:
                    short = str(v)[:180].replace("\n", " ")
                    lines.append(f"| **{k}** | {short} |")
        if risk:
            lines.append(f"\n### 风险提示\n\n{risk[:500]}")

        return "\n".join(lines)
    except (json.JSONDecodeError, AttributeError, TypeError, KeyError):
        return raw[:3000]


def analyze_portfolio() -> str:
    """持仓分析 - 读取实际持仓组合，逐个分析并汇总为结构化报告"""
    if not DB_PATH.exists():
        return "错误: 数据库不存在"

    # 1. 读取持仓列表
    portfolio = []
    try:
        conn = sqlite3.connect(str(DB_PATH))
        cursor = conn.execute(
            "SELECT code, name, cost_price, shares, category FROM stock_portfolio WHERE category='持仓' ORDER BY shares DESC"
        )
        for row in cursor.fetchall():
            portfolio.append({"code": row[0], "name": row[1] or row[0], "cost": row[2] or 0, "shares": row[3] or 0})
        conn.close()
    except Exception as e:
        return f"错误: 读取持仓数据失败 - {e}"

    if not portfolio:
        return "⚠️ 尚未配置持仓股票。请在「设置→股票池管理」中添加持仓股。"

    # 2. 逐个分析（限制最多3只，避免整体超时）
    MAX_ANALYZE = 3
    lines = [
        "## 📊 持仓组合分析报告",
        "",
        f"**持仓总览**: 共 {len(portfolio)} 只股票",
        "",
        "| 股票 | 成本价 | 持股数 | 持仓市值 |",
        "|------|--------|--------|----------|",
    ]

    # 获取实时价计算市值
    for stk in portfolio:
        try:
            conn2 = sqlite3.connect(str(DB_PATH))
            r = conn2.execute("SELECT price FROM stock_realtime WHERE code=?", (stk["code"],)).fetchone()
            conn2.close()
            price = r[0] if r else 0
        except:
            price = 0
        market_value = price * stk["shares"]
        stk["price"] = price
        stk["market_value"] = market_value
        lines.append(f"| **{stk['name']}** ({stk['code']}) | {stk['cost']:.2f} | {stk['shares']} | {market_value:.2f} |")

    lines.append("")

    # 3. 对前 N 只执行深度分析
    analyzed_count = 0
    for stk in portfolio[:MAX_ANALYZE]:
        lines.append(f"---")
        lines.append(f"### 🔍 {stk['name']}（{stk['code']}）深度分析")
        lines.append("")

        try:
            raw = _run_script("portfolio_analysis.py", stk["code"], timeout=120)
            data = json.loads(raw)
            if "error" in data:
                lines.append(f"⚠️ 分析失败: {data['error']}")
                continue

            # 总体操作建议
            overall = data.get("overall_action", "持有")
            lines.append(f"**总体建议**: {overall}")
            lines.append("")

            # 短/中/长期
            for period_key, period_label in [("short_term", "短期 (1-4周)"), ("mid_term", "中期 (1-3月)"), ("long_term", "长期 (6月+)")]:
                p = data.get(period_key, {})
                if not p:
                    continue
                action = p.get("action", "")
                lines.append(f"#### {period_label} — **{action}**")
                lines.append("")
                # 表格展示详细字段
                items = []
                if p.get("holding_period"):
                    items.append(("建议持有周期", p["holding_period"]))
                if p.get("percent"):
                    items.append(("操作比例", f"{p['percent']}%" if p['action'] in ('加仓','减仓') else "-"))
                if p.get("entry_condition"):
                    items.append(("进场条件", p["entry_condition"]))
                if p.get("price_target"):
                    items.append(("目标价区间", f"{p['price_target'][0]} - {p['price_target'][1]}"))
                if p.get("stop_loss"):
                    items.append(("止损位", p["stop_loss"]))
                if p.get("pullback_level"):
                    items.append(("回调预期", p["pullback_level"]))
                if p.get("key_risk"):
                    items.append(("核心风险", p["key_risk"]))
                if p.get("catalyst"):
                    items.append(("催化因素", p["catalyst"]))
                if p.get("reason"):
                    items.append(("综合理由", p["reason"]))
                if items:
                    for label, value in items:
                        lines.append(f"- **{label}**: {value}")
                    lines.append("")

            # 关键价位
            support = data.get("support")
            resistance = data.get("resistance")
            stop_loss = data.get("stop_loss")
            if support or resistance or stop_loss:
                lines.append("#### 关键价位")
                lines.append(f"- **支撑位**: {support}" if support else "")
                lines.append(f"- **阻力位**: {resistance}" if resistance else "")
                lines.append(f"- **止损位**: {stop_loss}" if stop_loss else "")
                lines.append("")

            analyzed_count += 1

        except json.JSONDecodeError:
            lines.append(f"⚠️ 分析数据格式异常（LLM 返回非 JSON）")
            lines.append("")
        except subprocess.TimeoutExpired:
            lines.append(f"⚠️ 分析超时（超过 120 秒）")
            lines.append("")
        except Exception as e:
            lines.append(f"⚠️ 分析异常: {e}")
            lines.append("")

    # 4. 未深度分析的股票
    remaining = portfolio[MAX_ANALYZE:]
    if remaining:
        lines.append("---")
        lines.append(f"### 📋 其他持仓")
        lines.append("")
        for stk in remaining:
            lines.append(f"- **{stk['name']}**（{stk['code']}）: 当前价 {stk.get('price', 'N/A')}")

    lines.append("")
    lines.append("---")
    lines.append("*以上分析基于公开行情数据，不构成投资建议。投资有风险，决策需谨慎。*")

    return "\n".join(lines)


def recommend_candidates() -> str:
    """候选推荐 - 复用 candidate_recommend.py"""
    return _run_script("candidate_recommend.py", timeout=180)


def analyze_market() -> str:
    """大盘分析 - 基于 stock_realtime + stock_fund_flow 聚合

    已知问题：stock_realtime 表中 code 字段都是股票代码（如 000001=平安银行），
    不包含大盘指数（000001.SH/399001.SZ/399006.SZ）且表结构无 type 列区分。
    因此本函数只输出 A 股市场的聚合统计（涨跌停、资金净流入），
    不输出具体指数点位（如需指数数据，请单独接入指数行情源）。
    """
    if not DB_PATH.exists():
        return "错误: 数据库不存在"

    conn = sqlite3.connect(str(DB_PATH))
    try:
        # 涨跌停统计（基于全市场 stock_realtime）
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
        lines.append("> 注：大盘指数点位（上证指数/深证成指/创业板指）需单独接入指数行情源，"
                     "本表（stock_realtime）只存储个股实时数据。\n")

        if up_down and up_down[2] and up_down[2] > 0:
            lines.append(f"**涨跌停**: 涨停 {up_down[0] or 0} / 跌停 {up_down[1] or 0} / 总 {up_down[2]}")

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
