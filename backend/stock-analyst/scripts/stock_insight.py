#!/usr/bin/env python3
import json
import sys
import os
import argparse
import contextlib

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from db_manager import DBManager
from llm_client import LLMClient
from stock_crawler import StockCrawler

DB_PATH = os.environ.get("STOCK_DB_PATH") or os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "stock_data.db")


def refresh_live_data(db, code):
    crawler = StockCrawler()
    realtime = crawler.get_realtime(code)
    if realtime and realtime.get("price", 0) > 0:
        # db_manager.insert_realtime 期望 list[dict] 入参
        db.insert_realtime([realtime])
        sys.stderr.write(f"[data] realtime refreshed: {realtime.get('name')} @ {realtime.get('price')}\n")
    fund = crawler.get_fund_flow(code)
    if fund:
        # db_manager.insert_fund_flow 同样期望 list[dict] 入参
        db.insert_fund_flow([fund])
        sys.stderr.write(f"[data] fund flow refreshed: {fund.get('main_inflow', 0)}\n")

    try:
        import baostock as bs
        # baostock 向 stdout 输出 login/logout 信息，重定向到 stderr 避免污染 JSON
        with contextlib.redirect_stdout(sys.stderr):
            lg = bs.login()
            if lg.error_code == '0':
                bs_code = f"sh.{code}" if code.startswith('6') else f"sz.{code}"

                report_date = ""

                # Profit data: ROE, EPS, netProfit, MBRevenue
                rs = bs.query_profit_data(code=bs_code, year='2025', quarter='1')
                roe = eps = profit = revenue = 0
                if rs.error_code == '0' and rs.next():
                    row = rs.get_row_data()
                    roe = float(row[3] or 0)
                    eps = float(row[4] or 0)
                    profit = float(row[6] or 0)
                    revenue = float(row[8] or 0) if row[8] else 0
                    report_date = row[2] or ""

                # Balance data: BPS (每股净资产) → compute PB = price / BPS
                bvps = 0
                rs2 = bs.query_balance_data(code=bs_code, year='2025', quarter='1')
                if rs2.error_code == '0' and rs2.next():
                    row = rs2.get_row_data()
                    bvps = float(row[8] or 0)
                    if not report_date:
                        report_date = row[2] or ""

                sys.stderr.write(f"[data] finance refreshed: ROE={roe:.2%} rev={revenue:.0f} profit={profit:.0f} bvps={bvps}\n")
                conn = __import__('sqlite3').connect(db.db_path)
                c = conn.cursor()

                # Store financial data
                c.execute('''INSERT OR REPLACE INTO stock_finance
                    (code, roe, revenue, profit, eps, bvps, report_date)
                    VALUES (?, ?, ?, ?, ?, ?, ?)''',
                    (code, roe, revenue, profit, eps, bvps, report_date))

                # Delete old garbage finance rows (roe=eps=0 from finance_fetcher)
                c.execute("DELETE FROM stock_finance WHERE code=? AND roe=0 AND eps=0 AND report_date!=?", (code, report_date))

                # Compute PB from BVPS and update stock_realtime
                if bvps > 0 and realtime and realtime.get('price', 0) > 0:
                    pb = round(realtime['price'] / bvps, 2)
                    c.execute("UPDATE stock_realtime SET pb=? WHERE code=?", (pb, code))
                    sys.stderr.write(f"[data] PB computed: {pb} (price={realtime['price']}, bvps={bvps})\n")

                conn.commit()
                conn.close()
                bs.logout()
    except Exception as e:
        sys.stderr.write(f"[data] finance refresh skipped: {e}\n")


def collect_stock_data(db, code):
    conn = __import__('sqlite3').connect(db.db_path)
    c = conn.cursor()
    item = {"code": code, "name": "", "price": 0, "change_pct": 0, "pe": 0, "pb": 0,
            "roe": 0, "revenue": 0, "profit": 0, "eps": 0, "bvps": 0,
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
        item["revenue"] = float(row[1] or 0)
        item["profit"] = float(row[2] or 0)
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
    item["news"] = [r[0] for r in c.fetchall()]

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

    conn.close()
    return item


def extract_json(text):
    text = text.strip()
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
        text = "\n".join(lines[start:end])
    return text.strip()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--code", required=True)
    args = parser.parse_args()

    db = DBManager(DB_PATH)
    refresh_live_data(db, args.code)
    data = collect_stock_data(db, args.code)

    if not data["name"]:
        print(json.dumps({"error": f"未找到股票 {args.code}"}, ensure_ascii=False))
        return

    prompt_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "ai", "prompts", "stock_insight.md")
    system_prompt = ""
    if os.path.exists(prompt_path):
        with open(prompt_path, "r") as f:
            system_prompt = f.read()

    client = LLMClient()
    user_message = json.dumps({"stock": data}, ensure_ascii=False, indent=2)

    # 支持重试：最大 3 次，遇到 429 限流时等待后重试
    max_retries = 3
    response = None
    error = None
    for attempt in range(max_retries):
        response, error = client.chat(user_message, system_prompt=system_prompt, max_tokens=16000, json_mode=True)
        if error and "429" in error:
            sys.stderr.write(f"[retry] Rate limited (429), attempt {attempt+1}/{max_retries}, waiting...\n")
            import time
            time.sleep(5 * (attempt + 1))
            continue
        break

    if error:
        print(json.dumps({"error": error}, ensure_ascii=False))
        return

    if not response:
        print(json.dumps({"error": "LLM返回为空"}, ensure_ascii=False))
        return

    cleaned = extract_json(response)
    try:
        result = json.loads(cleaned)
        result["basic_info"] = {
            "code": data["code"],
            "name": data["name"],
            "industry": data["industry"],
            "price": data["price"],
            "change_pct": data["change_pct"],
            "pe": data["pe"],
            "pb": data["pb"],
        }
        print(json.dumps(result, ensure_ascii=False))
    except json.JSONDecodeError:
        print(json.dumps({"error": "LLM返回格式错误", "raw": response, "extracted": cleaned}, ensure_ascii=False))


if __name__ == "__main__":
    main()