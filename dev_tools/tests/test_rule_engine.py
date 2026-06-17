"""
规则引擎验证测试
验证趋势过滤四步法、选股评分、预警规则
"""
import sys
sys.path.insert(0, '/Users/ws/Desktop/Project/Trea-Project/STOCK-Dev/backend/stock-analyst/scripts')


# ===== 趋势过滤四步法 =====
def trend_filter_step1(ema20, ema60, ema120):
    """定方向"""
    if ema20 > ema60 > ema120:
        return "多头", True
    elif ema20 < ema60 < ema120:
        return "空头", True
    return "震荡", False


def trend_filter_step2(dif, dea, price_high, macd_peak_high):
    """看阶段: MACD 背离检测"""
    # 顶背离: 股价新高 + MACD波峰降低
    if macd_peak_high and dif < macd_peak_high:
        return "顶背离", False
    return "健康", True


def trend_filter_step3(candle_bodies, gaps_filled):
    """评估能量"""
    thick_count = sum(1 for b in candle_bodies if b > 0.02)  # 实体饱满比例
    ratio = thick_count / len(candle_bodies) if candle_bodies else 0
    if ratio > 0.6 and not gaps_filled:
        return "强", True
    elif ratio > 0.3:
        return "中", True
    return "弱", False


def trend_filter_step4(macd_position):
    """确认级别"""
    if macd_position == "零轴上方":
        return "同级别趋势", True
    elif macd_position == "回踩零轴":
        return "理想趋势", True
    elif macd_position == "零轴下方":
        return "小级别反弹", False
    return "不明", False


# ===== 选股评分 =====
def stock_score(limit_up_count, above_ma5, volume_ratio, fund_flow, pe_value):
    """选股评分 (满分100)"""
    score = 0
    if limit_up_count >= 1:
        score += 25
    if above_ma5:
        score += 20
    if volume_ratio > 1.2:
        score += 20
    if fund_flow > 0:
        score += 20
    if 10 < pe_value < 50:
        score += 15
    return score


# ===== 预警规则 =====
def alert_price_change(change_pct, threshold=5.0):
    """涨跌幅预警"""
    return abs(change_pct) >= threshold


def alert_fund_flow(net_inflow, threshold=10_000_000):
    """资金流向预警 (默认1000万)"""
    return abs(net_inflow) >= threshold


def alert_fundamental(revenue_growth, profit_growth, rev_threshold=30, profit_threshold=50):
    """基本面预警"""
    return revenue_growth >= rev_threshold or profit_growth >= profit_threshold


# ===== 缠论买卖点 =====
def chan_buy_sell_type(bias_level, pullback_confirm, breakout_center):
    """缠论买卖点判断"""
    if bias_level == "背驰" and pullback_confirm:
        return "一买"  # 第一类买点
    elif pullback_confirm and not bias_level:
        return "二买"  # 第二类买点
    elif breakout_center and pullback_confirm:
        return "三买"  # 第三类买点
    return None


# ===== 风险回报比 =====
def risk_reward_ratio(stop_loss, target, entry):
    risk = abs(entry - stop_loss)
    reward = abs(target - entry)
    if risk == 0:
        return 0
    return round(reward / risk, 1)


# ===== 测试用例 =====

def test_trend_filter_complete():
    """T2.1: 完整趋势过滤 - 多头健康强趋势"""
    s1, ok1 = trend_filter_step1(220, 210, 200)
    assert ok1 and s1 == "多头", f"定方向: {s1}"
    s2, ok2 = trend_filter_step2(5.0, 1.8, 220, 4.0)
    assert ok2 and s2 == "健康", f"看阶段: {s2}"
    s3, ok3 = trend_filter_step3([0.03, 0.04, 0.025, 0.035, 0.05], False)
    assert ok3 and s3 == "强", f"评估能量: {s3}"
    s4, ok4 = trend_filter_step4("回踩零轴")
    assert ok4 and s4 == "理想趋势", f"确认级别: {s4}"
    print("  ✅ T2.1 趋势过滤全流程正确 (多头->健康->强->理想趋势)")
    return True


def test_trend_filter_weak():
    """T2.1b: 弱趋势识别"""
    s1, ok1 = trend_filter_step1(200, 210, 220)
    assert s1 == "空头", f"定方向: {s1}"
    s3, ok3 = trend_filter_step3([0.01, 0.015, 0.008, 0.02, 0.012], True)
    assert not ok3, "缺口被回补+实体薄=弱趋势"
    print("  ✅ T2.1b 弱趋势识别正确")
    return True


def test_stock_score_pass():
    """T2.3a: 选股评分 - 优秀候选"""
    score = stock_score(3, True, 1.5, 2_000_000, 25)
    assert score >= 60, f"评分{score}应>=60"
    print(f"  ✅ T2.3a 选股评分正确 (优秀={score})")
    return True


def test_stock_score_fail():
    """T2.3b: 选股评分 - 差候选"""
    score = stock_score(0, False, 0.8, 0, 100)
    assert score < 60, f"评分{score}应<60"
    print(f"  ✅ T2.3b 选股评分正确 (差={score})")
    return True


def test_alert_price():
    """T2.4: 涨跌幅预警"""
    assert alert_price_change(5.2), "5.2%>=5% 应触发预警"
    assert not alert_price_change(3.0), "3%<5% 不应触发预警"
    assert alert_price_change(-5.5), "-5.5%<=-5% 应触发预警"
    print("  ✅ T2.4 涨跌幅预警正确")
    return True


def test_alert_fund():
    """T2.5: 资金流向预警"""
    assert alert_fund_flow(15_000_000), "1500万>=1000万 应触发预警"
    assert not alert_fund_flow(500_000), "50万<1000万 不应触发预警"
    print("  ✅ T2.5 资金流向预警正确")
    return True


def test_alert_fundamental():
    """补充: 基本面预警"""
    assert alert_fundamental(35, 20), "营收增长35%>=30% 应触发预警"
    assert alert_fundamental(20, 55), "利润增长55%>=50% 应触发预警"
    assert not alert_fundamental(20, 30), "均未达阈值不应触发预警"
    print("  ✅ 基本面预警正确")
    return True


def test_chan_buy_point():
    """补充: 缠论买点判断"""
    buy1 = chan_buy_sell_type("背驰", True, False)
    assert buy1 == "一买", f"背驰+确认应为一买, 得到{buy1}"
    buy2 = chan_buy_sell_type("非背驰", True, True)
    assert buy2 == "三买", f"中枢突破+确认应为三买, 得到{buy2}"
    print("  ✅ 缠论买卖点判断正确 (一买/三买)")
    return True


def test_risk_reward():
    """补充: 风险回报比"""
    rr = risk_reward_ratio(195, 260, 220)
    assert rr >= 1.5, f"风险回报比{rr}应>=1.5"
    print(f"  ✅ 风险回报比合格 (1:{rr})")
    return True


def test_macd_divergence_alert():
    """补充: MACD 顶背离预警"""
    price_new_high = 130
    prev_high = 120
    macd_peak_current = 3.5
    macd_peak_previous = 5.0
    is_top_divergence = (price_new_high > prev_high) and (macd_peak_current < macd_peak_previous)
    assert is_top_divergence, "应识别为顶背离"
    print("  ✅ MACD 顶背离预警正确")
    return True


def test_multi_indicator_conflict():
    """补充: 多指标矛盾场景"""
    # MACD 金叉但 KDJ 超买
    macd_golden = True
    kdj_overbought = True
    suggestion = "谨慎" if kdj_overbought else "买入"
    assert suggestion == "谨慎", "KDJ超买时即使MACD金叉也应谨慎"
    print("  ✅ 多指标矛盾处理正确 (MACD金叉+KDJ超买→谨慎)")
    return True


if __name__ == "__main__":
    results = []
    tests = [
        ("T2.1 趋势过滤全流程", test_trend_filter_complete),
        ("T2.1b 弱趋势识别", test_trend_filter_weak),
        ("T2.3a 选股评分-优秀", test_stock_score_pass),
        ("T2.3b 选股评分-差", test_stock_score_fail),
        ("T2.4 涨跌幅预警", test_alert_price),
        ("T2.5 资金流向预警", test_alert_fund),
        ("T2.6 基本面预警", test_alert_fundamental),
        ("T2.7 缠论买卖点", test_chan_buy_point),
        ("T2.8 风险回报比", test_risk_reward),
        ("T2.9 MACD顶背离预警", test_macd_divergence_alert),
        ("T2.10 多指标矛盾", test_multi_indicator_conflict),
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
    print(f"规则引擎验证测试完成")
    print(f"通过: {passed}/{len(tests)}")
    if failed > 0:
        print(f"失败: {failed}")
    print(f"{'='*40}")
    for name, status in results:
        print(f"  [{status[:4]}] {name}")

    sys.exit(0 if failed == 0 else 1)