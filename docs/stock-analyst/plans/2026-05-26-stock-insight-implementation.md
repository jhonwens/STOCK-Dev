# 个股深度分析模块 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use subagent-driven-development (recommended) or executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Transform the "基本面" static demo page into an interactive stock deep analysis tool with LLM-driven insights, export, and watchlist integration.

**Architecture:** New Python sidecar (`stock_insight.py`) collects 12-dimension data and calls LLM for single-stock deep analysis. Rust commands bridge frontend and Python. React frontend replaces the static page with an input-driven analysis tool focused on buy points.

**Tech Stack:** Python 3 + SQLite (data collection), LLM (analysis), Rust/Tauri (IPC), React/TypeScript (frontend)

---

### Task 1: Add TypeScript types for stock insight

**Files:**
- Modify: `src/types/index.ts` (append after `CandidateRecommendation`)

- [ ] **Add StockInsightResult, BuyPointAnalysis, BuyPointLevel types**

Append to `src/types/index.ts`:

```typescript
export interface BuyPointLevel {
  point: string;
  price_range: [number, number];
  confidence: string;
  detail: string;
}

export interface BuyPointAnalysis {
  summary: string;
  short_term: BuyPointLevel;
  mid_term: BuyPointLevel;
  long_term: BuyPointLevel;
  position_suggestion: string;
  key_indicators: {
    support_level: number;
    resistance_level: number;
    stop_loss: number;
  };
}

export interface StockInsightResult {
  basic_info: {
    code: string;
    name: string;
    industry: string;
    price: number;
    change_pct: number;
    pe: number;
    pb: number;
  };
  buy_point_analysis: BuyPointAnalysis;
  analysis_12dim: Record<string, string>;
  risk_warning: string;
}

export interface StockSearchResult {
  code: string;
  name: string;
  industry: string;
}
```

- [ ] **Verify types compile**

Run: `cd /Users/ws/Desktop/Project/Trea-Project/STOCK-Dev && npx tsc --noEmit 2>&1 | tail -10`
Expected: No new type errors

---

### Task 2: Create LLM prompt for stock insight

**Files:**
- Create: `backend/ai/prompts/stock_insight.md`

- [ ] **Create the prompt file**

Content:

```markdown
# Stock Insight Prompt

You are a professional stock analyst. Your task is to perform a deep analysis of a single stock and provide actionable buy-point recommendations.

## Input Data

You will receive a JSON object with the stock's 12 dimensions of data:
1. 基本面分析 (Fundamental Analysis)
2. 财务经营分析 (Financial Analysis)
3. 行业价值趋势 (Industry Trend)
4. 热点信息影响 (News/Hot Topics)
5. 建议买入价格分布 (Suggested Buy Price Range)
6. 技术面综合评分 (Technical Score)
7. 估值对比分析 (Valuation Analysis)
8. 资金流向分析 (Capital Flow)
9. 机构持仓变动 (Institutional Holdings)
10. 风险指标 (Risk Metrics)
11. 同业竞争力对比 (Competitive Analysis)
12. 催化事件日历 (Catalyst Calendar)

## Your Task

Analyze the stock comprehensively and provide:

### 1. Buy Point Analysis (重点)
This is the MOST IMPORTANT section. Provide specific, actionable buy points for three time horizons:

- **短期 (Short-term, 1-4 weeks)**: Focus on technical signals (KDJ/MACD/RSI), capital flow, recent news catalysts
- **中期 (Mid-term, 1-3 months)**: Focus on trend following, valuation reversion, industry momentum
- **长期 (Long-term, 6+ months)**: Focus on fundamental value, ROE sustainability, competitive moat

For each horizon, include:
- Specific buy signal/trigger
- Suggested price range
- Confidence level (高/中/低)
- Detailed reasoning

### 2. Deep 12-Dimension Analysis
Provide detailed analysis for each of the 12 dimensions. Be specific with data points.

### 3. Risk Warning
Highlight key risks the investor should monitor.

## Output Format

Return valid JSON with this exact structure:

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
    "summary": "综合判断...",
    "short_term": {
      "point": "KDJ金叉形成，主力资金连续净流入",
      "price_range": [1520, 1540],
      "confidence": "高",
      "detail": "日线级别..."
    },
    "mid_term": {
      "point": "MACD周线金叉，估值处于低位",
      "price_range": [1480, 1520],
      "confidence": "中",
      "detail": "周线MACD..."
    },
    "long_term": {
      "point": "PE历史低位，ROE稳定30%+",
      "price_range": [1400, 1500],
      "confidence": "高",
      "detail": "当前PE-TTM..."
    },
    "position_suggestion": "建议30%仓位先建底仓，回调加仓",
    "key_indicators": {
      "support_level": 1480,
      "resistance_level": 1600,
      "stop_loss": 1420
    }
  },
  "analysis_12dim": {
    "基本面": "detailed analysis",
    "财务经营": "detailed analysis",
    "行业趋势": "detailed analysis",
    "热点信息": "detailed analysis",
    "建议买入价格": "detailed analysis",
    "技术面": "detailed analysis",
    "估值对比": "detailed analysis",
    "资金流向": "detailed analysis",
    "机构持仓": "detailed analysis",
    "风险指标": "detailed analysis",
    "同业对比": "detailed analysis",
    "催化事件": "detailed analysis"
  },
  "risk_warning": "主要风险..."
}
```

## Rules
- Output ONLY valid JSON, no markdown wrapping
- Be specific with price levels, dates, and data points
- Buy point analysis must be actionable, not generic
- All 12 dimensions must be filled
```

- [ ] **Verify file created**

Run: `wc -l /Users/ws/Desktop/Project/Trea-Project/STOCK-Dev/backend/ai/prompts/stock_insight.md`
Expected: ~100 lines

---

### Task 3: Create Python analysis script (stock_insight.py)

**Files:**
- Create: `backend/stock-analyst/scripts/stock_insight.py`

- [ ] **Create the script**

```python
#!/usr/bin/env python3
import json
import sys
import os
import argparse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from db_manager import DBManager
from llm_client import LLMClient

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "stock_data.db")


def collect_stock_data(db, code):
    conn = __import__('sqlite3').connect(db.db_path)
    c = conn.cursor()
    item = {"code": code, "name": "", "price": 0, "change_pct": 0, "pe": 0, "pb": 0,
            "roe": 0, "revenue_growth": 0, "profit_growth": 0, "eps": 0, "bvps": 0,
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
        item["revenue_growth"] = float(row[1] or 0)
        item["profit_growth"] = float(row[2] or 0)
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
    response, error = client.chat(user_message, system_prompt=system_prompt, max_tokens=8000)

    if error:
        print(json.dumps({"error": error}, ensure_ascii=False))
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
        print(json.dumps({"error": "LLM返回格式错误", "raw": response}, ensure_ascii=False))


if __name__ == "__main__":
    main()
```

- [ ] **Verify Python syntax**

Run: `python3 -c "import py_compile; py_compile.compile('/Users/ws/Desktop/Project/Trea-Project/STOCK-Dev/backend/stock-analyst/scripts/stock_insight.py', doraise=True)"`
Expected: No syntax errors

---

### Task 4: Add Rust commands for stock insight

**Files:**
- Modify: `src-tauri/src/commands.rs`

- [ ] **Add `run_stock_insight` command**

Append after `export_candidate_md`:

```rust
#[tauri::command]
pub fn search_stock(query: String) -> Result<String, String> {
    let conn = Connection::open(&db_path()).map_err(|e| e.to_string())?;
    let pattern = format!("%{}%", query);
    let mut stmt = conn.prepare(
        "SELECT code, name, industry FROM stock_realtime WHERE name LIKE ?1 OR code LIKE ?1 LIMIT 10"
    ).map_err(|e| e.to_string())?;
    let results: Vec<serde_json::Value> = stmt.query_map(
        rusqlite::params![pattern],
        |row| {
            let code: String = row.get(0)?;
            let name: String = row.get(1)?;
            let industry: String = row.get(2).unwrap_or_default();
            Ok(serde_json::json!({"code": code, "name": name, "industry": industry}))
        },
    ).map_err(|e| e.to_string())?.filter_map(|r| r.ok()).collect();
    Ok(serde_json::to_string(&results).map_err(|e| e.to_string())?)
}

#[tauri::command]
pub async fn run_stock_insight(code: String) -> Result<String, String> {
    let script_dir = python_script_dir()?;
    let output = tokio::process::Command::new("python3")
        .arg("stock_insight.py")
        .arg("--code")
        .arg(&code)
        .current_dir(&script_dir)
        .output()
        .await
        .map_err(|e| format!("Failed: {}", e))?;
    if output.status.success() {
        Ok(String::from_utf8_lossy(&output.stdout).to_string())
    } else {
        Err(String::from_utf8_lossy(&output.stderr).to_string())
    }
}

#[tauri::command]
pub fn save_stock_insight(code: String, analysis_json: String) -> Result<String, String> {
    let conn = Connection::open(&db_path()).map_err(|e| e.to_string())?;
    conn.execute(
        "INSERT OR REPLACE INTO stock_llm_report (report_type, scope, content, created_at) \
         VALUES ('stock_insight', ?1, ?2, \
         COALESCE((SELECT created_at FROM stock_llm_report WHERE report_type='stock_insight' AND scope=?1), datetime('now','localtime')))",
        rusqlite::params![code, analysis_json],
    ).map_err(|e| e.to_string())?;
    Ok("saved".to_string())
}

#[tauri::command]
pub fn load_stock_insight(code: String) -> Result<String, String> {
    let conn = Connection::open(&db_path()).map_err(|e| e.to_string())?;
    match conn.query_row(
        "SELECT content, created_at FROM stock_llm_report WHERE report_type='stock_insight' AND scope=?1 ORDER BY id DESC LIMIT 1",
        rusqlite::params![code],
        |row| {
            let content: String = row.get(0)?;
            let created_at: String = row.get(1)?;
            Ok(format!("{{\"data\":{},\"updated_at\":\"{}\"}}", content, created_at))
        },
    ) {
        Ok(r) => Ok(r),
        Err(rusqlite::Error::QueryReturnedNoRows) => Ok("{}".to_string()),
        Err(e) => Err(e.to_string()),
    }
}

#[tauri::command]
pub fn export_stock_insight_md(code: String, name: String, analysis_json: String) -> Result<String, String> {
    let parsed: serde_json::Value = serde_json::from_str(&analysis_json).map_err(|e| e.to_string())?;
    let mut md = String::new();

    md.push_str(&format!("# {}（{}）个股深度分析报告\n\n", name, code));
    md.push_str("---\n\n");

    if let Some(basic) = parsed.get("basic_info") {
        md.push_str("## 基本信息\n\n");
        md.push_str(&format!("- **代码**：{}\n", basic.get("code").and_then(|v| v.as_str()).unwrap_or("")));
        md.push_str(&format!("- **名称**：{}\n", basic.get("name").and_then(|v| v.as_str()).unwrap_or("")));
        md.push_str(&format!("- **行业**：{}\n", basic.get("industry").and_then(|v| v.as_str()).unwrap_or("")));
        md.push_str(&format!("- **现价**：{:.2}\n", basic.get("price").and_then(|v| v.as_f64()).unwrap_or(0.0)));
        md.push_str(&format!("- **涨跌幅**：{:.2}%\n", basic.get("change_pct").and_then(|v| v.as_f64()).unwrap_or(0.0)));
        md.push_str(&format!("- **PE**：{:.1}\n", basic.get("pe").and_then(|v| v.as_f64()).unwrap_or(0.0)));
        md.push_str(&format!("- **PB**：{:.1}\n\n", basic.get("pb").and_then(|v| v.as_f64()).unwrap_or(0.0)));
    }

    if let Some(bpa) = parsed.get("buy_point_analysis") {
        md.push_str("## 🎯 买入点分析\n\n");
        if let Some(s) = bpa.get("summary").and_then(|v| v.as_str()) {
            md.push_str(&format!("> {}\n\n", s));
        }
        for (key, label) in [("short_term", "🟢 短期"), ("mid_term", "🟡 中期"), ("long_term", "🔵 长期")] {
            if let Some(level) = bpa.get(key) {
                md.push_str(&format!("### {}买入点\n\n", label));
                md.push_str(&format!("- **信号**：{}\n", level.get("point").and_then(|v| v.as_str()).unwrap_or("")));
                if let Some(pr) = level.get("price_range").and_then(|v| v.as_array()) {
                    if pr.len() >= 2 {
                        let low = pr[0].as_f64().unwrap_or(0.0);
                        let high = pr[1].as_f64().unwrap_or(0.0);
                        md.push_str(&format!("- **建议区间**：{:.2} — {:.2}\n", low, high));
                    }
                }
                md.push_str(&format!("- **信心评级**：{}\n", level.get("confidence").and_then(|v| v.as_str()).unwrap_or("")));
                md.push_str(&format!("- **分析**：{}\n\n", level.get("detail").and_then(|v| v.as_str()).unwrap_or("")));
            }
        }
        if let Some(ps) = bpa.get("position_suggestion").and_then(|v| v.as_str()) {
            md.push_str(&format!("**仓位建议**：{}\n\n", ps));
        }
        if let Some(ki) = bpa.get("key_indicators") {
            md.push_str("- **关键价位**：\n");
            md.push_str(&format!("  - 支撑位：{:.0}\n", ki.get("support_level").and_then(|v| v.as_f64()).unwrap_or(0.0)));
            md.push_str(&format!("  - 阻力位：{:.0}\n", ki.get("resistance_level").and_then(|v| v.as_f64()).unwrap_or(0.0)));
            md.push_str(&format!("  - 止损位：{:.0}\n\n", ki.get("stop_loss").and_then(|v| v.as_f64()).unwrap_or(0.0)));
        }
    }

    if let Some(dims) = parsed.get("analysis_12dim").and_then(|v| v.as_object()) {
        md.push_str("## 📊 12 维深度分析\n\n");
        for (key, val) in dims {
            if let Some(text) = val.as_str() {
                if !text.is_empty() {
                    md.push_str(&format!("### {}\n\n{}\n\n", key, text));
                }
            }
        }
    }

    if let Some(rw) = parsed.get("risk_warning").and_then(|v| v.as_str()) {
        md.push_str("## ⚠️ 风险提示\n\n");
        md.push_str(&format!("{}\n\n", rw));
    }

    md.push_str("---\n");
    md.push_str("_报告由 衡势价值 自动生成_\n");

    let reports_dir = project_root().join("reference").join("analysis");
    std::fs::create_dir_all(&reports_dir).map_err(|e| format!("创建目录失败: {}", e))?;
    let file_name = format!("{}-{}-深度分析.md", code, name);
    let file_path = reports_dir.join(&file_name);
    std::fs::write(&file_path, &md).map_err(|e| format!("保存文件失败: {}", e))?;
    Ok(file_path.to_string_lossy().to_string())
}
```

- [ ] **Verify Rust compiles**

Run: `cd /Users/ws/Desktop/Project/Trea-Project/STOCK-Dev/src-tauri && cargo check 2>&1 | tail -10`
Expected: `Finished` with no errors

---

### Task 5: Register commands in main.rs

**Files:**
- Modify: `src-tauri/src/main.rs`

- [ ] **Add new commands to invoke_handler**

Insert after `commands::export_candidate_md,`:

```rust
            commands::search_stock,
            commands::run_stock_insight,
            commands::save_stock_insight,
            commands::load_stock_insight,
            commands::export_stock_insight_md,
```

- [ ] **Verify Rust compiles**

Run: `cd /Users/ws/Desktop/Project/Trea-Project/STOCK-Dev/src-tauri && cargo check 2>&1 | tail -10`
Expected: `Finished` with no errors

---

### Task 6: Add frontend API functions

**Files:**
- Modify: `src/services/api.ts`

- [ ] **Add stock insight API functions**

Append to `src/services/api.ts`:

```typescript
export async function searchStock(query: string): Promise<string> {
  return invoke("search_stock", { query });
}

export async function runStockInsight(code: string): Promise<string> {
  return invoke("run_stock_insight", { code });
}

export async function saveStockInsight(code: string, analysisJson: string): Promise<string> {
  return invoke("save_stock_insight", { code, analysisJson });
}

export async function loadStockInsight(code: string): Promise<string> {
  return invoke("load_stock_insight", { code });
}

export async function exportStockInsightMd(code: string, name: string, analysisJson: string): Promise<string> {
  return invoke("export_stock_insight_md", { code, name, analysisJson });
}
```

- [ ] **Verify TypeScript compiles**

Run: `cd /Users/ws/Desktop/Project/Trea-Project/STOCK-Dev && npx tsc --noEmit 2>&1 | tail -10`
Expected: No new type errors

---

### Task 7: Rewrite Fundamental.tsx → StockInsight.tsx

**Files:**
- Modify: `src/pages/Fundamental.tsx` (full rewrite as StockInsight)

- [ ] **Rewrite the page with stock insight UI**

```typescript
import { useState, useCallback } from "react";
import {
  searchStock,
  runStockInsight,
  saveStockInsight,
  loadStockInsight,
  exportStockInsightMd,
} from "../services/api";
import type { StockInsightResult, StockSearchResult, BuyPointLevel } from "../types";

const DIMENSION_LABELS: Record<string, string> = {
  "基本面": "🏢 基本面分析",
  "财务经营": "💰 财务经营分析",
  "行业趋势": "📈 行业价值趋势",
  "热点信息": "🔥 热点信息影响",
  "建议买入价格": "🎯 建议买入价格分布",
  "技术面": "📊 技术面综合评分",
  "估值对比": "💹 估值对比分析",
  "资金流向": "💧 资金流向分析",
  "机构持仓": "🏛️ 机构持仓变动",
  "风险指标": "⚠️ 风险指标",
  "同业对比": "🤝 同业竞争力对比",
  "催化事件": "📅 催化事件日历",
};

function renderBuyPointCard(label: string, color: string, level: BuyPointLevel | undefined) {
  if (!level) return null;
  const stars = level.confidence === "高" ? "⭐⭐⭐" : level.confidence === "中" ? "⭐⭐" : "⭐";
  return (
    <div style={{
      padding: "14px 16px", marginBottom: 10,
      borderLeft: `4px solid ${color}`,
      background: "#fff", borderRadius: 8,
      boxShadow: "0 1px 4px rgba(0,0,0,0.06)",
    }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 6 }}>
        <span style={{ fontWeight: 600, fontSize: 14, color }}>{label}</span>
        <span style={{ fontSize: 12, color: "#888" }}>{stars}</span>
      </div>
      <div style={{ fontSize: 13, color: "#333", marginBottom: 6, lineHeight: 1.5 }}>{level.point}</div>
      <div style={{ fontSize: 12, color: "#16a34a", fontWeight: 500 }}>
        建议区间: {level.price_range[0].toFixed(0)} — {level.price_range[1].toFixed(0)}
      </div>
      {level.detail && level.detail !== "..." && (
        <div style={{ fontSize: 12, color: "#666", marginTop: 6, lineHeight: 1.6 }}>{level.detail}</div>
      )}
    </div>
  );
}

const addButtonStyle: React.CSSProperties = {
  padding: "6px 14px", fontSize: 12, background: "#fff3e0",
  color: "#e65100", border: "1px solid #ffcc80",
  borderRadius: 6, cursor: "pointer", fontWeight: 500,
};
const exportButtonStyle: React.CSSProperties = {
  padding: "6px 14px", fontSize: 12, background: "#e8f5e9",
  color: "#2e7d32", border: "1px solid #a5d6a7",
  borderRadius: 6, cursor: "pointer", fontWeight: 500,
};

export default function StockInsight() {
  const [query, setQuery] = useState("");
  const [searchResults, setSearchResults] = useState<StockSearchResult[]>([]);
  const [selectedCode, setSelectedCode] = useState("");
  const [selectedName, setSelectedName] = useState("");
  const [insight, setInsight] = useState<StockInsightResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [cacheTime, setCacheTime] = useState("");
  const [mdStatus, setMdStatus] = useState("");
  const [addStatus, setAddStatus] = useState("");

  const handleSearch = useCallback(async () => {
    if (!query.trim()) return;
    setSearchResults([]);
    setSelectedCode("");
    setSelectedName("");
    setInsight(null);
    setCacheTime("");
    setError("");
    try {
      const res = await searchStock(query.trim());
      const data = JSON.parse(res);
      setSearchResults(data || []);
      if (data && data.length === 1) {
        selectStock(data[0]);
      }
    } catch (e) {
      setError(String(e));
    }
  }, [query]);

  const selectStock = async (stock: StockSearchResult) => {
    setSelectedCode(stock.code);
    setSelectedName(stock.name);
    setSearchResults([]);
    setQuery(stock.name);
    setInsight(null);
    setError("");
    setMdStatus("");
    try {
      const cached = await loadStockInsight(stock.code);
      if (cached && cached !== "{}") {
        const p = JSON.parse(cached);
        if (p.data && p.updated_at) {
          setInsight(p.data);
          setCacheTime(p.updated_at);
        }
      }
    } catch {}
  };

  const handleAnalyze = async () => {
    if (!selectedCode) return;
    setLoading(true);
    setError("");
    setMdStatus("");
    try {
      const res = await runStockInsight(selectedCode);
      const data = JSON.parse(res);
      if (data.error) {
        setError(data.error);
      } else {
        setInsight(data);
        saveStockInsight(selectedCode, res).catch(() => {});
      }
    } catch (e) {
      setError(String(e));
    }
    setLoading(false);
  };

  const handleExport = async () => {
    if (!insight || !selectedCode) return;
    try {
      const path = await exportStockInsightMd(selectedCode, selectedName, JSON.stringify(insight));
      setMdStatus(`✅ 已保存: ${path}`);
    } catch (e) {
      setMdStatus(`❌ 导出失败: ${e}`);
    }
  };

  const handleAddWatchlist = async () => {
    if (!selectedCode || !selectedName) return;
    try {
      const { invoke } = await import("@tauri-apps/api/core");
      await invoke("add_portfolio_stock", {
        code: selectedCode, name: selectedName,
        costPrice: 0, shares: 0, category: "候选",
      });
      setAddStatus("✅ 已加入自选股");
    } catch (e) {
      setAddStatus(`❌ 加入失败: ${e}`);
    }
  };

  const bpa = insight?.buy_point_analysis;

  const gridStyle: React.CSSProperties = {
    display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(260px, 1fr))",
    gap: 12, marginTop: 16,
  };
  const cardStyle: React.CSSProperties = {
    padding: 14, background: "#f8f9fa", borderRadius: 10, border: "1px solid #eee",
    fontSize: 13, lineHeight: 1.7,
  };

  return (
    <div>
      <h2 style={{ fontSize: 22, fontWeight: 700, margin: "0 0 16px" }}>📈 个股深度分析</h2>

      <div style={{ display: "flex", gap: 8, marginBottom: 12, flexWrap: "wrap" }}>
        <div style={{ flex: 1, minWidth: 200, display: "flex", gap: 6 }}>
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleSearch()}
            placeholder="输入股票名称或代码"
            style={{
              flex: 1, padding: "8px 12px", fontSize: 14,
              border: "1px solid var(--border)", borderRadius: 8, outline: "none",
            }}
          />
          <button onClick={handleSearch} style={{
            padding: "8px 16px", fontSize: 13, background: "#fff",
            border: "1px solid var(--border)", borderRadius: 8, cursor: "pointer",
          }}>搜索</button>
        </div>
        <button onClick={handleAnalyze} disabled={!selectedCode || loading} style={{
          padding: "8px 18px", fontSize: 13, fontWeight: 600,
          background: !selectedCode ? "#ddd" : "linear-gradient(135deg, #7c5cfc, #5b8def)",
          color: "#fff", border: "none", borderRadius: 8,
          cursor: !selectedCode || loading ? "not-allowed" : "pointer",
          opacity: !selectedCode || loading ? 0.6 : 1,
        }}>
          {loading ? "⏳ 分析中..." : "🤖 AI 分析"}
        </button>
        {insight && (
          <>
            <button onClick={handleExport} style={exportButtonStyle}>💾 导出报告</button>
            <button onClick={handleAddWatchlist} style={addButtonStyle}>➕ 加入自选</button>
          </>
        )}
      </div>

      {searchResults.length > 1 && (
        <div style={{
          marginBottom: 12, border: "1px solid var(--border)",
          borderRadius: 8, overflow: "hidden",
        }}>
          {searchResults.map((s) => (
            <div key={s.code} onClick={() => selectStock(s)}
              style={{
                padding: "10px 14px", cursor: "pointer", fontSize: 13,
                borderBottom: "1px solid #f0f0f0",
              }}
              onMouseEnter={(e) => { e.currentTarget.style.background = "#f5f0ff"; }}
              onMouseLeave={(e) => { e.currentTarget.style.background = "transparent"; }}
            >
              {s.name} ({s.code}) — {s.industry}
            </div>
          ))}
        </div>
      )}

      {cacheTime && (
        <div style={{ fontSize: 12, color: "#888", marginBottom: 8 }}>
          上次分析: {cacheTime} · <span style={{ color: "#7c5cfc", cursor: "pointer" }} onClick={handleAnalyze}>重新分析</span>
        </div>
      )}

      {error && (
        <div style={{ padding: "10px 14px", background: "#fef2f2", border: "1px solid #fecaca", borderRadius: 8, color: "#dc2626", fontSize: 13, marginBottom: 12 }}>
          {error}
        </div>
      )}

      {mdStatus && (
        <div style={{ padding: "10px 14px", background: "#f0fdf4", border: "1px solid #bbf7d0", borderRadius: 8, color: "#16a34a", fontSize: 13, marginBottom: 12 }}>
          {mdStatus}
        </div>
      )}

      {addStatus && (
        <div style={{ padding: "10px 14px", background: "#fff7ed", border: "1px solid #fed7aa", borderRadius: 8, color: "#c2410c", fontSize: 13, marginBottom: 12 }}>
          {addStatus}
        </div>
      )}

      {loading && (
        <div style={{ padding: 40, textAlign: "center", color: "#888", fontSize: 14 }}>
          ⏳ LLM 正在分析 {selectedName}...
        </div>
      )}

      {insight && (
        <div>
          <div style={{
            display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(140px, 1fr))",
            gap: 10, marginBottom: 20,
          }}>
            {[
              { label: "名称", value: insight.basic_info.name },
              { label: "代码", value: insight.basic_info.code },
              { label: "行业", value: insight.basic_info.industry },
              { label: "现价", value: insight.basic_info.price.toFixed(2), color: insight.basic_info.change_pct >= 0 ? "#dc2626" : "#16a34a" },
              { label: "涨跌幅", value: `${insight.basic_info.change_pct >= 0 ? "+" : ""}${insight.basic_info.change_pct.toFixed(2)}%`, color: insight.basic_info.change_pct >= 0 ? "#dc2626" : "#16a34a" },
              { label: "PE", value: insight.basic_info.pe.toFixed(1) },
              { label: "PB", value: insight.basic_info.pb.toFixed(1) },
            ].map((item) => (
              <div key={item.label} style={{ background: "#f0f7ff", borderRadius: 8, padding: "10px 12px" }}>
                <div style={{ fontSize: 11, color: "#888", marginBottom: 2 }}>{item.label}</div>
                <div style={{ fontSize: 15, fontWeight: 600, color: item.color || "#333" }}>{item.value}</div>
              </div>
            ))}
          </div>

          <div style={{ marginBottom: 20 }}>
            <div style={{ fontSize: 16, fontWeight: 700, marginBottom: 10, color: "#16a34a" }}>🎯 买入点分析</div>
            {bpa?.summary && (
              <div style={{
                fontSize: 13, color: "#555", marginBottom: 12,
                padding: "10px 14px", background: "#f0fdf4", borderRadius: 8,
                border: "1px solid #bbf7d0", lineHeight: 1.6,
              }}>
                💡 {bpa.summary}
              </div>
            )}
            {renderBuyPointCard("🟢 短期买入点", "#16a34a", bpa?.short_term)}
            {renderBuyPointCard("🟡 中期买入点", "#ca8a04", bpa?.mid_term)}
            {renderBuyPointCard("🔵 长期买入点", "#2563eb", bpa?.long_term)}
            {bpa?.position_suggestion && (
              <div style={{
                padding: "10px 14px", background: "#f8f9fa", borderRadius: 8,
                fontSize: 13, color: "#333", marginTop: 8,
              }}>
                <strong>仓位建议：</strong>{bpa.position_suggestion}
              </div>
            )}
            {bpa?.key_indicators && (
              <div style={{
                display: "flex", gap: 12, marginTop: 8, fontSize: 12,
              }}>
                <span style={{ color: "#16a34a" }}>支撑: {bpa.key_indicators.support_level.toFixed(0)}</span>
                <span style={{ color: "#dc2626" }}>阻力: {bpa.key_indicators.resistance_level.toFixed(0)}</span>
                <span style={{ color: "#888" }}>止损: {bpa.key_indicators.stop_loss.toFixed(0)}</span>
              </div>
            )}
          </div>

          <div style={{ fontSize: 16, fontWeight: 700, marginBottom: 4 }}>📊 12 维深度分析</div>
          <div style={gridStyle}>
            {Object.entries(DIMENSION_LABELS).map(([key, label]) => {
              const val = insight.analysis_12dim?.[key];
              if (!val || val === "...") return null;
              return (
                <div key={key} style={cardStyle}>
                  <div style={{ fontWeight: 600, marginBottom: 6, fontSize: 13 }}>{label}</div>
                  <div style={{ color: "#555", lineHeight: 1.6, whiteSpace: "pre-wrap", fontSize: 12 }}>
                    {val.length > 150 ? val.slice(0, 150) + "..." : val}
                  </div>
                </div>
              );
            })}
          </div>

          {insight.risk_warning && (
            <div style={{
              marginTop: 20, padding: "12px 16px", background: "#fef2f2",
              border: "1px solid #fecaca", borderRadius: 8,
            }}>
              <div style={{ fontWeight: 600, fontSize: 13, color: "#dc2626", marginBottom: 4 }}>⚠️ 风险提示</div>
              <div style={{ fontSize: 13, color: "#7f1d1d", lineHeight: 1.6 }}>{insight.risk_warning}</div>
            </div>
          )}
        </div>
      )}

      {!loading && !insight && !error && !cacheTime && (
        <div style={{ padding: 60, textAlign: "center", color: "#aaa", fontSize: 14 }}>
          输入股票名称，点击「AI 分析」获取深度分析报告
        </div>
      )}
    </div>
  );
}
```

- [ ] **Delete old Fundamental.tsx if it exists, rename the file or just overwrite**

The file `/Users/ws/Desktop/Project/Trea-Project/STOCK-Dev/src/pages/Fundamental.tsx` will be completely overwritten with the new content. No separate delete needed.

- [ ] **Verify TypeScript compiles**

Run: `cd /Users/ws/Desktop/Project/Trea-Project/STOCK-Dev && npx tsc --noEmit 2>&1 | tail -10`
Expected: No new type errors

---

### Task 8: Update sidebar label

**Files:**
- Modify: `src/components/Sidebar.tsx`

- [ ] **Change label from "基本面" to "个股分析"**

```diff
- { path: "/fundamental", label: "基本面", icon: "📊" },
+ { path: "/fundamental", label: "个股分析", icon: "📈" },
```

- [ ] **Verify TypeScript compiles**

Run: `cd /Users/ws/Desktop/Project/Trea-Project/STOCK-Dev && npx tsc --noEmit 2>&1 | tail -10`
Expected: No new type errors

---

### Task 9: Verify full build

- [ ] **Check Rust compilation**

```bash
cd /Users/ws/Desktop/Project/Trea-Project/STOCK-Dev/src-tauri && cargo check 2>&1 | tail -10
```

Expected: `Finished` with no errors

- [ ] **Check TypeScript compilation**

```bash
cd /Users/ws/Desktop/Project/Trea-Project/STOCK-Dev && npx tsc --noEmit 2>&1 | tail -10
```

Expected: No new type errors (pre-existing errors allowed)

- [ ] **Fix any errors found and re-verify**