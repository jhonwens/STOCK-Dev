"""
技术指标计算模块
EMA20/60/120, MACD, KDJ, RSI(14), BOLL(20,2), OBV
输入: OHLC 历史K线数据 (list of dict)
输出: 最新指标的 dict
"""
import math


def calculate_ema(prices, period):
    if len(prices) < period:
        return [0.0] * len(prices)
    multiplier = 2 / (period + 1)
    ema = [sum(prices[:period]) / period]
    for i in range(period, len(prices)):
        ema.append((prices[i] - ema[-1]) * multiplier + ema[-1])
    return [0.0] * (period - 1) + ema


def calculate_macd(closes):
    ema12 = calculate_ema(closes, 12)
    ema26 = calculate_ema(closes, 26)
    dif = [e12 - e26 for e12, e26 in zip(ema12, ema26)]
    dea = calculate_ema(dif, 9)
    hist = [(d - e) * 2 for d, e in zip(dif, dea)]
    return {"DIF": round(dif[-1], 2), "DEA": round(dea[-1], 2),
            "hist": round(hist[-1], 2), "golden_cross": dif[-2] <= dea[-2] and dif[-1] > dea[-1],
            "death_cross": dif[-2] >= dea[-2] and dif[-1] < dea[-1],
            "above_zero": dif[-1] > 0}


def calculate_kdj(highs, lows, closes, period=9):
    low_min = [min(lows[max(0, i - period + 1):i + 1]) for i in range(len(lows))]
    high_max = [max(highs[max(0, i - period + 1):i + 1]) for i in range(len(highs))]
    rsv = []
    for i in range(len(closes)):
        if high_max[i] - low_min[i] == 0:
            rsv.append(50.0)
        else:
            rsv.append((closes[i] - low_min[i]) / (high_max[i] - low_min[i]) * 100)
    k = [50.0]
    d = [50.0]
    for i in range(1, len(rsv)):
        k.append(2 / 3 * k[-1] + 1 / 3 * rsv[i])
        d.append(2 / 3 * d[-1] + 1 / 3 * k[-1])
    j = [3 * k[i] - 2 * d[i] for i in range(len(k))]
    return {"K": round(k[-1], 1), "D": round(d[-1], 1), "J": round(j[-1], 1),
            "overbought": j[-1] > 80, "oversold": j[-1] < 20,
            "golden_cross": k[-2] <= d[-2] and k[-1] > d[-1]}


def calculate_rsi(closes, period=14):
    if len(closes) < period + 1:
        return {"RSI": 50.0, "overbought": False, "oversold": False}
    gains, losses = [], []
    for i in range(1, len(closes)):
        diff = closes[i] - closes[i - 1]
        gains.append(max(diff, 0))
        losses.append(max(-diff, 0))
    avg_gain = sum(gains[-period:]) / period
    avg_loss = sum(losses[-period:]) / period
    if avg_loss == 0:
        rsi = 100.0
    else:
        rs = avg_gain / avg_loss
        rsi = 100 - 100 / (1 + rs)
    return {"RSI": round(rsi, 1), "overbought": rsi > 70, "oversold": rsi < 30}


def calculate_bollinger(closes, period=20, multiplier=2):
    if len(closes) < period:
        return {"upper": 0, "mid": 0, "lower": 0, "position": "unknown"}
    ma = sum(closes[-period:]) / period
    variance = sum((c - ma) ** 2 for c in closes[-period:]) / period
    std = math.sqrt(variance)
    upper = ma + multiplier * std
    lower = ma - multiplier * std
    current = closes[-1]
    position = "above_upper" if current >= upper else "below_lower" if current <= lower else "inside"
    return {"upper": round(upper, 2), "mid": round(ma, 2), "lower": round(lower, 2),
            "position": position, "overbought": current >= upper, "oversold": current <= lower}


def calculate_obv(closes, volumes):
    obv = [volumes[0]]
    for i in range(1, len(closes)):
        if closes[i] > closes[i - 1]:
            obv.append(obv[-1] + volumes[i])
        elif closes[i] < closes[i - 1]:
            obv.append(obv[-1] - volumes[i])
        else:
            obv.append(obv[-1])
    if len(obv) < 5:
        obv_trend = "flat"
    else:
        obv_trend = "rising" if obv[-1] > obv[-5] else "falling" if obv[-1] < obv[-5] else "flat"
    return {"OBV": int(obv[-1]), "trend": obv_trend}


def calculate_trend_filter(ema20, ema60, ema120, macd_data):
    direction = "多头" if ema20 > ema60 > ema120 else "空头" if ema20 < ema60 < ema120 else "震荡"
    healthy = not macd_data.get("頂背離", False)
    return {"direction": direction, "healthy": healthy,
            "bullish": direction == "多头", "all_ok": direction == "多头" and healthy}


def calculate_all_indicators(klines):
    closes = [k["close"] for k in klines]
    highs = [k["high"] for k in klines]
    lows = [k["low"] for k in klines]
    volumes = [k["volume"] for k in klines]

    ema20 = calculate_ema(closes, 20)
    ema60 = calculate_ema(closes, 60)
    ema120 = calculate_ema(closes, 120)
    macd = calculate_macd(closes)
    kdj = calculate_kdj(highs, lows, closes)
    rsi = calculate_rsi(closes)
    boll = calculate_bollinger(closes)
    obv = calculate_obv(closes, volumes)
    trend = calculate_trend_filter(ema20[-1], ema60[-1], ema120[-1], macd)

    return {
        "ema20": round(ema20[-1], 2), "ema60": round(ema60[-1], 2), "ema120": round(ema120[-1], 2),
        "macd": macd, "kdj": kdj, "rsi": rsi, "boll": boll, "obv": obv,
        "trend_filter": trend,
        "multi_head": ema20[-1] > ema60[-1] > ema120[-1],
    }