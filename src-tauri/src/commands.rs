use std::collections::HashMap;
use std::path::PathBuf;
use serde::{Deserialize, Serialize};
use serde_json;
use rusqlite::Connection;

#[derive(Debug, Serialize, Deserialize)]
pub struct StockSummary {
    pub total_stocks: i32,
    pub total_holdings: i32,
    pub total_pnl: f64,
    pub alert_count: i32,
    pub candidate_count: i32,
    pub chan_signals: i32,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct MarketMover {
    pub code: String,
    pub name: String,
    pub price: f64,
    pub change_pct: f64,
    pub volume: i64,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct MarketOverview {
    pub top_gainers: Vec<MarketMover>,
    pub top_losers: Vec<MarketMover>,
    pub last_update: String,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct StockListEntry {
    pub code: String,
    pub name: String,
    pub industry: String,
}

#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct StockItem {
    pub code: String,
    pub name: String,
    pub industry: String,
    pub price: f64,
    pub change_pct: f64,
    pub score: i32,
    pub suggestion: String,
    pub risk_level: String,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct PortfolioStock {
    pub id: i64,
    pub code: String,
    pub name: String,
    pub category: String,
    pub cost_price: f64,
    pub shares: i64,
    pub add_date: String,
    pub notes: String,
    pub price: f64,
    pub change_pct: f64,
    pub score: i32,
    pub suggestion: String,
    pub risk_level: String,
}

fn project_root() -> PathBuf {
    let manifest = PathBuf::from(env!("CARGO_MANIFEST_DIR"));
    manifest.parent().map(PathBuf::from).unwrap_or_else(|| PathBuf::from("."))
}

fn db_path() -> PathBuf {
    if let Ok(path) = std::env::var("STOCK_DB_PATH") {
        return PathBuf::from(path);
    }
    project_root().join("backend").join("stock-analyst").join("data").join("stock_data.db")
}

fn python_script_dir() -> Result<PathBuf, String> {
    let dir = project_root().join("backend").join("stock-analyst").join("scripts");
    if dir.exists() {
        Ok(dir)
    } else {
        Err(format!("Script directory not found: {}", dir.display()))
    }
}

fn load_stock_list() -> Result<Vec<StockListEntry>, String> {
    let path = stock_list_path();
    let content = std::fs::read_to_string(&path)
        .map_err(|e| format!("Failed to read stock_list.yaml: {}", e))?;
    let parsed: serde_yaml::Value =
        serde_yaml::from_str(&content).map_err(|e| e.to_string())?;
    let stocks = parsed["stocks"]
        .as_sequence()
        .ok_or("Invalid stock_list.yaml format")?;
    let entries: Vec<StockListEntry> = stocks
        .iter()
        .map(|v| StockListEntry {
            code: v["code"].as_str().unwrap_or("").to_string(),
            name: v["name"].as_str().unwrap_or("").to_string(),
            industry: v["industry"].as_str().unwrap_or("").to_string(),
        })
        .collect();
    Ok(entries)
}

fn stock_list_path() -> PathBuf {
    project_root().join("backend").join("stock-analyst").join("resource").join("stock_list.yaml")
}

fn build_industry_map() -> Result<HashMap<String, StockListEntry>, String> {
    let list = load_stock_list()?;
    let mut map = HashMap::new();
    for entry in list {
        if !entry.code.is_empty() {
            map.insert(entry.code.clone(), entry);
        }
    }
    Ok(map)
}

#[tauri::command]
pub fn get_dashboard_summary() -> Result<StockSummary, String> {
    let conn = Connection::open(db_path()).map_err(|e| e.to_string())?;
    let holdings: i32 = conn
        .query_row("SELECT COUNT(*) FROM stock_portfolio WHERE category='持仓'", [], |r| r.get(0))
        .unwrap_or(0);
    let alerts: i32 = conn
        .query_row("SELECT COUNT(*) FROM stock_alert", [], |r| r.get(0))
        .unwrap_or(0);
    let stock_list = load_stock_list().unwrap_or_default();
    Ok(StockSummary {
        total_stocks: stock_list.len() as i32,
        total_holdings: holdings,
        total_pnl: 3.2,
        alert_count: alerts,
        candidate_count: 8,
        chan_signals: 3,
    })
}

#[tauri::command]
pub fn get_stock_list() -> Result<Vec<StockListEntry>, String> {
    load_stock_list()
}

#[tauri::command]
pub fn get_market_movers() -> Result<MarketOverview, String> {
    let conn = Connection::open(db_path()).map_err(|e| e.to_string())?;

    let mut stmt = conn
        .prepare(
            "SELECT code, name, price, change_pct, COALESCE(volume, 0) FROM stock_realtime GROUP BY code ORDER BY change_pct DESC LIMIT 10"
        )
        .map_err(|e| e.to_string())?;
    let top_gainers = stmt
        .query_map([], |row| {
            Ok(MarketMover {
                code: row.get(0)?,
                name: row.get(1)?,
                price: row.get(2)?,
                change_pct: row.get(3)?,
                volume: row.get(4)?,
            })
        })
        .map_err(|e| e.to_string())?
        .filter_map(|r| r.ok())
        .collect();

    let mut stmt = conn
        .prepare(
            "SELECT code, name, price, change_pct, COALESCE(volume, 0) FROM stock_realtime GROUP BY code ORDER BY change_pct ASC LIMIT 10"
        )
        .map_err(|e| e.to_string())?;
    let top_losers = stmt
        .query_map([], |row| {
            Ok(MarketMover {
                code: row.get(0)?,
                name: row.get(1)?,
                price: row.get(2)?,
                change_pct: row.get(3)?,
                volume: row.get(4)?,
            })
        })
        .map_err(|e| e.to_string())?
        .filter_map(|r| r.ok())
        .collect();

    let last_update: String = conn
        .query_row(
            "SELECT COALESCE(MAX(update_time), '暂无数据') FROM stock_realtime",
            [],
            |r| r.get(0),
        )
        .unwrap_or_else(|_| "暂无数据".to_string());

    Ok(MarketOverview { top_gainers, top_losers, last_update })
}

#[tauri::command]
pub fn get_portfolio() -> Result<Vec<StockItem>, String> {
    let conn = Connection::open(db_path()).map_err(|e| e.to_string())?;
    let industry_map = build_industry_map().unwrap_or_default();

    let mut stmt = conn
        .prepare(
            "SELECT r.code, r.name, r.price, r.change_pct,
                    COALESCE(s.score, 0), COALESCE(s.suggestion, ''), COALESCE(s.risk_level, '')
             FROM stock_realtime r
             LEFT JOIN stock_score s ON r.code = s.code
             GROUP BY r.code ORDER BY r.change_pct DESC"
        )
        .map_err(|e| e.to_string())?;
    let items = stmt
        .query_map([], |row| {
            let code: String = row.get(0)?;
            let entry = industry_map.get(&code);
            Ok(StockItem {
                code: code.clone(),
                name: row.get(1)?,
                industry: entry.map(|e| e.industry.clone()).unwrap_or_default(),
                price: row.get(2)?,
                change_pct: row.get(3)?,
                score: row.get(4)?,
                suggestion: row.get(5)?,
                risk_level: row.get(6)?,
            })
        })
        .map_err(|e| e.to_string())?
        .filter_map(|r| r.ok())
        .collect();
    Ok(items)
}

#[tauri::command]
pub fn get_technical_indicators(code: String) -> Result<serde_json::Value, String> {
    let conn = Connection::open(db_path()).map_err(|e| e.to_string())?;
    let result = conn
        .query_row(
            "SELECT indicators_json FROM stock_technical WHERE code = ?1 ORDER BY created_at DESC LIMIT 1",
            [&code],
            |r| r.get::<_, String>(0),
        )
        .map_err(|e| e.to_string())?;
    serde_json::from_str(&result).map_err(|e| e.to_string())
}

#[tauri::command]
pub async fn run_analysis() -> Result<String, String> {
    let script_dir = python_script_dir()?;
    let output = tokio::process::Command::new("python3")
        .arg("main.py")
        .arg("--mode")
        .arg("quick")
        .current_dir(&script_dir)
        .output()
        .await
        .map_err(|e| format!("Failed to start Python: {}", e))?;
    if output.status.success() {
        Ok(String::from_utf8_lossy(&output.stdout).to_string())
    } else {
        Err(String::from_utf8_lossy(&output.stderr).to_string())
    }
}

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

#[tauri::command]
pub async fn run_llm_analysis(scope: String) -> Result<String, String> {
    let script_dir = python_script_dir()?;
    let output = tokio::process::Command::new("python3")
        .arg("main.py")
        .arg("--mode")
        .arg("llm")
        .arg("--scope")
        .arg(&scope)
        .current_dir(&script_dir)
        .output()
        .await
        .map_err(|e| format!("Failed to start Python: {}", e))?;
    if output.status.success() {
        Ok(String::from_utf8_lossy(&output.stdout).to_string())
    } else {
        Err(String::from_utf8_lossy(&output.stderr).to_string())
    }
}

#[tauri::command]
pub fn save_llm_config(url: String, api_key: String, model: String, temperature: f64) -> Result<String, String> {
    // 向后兼容：转成单条 save_model（无 id，自动生成）
    let payload = serde_json::json!({
        "name": "默认模型",
        "provider": "custom",
        "api_base": url,
        "api_key": api_key,
        "model": model,
        "temperature": temperature,
        "enabled": true,
    });
    call_llm_cli(&["save", &payload.to_string()])
}

#[tauri::command]
pub fn load_llm_config() -> Result<String, String> {
    // 向后兼容：返回当前激活的单个模型
    call_llm_cli(&["get-active"])
}

/// 通过 Python CLI 转发 LLM 配置命令
fn call_llm_cli(args: &[&str]) -> Result<String, String> {
    use std::process::Command;
    let py = llm_python_path();
    let cli = llm_cli_path();

    let output = Command::new(&py)
        .arg(&cli)
        .args(args)
        .output()
        .map_err(|e| format!("调用 Python 失败 ({}): {}", py.display(), e))?;

    if !output.status.success() {
        let stderr = String::from_utf8_lossy(&output.stderr);
        return Err(format!("Python CLI 错误: {}", stderr.trim()));
    }
    Ok(String::from_utf8_lossy(&output.stdout).trim().to_string())
}

fn llm_python_path() -> PathBuf {
    if let Ok(p) = std::env::var("STOCK_PYTHON") {
        return PathBuf::from(p);
    }
    PathBuf::from("python3")
}

fn llm_cli_path() -> PathBuf {
    project_root()
        .join("backend")
        .join("stock-analyst")
        .join("scripts")
        .join("llm_config_cli.py")
}

// 多模型管理新命令
#[tauri::command]
pub fn list_llm_models() -> Result<String, String> {
    call_llm_cli(&["list"])
}

#[tauri::command]
pub fn save_llm_model(model_json: String) -> Result<String, String> {
    call_llm_cli(&["save", &model_json])
}

#[tauri::command]
pub fn delete_llm_model(model_id: String) -> Result<String, String> {
    call_llm_cli(&["delete", &model_id])
}

#[tauri::command]
pub fn set_active_llm_model(model_id: String) -> Result<String, String> {
    call_llm_cli(&["set-active", &model_id])
}

#[tauri::command]
pub fn test_llm_connection(api_base: String, api_key: String, model: String) -> Result<String, String> {
    call_llm_cli(&["test", &api_base, &api_key, &model])
}

#[tauri::command]
pub fn save_portfolio_analysis(code: String, analysis_json: String) -> Result<String, String> {
    let conn = Connection::open(&db_path()).map_err(|e| e.to_string())?;
    conn.execute(
        "INSERT OR REPLACE INTO stock_llm_report (report_type, scope, content, created_at) \
         VALUES ('portfolio', ?1, ?2, COALESCE((SELECT created_at FROM stock_llm_report WHERE report_type='portfolio' AND scope=?1), datetime('now','localtime')))",
        rusqlite::params![code, analysis_json],
    ).map_err(|e| e.to_string())?;
    Ok("saved".to_string())
}

#[tauri::command]
pub fn load_portfolio_analysis(code: String) -> Result<String, String> {
    let conn = Connection::open(&db_path()).map_err(|e| e.to_string())?;
    match conn.query_row(
        "SELECT content, created_at FROM stock_llm_report WHERE report_type='portfolio' AND scope=?1 ORDER BY id DESC LIMIT 1",
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
pub fn export_portfolio_md(code: String, name: String, analysis_json: String) -> Result<String, String> {
    let parsed: serde_json::Value = serde_json::from_str(&analysis_json).map_err(|e| e.to_string())?;
    let mut md = String::new();
    md.push_str(&format!("# {}（{}）个股分析报告\n\n", name, code));
    md.push_str("---\n\n");

    if let Some(v) = parsed.get("综合评分").and_then(|v| v.as_i64()) {
        let bar = "█".repeat((v / 5) as usize) + &"░".repeat((20 - v / 5) as usize);
        md.push_str(&format!("**综合评分：{} / 100**  {}\n\n", v, bar));
    }

    let sections = [
        ("核心业务板块", "🏢 核心业务板块"),
        ("技术面结论", "📈 技术面结论"),
        ("热点信息", "🔥 热点信息"),
        ("资金流向分析", "💰 资金流向分析"),
        ("关键价位", "🎯 关键价位"),
        ("买卖点建议", "📊 买卖点建议"),
        ("加仓点建议", "⚡ 加仓点建议"),
        ("仓位建议", "⚖️ 仓位建议"),
    ];
    for (key, title) in &sections {
        if let Some(v) = parsed.get(*key).and_then(|v| v.as_str()) {
            if !v.is_empty() {
                md.push_str(&format!("## {} {}\n\n{} \n\n", title, key, v));
            }
        }
    }

    if let Some(arr) = parsed.get("利好利空").and_then(|v| v.as_array()) {
        if !arr.is_empty() {
            md.push_str("## 📋 利好 / 利空\n\n");
            for item in arr {
                if let Some(s) = item.as_str() {
                    md.push_str(&format!("- {}\n", s));
                }
            }
            md.push_str("\n");
        }
    }

    let signal_keys = [("卖出信号", "🔴 卖出提示")];
    for (sig_key, sig_title) in &signal_keys {
        if let Some(obj) = parsed.get(*sig_key).and_then(|v| v.as_object()) {
            md.push_str(&format!("## {} \n\n", sig_title));
            for (period, signals) in obj {
                if let Some(arr) = signals.as_array() {
                    for s in arr {
                        if let Some(text) = s.as_str() {
                            md.push_str(&format!("- **{}**: {}\n", period, text));
                        }
                    }
                }
            }
            md.push_str("\n");
        }
    }

    if let Some(v) = parsed.get("加仓点建议").and_then(|v| v.as_str()) {
        if !v.is_empty() {
            md.push_str(&format!("## ⚡ 加仓点建议\n\n{} \n\n", v));
        }
    }

    if let Some(v) = parsed.get("实时行情总结").and_then(|v| v.as_str()) {
        if !v.is_empty() {
            md.push_str(&format!("> {}\n\n", v));
        }
    }

    md.push_str("---\n");
    md.push_str(&format!("_报告由 衡势价值 自动生成_\n"));

    let reports_dir = project_root().join("reference");
    std::fs::create_dir_all(&reports_dir).map_err(|e| format!("创建目录失败: {}", e))?;
    let file_name = format!("{}-{}-分析报告.md", code, name);
    let file_path = reports_dir.join(&file_name);
    std::fs::write(&file_path, &md).map_err(|e| format!("保存文件失败: {}", e))?;
    Ok(file_path.to_string_lossy().to_string())
}

#[tauri::command]
pub fn add_stock_to_list(code: String, name: String, industry: String) -> Result<String, String> {
    let path = stock_list_path();
    let entries = load_stock_list().unwrap_or_default();
    if entries.iter().any(|e| e.code == code) {
        return Err("该股票已在列表中".to_string());
    }
    let content = std::fs::read_to_string(&path).map_err(|e| e.to_string())?;
    let mut value: serde_yaml::Value = serde_yaml::from_str(&content).map_err(|e| e.to_string())?;
    let new_item = serde_yaml::Value::Mapping({
        let mut m = serde_yaml::Mapping::new();
        m.insert(serde_yaml::Value::String("code".into()), serde_yaml::Value::String(code.clone()));
        m.insert(serde_yaml::Value::String("name".into()), serde_yaml::Value::String(name));
        m.insert(serde_yaml::Value::String("industry".into()), serde_yaml::Value::String(industry));
        m
    });
    if let Some(stocks) = value["stocks"].as_sequence_mut() {
        stocks.push(new_item);
    }
    let out = serde_yaml::to_string(&value).map_err(|e| e.to_string())?;
    std::fs::write(&path, out).map_err(|e| e.to_string())?;
    Ok(format!("✅ 已添加 {}", code))
}

#[tauri::command]
pub fn remove_stock_from_list(code: String) -> Result<String, String> {
    let path = stock_list_path();
    let content = std::fs::read_to_string(&path).map_err(|e| e.to_string())?;
    let mut value: serde_yaml::Value = serde_yaml::from_str(&content).map_err(|e| e.to_string())?;
    let removed = if let Some(stocks) = value["stocks"].as_sequence_mut() {
        let len_before = stocks.len();
        stocks.retain(|v| v["code"].as_str().unwrap_or("") != code);
        len_before > stocks.len()
    } else {
        false
    };
    if !removed {
        return Err("未找到该股票".to_string());
    }
    let out = serde_yaml::to_string(&value).map_err(|e| e.to_string())?;
    std::fs::write(&path, out).map_err(|e| e.to_string())?;

    let conn = Connection::open(db_path()).map_err(|e| e.to_string())?;
    conn.execute("DELETE FROM stock_score WHERE code=?1", [&code]).ok();
    conn.execute("DELETE FROM stock_realtime WHERE code=?1", [&code]).ok();
    Ok(format!("✅ 已移除 {}", code))
}

#[tauri::command]
pub fn get_portfolio_stocks() -> Result<Vec<PortfolioStock>, String> {
    let conn = Connection::open(db_path()).map_err(|e| e.to_string())?;
    let mut stmt = conn
        .prepare(
            "SELECT p.id, p.code, COALESCE(p.name,''), p.category,
                    COALESCE(p.cost_price,0), COALESCE(p.shares,0),
                    COALESCE(p.add_date,''), COALESCE(p.notes,''),
                    COALESCE(r.price,0), COALESCE(r.change_pct,0),
                    COALESCE(s.score,0), COALESCE(s.suggestion,''), COALESCE(s.risk_level,'')
             FROM stock_portfolio p
             LEFT JOIN stock_realtime r ON p.code = r.code
             LEFT JOIN stock_score s ON p.code = s.code
             ORDER BY p.add_date DESC"
        )
        .map_err(|e| e.to_string())?;
    let items = stmt
        .query_map([], |row| {
            Ok(PortfolioStock {
                id: row.get(0)?,
                code: row.get(1)?,
                name: row.get(2)?,
                category: row.get(3)?,
                cost_price: row.get(4)?,
                shares: row.get(5)?,
                add_date: row.get(6)?,
                notes: row.get(7)?,
                price: row.get(8)?,
                change_pct: row.get(9)?,
                score: row.get(10)?,
                suggestion: row.get(11)?,
                risk_level: row.get(12)?,
            })
        })
        .map_err(|e| e.to_string())?
        .filter_map(|r| r.ok())
        .collect();
    Ok(items)
}

#[tauri::command]
pub fn add_portfolio_stock(code: String, name: String, cost_price: f64, shares: i64, category: String) -> Result<String, String> {
    let conn = Connection::open(db_path()).map_err(|e| e.to_string())?;
    conn.execute(
        "INSERT OR REPLACE INTO stock_portfolio (code, name, category, cost_price, shares) VALUES (?1, ?2, ?3, ?4, ?5)",
        rusqlite::params![code, name, category, cost_price, shares],
    ).map_err(|e| e.to_string())?;
    Ok(format!("✅ 已添加到持仓: {}", name))
}

#[tauri::command]
pub fn remove_portfolio_stock(id: i64) -> Result<String, String> {
    let conn = Connection::open(db_path()).map_err(|e| e.to_string())?;
    conn.execute("DELETE FROM stock_portfolio WHERE id=?1", [id]).map_err(|e| e.to_string())?;
    Ok("✅ 已移除持仓".to_string())
}

#[tauri::command]
pub async fn run_portfolio_llm(code: String) -> Result<String, String> {
    let script_dir = python_script_dir()?;
    let output = tokio::process::Command::new("python3")
        .arg("portfolio_analysis.py")
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
pub fn search_stock(query: String) -> Result<String, String> {
    let conn = Connection::open(&db_path()).map_err(|e| e.to_string())?;
    let pattern = format!("%{}%", query);
    let mut stmt = conn.prepare(
        "SELECT code, name FROM stock_realtime WHERE name LIKE ?1 OR code LIKE ?1 LIMIT 10"
    ).map_err(|e| e.to_string())?;
    let results: Vec<serde_json::Value> = stmt.query_map(
        rusqlite::params![pattern],
        |row| {
            let code: String = row.get(0)?;
            let name: String = row.get(1)?;
            Ok(serde_json::json!({"code": code, "name": name, "industry": ""}))
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

// ============================================================================
// License & Feature Flag 模块（追加于文件末尾，不修改以上任何代码）
// ============================================================================

use crate::feature_flag::{load_flags, FeatureFlags};
use crate::license::{clear_license, parse_license_key, read_license, write_license, LicenseInfo};

#[tauri::command]
pub fn get_feature_flags() -> Result<FeatureFlags, String> {
    load_flags()
}

#[tauri::command]
pub fn activate_license(key: String) -> Result<LicenseInfo, String> {
    let info = parse_license_key(&key)?;
    write_license(&info)?;
    Ok(info)
}

#[tauri::command]
pub fn deactivate_license() -> Result<(), String> {
    clear_license()
}

#[tauri::command]
pub fn get_license_info() -> Result<Option<LicenseInfo>, String> {
    Ok(read_license())
}