# 候选推荐模块 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use subagent-driven-development (recommended) or executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a candidate recommendation module that analyzes the user's stock pool, excludes holdings, and recommends Top 5 short-term + Top 5 long-term stocks with 12-dimension analysis.

**Architecture:** Python sidecar (`candidate_recommend.py`) collects 12-dimension data from SQLite and calls LLM for comprehensive analysis. Rust commands bridge frontend and Python. React frontend displays results in a scrollable card layout with modal detail view.

**Tech Stack:** Python 3 + SQLite (data collection), LLM (analysis), Rust/Tauri (IPC), React/TypeScript (frontend)

---

### Task 1: Add TypeScript types for candidate recommendation

**Files:**
- Modify: `src/types/index.ts` (append after `IndustryGroup`)

- [ ] **Add CandidateStock and CandidateRecommendation types**

Append to `src/types/index.ts`:

```typescript
export interface CandidateStock {
  rank: number;
  code: string;
  name: string;
  overall_score: number;
  recommend_reason: string;
  suggested_price_range: [number, number];
  risk_warning: string;
  holding_period: string;
  analysis_12dim: Record<string, string>;
}

export interface CandidateCategory {
  summary: string;
  top5: CandidateStock[];
}

export interface CandidateRecommendation {
  short_term: CandidateCategory;
  long_term: CandidateCategory;
}
```

- [ ] **Commit**

```bash
git add src/types/index.ts
git commit -m "feat: add CandidateStock and CandidateRecommendation types"
```

---

### Task 2: Create LLM prompt for candidate recommendation

**Files:**
- Create: `backend/ai/prompts/candidate_recommend.md`

- [ ] **Create the prompt file**

Content:

```markdown
# Candidate Recommendation Prompt

You are a professional stock analyst. Your task is to analyze a batch of candidate stocks and recommend the best ones for two investment styles.

## Input Data

You will receive a JSON array of candidate stocks. Each stock has the following 12 dimensions of data:
1. 基本面分析 (Fundamental Analysis) - business model, competitive moat
2. 财务经营分析 (Financial Analysis) - ROE, revenue, profit, EPS, BVPS
3. 行业价值趋势 (Industry Trend) - sector outlook, policy direction
4. 热点信息影响 (News/Hot Topics) - recent news, social sentiment
5. 建议买入价格分布 (Suggested Buy Price Range) - fair value range
6. 技术面综合评分 (Technical Score) - MA trend, MACD, KDJ, RSI, BOLL
7. 估值对比分析 (Valuation Analysis) - PE/PB/PS vs industry average
8. 资金流向分析 (Capital Flow) - main force net inflow/outflow
9. 机构持仓变动 (Institutional Holdings) - fund/north-bound changes
10. 风险指标 (Risk Metrics) - Beta, volatility, max drawdown
11. 同业竞争力对比 (Competitive Analysis) - vs 2-3 peers
12. 催化事件日历 (Catalyst Calendar) - upcoming earnings, product launches

## Your Task

From the provided candidate stocks, select and rank:
1. **中短期持有 Top 5** - Best stocks for short-term trading (1-4 weeks). Prioritize: technical signals, capital flow, news/hot topics, catalysts.
2. **长期价值投资 Top 5** - Best stocks for long-term value investing (6+ months). Prioritize: fundamentals, financials, valuation, institutional holdings, competitive moat.

## Output Format

Return valid JSON with this exact structure:

```json
{
  "short_term": {
    "summary": "Brief market assessment for short-term (Chinese)",
    "top5": [
      {
        "rank": 1,
        "code": "000001",
        "name": "Stock Name",
        "overall_score": 0-100,
        "recommend_reason": "Key reasons for recommendation in Chinese",
        "suggested_price_range": [buy_price_low, buy_price_high],
        "risk_warning": "Risk warning in Chinese",
        "holding_period": "e.g. 1-4周",
        "analysis_12dim": {
          "基本面": "analysis text",
          "财务经营": "analysis text",
          "行业趋势": "analysis text",
          "热点信息": "analysis text",
          "建议买入价格": "analysis text",
          "技术面": "analysis text",
          "估值对比": "analysis text",
          "资金流向": "analysis text",
          "机构持仓": "analysis text",
          "风险指标": "analysis text",
          "同业对比": "analysis text",
          "催化事件": "analysis text"
        }
      }
    ]
  },
  "long_term": {
    "summary": "Brief market assessment for long-term (Chinese)",
    "top5": [
      {
        "rank": 1,
        "code": "000001",
        "name": "Stock Name",
        "overall_score": 0-100,
        "recommend_reason": "Key reasons in Chinese",
        "suggested_price_range": [buy_price_low, buy_price_high],
        "risk_warning": "Risk warning in Chinese",
        "holding_period": "e.g. 6个月以上",
        "analysis_12dim": {
          "基本面": "analysis text",
          ...
        }
      }
    ]
  }
}
```

## Rules
- Output ONLY valid JSON, no markdown wrapping or explanations
- Each stock must have all 12 dimensions filled in analysis_12dim
- If there are fewer than 5 suitable candidates for a category, return what's available
- Be objective and data-driven in your analysis
- Scores should reflect realistic assessments
```

- [ ] **Commit**

```bash
git add backend/ai/prompts/candidate_recommend.md
git commit -m "feat: add LLM prompt for candidate recommendation"
```

---

### Task 3: Create Python analysis script (candidate_recommend.py)

**Files:**
- Create: `backend/stock-analyst/scripts/candidate_recommend.py`

- [ ] **Create the script with 12-dimension data collection and LLM analysis**

```python
#!/usr/bin/env python3
import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from db_manager import DBManager
from llm_client import LLMClient

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "stock_data.db")


def load_stock_pool(db):
    candidates = []
    seen = set()
    yaml_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "resource", "stock_list.yaml")
    if os.path.exists(yaml_path):
        import yaml
        with open(yaml_path, "r") as f:
            data = yaml.safe_load(f)
        for s in data.get("stocks", []):
            code = s.get("code", "")
            if code:
                seen.add(code)
                candidates.append({"code": code, "name": s.get("name", ""), "industry": s.get("industry", "")})
    return candidates, seen


def get_held_codes(db):
    conn = db._connect() if hasattr(db, '_connect') else __import__('sqlite3').connect(db.db_path)
    c = conn.cursor()
    c.execute("SELECT code FROM stock_portfolio WHERE category='持仓'")
    held = {r[0] for r in c.fetchall()}
    conn.close()
    return held


def collect_candidate_data(db, codes):
    conn = __import__('sqlite3').connect(db.db_path)
    c = conn.cursor()
    results = []
    for code in codes[:20]:
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
        news_rows = c.fetchall()
        item["news"] = [r[0] for r in news_rows]

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

        results.append(item)

    conn.close()
    return results


def main():
    db = DBManager(DB_PATH)
    candidates, all_codes = load_stock_pool(db)
    held_codes = get_held_codes(db)
    filtered = [c for c in candidates if c["code"] not in held_codes]
    codes_to_analyze = [c["code"] for c in filtered]

    if not codes_to_analyze:
        print(json.dumps({"error": "没有可供分析的候选股票"}))
        return

    data = collect_candidate_data(db, codes_to_analyze)

    prompt_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "ai", "prompts", "candidate_recommend.md")
    system_prompt = ""
    if os.path.exists(prompt_path):
        with open(prompt_path, "r") as f:
            system_prompt = f.read()

    client = LLMClient()
    user_message = json.dumps({"candidates": data}, ensure_ascii=False, indent=2)
    response = client.chat(system=system_prompt, message=user_message)

    try:
        result = json.loads(response)
        print(json.dumps(result, ensure_ascii=False))
    except json.JSONDecodeError:
        print(json.dumps({"error": "LLM返回格式错误", "raw": response}, ensure_ascii=False))


if __name__ == "__main__":
    main()
```

- [ ] **Commit**

```bash
git add backend/stock-analyst/scripts/candidate_recommend.py
git commit -m "feat: add candidate_recommend.py with 12-dimension analysis"
```

---

### Task 4: Add Rust commands for candidate recommendation

**Files:**
- Modify: `src-tauri/src/commands.rs` (append new commands at end of file)

- [ ] **Add candidate-related Rust commands**

Append to `src-tauri/src/commands.rs`:

```rust
#[tauri::command]
pub async fn run_candidate_llm() -> Result<String, String> {
    let script_dir = python_script_dir()?;
    let output = tokio::process::Command::new("python3")
        .arg("candidate_recommend.py")
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
pub fn save_candidate_analysis(analysis_json: String) -> Result<String, String> {
    let conn = Connection::open(&db_path()).map_err(|e| e.to_string())?;
    conn.execute(
        "INSERT OR REPLACE INTO stock_llm_report (report_type, scope, content, created_at) \
         VALUES ('candidate', 'all', ?1, \
         COALESCE((SELECT created_at FROM stock_llm_report WHERE report_type='candidate' AND scope='all'), datetime('now','localtime')))",
        rusqlite::params![analysis_json],
    ).map_err(|e| e.to_string())?;
    Ok("saved".to_string())
}

#[tauri::command]
pub fn load_candidate_analysis() -> Result<String, String> {
    let conn = Connection::open(&db_path()).map_err(|e| e.to_string())?;
    match conn.query_row(
        "SELECT content, created_at FROM stock_llm_report WHERE report_type='candidate' AND scope='all' ORDER BY id DESC LIMIT 1",
        [],
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

fn today_date() -> String {
    let dur = std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .unwrap_or_default();
    let days = (dur.as_secs() / 86400) as i64;
    let mut y = 1970i64;
    let mut rem = days;
    loop {
        let leap = (y % 4 == 0 && y % 100 != 0) || (y % 400 == 0);
        let dim = if leap { 366 } else { 365 };
        if rem < dim { break; }
        rem -= dim;
        y += 1;
    }
    let leap = (y % 4 == 0 && y % 100 != 0) || (y % 400 == 0);
    let mdays = [31, if leap { 29 } else { 28 }, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31];
    let mut m = 1usize;
    for &d in &mdays {
        if rem < d { break; }
        rem -= d;
        m += 1;
    }
    format!("{:04}-{:02}-{:02}", y, m, rem + 1)
}

#[tauri::command]
pub fn export_candidate_md(analysis_json: String) -> Result<String, String> {
    let parsed: serde_json::Value = serde_json::from_str(&analysis_json).map_err(|e| e.to_string())?;
    let mut md = String::new();
    let today = today_date();
    md.push_str(&format!("# {} 候选推荐报告\n\n", today));
    md.push_str("---\n\n");

    for (period_key, period_title) in [("short_term", "📈 中短期持有 Top 5"), ("long_term", "📊 长期价值投资 Top 5")] {
        if let Some(cat) = parsed.get(period_key) {
            md.push_str(&format!("## {} \n\n", period_title));
            if let Some(summary) = cat.get("summary").and_then(|v| v.as_str()) {
                md.push_str(&format!("> {}\n\n", summary));
            }
            if let Some(top5) = cat.get("top5").and_then(|v| v.as_array()) {
                for stock in top5 {
                    let rank = stock.get("rank").and_then(|v| v.as_i64()).unwrap_or(0);
                    let name = stock.get("name").and_then(|v| v.as_str()).unwrap_or("");
                    let code = stock.get("code").and_then(|v| v.as_str()).unwrap_or("");
                    let score = stock.get("overall_score").and_then(|v| v.as_i64()).unwrap_or(0);
                    let reason = stock.get("recommend_reason").and_then(|v| v.as_str()).unwrap_or("");
                    let price_range = stock.get("suggested_price_range").and_then(|v| v.as_array());
                    let risk = stock.get("risk_warning").and_then(|v| v.as_str()).unwrap_or("");
                    let period = stock.get("holding_period").and_then(|v| v.as_str()).unwrap_or("");

                    md.push_str(&format!("### {}. {}（{}）— 评分：{}/100\n\n", rank, name, code, score));
                    md.push_str(&format!("- **持有周期**：{}\n", period));
                    md.push_str(&format!("- **推荐理由**：{}\n", reason));
                    if let Some(range) = price_range {
                        if range.len() >= 2 {
                            let low = range[0].as_f64().unwrap_or(0.0);
                            let high = range[1].as_f64().unwrap_or(0.0);
                            md.push_str(&format!("- **建议买入区间**：{:.2} — {:.2}\n", low, high));
                        }
                    }
                    md.push_str(&format!("- **风险提示**：{}\n\n", risk));

                    if let Some(dims) = stock.get("analysis_12dim").and_then(|v| v.as_object()) {
                        for (_key, val) in dims {
                            if let Some(text) = val.as_str() {
                                if !text.is_empty() {
                                    md.push_str(&format!("  - {}：{}\n", _key, text));
                                }
                            }
                        }
                        md.push_str("\n");
                    }
                }
            }
        }
    }

    md.push_str("---\n");
    md.push_str(&format!("_报告由 衡势价值 自动生成于 {}\n", today));

    let reports_dir = project_root().join("reference").join("candidate");
    std::fs::create_dir_all(&reports_dir).map_err(|e| format!("创建目录失败: {}", e))?;
    let file_name = format!("{}-候选推荐报告.md", today);
    let file_path = reports_dir.join(&file_name);
    std::fs::write(&file_path, &md).map_err(|e| format!("保存文件失败: {}", e))?;
    Ok(file_path.to_string_lossy().to_string())
}
```

- [ ] **Commit**

```bash
git add src-tauri/src/commands.rs
git commit -m "feat: add Rust commands for candidate recommendation"
```

---

### Task 5: Register new commands in main.rs

**Files:**
- Modify: `src-tauri/src/main.rs`

- [ ] **Add new commands to invoke_handler**

```rust
commands::run_candidate_llm,
commands::save_candidate_analysis,
commands::load_candidate_analysis,
commands::export_candidate_md,
```

Insert after `commands::export_portfolio_md,`:

- [ ] **Commit**

```bash
git add src-tauri/src/main.rs
git commit -m "feat: register candidate recommendation commands"
```

---

### Task 6: Add frontend API functions

**Files:**
- Modify: `src/services/api.ts`

- [ ] **Add candidate recommendation API functions**

Append to `src/services/api.ts`:

```typescript
export async function runCandidateLlm(): Promise<string> {
  return invoke("run_candidate_llm");
}

export async function saveCandidateAnalysis(analysisJson: string): Promise<string> {
  return invoke("save_candidate_analysis", { analysisJson });
}

export async function loadCandidateAnalysis(): Promise<string> {
  return invoke("load_candidate_analysis");
}

export async function exportCandidateMd(analysisJson: string): Promise<string> {
  return invoke("export_candidate_md", { analysisJson });
}
```

- [ ] **Commit**

```bash
git add src/services/api.ts
git commit -m "feat: add candidate recommendation API functions"
```

---

### Task 7: Update sidebar label

**Files:**
- Modify: `src/components/Sidebar.tsx`

- [ ] **Change label from "候选池" to "候选推荐"**

```diff
- { path: "/watchlist", label: "候选池", icon: "🎯" },
+ { path: "/watchlist", label: "候选推荐", icon: "🎯" },
```

- [ ] **Commit**

```bash
git add src/components/Sidebar.tsx
git commit -m "refactor: rename 候选池 to 候选推荐 in sidebar"
```

---

### Task 8: Rewrite Watchlist.tsx — main page

**Files:**
- Modify: `src/pages/Watchlist.tsx` (full rewrite)

- [ ] **Rewrite the Watchlist page with candidate recommendation UI**

```typescript
import { useState, useEffect } from "react";
import {
  runCandidateLlm,
  saveCandidateAnalysis,
  loadCandidateAnalysis,
  exportCandidateMd,
} from "../services/api";
import type { CandidateRecommendation, CandidateStock } from "../types";
import RecommendDetailDrawer from "./components/RecommendDetailDrawer";

export default function Watchlist() {
  const [recommendation, setRecommendation] = useState<CandidateRecommendation | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [cacheTime, setCacheTime] = useState("");
  const [selectedStock, setSelectedStock] = useState<CandidateStock | null>(null);
  const [showDrawer, setShowDrawer] = useState(false);
  const [mdStatus, setMdStatus] = useState("");

  useEffect(() => {
    loadCandidateAnalysis().then((res) => {
      if (res && res !== "{}") {
        try {
          const p = JSON.parse(res);
          if (p.data && p.updated_at) {
            setRecommendation(p.data);
            setCacheTime(p.updated_at);
          }
        } catch {}
      }
    });
  }, []);

  const handleAiAnalyze = async () => {
    setLoading(true);
    setError("");
    setMdStatus("");
    try {
      const res = await runCandidateLlm();
      const data = JSON.parse(res);
      if (data.error) {
        setError(data.error);
      } else {
        setRecommendation(data);
        saveCandidateAnalysis(res).catch(() => {});
      }
    } catch (e) {
      setError(String(e));
    }
    setLoading(false);
  };

  const handleExportMd = async () => {
    if (!recommendation) return;
    try {
      const path = await exportCandidateMd(JSON.stringify(recommendation));
      setMdStatus(`✅ 已保存: ${path}`);
    } catch (e) {
      setMdStatus(`❌ 导出失败: ${e}`);
    }
  };

  const handleCardClick = (stock: CandidateStock) => {
    setSelectedStock(stock);
    setShowDrawer(true);
  };

  const renderCard = (stock: CandidateStock, index: number, colorScheme: "short" | "long") => {
    const borderColor = colorScheme === "short" ? "#7c5cfc" : "#2e7d32";
    const bgGradient = colorScheme === "short"
      ? "linear-gradient(135deg, #f5f0ff, #f0f4ff)"
      : "linear-gradient(135deg, #e8f5e9, #f1f8e9)";

    return (
      <div
        key={stock.code}
        onClick={() => handleCardClick(stock)}
        style={{
          background: bgGradient,
          borderRadius: 12,
          border: `1px solid ${borderColor}33`,
          padding: 16,
          cursor: "pointer",
          transition: "box-shadow 0.2s, transform 0.15s",
          boxShadow: "0 1px 4px rgba(0,0,0,0.06)",
        }}
        onMouseEnter={(e) => { e.currentTarget.style.boxShadow = "0 4px 12px rgba(0,0,0,0.1)"; e.currentTarget.style.transform = "translateY(-2px)"; }}
        onMouseLeave={(e) => { e.currentTarget.style.boxShadow = "0 1px 4px rgba(0,0,0,0.06)"; e.currentTarget.style.transform = "none"; }}
      >
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 8 }}>
          <div>
            <span style={{ fontSize: 13, fontWeight: 700, color: borderColor }}>
              {"⭐".repeat(Math.ceil(stock.overall_score / 20))}
            </span>
            <span style={{ fontSize: 12, color: "#666", marginLeft: 4 }}>
              {stock.overall_score}/100
            </span>
          </div>
          <span style={{ fontSize: 11, color: "#999" }}>#{stock.rank}</span>
        </div>
        <div style={{ fontSize: 16, fontWeight: 600, marginBottom: 4 }}>{stock.name}</div>
        <div style={{ fontSize: 12, color: "#666", marginBottom: 8, lineHeight: 1.5 }}>
          {stock.recommend_reason.length > 40
            ? stock.recommend_reason.slice(0, 40) + "..."
            : stock.recommend_reason}
        </div>
        <div style={{ fontSize: 11, color: "#888" }}>
          建议区间: {stock.suggested_price_range[0].toFixed(2)} - {stock.suggested_price_range[1].toFixed(2)}
        </div>
        <div style={{ fontSize: 11, color: "#e53935", marginTop: 2 }}>
          ⚠ {stock.risk_warning.length > 20 ? stock.risk_warning.slice(0, 20) + "..." : stock.risk_warning}
        </div>
        <button
          onClick={(e) => { e.stopPropagation(); handleCardClick(stock); }}
          style={{
            marginTop: 10, padding: "6px 14px", fontSize: 12,
            background: "transparent", border: `1px solid ${borderColor}`,
            color: borderColor, borderRadius: 6, cursor: "pointer",
            width: "100%", fontWeight: 500,
          }}
        >
          查看详情
        </button>
      </div>
    );
  };

  const renderCategory = (data: { summary: string; top5: CandidateStock[] } | undefined, title: string, colorScheme: "short" | "long") => {
    if (!data) return null;
    return (
      <div style={{ marginBottom: 28 }}>
        <div style={{
          fontSize: 18, fontWeight: 700, marginBottom: 4,
          color: colorScheme === "short" ? "#7c5cfc" : "#2e7d32",
        }}>
          {title}
        </div>
        {data.summary && (
          <div style={{
            fontSize: 13, color: "#555", marginBottom: 14,
            padding: "10px 14px", background: "#f8f9fa", borderRadius: 8,
            lineHeight: 1.6,
          }}>
            💡 {data.summary}
          </div>
        )}
        <div style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fill, minmax(240px, 1fr))",
          gap: 14,
        }}>
          {(data.top5 || []).map((stock, i) => renderCard(stock, i, colorScheme))}
        </div>
      </div>
    );
  };

  return (
    <div>
      <div style={{
        display: "flex", justifyContent: "space-between", alignItems: "center",
        marginBottom: 20, flexWrap: "wrap", gap: 8,
      }}>
        <div>
          <h2 style={{ fontSize: 22, fontWeight: 700, margin: 0 }}>🎯 候选推荐</h2>
          {cacheTime && (
            <div style={{ fontSize: 12, color: "#888", marginTop: 2 }}>
              上次分析: {cacheTime}
            </div>
          )}
        </div>
        <div style={{ display: "flex", gap: 8 }}>
          <button
            onClick={handleAiAnalyze}
            disabled={loading}
            style={{
              padding: "8px 18px", fontSize: 13, fontWeight: 600,
              background: "linear-gradient(135deg, #7c5cfc, #5b8def)",
              color: "#fff", border: "none", borderRadius: 8,
              cursor: loading ? "not-allowed" : "pointer", opacity: loading ? 0.6 : 1,
            }}
          >
            {loading ? "⏳ 分析中..." : "🤖 AI 推荐"}
          </button>
          {recommendation && (
            <button
              onClick={handleExportMd}
              style={{
                padding: "8px 18px", fontSize: 13, fontWeight: 500,
                background: "#fff", border: "1px solid var(--border)",
                borderRadius: 8, cursor: "pointer",
              }}
            >
              💾 保存报告
            </button>
          )}
        </div>
      </div>

      {error && (
        <div style={{
          padding: "12px 16px", background: "#fef2f2", border: "1px solid #fecaca",
          borderRadius: 8, color: "#dc2626", fontSize: 13, marginBottom: 16,
        }}>
          {error}
        </div>
      )}

      {mdStatus && (
        <div style={{
          padding: "10px 14px", background: "#f0fdf4", border: "1px solid #bbf7d0",
          borderRadius: 8, color: "#16a34a", fontSize: 13, marginBottom: 16,
        }}>
          {mdStatus}
        </div>
      )}

      {loading && (
        <div style={{
          padding: 40, textAlign: "center", color: "#888", fontSize: 14,
        }}>
          ⏳ LLM 正在分析候选股票...
        </div>
      )}

      {!loading && !recommendation && !error && (
        <div style={{
          padding: 60, textAlign: "center", color: "#aaa", fontSize: 14,
        }}>
          点击「AI 推荐」按钮，系统将从股票池中分析并推荐最适合的股票
        </div>
      )}

      {!loading && recommendation && (
        <div>
          {renderCategory(recommendation.short_term, "📈 中短期持有 Top 5", "short")}
          {renderCategory(recommendation.long_term, "📊 长期价值投资 Top 5", "long")}
        </div>
      )}

      {showDrawer && selectedStock && (
        <RecommendDetailDrawer
          stock={selectedStock}
          onClose={() => { setShowDrawer(false); setSelectedStock(null); }}
        />
      )}
    </div>
  );
}
```

- [ ] **Commit**

```bash
git add src/pages/Watchlist.tsx
git commit -m "feat: rewrite Watchlist with candidate recommendation UI"
```

---

### Task 9: Create RecommendDetailDrawer component

**Files:**
- Create: `src/pages/components/RecommendDetailDrawer.tsx`

- [ ] **Create the detail drawer component**

```typescript
import type { CandidateStock } from "../../types";

interface Props {
  stock: CandidateStock;
  onClose: () => void;
}

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

export default function RecommendDetailDrawer({ stock, onClose }: Props) {
  const dims = stock.analysis_12dim || {};
  const entries = Object.entries(DIMENSION_LABELS);

  return (
    <div
      onClick={onClose}
      style={{
        position: "fixed", inset: 0, zIndex: 1000,
        background: "rgba(0,0,0,0.4)",
        display: "flex", alignItems: "center", justifyContent: "center",
        padding: 20,
      }}
    >
      <div
        onClick={(e) => e.stopPropagation()}
        style={{
          background: "#fff", borderRadius: 16, maxWidth: 640, width: "100%",
          maxHeight: "85vh", overflow: "auto",
          boxShadow: "0 20px 60px rgba(0,0,0,0.15)",
        }}
      >
        <div style={{
          position: "sticky", top: 0, background: "#fff", zIndex: 1,
          padding: "20px 24px 12px",
          borderBottom: "1px solid var(--border)",
          display: "flex", justifyContent: "space-between", alignItems: "flex-start",
        }}>
          <div>
            <div style={{ fontSize: 18, fontWeight: 700 }}>
              {stock.name}
              <span style={{ fontSize: 13, color: "#888", fontWeight: 400, marginLeft: 8 }}>
                {stock.code}
              </span>
            </div>
            <div style={{ fontSize: 13, color: "#666", marginTop: 4 }}>
              ⭐ {stock.overall_score}/100 · {stock.holding_period}
            </div>
          </div>
          <button
            onClick={onClose}
            style={{
              background: "none", border: "none", fontSize: 22, cursor: "pointer",
              color: "#888", padding: "0 4px", lineHeight: 1,
            }}
          >
            ×
          </button>
        </div>

        <div style={{ padding: "16px 24px 24px" }}>
          <div style={{
            padding: "12px 16px", background: "#f0f7ff", borderRadius: 10,
            marginBottom: 16, fontSize: 13, lineHeight: 1.6, color: "#1a4d8f",
          }}>
            <strong>推荐理由：</strong>{stock.recommend_reason}
          </div>

          <div style={{
            display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10,
            marginBottom: 16, fontSize: 12,
          }}>
            <div style={{ padding: "8px 12px", background: "#f8f9fa", borderRadius: 8 }}>
              <span style={{ color: "#888" }}>建议买入区间</span>
              <div style={{ fontWeight: 600, color: "#16a34a", marginTop: 2 }}>
                {stock.suggested_price_range[0].toFixed(2)} — {stock.suggested_price_range[1].toFixed(2)}
              </div>
            </div>
            <div style={{ padding: "8px 12px", background: "#fef2f2", borderRadius: 8 }}>
              <span style={{ color: "#888" }}>风险提示</span>
              <div style={{ fontWeight: 500, color: "#dc2626", marginTop: 2, fontSize: 12 }}>
                {stock.risk_warning}
              </div>
            </div>
          </div>

          {entries.map(([key, label]) => {
            const val = dims[key];
            if (!val || val === "...") return null;
            return (
              <div key={key} style={{ marginBottom: 14 }}>
                <div style={{
                  fontSize: 14, fontWeight: 600, marginBottom: 6,
                  paddingBottom: 4, borderBottom: "1px solid #eee",
                }}>
                  {label}
                </div>
                <div style={{ fontSize: 13, color: "#444", lineHeight: 1.7, whiteSpace: "pre-wrap" }}>
                  {val}
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
```

- [ ] **Commit**

```bash
git add src/pages/components/RecommendDetailDrawer.tsx
git commit -m "feat: add RecommendDetailDrawer for candidate stock detail"
```

---

### Task 10: Verify build

- [ ] **Check TypeScript compilation**

```bash
cd /Users/ws/Desktop/Project/Trea-Project/STOCK-Dev && npx tsc --noEmit 2>&1 | head -50
```

Expected: No type errors

- [ ] **Check Rust compilation**

```bash
cd /Users/ws/Desktop/Project/Trea-Project/STOCK-Dev/src-tauri && cargo check 2>&1 | tail -20
```

Expected: `Compiling ...` and `Finished` with no errors

- [ ] **If errors found, fix and verify again**