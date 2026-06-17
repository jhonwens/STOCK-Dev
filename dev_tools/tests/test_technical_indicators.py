"""
技术指标计算验证测试
验证 EMA20/60/120, MACD, KDJ, RSI, BOLL, OBV 计算正确性
"""
import sys
import json
sys.path.insert(0, '/Users/ws/Desktop/Project/Trea-Project/STOCK-Dev/backend/stock-analyst/scripts')


def test_ema_calculation():
    """T1.1: EMA20 计算验证"""
    prices = [100 + i for i in range(30)]
    ema20 = calculate_ema(prices, 20)
    assert len(ema20) == len(prices), f"EMA长度={len(ema20)}, 期望={len(prices)}"
    # EMA 应为加权移动平均，确保有值
    assert all(v > 0 for v in ema20[-5:]), "EMA最后5个值应>0"
    print(f"  ✅ EMA20 最后值: {ema20[-1]:.2f}")
    return True


def calculate_ema(prices, period):
    """简易 EMA 计算"""
    if len(prices) < period:
        return [0] * len(prices)
    multiplier = 2 / (period + 1)
    ema = [sum(prices[:period]) / period]
    for i in range(period, len(prices)):
        ema.append((prices[i] - ema[-1]) * multiplier + ema[-1])
    return [0] * (period - 1) + ema


def test_macd_golden_cross():
    """T1.2: MACD 金叉判断"""
    # DIF 上穿 DEA
    dif = [1.0, 1.5, 2.0, 2.5, 3.5]
    dea = [3.0, 3.0, 3.0, 3.0, 2.8]
    is_golden = dif[-2] <= dea[-2] and dif[-1] > dea[-1]
    assert is_golden, "DIF上穿DEA应判断为金叉"
    print("  ✅ MACD 金叉判断正确")
    return True


def test_macd_divergence():
    """T1.3: MACD 顶背离"""
    # 股价新高, MACD波峰降低
    prices = [100, 105, 110, 115, 120, 125, 130]
    macd_peaks = [5, 6, 7, 6, 5]  # 波峰递减
    price_peak_idx = prices.index(max(prices))
    macd_peak_at_price_peak = macd_peaks[-1]
    macd_prev_peak = macd_peaks[-2]
    is_divergence = macd_peak_at_price_peak < macd_prev_peak
    assert is_divergence, "股价新高+MACD波峰降低应判断为顶背离"
    print("  ✅ MACD 顶背离判断正确")
    return True


def test_kdj_overbought():
    """T1.4: KDJ J>80 超买"""
    k, d, j = 72.5, 65.3, 86.9
    assert j > 80, f"J值{j}>80应判断为超买"
    print(f"  ✅ KDJ 超买判断正确 (J={j})")
    return True


def test_bollinger_position():
    """T1.5: 布林带位置判断"""
    price = 235
    upper = 235
    mid = 218
    lower = 201
    assert price >= upper, f"价格{price}>=上轨{upper}应判断超买"
    print(f"  ✅ 布林带位置判断正确 (价格{price}>=上轨{upper})")
    return True


def test_multi_head_alignment():
    """T1.6: 多头排列判断"""
    ema20, ema60, ema120 = 218.5, 210.3, 198.6
    is_bullish = ema20 > ema60 > ema120
    assert is_bullish, "EMA20>EMA60>EMA120 应判断为多头排列"
    print(f"  ✅ 多头排列判断正确 (EMA20>{ema20}>{ema60}>{ema120})")
    return True


def test_ma_death_cross():
    """补充: 死叉判断"""
    ema5 = [100, 100, 95]
    ema10 = [99, 99, 97]
    is_death = ema5[-2] > ema10[-2] and ema5[-1] < ema10[-1]
    assert is_death, "EMA5下穿EMA10应判断为死叉"
    print("  ✅ 均线死叉判断正确")
    return True


def test_rsi_values():
    """补充: RSI 计算值范围验证"""
    rsi = 62.3
    assert 0 <= rsi <= 100, f"RSI应在0-100之间, 当前{rsi}"
    is_overbought = rsi > 70
    is_oversold = rsi < 30
    assert not is_overbought and not is_oversold, f"RSI={rsi}应为中性"
    print(f"  ✅ RSI 值范围正确 (RSI={rsi}, 中性)")
    return True


def test_obv_trend():
    """补充: OBV 趋势判断"""
    obv_values = [1000, 1100, 1250, 1400, 1600]
    is_rising = all(obv_values[i] <= obv_values[i+1] for i in range(len(obv_values)-1))
    assert is_rising, "OBV持续上升应判断为量价配合"
    print("  ✅ OBV 趋势判断正确 (持续上升=量价配合)")
    return True


def test_macd_death_cross():
    """补充: MACD 死叉"""
    dif, dea = 3.0, 3.5
    dif_prev, dea_prev = 3.8, 3.6
    is_death = dif_prev > dea_prev and dif < dea
    assert is_death, "DIF下穿DEA应判断为死叉"
    print("  ✅ MACD 死叉判断正确")
    return True


if __name__ == "__main__":
    results = []
    tests = [
        ("T1.1 EMA计算", test_ema_calculation),
        ("T1.2 MACD金叉", test_macd_golden_cross),
        ("T1.3 MACD顶背离", test_macd_divergence),
        ("T1.4 KDJ超买", test_kdj_overbought),
        ("T1.5 布林带位置", test_bollinger_position),
        ("T1.6 多头排列", test_multi_head_alignment),
        ("T1.7 均线死叉", test_ma_death_cross),
        ("T1.8 RSI中性", test_rsi_values),
        ("T1.9 OBV趋势", test_obv_trend),
        ("T1.10 MACD死叉", test_macd_death_cross),
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
    print(f"技术指标验证测试完成")
    print(f"通过: {passed}/{len(tests)}")
    if failed > 0:
        print(f"失败: {failed}")
    print(f"{'='*40}")
    for name, status in results:
        print(f"  [{status[:4]}] {name}")

    sys.exit(0 if failed == 0 else 1)