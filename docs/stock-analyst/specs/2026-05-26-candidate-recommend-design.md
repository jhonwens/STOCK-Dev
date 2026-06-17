# 候选推荐模块 — 设计文档

## 一、需求概述

### 1.1 业务目标
从用户维护的完整跟踪列表（股票池）中，排除已持仓股票，通过**数据计算 + LLM 综合研判**的方式，推荐两类 Top 5 候选股票：
- **中短期持有 Top 5** — 适合短期反复波段操作的股票
- **长期价值投资 Top 5** — 低估值、适合长期持有的价值股

### 1.2 核心流程

```
stock_list.yaml → 排除已持仓 → 12 维数据采集 → LLM 综合分析 → 输出推荐
```

### 1.3 12 维分析维度

| # | 维度 | 数据来源 | 中短期权重 | 长期权重 |
|---|------|---------|-----------|---------|
| 1 | 基本面分析 | DB (stock_finance + 规则计算) | 中 | 高 |
| 2 | 财务经营分析 | DB (stock_finance) | 中 | 高 |
| 3 | 行业价值趋势 | DB (stock_trend) | 中 | 高 |
| 4 | 热点信息影响 | DB (stock_news) | 高 | 中 |
| 5 | 建议买入价格分布 | 估值模型计算 | 中 | 高 |
| 6 | 技术面综合评分 | DB (stock_technical) | 高 | 中 |
| 7 | 估值对比分析 (PE/PB/PS) | DB (stock_realtime) | 低 | 高 |
| 8 | 资金流向分析 | DB (stock_fund_flow) | 高 | 中 |
| 9 | 机构持仓变动 | 待接入 | 低 | 高 |
| 10 | 风险指标 (Beta/波动率/回撤) | 历史K线计算 | 高 | 高 |
| 11 | 同业竞争力对比 | 待接入 | 中 | 高 |
| 12 | 催化事件日历 | 待接入 | 高 | 中 |

---

## 二、技术架构

### 2.1 架构总览

```
┌────────────── Frontend (React) ──────────────┐
│  Watchlist.tsx                                │
│  ┌────────────────────────────────────────┐   │
│  │  上下分区滚动布局                        │   │
│  │  ┌─ [AI 推荐] 按钮 ─────────────────┐  │   │
│  │  │  📈 中短期持有 Top 5 (卡片列表)    │  │   │
│  │  ├────────────────────────────────────┤  │   │
│  │  │  📊 长期价值投资 Top 5 (卡片列表)  │  │   │
│  │  └────────────────────────────────────┘  │   │
│  │                                           │   │
│  │  RecommendDetailDrawer.tsx (弹窗详情)     │   │
│  └────────────────────────────────────────┘   │
└──────────────────┬────────────────────────────┘
                   │ Tauri IPC (invoke)
┌──────────────────▼──────── Rust ───────────────┐
│  commands.rs                                    │
│  ├─ run_candidate_llm() → Python sidecar       │
│  ├─ save_candidate_analysis() → DB             │
│  ├─ load_candidate_analysis() → DB             │
│  └─ export_candidate_md() → reference/candidate/│
└──────────────────┬────────────────────────────┘
                   │ tokio::process::Command
┌──────────────────▼──── Python sidecar ─────────┐
│  candidate_recommend.py (新增)                  │
│  1. 读取 stock_list.yaml                       │
│  2. 排除 stock_portfolio WHERE category='持仓' │
│  3. 采集 12 维数据（DB 查询+计算）              │
│  4. 调用 prompt_loader 加载 prompt             │
│  5. 调用 LLM 综合分析                           │
│  6. 输出结构化 JSON                            │
└──────────────────┬────────────────────────────┘
                   │ SQLite
┌──────────────────▼──── Database ────────────────┐
│  stock_llm_report (report_type='candidate')     │
│  stock_list.yaml (股票池)                       │
│  stock_portfolio (排除已持仓)                    │
└─────────────────────────────────────────────────┘
```

### 2.2 数据流

```
1. 前端点击 [AI 推荐] → invoke("run_candidate_llm")
2. Rust → tokio::spawn → python3 candidate_recommend.py
3. Python 读取 stock_list.yaml → 获取全量跟踪列表
4. Python 查询 stock_portfolio WHERE category='持仓' → 排除
5. 对剩余候选股票采集 12 维数据
6. 打包为结构化 JSON 数据包
7. 调用 LLM（通过 llm_client.py）
8. LLM 返回推荐结果（JSON）
9. Python 输出 JSON → stdout
10. Rust 解析 → 返回前端
11. 前端渲染：上下分区 + 卡片列表
12. 用户点击股票 → 弹窗展示 12 维详细分析
```

---

## 三、Python 分析脚本设计

### 3.1 文件位置

```
backend/stock-analyst/scripts/
├── candidate_recommend.py   ← 新增
├── portfolio_analysis.py    ← 已有
└── ...
```

### 3.2 LLM Prompt 设计

- prompt 配置放在 `backend/ai/prompts/candidate_recommend.md`
- 通过 `prompt_loader.py` 加载，禁止硬编码

### 3.3 LLM 输入

```json
{
  "candidates": [
    {
      "code": "000001",
      "name": "平安银行",
      "price": 12.34,
      "change_pct": 2.3,
      "pe": 5.2,
      "pb": 0.6,
      "roe": 11.2,
      "revenue_growth": 3.5,
      "profit_growth": 2.1,
      "eps": 1.23,
      "bvps": 12.5,
      "technical_score": 78,
      "technical_detail": {
        "ma5_trend": "up",
        "ma10_trend": "up",
        "macd_signal": "golden_cross",
        "kdj": "bullish",
        "rsi": 62
      },
      "main_inflow": 1.2e8,
      "institutional_holding_change": 0.5,
      "news": ["...", "..."],
      "industry": "银行",
      "industry_trend": "银行板块整体估值偏低...",
      "risk_beta": 0.8,
      "volatility": 0.25,
      "max_drawdown": 0.15,
      "fair_price_range": [11.5, 13.0],
      "catalysts": ["2026-06-15 股东大会"]
    }
  ]
}
```

### 3.4 LLM 输出格式

```json
{
  "short_term": {
    "summary": "短期市场情绪...",
    "top5": [
      {
        "rank": 1,
        "code": "000001",
        "name": "平安银行",
        "overall_score": 92,
        "recommend_reason": "短期KDJ金叉+主力资金持续流入+板块轮动机会",
        "suggested_price_range": [11.80, 12.50],
        "risk_warning": "注意前高13.20压力位",
        "holding_period": "1-4周",
        "analysis_12dim": {
          "基本面": "...",
          "财务经营": "...",
          "行业趋势": "...",
          "热点信息": "...",
          "建议买入价格": "...",
          "技术面": "...",
          "估值对比": "...",
          "资金流向": "...",
          "机构持仓": "...",
          "风险指标": "...",
          "同业对比": "...",
          "催化事件": "..."
        }
      }
    ]
  },
  "long_term": {
    "summary": "长期价值投资机会...",
    "top5": [
      {
        "rank": 1,
        "code": "000001",
        "name": "平安银行",
        "overall_score": 88,
        "recommend_reason": "低估值+高ROE+机构增持",
        "suggested_price_range": [11.00, 12.00],
        "risk_warning": "关注不良率变化",
        "holding_period": "6个月以上",
        "analysis_12dim": { ... }
      }
    ]
  }
}
```

---

## 四、前端 UI 设计

### 4.1 主页面 (Watchlist.tsx — 重写)

**布局**：上下分区滚动

```
┌──────────────────────────────────────────────┐
│  🎯 候选推荐   [🤖 AI 推荐]  [💾 保存报告]   │
├──────────────────────────────────────────────┤
│                                              │
│  ┌── 📈 中短期持有 Top 5 ──────────────────┐ │
│  │  ┌──── 卡片 ────┐  ┌──── 卡片 ────┐   │ │
│  │  │ ⭐⭐⭐ 评分 92 │  │ ⭐⭐ 评分 85  │   │ │
│  │  │ 平安银行      │  │ 中兴通讯      │   │ │
│  │  │ 现价 12.34    │  │ 现价 28.50    │   │ │
│  │  │ +2.3%         │  │ -0.8%         │   │ │
│  │  │ 推荐理由...   │  │ 推荐理由...   │   │ │
│  │  │ [查看详情]    │  │ [查看详情]    │   │ │
│  │  └───────────────┘  └───────────────┘   │ │
│  │  ...（共 5 张卡片，自适应网格）           │ │
│  └──────────────────────────────────────────-│
│                                              │
│  ┌── 📊 长期价值投资 Top 5 ────────────────┐ │
│  │  （同卡片布局，蓝色系风格区分）            │ │
│  └──────────────────────────────────────────-│
│                                              │
└──────────────────────────────────────────────┘
```

**卡片设计**：
- 每张卡片展示：排名星级、评分、股票名、现价/涨跌幅、一句话推荐理由、操作按钮
- 中短期卡片用**紫色/橙色**色系区分
- 长期卡片用**蓝色/绿色**色系区分

**交互**：
- 点击卡片 → 弹出 `RecommendDetailDrawer` 展示 12 维详情
- 点击 [AI 推荐] → 调用后端分析，loading 状态
- 点击 [保存报告] → 导出到 `reference/candidate/`

### 4.2 详情弹窗 (RecommendDetailDrawer.tsx — 新增)

- 使用 Modal/抽屉组件
- Tab 或折叠面板展示 12 个维度
- 每个维度含：标题 + 内容 + 评分/指标
- 底部操作：加入持仓（跳转 Portfolio）、导出 MD

### 4.3 侧边栏更新

`Sidebar.tsx` 将 `"候选池"` 改为 `"候选推荐"`

---

## 五、Rust 命令 & API 设计

### 5.1 新增 Tauri 命令

| 命令 | 参数 | 返回值 | 说明 |
|------|------|--------|------|
| `run_candidate_llm()` | 无 | `String` (JSON) | 调用 Python sidecar 分析 |
| `save_candidate_analysis(analysis_json)` | `analysis_json: String` | `String` | 保存结果到 DB |
| `load_candidate_analysis()` | 无 | `String` (JSON or "{}") | 加载最近一次缓存 |
| `export_candidate_md(analysis_json)` | `analysis_json: String` | `String` (文件路径) | 导出 MD 到 reference/candidate/ |

### 5.2 前端 API 函数

```typescript
// api.ts 新增
export async function runCandidateLlm(): Promise<string>
export async function saveCandidateAnalysis(analysisJson: string): Promise<string>
export async function loadCandidateAnalysis(): Promise<string>
export async function exportCandidateMd(analysisJson: string): Promise<string>
```

### 5.3 缓存策略

- 复用 `stock_llm_report` 表
- `report_type='candidate'`, `scope='all'`
- 每次成功 AI 分析后自动保存
- 页面加载时先读缓存，显示上次分析时间和摘要

---

## 六、导出文件目录结构

### 6.1 目录规划

```
reference/
├── portfolio/       ← 持仓分析报告（现有报告调整至此）
│   ├── 000001-平安银行-分析报告.md
│   └── ...
└── candidate/       ← 候选推荐报告（新增）
    └── 2026-05-26-候选推荐报告.md
```

### 6.2 候选推荐报告内容

- 标题：`2026-05-26 候选推荐报告`
- 第一部分：中短期持有 Top 5（含每只股票完整分析）
- 第二部分：长期价值投资 Top 5（含每只股票完整分析）
- 第三部分：LLM 综合市场判断摘要
- 底部：生成时间、数据来源声明

### 6.3 现有持仓报告迁移

现有 `reference/` 根目录下的持仓分析 MD 文件，后续迁移到 `reference/portfolio/` 子目录。

---

## 七、数据模型变更

无需新增数据库表，复用现有表：

| 表 | 用途 |
|----|------|
| `stock_llm_report` | `report_type='candidate'` 缓存分析结果 |
| `stock_list.yaml` | 股票池（待分析候选来源） |
| `stock_portfolio` | `category='持仓'` 用于排除已持仓 |
| `stock_realtime` | 行情/估值数据 |
| `stock_finance` | 财务数据 |
| `stock_trend` | 行业趋势 |
| `stock_news` | 热点信息 |
| `stock_technical` | 技术指标 |
| `stock_fund_flow` | 资金流向 |
| `stock_history` | 风险指标计算 |

---

## 八、安全设计

| 风险 | 应对 |
|------|------|
| 大量候选导致 LLM token 超限 | 限制每批最多 20 只候选送入 LLM；若超过则分批处理 |
| LLM 输出不符合 JSON 格式 | Python 端增加重试+降级逻辑（最多重试 2 次） |
| 并发多次点击 AI 推荐 | 前端加锁，分析完成前按钮禁用 |
| 导出路径冲突 | 文件名以日期命名，同一天多次保存自动加序号 |