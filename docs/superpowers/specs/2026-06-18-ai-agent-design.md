# 衡势价值 · 智能分析 Agent 设计 Spec

**日期**：2026-06-18
**作者**：衡势价值产品设计
**状态**：待审阅

## 一、背景与目标

### 1.1 现状

衡势价值（hengshi-value）当前为单只股票 / 持仓 / 候选股的"单点分析工具"：
- **个股分析页**（`/fundamental`，`src/pages/Fundamental.tsx`）：用户输入股票 → AI 生成 12 维分析 + 买入点 → 导出 MD
- **候选推荐页**（`/watchlist`）：AI 推荐 5+5 = 10 只
- **持仓分析页**（`/portfolio`）：每只持仓单独分析
- **浮窗 AI 分析师**（`src/components/LLMChat.tsx`）：屏幕右下角 💬 按钮，弹出 400×520 对话框

### 1.2 问题

1. **割裂**：用户想"对比 688256 和 688041" / "我的持仓风险" / "半导体行业前景" 之类的综合问题，没有合适入口
2. **浮窗简陋**：`LLMChat` 没有持久化、没有上下文管理、调用的是早期 `run_llm_analysis`，未走 LLM 路由
3. **原个股分析页**：静态表单 + 一次性结果，缺少连续追问能力

### 1.3 目标

将"个股分析"入口改造为**智能分析（AI Agent）** 页面，集成 ReAct 多步 Agent、多会话管理、多 skill 工具调用，给用户"咨询一位 AI 投资顾问"的专业体验。

---

## 二、关键决策（已确认）

| 维度 | 决策 | 理由 |
|------|------|------|
| **入口位置** | 侧边栏"个股分析"改名为"智能分析"（路由 `/fundamental` → `/ai-analyst`）| 用户明确要求 |
| **Agent 架构** | ReAct 多步 Agent（function calling 自动路由）| 用户明确要求 "感知-决策-行动-闭环" |
| **会话管理** | 多会话管理（侧边栏切换）| 用户明确要求 |
| **感知能力** | 查询任意股票数据 | 用户明确要求 |
| **报告保存** | MD + HTML 双按钮 | 用户明确要求 |
| **原浮窗** | 删除 `LLMChat.tsx` | 用户明确要求 |
| **原个股分析页** | 删除 `Fundamental.tsx`（功能由 Agent skill 提供）| 用户明确要求 |
| **原 12 维分析** | 作为 Agent 的 `analyze_stock` skill | 用户明确要求 |

---

## 三、整体架构

```
┌─────────────────────────────────────────────┐
│ 智能分析页面 (AIAgent.tsx, 路由 /ai-analyst) │
│ ┌──────────┬──────────────────────────────┐ │
│ │ 会话列表 │ 对话区                        │ │
│ │ (左 240) │ - 用户消息（蓝气泡）         │ │
│ │ +新建    │ - Agent 消息（白卡片）       │ │
│ │  ·会话A  │   - 💭 思考中...            │ │
│ │  ·会话B  │   - 🔧 调用 个股分析 skill  │ │
│ │          │   - ✅ 结果 (12 维表格)     │ │
│ │          │   - 💾 保存为 MD/HTML        │ │
│ │          │ - 输入框 + 发送             │ │
│ └──────────┴──────────────────────────────┘ │
└─────────────────────────────────────────────┘
                ↓ Tauri invoke (SSE 流)
        ┌────────────────────┐
        │ Rust 调度层         │
        │ (run_agent 入口)   │
        └────────────────────┘
                ↓
        ┌────────────────────────────────┐
        │ Python Agent 引擎（新增）       │
        │ 1. 接收消息 + 会话历史          │
        │ 2. function calling 路由 skill  │
        │ 3. ReAct 循环（最多 5 步）      │
        │ 4. 输出 SSE 流（思考+工具+结果）│
        └────────────────────────────────┘
                ↓
        ┌────────────────────────────────┐
        │ Skills (Python 函数)            │
        │ ① analyze_stock (个股)         │
        │ ② analyze_portfolio (持仓)     │
        │ ③ recommend_candidates (候选)  │
        │ ④ analyze_market (大盘)        │
        │ ⑤ analyze_industry (行业)      │
        │ ⑥ search_stock (查任意股)       │
        └────────────────────────────────┘
```

---

## 四、Skill 工具集（6 个）

| # | Skill 函数 | 复用现有 | 触发场景示例 | 预计耗时 |
|---|------------|----------|---------------|----------|
| 1 | `analyze_stock(code)` | ✅ 复用 `run_stock_insight.py` | "分析 688256"、"688256 怎么样" | 15-30s |
| 2 | `analyze_portfolio()` | ✅ 复用 `portfolio_analysis.py` | "我的持仓"、"持仓怎么样" | 20-40s |
| 3 | `recommend_candidates()` | ✅ 复用 `candidate_recommend.py` | "推荐股票"、"有什么好股" | 30-50s |
| 4 | `analyze_market()` | 🆕 新增（基于 `stock_realtime` + `stock_fund_flow` 聚合）| "大盘怎么样"、"市场分析" | 15-25s |
| 5 | `analyze_industry(industry_name)` | 🆕 新增（基于 `stock_finance` + `stock_technical` 聚合）| "半导体行业前景"、"新能源怎么样" | 20-35s |
| 6 | `search_stock(query)` | ✅ 复用 `search_stock.py` | "688256 是什么股"、"宁德时代代码" | 3-5s |

**Skill 4（analyze_market）实现要点**：
- 查询 `stock_realtime` 计算大盘涨跌数
- 查询 `stock_fund_flow` 计算总资金净流入
- 查询 `stock_limit_up` 计算涨停数
- LLM 综合输出市场情绪判断

**Skill 5（analyze_industry）实现要点**：
- 用户输入行业名（如"半导体"、"新能源"）
- SQL `SELECT * FROM stock_list WHERE industry LIKE '%半导体%'` 找相关股票
- 聚合这些股票的资金/技术/财务
- LLM 输出行业分析报告

---

## 五、ReAct 循环流程

### 5.1 单步执行示例

用户问："688256 现在能买吗"

```
第 1 步：
  💭 思考: 用户想了解 688256 投资价值，先调个股分析
  🔧 调用: analyze_stock(code="688256")
  👀 观察: 12 维分析结果 + 综合评分 88
  状态: ✓ success

第 2 步：
  💭 思考: 用户问"能买吗"需要看大盘情绪，再调大盘分析
  🔧 调用: analyze_market()
  👀 观察: 大盘偏多，资金净流入 234 亿
  状态: ✓ success

第 3 步：
  💭 思考: 数据齐全，输出最终建议
  ✍️ 输出: "综合评分 88，大盘偏多，建议支撑位 280 附近分批建仓..."
  状态: ✓ 完成
```

### 5.2 多步约束

- **最多 5 步循环**（防止无限循环 / 成本失控）
- **每步超时 60 秒**
- **总超时 5 分钟**
- **失败处理**：单 skill 失败时继续执行，错误信息注入观察

### 5.3 function calling 协议

LLM 通过 OpenAI 兼容 SDK 的 `tools` 参数声明：

```json
[
  {
    "type": "function",
    "function": {
      "name": "analyze_stock",
      "description": "对单只股票进行 12 维深度分析，包括基本面/技术/估值/资金等",
      "parameters": {
        "type": "object",
        "properties": {
          "code": {"type": "string", "description": "股票代码，如 688256"}
        },
        "required": ["code"]
      }
    }
  },
  // ... 其他 5 个
]
```

---

## 六、UI 设计

### 6.1 整体布局

```
┌────────────────────────────────────────────────────────────┐
│ 顶栏: 🤖 智能分析                          [⚙️ 设置] [清空] │
├──────────────┬─────────────────────────────────────────────┤
│ 会话列表      │ 消息区（流式渲染）                          │
│ ┌──────────┐ │                                              │
│ │ ➕ 新建   │ │  ┌─────────────────────────┐                │
│ └──────────┘ │  │ 👤 用户                  │                │
│              │  │ 688256 现在能买吗         │                │
│ 📌 当前       │  └─────────────────────────┘                │
│ 宁德时代分析  │                                              │
│ • 12:34      │  ┌─────────────────────────┐                │
│              │  │ 🤖 Agent                │                │
│ 🕐 半导体行业 │  │ 💭 思考中：用户想了解     │                │
│ • 昨天       │  │   688256 投资价值...     │                │
│              │  │                          │                │
│ 🕐 持仓诊断   │  │ 🔧 调用 个股分析 skill   │                │
│ • 3天前      │  │    ⏳ 加载中...          │                │
│              │  │                          │                │
│ 🕐 大盘看法   │  │ ✅ 12 维分析结果         │                │
│ • 上周       │  │ ┌──────┬──────┬──────┐  │                │
│              │  │ │基本面 │财务  │行业  │  │                │
│              │  │ │9.2/10│8.8   │8.5   │  │                │
│              │  │ ├──────┼──────┼──────┤  │                │
│              │  │ │技术面│资金  │估值  │  │                │
│              │  │ │9.0   │9.5   │7.8   │  │                │
│              │  │ └──────┴──────┴──────┘  │                │
│              │  │                          │                │
│              │  │ 💡 综合建议              │                │
│              │  │ 综合评分 88，建议支撑位   │                │
│              │  │ 280 附近分批建仓...       │                │
│              │  │                          │                │
│              │  │ [💾 保存为 MD] [🌐 HTML] │                │
│              │  └─────────────────────────┘                │
│              │                                              │
│              ├──────────────────────────────────────────────┤
│              │ 输入区                                        │
│              │ [📎 添加股票] [💡 示例问题 ▼]                │
│              │ ┌──────────────────────────────────────┐ [发送 ➤]
│              │ │ 输入你的问题...                        │         │
│              │ └──────────────────────────────────────┘         │
└──────────────┴──────────────────────────────────────────────┘
```

### 6.2 消息类型（4 种）

| 类型 | 渲染 | 来源 | 颜色方案 |
|------|------|------|----------|
| **用户消息** | 蓝气泡，右对齐 | 用户输入 | 蓝（`var(--primary)`） |
| **Agent 思考** | 灰色小字 + 💭 动画 | ReAct 内部 | 浅灰（`#888`） |
| **工具调用卡片** | 紫色卡片，显示 skill 名 + 状态 | function_call 拦截 | 紫（`#7c5cfc`） |
| **最终回答** | 白色卡片（Agent 头像在左）| LLM 综合输出 | 白底 + Markdown 渲染 |

### 6.3 工具调用卡片状态

| 状态 | 视觉 | 含义 |
|------|------|------|
| `running` | ⏳ 转圈 + 紫色 | 正在执行 |
| `success` | ✓ 绿色 + 完整结果 | 成功 |
| `error` | ✗ 红色 + 错误信息 | 失败 |

### 6.4 特殊交互

| 元素 | 行为 |
|------|------|
| **📎 添加股票** | 弹出股票搜索框，结果以 `@688256` 形式插入输入框 |
| **💡 示例问题** | 下拉菜单，预设 10 个示例 |
| **重命名会话** | 双击会话名 → inline edit |
| **删除会话** | 悬停显示 🗑️ 图标 |
| **保存为 MD** | 调用 `agent_export(session_id, msg_id, "md")` |
| **保存为 HTML** | 调用 `agent_export(session_id, msg_id, "html")`，带 CSS 样式 |

### 6.5 Markdown 渲染

Agent 回答中的 Markdown：
- 标题（h1-h4）
- 列表（有序/无序）
- 表格
- 代码块
- 引用
- 链接

---

## 七、数据模型（SQLite）

新增 3 张表到 `backend/stock-analyst/data/stock_data.db`：

```sql
-- 1. 会话表
CREATE TABLE agent_session (
    id              TEXT PRIMARY KEY,         -- UUID v4
    title           TEXT NOT NULL,            -- 会话名（默认"新会话"，可改名）
    created_at      DATETIME DEFAULT (datetime('now', 'localtime')),
    updated_at      DATETIME DEFAULT (datetime('now', 'localtime')),
    message_count   INTEGER DEFAULT 0,        -- 消息数（用于排序）
    is_pinned       INTEGER DEFAULT 0,        -- 0/1
    last_message    TEXT                      -- 最后一条消息预览（前 100 字）
);
CREATE INDEX idx_session_updated ON agent_session(updated_at DESC);

-- 2. 消息表
CREATE TABLE agent_message (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id      TEXT NOT NULL,
    role            TEXT NOT NULL,            -- 'user' | 'assistant' | 'tool'
    content         TEXT,                     -- 消息内容（Markdown / 纯文本）
    tool_calls      TEXT,                     -- JSON: [{name, args, result, status}]
    created_at      DATETIME DEFAULT (datetime('now', 'localtime')),
    token_count     INTEGER,                  -- LLM token 消耗
    duration_ms     INTEGER,                  -- 响应耗时
    FOREIGN KEY (session_id) REFERENCES agent_session(id) ON DELETE CASCADE
);
CREATE INDEX idx_msg_session ON agent_message(session_id, created_at);

-- 3. 导出历史表（可选，便于追溯）
CREATE TABLE agent_export (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id      TEXT NOT NULL,
    message_id      INTEGER,
    format          TEXT NOT NULL,            -- 'md' | 'html'
    file_path       TEXT NOT NULL,
    created_at      DATETIME DEFAULT (datetime('now', 'localtime')),
    FOREIGN KEY (session_id) REFERENCES agent_session(id) ON DELETE CASCADE
);
```

### Tool Call JSON 结构

`agent_message.tool_calls` 字段存储：

```json
[
  {
    "name": "analyze_stock",
    "args": {"code": "688256"},
    "status": "success",
    "result_preview": "综合评分 88，建议...",
    "duration_ms": 12500
  }
]
```

### 前端 TypeScript 类型

```typescript
interface AgentSession {
  id: string;
  title: string;
  createdAt: string;
  updatedAt: string;
  messageCount: number;
  isPinned: boolean;
  lastMessage?: string;
}

interface AgentMessage {
  id: number;
  sessionId: string;
  role: "user" | "assistant" | "tool";
  content: string;
  toolCalls?: ToolCall[];
  createdAt: string;
  tokenCount?: number;
  durationMs?: number;
}

interface ToolCall {
  name: string;
  args: Record<string, any>;
  status: "running" | "success" | "error";
  resultPreview?: string;
  durationMs?: number;
}
```

---

## 八、Tauri Commands（新增 8 个）

| Command | 参数 | 返回 | 功能 |
|---------|------|------|------|
| `agent_create_session` | `title?: string` | `AgentSession` | 创建新会话 |
| `agent_list_sessions` | - | `AgentSession[]` | 列出所有会话（按 updated_at 倒序）|
| `agent_rename_session` | `id: string, title: string` | `void` | 重命名 |
| `agent_delete_session` | `id: string` | `void` | 删除（CASCADE）|
| `agent_pin_session` | `id: string, pinned: bool` | `void` | 置顶/取消 |
| `agent_get_messages` | `session_id: string` | `AgentMessage[]` | 加载历史 |
| `agent_send_message` | `session_id: string, text: string` | **SSE 流** | 核心入口 |
| `agent_export` | `session_id: string, message_id: number, format: "md" \| "html"` | `string` (文件路径) | 导出 |

### 8.1 `agent_send_message` SSE 事件协议

```
event: thinking
data: {"step": 1, "content": "用户想了解 688256 投资价值..."}

event: tool_call
data: {"name": "analyze_stock", "args": {"code": "688256"}, "status": "running"}

event: tool_result
data: {"name": "analyze_stock", "status": "success", "result_preview": "...", "duration_ms": 12500}

event: thinking
data: {"step": 2, "content": "继续看大盘情绪..."}

event: tool_call
data: {"name": "analyze_market", "status": "running"}

event: tool_result
data: {"name": "analyze_market", "status": "success", "result_preview": "...", "duration_ms": 8000}

event: final_answer
data: {"content": "综合评分 88，大盘偏多，建议...", "markdown": true}

event: done
data: {"message_id": 123, "token_count": 1234, "duration_ms": 30500}
```

---

## 九、Python Agent 引擎（新增）

### 9.1 文件位置

- `backend/ai/agent.py`（核心引擎）
- `backend/ai/skills.py`（skill 注册表）
- `backend/ai/prompts/agent_system.md`（system prompt 模板）

### 9.2 `agent.py` 主要类

```python
class StockAgent:
    def __init__(self, config: LLMConfig):
        self.client = OpenAI(...)
        self.skills = SkillRegistry()
        self.max_steps = 5
        self.step_timeout = 60  # 秒
        self.total_timeout = 300  # 秒

    def run(self, user_message: str, history: list, session_id: str) -> Iterator[SSEEvent]:
        """ReAct 循环主入口"""
        for event in self._react_loop(user_message, history, session_id):
            yield event

    def _react_loop(self, user_message, history, session_id) -> Iterator[SSEEvent]:
        messages = self._build_messages(user_message, history)
        for step in range(1, self.max_steps + 1):
            # 思考 + tool_calls
            response = self.client.chat.completions.create(
                model=self.config.model,
                messages=messages,
                tools=self.skills.to_openai_tools(),
                tool_choice="auto",
                response_format={"type": "json_object"},  # 仅在最终回答时
            )
            # 解析 tool_calls 或最终回答
            ...
```

### 9.3 `skills.py` 6 个 skill

```python
class SkillRegistry:
    def __init__(self):
        self.skills = {
            "analyze_stock": Skill(
                name="analyze_stock",
                description="对单只股票进行 12 维深度分析",
                parameters={"code": "string"},
                func=self.analyze_stock,
            ),
            # ... 其他 5 个
        }

    def analyze_stock(self, code: str) -> str:
        """调用 run_stock_insight.py"""
        # 复用现有 run_stock_insight 逻辑
        ...
```

### 9.4 `agent_system.md` 关键内容

```markdown
# 角色
你是"衡势价值"AI 投资顾问，专业的 A 股研究分析师。

# 能力
你能调用以下工具（skills）来帮助用户：
1. analyze_stock(code) - 个股深度分析
2. analyze_portfolio() - 用户持仓诊断
3. recommend_candidates() - 推荐候选股
4. analyze_market() - 大盘分析
5. analyze_industry(name) - 行业分析
6. search_stock(query) - 股票代码查询

# 工作原则
- 回答用户问题时，先思考（💭）需要调用哪些 skill
- 必要时连续调用多个 skill，综合输出
- 最终回答使用 Markdown 格式，可读性强
- 引用具体数据，不要编造
- 明确风险提示
```

---

## 十、报告导出

### 10.1 MD 格式

```markdown
# 智能分析报告 - 688256 寒武纪

**生成时间**: 2026-06-18 14:23
**会话**: 宁德时代分析
**分析步骤**: 2 步

## 综合建议
综合评分 88，大盘偏多，建议支撑位 280 附近分批建仓...

## 12 维分析
| 维度 | 评分 | 摘要 |
|------|------|------|
| 基本面 | 9.2/10 | ... |
...
```

### 10.2 HTML 格式

带内嵌 CSS（响应式 + 卡片样式）：

```html
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>智能分析报告 - 688256</title>
  <style>
    body { font-family: -apple-system, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; background: #fafafa; }
    .card { background: #fff; border-radius: 8px; padding: 20px; margin: 16px 0; box-shadow: 0 1px 4px rgba(0,0,0,0.06); }
    .score { color: #16a34a; font-weight: 700; }
    table { width: 100%; border-collapse: collapse; }
    th, td { padding: 8px; border-bottom: 1px solid #eee; text-align: left; }
  </style>
</head>
<body>
  <h1>智能分析报告 - 688256 寒武纪</h1>
  <div class="card">
    <h2>综合建议</h2>
    <p>综合评分 <span class="score">88</span>，大盘偏多，建议支撑位 280 附近分批建仓...</p>
  </div>
  ...
</body>
</html>
```

### 10.3 文件位置

`~/Documents/衡势价值/智能分析报告/{session_title}_{message_id}_{timestamp}.{md|html}`

---

## 十一、实施步骤（5 阶段，3-4 周）

| 阶段 | 内容 | 周期 | 验收标准 |
|------|------|------|----------|
| **1. 后端 Agent 引擎** | Python `agent.py` + ReAct 循环 + 6 个 skill | 5 天 | `python agent.py` 能跑通单步 function calling |
| **2. SQLite + Tauri** | 3 张表 + 8 个 commands | 3 天 | Rust 单元测试通过 |
| **3. 前端骨架** | 路由 `/ai-analyst` + 会话列表 + 输入框 | 3 天 | 能看到空对话界面 |
| **4. 流式渲染 + 工具卡片** | SSE 流解析 + 4 种消息类型 | 4 天 | 看到完整思考+工具+结果流程 |
| **5. 报告导出 + 优化** | MD/HTML 导出 + 性能 + 错误处理 | 3 天 | 点击按钮能保存 |

**关键依赖**：
- 阶段 1 + 2 → 阶段 4（流式渲染）
- 阶段 4 → 阶段 5（导出）
- 阶段 3 独立并行

---

## 十二、文件变更清单

| 操作 | 文件 |
|------|------|
| **删除** | `src/components/LLMChat.tsx`、`src/pages/Fundamental.tsx`（备份到 `archive/`）|
| **新增** | `src/pages/AIAgent.tsx`、`src/components/agent/SessionList.tsx`、`src/components/agent/MessageList.tsx`、`src/components/agent/MessageItem.tsx`、`src/components/agent/ToolCallCard.tsx`、`src/components/agent/InputBox.tsx`、`src/services/agent.ts`、`backend/ai/agent.py`、`backend/ai/skills.py`、`backend/ai/prompts/agent_system.md` |
| **修改** | `src/components/Layout.tsx`（移除 LLMChat）、`src/components/Sidebar.tsx`（改名 + 路径）、`src/App.tsx`（路由）、`src/services/api.ts`（新增 8 个 invoke）、`src-tauri/src/commands.rs`（新增 8 个 commands）、`src-tauri/src/main.rs`（注册）|

---

## 十三、风险与缓解

| 风险 | 缓解措施 |
|------|----------|
| **LLM 调用成本高** | 限制 max_steps=5；用户级 token 计数；可选模型降级 |
| **ReAct 循环不收敛** | 严格 max_steps + total_timeout；检测重复工具调用 |
| **Skill 调用失败** | 失败信息注入观察循环，不中断整体 |
| **响应延迟长** | 流式 SSE 输出，用户看到"思考中"提示 |
| **数据库历史膨胀** | 单会话最多 100 条消息（超出截断） |
| **历史泄露隐私** | 所有数据本地 SQLite，不上传云端 |

---

## 十四、未来扩展

不在本设计范围，但可作为后续迭代：
- 多 Agent 协作（投资策略 Agent + 风控 Agent + 选股 Agent）
- 工具市场（用户可自定义 skill）
- 知识库（RAG 接入历史报告）
- 多模态（K 线图截图、新闻图片理解）

---

**Spec 版本**：v1.0
**下一步**：用户审阅 → writing-plans skill → 实施
