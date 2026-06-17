import sqlite3
import json
from datetime import datetime

def build_suggestion(score):
    if score >= 80:
        return "买入", "低"
    elif score >= 65:
        return "增持", "中低"
    elif score >= 50:
        return "持有", "中"
    elif score >= 35:
        return "减持", "中高"
    else:
        return "卖出", "高"

def calc_technical_score(indicators_json):
    try:
        ind = json.loads(indicators_json) if isinstance(indicators_json, str) else indicators_json
    except Exception:
        return 0

    score = 0
    macd = ind.get("histogram", 0)
    if macd > 0:
        score += 12
    rsi = ind.get("rsi14", 50)
    if 30 <= rsi <= 70:
        score += 10
    elif rsi < 30:
        score += 8
    k = ind.get("k", 50)
    if k < 30:
        score += 8
    price = ind.get("close", 0)
    middle = ind.get("middle_band", 0)
    upper = ind.get("upper_band", 0)
    lower = ind.get("lower_band", 0)
    if middle > 0 and price > middle:
        score += 10
    if lower > 0 and price <= lower + (upper - lower) * 0.1:
        score += 6
    obv = ind.get("obv", 0)
    if obv > 0:
        score += 4
    return min(score, 40)

def calc_fundamental_score(realtime_row, finance_rows):
    score = 0
    if realtime_row:
        pe = realtime_row.get("pe", 0) or 0
        if 0 < pe <= 50:
            score += 12
        elif pe <= 100:
            score += 6
        pb = realtime_row.get("pb", 0) or 0
        if 0 < pb <= 5:
            score += 8
        elif pb <= 10:
            score += 4
    if finance_rows:
        fr = finance_rows[0]
        roe = fr.get("roe", 0) or 0
        if roe > 0.15:
            score += 15
        elif roe > 0.08:
            score += 10
        elif roe > 0.05:
            score += 5
        rev = fr.get("revenue", 0) or 0
        profit = fr.get("profit", 0) or 0
        eps = fr.get("eps", 0) or 0
        if profit > 0:
            score += 5
        if eps > 0:
            score += 5
    return min(score, 50)

def calc_trend_score(code, db_path):
    score = 5
    try:
        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        rows = c.execute(
            "SELECT close, change_pct, volume FROM stock_history WHERE code=? ORDER BY trade_date DESC LIMIT 20",
            (code,)
        ).fetchall()
        if len(rows) >= 5:
            recent = rows[:5]
            up_days = sum(1 for r in recent if r[1] and r[1] > 0)
            score += up_days * 2
            avg_vol_20 = sum(r[2] or 0 for r in rows) / max(len(rows), 1)
            avg_vol_5 = sum(r[2] or 0 for r in recent) / 5
            if avg_vol_20 > 0 and avg_vol_5 > avg_vol_20 * 1.3:
                score += 4
            closes = [r[0] or 0 for r in rows[:5]]
            if len(closes) >= 3 and closes[0] > closes[-1]:
                score += 3
        conn.close()
    except Exception:
        pass
    return min(score, 10)

def score_stock(code, db_path):
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    tech_row = c.execute(
        "SELECT indicators_json FROM stock_technical WHERE code=? ORDER BY created_at DESC LIMIT 1",
        (code,)
    ).fetchone()
    realtime_row = c.execute(
        "SELECT pe, pb FROM stock_realtime WHERE code=?", (code,)
    ).fetchone()
    finance_rows = c.execute(
        "SELECT roe, revenue, profit, eps FROM stock_finance WHERE code=? ORDER BY report_date DESC LIMIT 1",
        (code,)
    ).fetchone()
    conn.close()

    tech_score = calc_technical_score(tech_row[0] if tech_row else "{}")
    rt = {"pe": realtime_row[0], "pb": realtime_row[1]} if realtime_row else {}
    fr = [{"roe": finance_rows[0], "revenue": finance_rows[1], "profit": finance_rows[2], "eps": finance_rows[3]}] if finance_rows else []
    fund_score = calc_fundamental_score(rt, fr)
    trend_score = calc_trend_score(code, db_path)

    total = tech_score + fund_score + trend_score
    suggestion, risk = build_suggestion(total)
    return {
        "code": code,
        "score": total,
        "suggestion": suggestion,
        "risk_level": risk,
        "tech_score": tech_score,
        "fund_score": fund_score,
        "trend_score": trend_score,
    }

def score_all_stocks(db_path, codes):
    results = []
    for code in codes:
        try:
            result = score_stock(code, db_path)
            results.append(result)
        except Exception as e:
            print(f"评分异常 {code}: {e}")
    return results

def save_scores(db_path, scores):
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    c.execute('''CREATE TABLE IF NOT EXISTS stock_score (
        code TEXT PRIMARY KEY, score INTEGER, suggestion TEXT,
        risk_level TEXT, tech_score INTEGER DEFAULT 0,
        fund_score INTEGER DEFAULT 0, trend_score INTEGER DEFAULT 0,
        updated_at TEXT
    )''')
    for s in scores:
        c.execute(
            "INSERT OR REPLACE INTO stock_score (code, score, suggestion, risk_level, tech_score, fund_score, trend_score, updated_at) VALUES (?,?,?,?,?,?,?,?)",
            (s["code"], s["score"], s["suggestion"], s["risk_level"],
             s["tech_score"], s["fund_score"], s["trend_score"], now)
        )
    conn.commit()
    conn.close()

def run_scoring(db_path, codes):
    scores = score_all_stocks(db_path, codes)
    save_scores(db_path, scores)
    return scores