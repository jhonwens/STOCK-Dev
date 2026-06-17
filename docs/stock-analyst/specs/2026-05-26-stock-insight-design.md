# 个股深度分析模块 — 设计文档

## 一、需求概述

### 1.1 业务目标
将现有的"基本面"静态示例页面改造为**个股深度分析**工具。用户输入单只股票名称，系统采集多维数据后调用 LLM 进行深度分析，重点突出买入点建议，并提供导出报告和加入自选股功能。

### 1.2 核心流程

```
用户输入股票名称 → 系统匹配股票代码 → 采集 12 维数据 → LLM 深度分析
→ 展示结果（买入点优先） → 用户可选择导出 MD 或加入自选
```

### 1.3 功能清单

| # | 功能 | 说明 |
|---|------|------|
| 1 | 股票搜索 | 输入股票名称或代码，匹配后显示基本信息 |
| 2 | AI 分析 | 采集 12 维数据 → LLM 深度分析 |
| 3 | 买入点重点展示 | 短期/中期/长期三个维度，含价格区间和信心评级 |
| 4 | 12 维分析展示 | 网格卡片布局展示全部 12 维分析结果 |
| 5 | 导出报告 | Markdown 格式，保存到 `reference/analysis/` |
| 6 | 加入自选 | 将股票加入 stock_portfolio，category='候选' |
| 7 | 缓存 | 复用 `stock_llm_report` 表，避免重复分析 |

---

## 二、技术架构

### 2.1 架构总览

```
┌────────────── Frontend (React) ──────────────┐
│  StockInsight.tsx                             │
│  ┌─ 输入 & 操作栏 ───────────────────────┐   │
│  │ [输入框] [AI分析] [导出] [加入自选]    │   │
│  ├─ 基本信息卡片 ────────────────────────┤   │
│  ├─ 🎯 买入点分析专区 ───────────────────┤   │
│  ├─ 12 维分析网格 ──────────────────────┤   │
│  └────────────────────────────────────────┘   │
└──────────────────┬────────────────────────────┘
                   │ Tauri IPC
┌──────────────────▼──────── Rust ───────────────┐
│  commands.rs                                    │
│  ├─ run_stock_insight(code) → Python sidecar   │
│  ├─ search_stock(query) → 模糊搜索股票         │
│  └─ 复用: add_portfolio_stock / 导出系命令     │
└──────────────────┬────────────────────────────┘
                   │ tokio::process::Command
┌──────────────────▼──── Python sidecar ─────────┐
│  stock_insight.py (新增)                        │
│  ├─ 接收 --code 参数                           │
│  ├─ 采集 12 维数据                             │
│  ├─ 加载 stock_insight.md prompt               │
│  ├─ LLM 分析 → JSON                           │
│  └─ 输出到 stdout                             │
└──────────────────┬────────────────────────────┘
                   │ SQLite
┌──────────────────▼──── Database ────────────────┐
│  stock_llm_report (report_type='stock_insight') │
│  stock_list.yaml (名称→代码映射)                │
│  stock_portfolio (加入自选)                      │
│  stock_realtime / stock_finance / 各数据表       │
└─────────────────────────────────────────────────┘
```

### 2.2 数据流

```
1. 用户输入股票名称 → 模糊搜索匹配代码
2. 点击 AI 分析 → invoke("run_stock_insight", { code: "600519" })
3. Rust → tokio::spawn → python3 stock_insight.py --code 600519
4. Python 采集 12 维数据（从各 DB 表读取）
5. 加载 LLM prompt (stock_insight.md)
6. 调用 LLM → 获取深度分析 JSON
7. Python 输出 JSON → stdout
8. Rust 返回前端
9. 前端渲染：买入点专区 + 12 维网格
10. 用户可导出 MD 或加入自选
```

---

## 三、Python 分析脚本设计

### 3.1 文件位置

```
backend/stock-analyst/scripts/
├── stock_insight.py           ← 新增
├── candidate_recommend.py     ← 已有 (可复用 collect 逻辑)
└── ...
```

### 3.2 脚本功能

```python
# 伪代码示意
def main():
    code = parse_args().code
    # 1. 确认股票存在
    basic = get_basic_info(code)
    # 2. 采集 12 维数据
    data = collect_stock_data(code)  # 复用 candidate_recommend 的 collect 逻辑
    # 3. 加载 prompt
    prompt = load_prompt("stock_insight.md")
    # 4. 调用 LLM
    result = llm_client.chat(data, system_prompt=prompt)
    # 5. 输出
    print(json.dumps(result))
```

### 3.3 LLM Prompt (`backend/ai/prompts/stock_insight.md`)

**与候选推荐 prompt 的关键区别**：
- 聚焦单只股票的深度分析，而非批量对比筛选
- **买入点分析**作为核心输出模块，分短期/中期/长期三个维度
- 每个买入点含：具体信号/理由、建议价格区间、信心评级
- 12 维分析要求比候选推荐更加详细和深入

### 3.4 LLM 输出格式

```json
{
  "basic_info": {
    "code": "600519",
    "name": "贵州茅台",
    "industry": "白酒",
    "price": 1536.80,
    "change_pct": 1.23,
    "pe": 25.3,
    "pb": 6.8
  },
  "buy_point_analysis": {
    "summary": "综合判断当前处于估值低位...",
    "short_term": {
      "point": "KDJ金叉形成，主力资金连续3日净流入",
      "price_range": [1520, 1540],
      "confidence": "高",
      "detail": "日线级别KDJ指标于昨日形成金叉..."
    },
    "mid_term": {
      "point": "MACD周线金叉，估值处于近3年30%分位",
      "price_range": [1480, 1520],
      "confidence": "中",
      "detail": "周线MACD快线已上穿慢线形成金叉..."
    },
    "long_term": {
      "point": "PE处于历史低位，ROE稳定30%+",
      "price_range": [1400, 1500],
      "confidence": "高",
      "detail": "当前PE-TTM为25倍，处于近5年20%分位..."
    },
    "position_suggestion": "建议30%仓位先建底仓，回调至1480以下加仓至50%",
    "key_indicators": {
      "support_level": 1480,
      "resistance_level": 1600,
      "stop_loss": 1420
    }
  },
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
  },
  "risk_warning": "当前主要风险为消费复苏不及预期..."
}
```

---

## 四、前端 UI 设计

### 4.1 主页面 (StockInsight.tsx — 重写 Fundamental.tsx)

**布局**：纵向单列布局

```
┌──────────────────────────────────────────────┐
│  📈 个股深度分析                              │
├──────────────────────────────────────────────┤
│                                              │
│  搜索框 + 操作栏（一行）                      │
│  ┌────────────────────┐ ┌─────────┐         │
│  │ 📝 输入股票名称/代码 │ │ 搜索    │         │
│  └────────────────────┘ └─────────┘         │
│  [🤖 AI 分析] [💾 导出报告] [➕ 加入自选]   │
│                                              │
│  ┌── 基本信息卡片 ────────────────────────┐  │
│  │ 名称 代码 行业 现价 涨跌幅 PE PB       │  │
│  └────────────────────────────────────────┘  │
│                                              │
│  ┌── 🎯 买入点分析 ──────────────────────┐  │
│  │  🟢 短期: 信号描述                      │  │
│  │     建议区间: 1,520-1,540  ⭐⭐⭐ 高    │  │
│  │  🟡 中期: 信号描述                      │  │
│  │     建议区间: 1,480-1,520  ⭐⭐ 中     │  │
│  │  🔵 长期: 信号描述                      │  │
│  │     建议区间: 1,400-1,500  ⭐⭐⭐ 高    │  │
│  │  仓位建议: 30%底仓 + 分批加仓           │  │
│  │  支撑/阻力/止损: 1480 / 1600 / 1420    │  │
│  └────────────────────────────────────────┘  │
│                                              │
│  ┌── 12 维分析 ──────────────────────────┐  │
│  │  ┌──────┐ ┌──────┐ ┌──────┐         │  │
│  │  │🏢基本面│ │💰财务 │ │📈行业 │         │  │
│  │  └──────┘ └──────┘ └──────┘         │  │
│  │  ┌──────┐ ┌──────┐ ┌──────┐         │  │
│  │  │🔥热点 │ │🎯价格 │ │📊技术 │         │  │
│  │  └──────┘ └──────┘ └──────┘         │  │
│  │  （三列网格，每个维度一卡片）           │  │
│  └────────────────────────────────────────┘  │
│                                              │
│  ┌── ⚠️ 风险提示 ────────────────────────┐  │
│  └────────────────────────────────────────┘  │
└──────────────────────────────────────────────┘
```

### 4.2 交互逻辑

| 操作 | 行为 |
|------|------|
| 输入股票名称/代码 | 点击搜索后匹配，显示股票选择 |
| 点击 AI 分析 | 调 `run_stock_insight`，带 loading 状态 |
| 分析完成 | 渲染买入点专区 + 12 维网格 |
| 点击导出报告 | 调 export 命令，保存到 `reference/analysis/` |
| 点击加入自选 | 调 `add_portfolio_stock(code, name, 0, 0, '候选')` |
| 已有缓存 | 自动读取，显示上次分析时间 |

### 4.3 侧边栏

`Sidebar.tsx`：`"基本面"` → `"个股分析"`，路由 `/fundamental` 不变

### 4.4 买入点专区样式

- 绿色底色 + 左边框的卡片布局
- 短期/中期/长期三个条目，用颜色区分（绿/黄/蓝）
- 每个条目含：信号描述、价格区间、信心星级（⭐）
- 底部显示：仓位建议、支撑位/阻力位/止损位

---

## 五、Rust 命令 & API 设计

### 5.1 新增 Tauri 命令

| 命令 | 参数 | 返回值 | 说明 |
|------|------|--------|------|
| `run_stock_insight(code)` | `code: String` | `String` (JSON) | 调用 Python sidecar 分析单只股票 |
| `search_stock(query)` | `query: String` | `String` (JSON) | 模糊搜索股票名称/代码 |

### 5.2 复用已有命令

| 命令 | 用途 |
|------|------|
| `add_portfolio_stock` | 加入自选（category='候选'） |
| `save_portfolio_analysis` | 保存分析结果到缓存（通用模式） |
| `load_portfolio_analysis` | 加载缓存（通用模式） |
| `export_portfolio_md` | 导出 Markdown（参考其模式实现） |

### 5.3 前端 API 函数

```typescript
export async function runStockInsight(code: string): Promise<string>
export async function searchStock(query: string): Promise<string>
```

### 5.4 缓存策略

- `stock_llm_report` 表
- `report_type='stock_insight'`, `scope=股票代码`
- 页面加载时检查缓存，显示分析时间和摘要
- 重新分析时覆盖更新

---

## 六、导出文件目录

### 6.1 目录结构

```
reference/
├── portfolio/       ← 持仓分析报告（已有）
├── candidate/       ← 候选推荐报告（已有）
└── analysis/        ← 个股深度分析报告（新增）
    └── 600519-贵州茅台-深度分析.md
```

### 6.2 报告内容

- 标题：个股深度分析报告
- 基本信息：代码、名称、行业、现价
- 买入点分析（重点）：短期/中期/长期 + 仓位建议
- 12 维详细分析
- 风险提示
- 生成时间

---

## 七、数据模型

无需新增数据库表，复用现有表：

| 表 | 用途 |
|----|------|
| `stock_llm_report` | `report_type='stock_insight'` 缓存分析结果 |
| `stock_list.yaml` | 股票名称→代码映射（搜索时匹配） |
| `stock_portfolio` | 加入自选（category='候选'） |
| `stock_realtime` | 行情数据 |
| `stock_finance` | 财务数据 |
| `stock_technical` | 技术指标 |
| `stock_fund_flow` | 资金流向 |
| `stock_news` | 热点信息 |
| `stock_history` | 风险指标计算 |

---

## 八、安全设计

| 风险 | 应对 |
|------|------|
| 用户输入无效股票名 | 搜索时模糊匹配+选择确认，未匹配时提示 |
| LLM 输出非 JSON | 同候选推荐，增加 extract_json 清洗和重试 |
| 并发多次点击 AI 分析 | 前端加锁，分析中按钮禁用 |
| 重复加入自选 | 使用 INSERT OR IGNORE / 加 UNIQUE 约束防重 |
| 导出路径冲突 | 以"代码-名称-分析报告.md"命名，天然唯一 |