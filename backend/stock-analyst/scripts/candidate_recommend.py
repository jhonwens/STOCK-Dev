#!/usr/bin/env python3
import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from db_manager import DBManager
from llm_client import LLMClient

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "stock_data.db")


def load_stock_pool(db):
    candidates = []
    seen = set()
    yaml_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "resource", "stock_list.yaml")
    if os.path.exists(yaml_path):
        import yaml
        with open(yaml_path, "r") as f:
            data = yaml.safe_load(f)
        for s in data.get("stocks", []):
            code = s.get("code", "")
            if code:
                seen.add(code)
                candidates.append({"code": code, "name": s.get("name", ""), "industry": s.get("industry", "")})
    return candidates, seen


def get_held_codes(db):
    conn = __import__('sqlite3').connect(db.db_path)
    c = conn.cursor()
    c.execute("SELECT code FROM stock_portfolio WHERE category='持仓'")
    held = {r[0] for r in c.fetchall()}
    conn.close()
    return held


def collect_candidate_data(db, codes):
    conn = __import__('sqlite3').connect(db.db_path)
    c = conn.cursor()
    results = []
    for code in codes[:20]:
        item = {"code": code, "name": "", "price": 0, "change_pct": 0, "pe": 0, "pb": 0,
                "roe": 0, "revenue_growth": 0, "profit_growth": 0, "eps": 0, "bvps": 0,
                "technical_score": 0, "technical_detail": {}, "main_inflow": 0,
                "institutional_holding_change": 0, "news": [], "industry": "",
                "industry_trend": "", "risk_beta": 0, "volatility": 0, "max_drawdown": 0,
                "fair_price_range": [0, 0], "catalysts": []}

        c.execute("SELECT name, price, change_pct, pe, pb FROM stock_realtime WHERE code=? LIMIT 1", (code,))
        row = c.fetchone()
        if row:
            item["name"] = row[0] or ""
            item["price"] = float(row[1] or 0)
            item["change_pct"] = float(row[2] or 0)
            item["pe"] = float(row[3] or 0)
            item["pb"] = float(row[4] or 0)

        c.execute("SELECT roe, revenue, profit, eps, bvps FROM stock_finance WHERE code=? ORDER BY report_date DESC LIMIT 1", (code,))
        row = c.fetchone()
        if row:
            item["roe"] = float(row[0] or 0)
            item["revenue_growth"] = float(row[1] or 0)
            item["profit_growth"] = float(row[2] or 0)
            item["eps"] = float(row[3] or 0)
            item["bvps"] = float(row[4] or 0)

        c.execute("SELECT indicators_json FROM stock_technical WHERE code=? ORDER BY created_at DESC LIMIT 1", (code,))
        row = c.fetchone()
        if row:
            try:
                tech = json.loads(row[0])
                item["technical_score"] = tech.get("composite_score", 0)
                item["technical_detail"] = {k: v for k, v in tech.items() if k != "composite_score"}
            except:
                pass

        c.execute("SELECT main_inflow FROM stock_fund_flow WHERE code=? ORDER BY update_date DESC LIMIT 1", (code,))
        row = c.fetchone()
        if row:
            item["main_inflow"] = float(row[0] or 0)

        c.execute("SELECT title FROM stock_news WHERE code=? ORDER BY publish_date DESC LIMIT 5", (code,))
        news_rows = c.fetchall()
        item["news"] = [r[0] for r in news_rows]

        c.execute("SELECT rev_growth, profit_growth, trend_signal FROM stock_trend WHERE code=? LIMIT 1", (code,))
        row = c.fetchone()
        if row:
            item["industry_trend"] = row[2] or ""

        prices = []
        c.execute("SELECT close FROM stock_history WHERE code=? ORDER BY trade_date DESC LIMIT 250", (code,))
        history = c.fetchall()
        if len(history) > 20:
            prices = [float(r[0]) for r in history]
            mean_p = sum(prices) / len(prices)
            variance = sum((p - mean_p) ** 2 for p in prices) / len(prices)
            item["volatility"] = round(variance ** 0.5 / mean_p, 4) if mean_p > 0 else 0
            item["max_drawdown"] = round(
                max((max(prices[:i+1]) - prices[i]) / max(prices[:i+1]) for i in range(1, len(prices))), 4
            ) if prices else 0

        results.append(item)

    conn.close()
    return results


def extract_json(text):
    """从 LLM 返回中提取 JSON。容忍多种格式：
    1. 纯 JSON
    2. ```json ... ``` 代码块
    3. ``` ... ``` 任意代码块
    4. 嵌入在中文文本中的 JSON（用花括号定位）
    提取失败返回空字符串，让上层走错误处理。
    """
    text = text.strip()
    if not text:
        return ""

    # 1. 剥代码块（```json ... ``` 或 ``` ... ```）
    if text.startswith("```"):
        lines = text.split("\n")
        start = 0
        for i, line in enumerate(lines):
            if line.strip().startswith("```"):
                start = i + 1
                break
        end = len(lines)
        for i in range(len(lines) - 1, start - 1, -1):
            if lines[i].strip().startswith("```"):
                end = i
                break
        text = "\n".join(lines[start:end]).strip()

    # 2. 如果首字符是 { 或 [，尝试直接解析
    if text.startswith(("{", "[")):
        return text

    # 3. 嵌入文本：找最外层 { ... } 块
    first = text.find("{")
    last = text.rfind("}")
    if first != -1 and last != -1 and last > first:
        candidate = text[first:last + 1]
        return candidate

    return ""


def main():
    db = DBManager(DB_PATH)
    candidates, all_codes = load_stock_pool(db)
    held_codes = get_held_codes(db)
    filtered = [c for c in candidates if c["code"] not in held_codes]
    codes_to_analyze = [c["code"] for c in filtered]

    if not codes_to_analyze:
        print(json.dumps({"error": "没有可供分析的候选股票"}))
        return

    data = collect_candidate_data(db, codes_to_analyze)

    prompt_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "ai", "prompts", "candidate_recommend.md")
    system_prompt = ""
    if os.path.exists(prompt_path):
        with open(prompt_path, "r") as f:
            system_prompt = f.read()

    client = LLMClient()
    user_message = json.dumps({"candidates": data}, ensure_ascii=False, indent=2)
    # max_tokens=16000: 5 短期 + 5 长期 = 10 股票 × 12 维度 ≈ 12000+ tokens
    # json_mode=True: 强制 LLM 输出合法 JSON（Qwen/DeepSeek/OpenAI 都支持）
    response, error = client.chat(
        user_message,
        system_prompt=system_prompt,
        max_tokens=16000,
        json_mode=True,
    )

    if error:
        print(json.dumps({"error": error}, ensure_ascii=False))
        return

    cleaned = extract_json(response)
    if not cleaned:
        print(json.dumps({
            "error": "LLM 未返回 JSON 内容",
            "raw_preview": response[:200] if response else "(空)"
        }, ensure_ascii=False))
        return
    try:
        result = json.loads(cleaned)
        print(json.dumps(result, ensure_ascii=False))
    except json.JSONDecodeError as e:
        print(json.dumps({
            "error": f"LLM 返回的 JSON 解析失败: {e}",
            "raw_preview": response[:200]
        }, ensure_ascii=False))


if __name__ == "__main__":
    main()