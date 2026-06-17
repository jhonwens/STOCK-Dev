import sys
import os
import json
import ast
import sqlite3
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from llm_client import LLMClient

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), '../data/stock_data.db')

def compute_ma(closes, period):
    if len(closes) < period:
        return None
    return round(sum(closes[:period]) / period, 2)

def query_stock_data(code):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    realtime = c.execute(
        "SELECT price, change_pct, volume, amount, turnover, pe, pb FROM stock_realtime WHERE code=?",
        (code,)
    ).fetchone()
    history = c.execute(
        "SELECT trade_date, close, volume, high, low FROM stock_history WHERE code=? ORDER BY trade_date DESC LIMIT 30",
        (code,)
    ).fetchall()
    technical = c.execute(
        "SELECT indicators_json FROM stock_technical WHERE code=? ORDER BY created_at DESC LIMIT 1",
        (code,)
    ).fetchone()
    fund_flow = c.execute(
        "SELECT main_inflow FROM stock_fund_flow WHERE code=?", (code,)
    ).fetchone()
    limit_up = c.execute(
        "SELECT COUNT(*) FROM stock_limit_up WHERE code=? AND limit_date >= date('now', '-20 days')",
        (code,)
    ).fetchone()
    news = c.execute(
        "SELECT title, publish_date FROM stock_news WHERE code=? ORDER BY publish_date DESC LIMIT 5",
        (code,)
    ).fetchall()
    name = c.execute("SELECT name FROM stock_realtime WHERE code=?", (code,)).fetchone()
    conn.close()

    closes = [r[1] for r in history if r[1]]
    volumes = [r[2] or 0 for r in history if r[2]]
    highs = [r[3] or 0 for r in history if r[3]]
    lows = [r[4] or 0 for r in history if r[4]]

    ma5 = compute_ma(closes, 5)
    ma10 = compute_ma(closes, 10)
    ma20 = compute_ma(closes, 20)
    last_price = realtime[0] if realtime else (closes[0] if closes else 0)
    turnover = realtime[4] if realtime and realtime[4] else 0

    avg_vol_5 = sum(volumes[:5]) / max(len(volumes[:5]), 1)
    avg_vol_20 = sum(volumes[:20]) / max(len(volumes[:20]), 1)
    vol_ratio = round(avg_vol_5 / max(avg_vol_20, 1), 2) if avg_vol_20 > 0 else 0
    limit_up_count = limit_up[0] if limit_up else 0
    main_inflow = fund_flow[0] if fund_flow else None
    indicators = ast.literal_eval(technical[0]) if technical and technical[0] else {}
    stock_name = name[0] if name else code

    price_change = realtime[1] if realtime else 0
    volume_val = realtime[2] or 0 if realtime else 0

    prev_5_closes = closes[:5] if len(closes) >= 5 else closes
    ma5_trend = "上升"
    if len(prev_5_closes) >= 3:
        if prev_5_closes[0] < prev_5_closes[-1]:
            ma5_trend = "下降"
        elif prev_5_closes[0] == prev_5_closes[-1]:
            ma5_trend = "持平"

    price_above_ma5 = last_price > ma5 if ma5 else None
    price_above_ma20 = last_price > ma20 if ma20 else None
    volume_surge = vol_ratio > 1.3

    EMAs = {k: indicators.get(k) for k in ["ema20", "ema60", "ema120"]}
    macd_data = indicators.get("macd", {})
    macd_dif = macd_data.get("DIF", 0)
    macd_dea = macd_data.get("DEA", 0)
    histogram = macd_data.get("hist", 0)
    macd_golden = macd_data.get("golden_cross", False)
    macd_death = macd_data.get("death_cross", False)
    macd_above_zero = macd_data.get("above_zero", False)
    kdj_data = indicators.get("kdj", {})
    k = kdj_data.get("K", 50)
    d_val = kdj_data.get("D", 50)
    j = kdj_data.get("J", 50)
    kdj_golden = kdj_data.get("golden_cross", False)
    rsi_data = indicators.get("rsi", {})
    rsi14 = rsi_data.get("RSI", 50)
    rsi_overbought = rsi_data.get("overbought", False)
    rsi_oversold = rsi_data.get("oversold", False)
    boll_data = indicators.get("boll", {})
    upper_band = boll_data.get("upper", 0)
    middle_band = boll_data.get("mid", 0)
    lower_band = boll_data.get("lower", 0)
    boll_position = boll_data.get("position", "inside")
    obv_data = indicators.get("obv", {})
    obv_value = obv_data.get("OBV", 0)
    obv_trend = obv_data.get("trend", "unknown")

    red_candles = sum(1 for r in history[:5] if r[1] and r[1] >= (r[3] or r[1]))
    total_vol_5 = sum(r[2] or 0 for r in history[:5])
    avg_candle_vol = total_vol_5 / max(len(history[:5]), 1)

    red_green_ratio_text = "红肥绿瘦" if red_candles >= 3 else "绿肥红瘦"

    return {
        "code": code,
        "name": stock_name,
        "price": last_price,
        "change_pct": price_change,
        "volume": volume_val,
        "turnover": turnover,
        "pe": realtime[5] if realtime else None,
        "pb": realtime[6] if realtime else None,
        "ma5": ma5,
        "ma10": ma10,
        "ma20": ma20,
        "ma5_trend": ma5_trend,
        "price_above_ma5": price_above_ma5,
        "price_above_ma20": price_above_ma20,
        "avg_vol_5": int(avg_vol_5),
        "avg_vol_20": int(avg_vol_20),
        "vol_ratio": vol_ratio,
        "volume_surge": volume_surge,
        "limit_up_count_20d": limit_up_count,
        "main_inflow": main_inflow,
        "red_green_ratio": red_green_ratio_text,
        "red_candles_5d": red_candles,
        "indicators": {
            "macd_dif": macd_dif,
            "macd_dea": macd_dea,
            "histogram": histogram,
            "macd_golden": macd_golden,
            "macd_death": macd_death,
            "macd_above_zero": macd_above_zero,
            "rsi14": rsi14,
            "rsi_overbought": rsi_overbought,
            "rsi_oversold": rsi_oversold,
            "k": k,
            "d": d_val,
            "j": j,
            "kdj_golden": kdj_golden,
            "upper_band": upper_band,
            "middle_band": middle_band,
            "lower_band": lower_band,
            "boll_position": boll_position,
            "obv_value": obv_value,
            "obv_trend": obv_trend,
            "ema20": EMAs.get("ema20"),
            "ema60": EMAs.get("ema60"),
            "ema120": EMAs.get("ema120"),
        },
        "news": [{"title": n[0], "date": n[1]} for n in news] if news else [],
    }

def run_analysis(code):
    data = query_stock_data(code)

    prompt = f"""你是专业的A股投资分析师。请对股票 **{data['name']}（{data['code']}）** 进行分析，输出**最精简的操作建议**。

## 实时行情数据
- 最新价: {data['price']}
- 涨跌幅: {data['change_pct']}%
- PE: {data['pe']}, PB: {data['pb']}

## 均线数据
- MA5: {data['ma5']}（趋势:{data['ma5_trend']}）
- MA10: {data['ma10']}
- MA20: {data['ma20']}
- 价格在MA5上方: {'是' if data['price_above_ma5'] else '否'}
- 价格在MA20上方: {'是' if data['price_above_ma20'] else '否'}

## 技术指标
- MACD DIF: {data['indicators']['macd_dif']}, DEA: {data['indicators']['macd_dea']}, 柱状图: {data['indicators']['histogram']}
- MACD金叉: {'是' if data['indicators']['macd_golden'] else '否'}, 死叉: {'是' if data['indicators']['macd_death'] else '否'}
- RSI(14): {data['indicators']['rsi14']}
- KDJ: K={data['indicators']['k']}, D={data['indicators']['d']}, J={data['indicators']['j']}
- KDJ金叉: {'是' if data['indicators']['kdj_golden'] else '否'}
- BOLL中轨: {data['indicators']['middle_band']}
- 当前价相对BOLL中轨位置: {'上方' if data['price'] > data['indicators']['middle_band'] else '下方'}
- OBV趋势: {data['indicators']['obv_trend']}

## 量能分析
- 量比: {data['vol_ratio']}
- 量能放大: {'是' if data['volume_surge'] else '否'}
- K线形态(5日): {data['red_green_ratio']}
- 20日涨停次数: {data['limit_up_count_20d']}次

## 资金流向
- 主力净流入: {data['main_inflow'] if data['main_inflow'] is not None else '暂无数据'}

## 输出要求
输出JSON格式（只输出JSON，不要其他文字），包含以下字段：
1. overall_action: 总体操作建议，只能是"加仓"/"减仓"/"持有"之一
2. short_term: 短期（1-4周）操作
3. mid_term: 中期（1-3月）操作  
4. long_term: 长期（6月+）操作
   - 每个周期包含: action（"加仓"/"减仓"/"持有"）、percent（操作百分比，如减仓30%表示卖出当前持仓的30%）、reason（一句话理由）
5. support: 支撑位价格
6. resistance: 阻力位价格
7. stop_loss: 止损位价格

{{
  "overall_action": "加仓",
  "short_term": {{"action": "加仓", "percent": 20, "reason": "KDJ金叉形成，短期动能充足"}},
  "mid_term": {{"action": "持有", "percent": 0, "reason": "趋势不明朗，等待进一步确认"}},
  "long_term": {{"action": "减仓", "percent": 30, "reason": "行业景气度下行，PE处于历史高位"}},
  "support": 1480,
  "resistance": 1600,
  "stop_loss": 1420
}}"""

    client = LLMClient()
    result, error = client.chat(prompt, max_tokens=3000)
    if error:
        return json.dumps({"error": error, "data": data}, ensure_ascii=False)

    try:
        parsed = json.loads(result)
        parsed["_raw_data"] = data
        return json.dumps(parsed, ensure_ascii=False)
    except json.JSONDecodeError:
        return json.dumps({"raw_analysis": result, "_raw_data": data}, ensure_ascii=False)

if __name__ == "__main__":
    code = sys.argv[1] if len(sys.argv) > 1 else "300750"
    print(run_analysis(code))