# 智能分析输出修复 & 持仓分析深度增强方案

## 一、问题描述

### 问题 1：stock_insight.py 输出乱码
- `stock_insight.py` 中调用了 `baostock.login()` / `baostock.logout()`
- baostock 向 stdout 输出 `login success!` / `logout success!`
- 这些非 JSON 文本混入 stdout，导致 `skill_impl.py:analyze_stock()` 中 `json.loads(raw)` 解析失败
- 回退到 `return raw[:3000]` → 前端展示原始 JSON + baostock 日志

### 问题 2：持仓分析操作建议深度不够
- `portfolio_analysis.py` 的 LLM prompt 只要求输出 `action/percent/reason` 三个字段
- 缺乏具体持有周期、目标价位、进场/离场信号、核心风险等可执行信息
- 用户无法获得有操作价值的参考

## 二、修复方案

### 2.1 stock_insight.py — 屏蔽 baostock stdout

在 `refresh_live_data()` 中，临时将 `sys.stdout` 重定向到 `sys.stderr`：
```python
import contextlib

with contextlib.redirect_stdout(sys.stderr):
    lg = bs.login()
    # ... all baostock calls ...
    bs.logout()
```

保证 stdout 只输出最终 JSON。

### 2.2 portfolio_analysis.py — 增强 prompt 输出结构

每个时间维度扩展为：

```json
{
  "short_term": {
    "action": "加仓/减仓/持有/观望",
    "holding_period": "1-2周",
    "percent": 20,
    "entry_condition": "股价回踩25元且KDJ金叉确认",
    "price_target": [27, 29],
    "stop_loss": 23.5,
    "pullback_level": "预计在26元附近震荡整理",
    "key_risk": "大盘回调拖累板块",
    "catalyst": "中报业绩预告若超预期",
    "reason": "KDJ进入超卖区，主力资金小幅流入，短期有技术性反弹需求"
  },
  "mid_term": {
    "action": "持有",
    "holding_period": "1-3个月",
    "percent": 0,
    "entry_condition": "等待放量突破28元确认趋势",
    "price_target": [28, 32],
    "stop_loss": 24,
    "pullback_level": "关注26元支撑位得失",
    "key_risk": "行业景气度下行",
    "catalyst": "数字经济发展政策出台",
    "reason": "趋势尚未明朗，等待进一步确认信号"
  },
  "long_term": {
    "action": "减仓",
    "holding_period": "6个月以上",
    "percent": 30,
    "entry_condition": "待ROE回升至5%以上再考虑加仓",
    "price_target": [30, 35],
    "stop_loss": 20,
    "pullback_level": "基本面改善前估值有持续回归风险",
    "key_risk": "PE为负、PB高达19倍存在估值回归风险",
    "catalyst": "公司盈利能力改善、行业拐点确认",
    "reason": "企业信息化长期赛道好，但当前盈利能力弱，估值偏高"
  }
}
```

同时分析范围：读取 `stock_portfolio` 表或 `stock_list.yaml` 中标记为"持仓"的股票，输出完整的组合分析报告。

## 三、实施步骤

| 步骤 | 文件 | 改动 |
|------|------|------|
| 1 | `stock_insight.py` | `refresh_live_data()` 中用 `redirect_stdout` 包裹 baostock 调用 |
| 2 | `portfolio_analysis.py` | 重写 prompt，增加 holding_period/price_target/entry_condition/exit_condition/stop_loss/pullback_level/key_risk/catalyst 字段 |
| 3 | 验证 | 运行 `analyze_stock("300687")` 确认无 baostock 日志；检查 portfolio 输出结构 |

## 四、影响范围

- **`stock_insight.py`**：仅 stdout 输出方式变化，JSON 内容不变，无副作用
- **`portfolio_analysis.py`**：LLM 输出结构变化，前端需适配新字段（前端已有灵活渲染，新字段自动展示）
- **不涉及**：agent.py、skill_impl.py、前端组件