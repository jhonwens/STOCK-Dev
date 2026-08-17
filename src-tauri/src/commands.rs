use std::collections::HashMap;
use std::path::PathBuf;
use std::sync::OnceLock;
use serde::{Deserialize, Serialize};
use serde_json;
use rusqlite::Connection;

static APP_ROOT: OnceLock<PathBuf> = OnceLock::new();

/// 初始化应用根路径（在 main.rs 启动时调用一次）
/// - 打包模式：使用 .app bundle 内的 Resources 目录
/// - 开发模式：使用 CARGO_MANIFEST_DIR 的父目录（项目根）
pub fn init_app_root(bundled_root: Option<PathBuf>) {
    if let Some(root) = bundled_root {
        APP_ROOT.get_or_init(|| root);
    } else {
        let manifest = PathBuf::from(env!("CARGO_MANIFEST_DIR"));
        let root = manifest.parent().map(PathBuf::from).unwrap_or_else(|| PathBuf::from("."));
        APP_ROOT.get_or_init(|| root);
    }
}

pub fn project_root() -> PathBuf {
    APP_ROOT.get().cloned().unwrap_or_else(|| {
        let manifest = PathBuf::from(env!("CARGO_MANIFEST_DIR"));
        manifest.parent().map(PathBuf::from).unwrap_or_else(|| PathBuf::from("."))
    })
}

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

pub fn db_path() -> PathBuf {
    if let Ok(path) = std::env::var("STOCK_DB_PATH") {
        return PathBuf::from(path);
    }
    project_root().join("backend").join("stock-analyst").join("data").join("stock_data.db")
}

/// 构建后端可执行文件的同步命令
/// - 打包模式：STOCK_BACKEND_RUNNER -> backend-runner（编译后的独立可执行文件）
/// - 开发模式：python3 backend/pyentry/entry.py
///
/// 关键：子进程不会自动继承 Rust 进程的环境变量（特别是 Tauri 启动后
/// 通过 set_var 设置的）。所以这里显式传入 STOCK_DB_PATH/STOCK_CONFIG_DIR
/// 等关键变量，确保 Python 脚本能正确找到数据库和配置文件。
pub fn backend_cmd_sync() -> std::process::Command {
    let mut cmd = if let Ok(runner) = std::env::var("STOCK_BACKEND_RUNNER") {
        std::process::Command::new(runner)
    } else {
        let entry = project_root().join("backend").join("pyentry").join("entry.py");
        let mut cmd = std::process::Command::new("python3");
        cmd.arg(entry);
        cmd
    };
    inject_runtime_env(&mut cmd);
    cmd
}

/// 构建后端可执行文件的异步命令（用于 async 函数）
pub fn backend_cmd_async() -> tokio::process::Command {
    let mut cmd = if let Ok(runner) = std::env::var("STOCK_BACKEND_RUNNER") {
        tokio::process::Command::new(runner)
    } else {
        let entry = project_root().join("backend").join("pyentry").join("entry.py");
        let mut cmd = tokio::process::Command::new("python3");
        cmd.arg(entry);
        cmd
    };
    inject_runtime_env_async(&mut cmd);
    cmd
}

/// 同步命令注入运行时环境变量
fn inject_runtime_env(cmd: &mut std::process::Command) {
    for key in [
        "STOCK_PROJECT_ROOT",
        "STOCK_BACKEND_RUNNER",
        "STOCK_DB_PATH",
        "STOCK_CONFIG_DIR",
        "STOCK_LIST_PATH",
        "SSL_CERT_FILE",
        "REQUESTS_CA_BUNDLE",
    ] {
        if let Ok(val) = std::env::var(key) {
            cmd.env(key, val);
        }
    }
}

/// 异步命令注入运行时环境变量
fn inject_runtime_env_async(cmd: &mut tokio::process::Command) {
    for key in [
        "STOCK_PROJECT_ROOT",
        "STOCK_BACKEND_RUNNER",
        "STOCK_DB_PATH",
        "STOCK_CONFIG_DIR",
        "STOCK_LIST_PATH",
        "SSL_CERT_FILE",
        "REQUESTS_CA_BUNDLE",
    ] {
        if let Ok(val) = std::env::var(key) {
            cmd.env(key, val);
        }
    }
}

fn load_stock_list() -> Result<Vec<StockListEntry>, String> {
    let path = stock_list_path();
    let content = std::fs::read_to_string(&path)
        .map_err(|e| format!("读取 stock 列表失败: {}", e))?;
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
    // 打包模式：优先读可写应用数据目录中的 stock_list.yaml（支持增删股票）
    if let Ok(path) = std::env::var("STOCK_LIST_PATH") {
        let pb = PathBuf::from(&path);
        if pb.exists() {
            return pb;
        }
        // 首次启动：从 bundle 资源拷贝初始股票列表到可写目录
        if let Some(parent) = pb.parent() {
            let _ = std::fs::create_dir_all(parent);
        }
        let bundled = project_root().join("backend").join("stock-analyst").join("resource").join("stock_list.yaml");
        if bundled.exists() {
            let _ = std::fs::copy(&bundled, &pb);
        } else {
            let _ = std::fs::write(&pb, "stocks: []\n");
        }
        return pb;
    }
    // 开发模式 / 兜底：项目目录下的 stock_list.yaml
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
            "SELECT code, name, price, change_pct, COALESCE(volume, 0) \
             FROM stock_realtime GROUP BY code ORDER BY change_pct DESC LIMIT 10"
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
            "SELECT code, name, price, change_pct, COALESCE(volume, 0) \
             FROM stock_realtime GROUP BY code ORDER BY change_pct ASC LIMIT 10"
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
    use tokio::time::{timeout, Duration};
    let cmd_fut = backend_cmd_async()
        .arg("script").arg("main.py").arg("--mode").arg("quick")
        .output();
    eprintln!("[run_analysis] starting backend (timeout=600s)...");
    match timeout(Duration::from_secs(600), cmd_fut).await {
        Ok(Ok(output)) => {
            let stdout = String::from_utf8_lossy(&output.stdout);
            let stderr = String::from_utf8_lossy(&output.stderr);
            eprintln!("[run_analysis] stdout:\n{}", stdout);
            if !stderr.is_empty() {
                eprintln!("[run_analysis] stderr:\n{}", stderr);
            }
            if output.status.success() {
                Ok(stdout.to_string())
            } else {
                Err(stderr.to_string())
            }
        }
        Ok(Err(e)) => Err(format!("Failed to start backend: {}", e)),
        Err(_) => Err("数据更新超时（>600秒），请稍后重试".to_string()),
    }
}

#[tauri::command]
pub async fn run_candidate_llm() -> Result<String, String> {
    let output = backend_cmd_async()
        .arg("script").arg("candidate_recommend.py")
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
    let output = backend_cmd_async()
        .arg("script").arg("main.py").arg("--mode").arg("llm").arg("--scope").arg(&scope)
        .output()
        .await
        .map_err(|e| format!("Failed to start backend: {}", e))?;
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

fn llm_config_path() -> PathBuf {
    if let Ok(dir) = std::env::var("STOCK_CONFIG_DIR") {
        PathBuf::from(dir).join("llm_config.json")
    } else {
        project_root().join("config").join("llm_config.json")
    }
}

fn read_llm_config() -> Result<serde_json::Value, String> {
    let path = llm_config_path();
    let content = std::fs::read_to_string(&path)
        .map_err(|e| format!("读取 LLM 配置失败: {}", e))?;
    serde_json::from_str(&content).map_err(|e| e.to_string())
}

fn write_llm_config(value: &serde_json::Value) -> Result<(), String> {
    let path = llm_config_path();
    if let Some(parent) = path.parent() {
        std::fs::create_dir_all(parent).map_err(|e| e.to_string())?;
    }
    let content = serde_json::to_string_pretty(value).map_err(|e| e.to_string())?;
    std::fs::write(&path, content).map_err(|e| e.to_string())
}

#[tauri::command]
pub fn load_llm_config() -> Result<String, String> {
    // 向后兼容：返回当前激活的单个模型
    let config = read_llm_config()?;
    // JSON 数组格式 → 取第一个 enabled=true 的对象
    let active = config.as_array()
        .and_then(|arr| arr.iter().find(|m| m.get("enabled").and_then(|v| v.as_bool()).unwrap_or(false)))
        .cloned()
        .unwrap_or(serde_json::Value::Null);
    Ok(serde_json::to_string(&active).unwrap_or_else(|_| "{}".to_string()))
}

/// 通过 Python CLI 转发 LLM 配置命令（写操作和测试连接）
fn call_llm_cli(args: &[&str]) -> Result<String, String> {
    let mut cmd = backend_cmd_sync();
    cmd.arg("script").arg("llm_config_cli.py");
    cmd.args(args);

    let output = cmd
        .output()
        .map_err(|e| format!("调用后端失败: {}", e))?;

    if !output.status.success() {
        let stderr = String::from_utf8_lossy(&output.stderr);
        return Err(format!("CLI 错误: {}", stderr.trim()));
    }
    Ok(String::from_utf8_lossy(&output.stdout).trim().to_string())
}

// 多模型管理新命令
#[tauri::command]
pub fn list_llm_models() -> Result<String, String> {
    let config = read_llm_config()?;
    Ok(serde_json::to_string(&config).unwrap_or_else(|_| "[]".to_string()))
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
    let content = std::fs::read_to_string(&path).unwrap_or_default();
    let mut value: serde_yaml::Value = serde_yaml::from_str(&content).unwrap_or(serde_yaml::Value::Mapping({
        let mut m = serde_yaml::Mapping::new();
        m.insert(serde_yaml::Value::String("stocks".into()), serde_yaml::Value::Sequence(vec![]));
        m
    }));
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
    if let Some(parent) = path.parent() {
        std::fs::create_dir_all(parent).map_err(|e| e.to_string())?;
    }
    std::fs::write(&path, out).map_err(|e| e.to_string())?;
    Ok(format!("✅ 已添加 {}", code))
}

#[tauri::command]
pub fn remove_stock_from_list(code: String) -> Result<String, String> {
    let path = stock_list_path();
    let content = std::fs::read_to_string(&path).unwrap_or_default();
    let mut value: serde_yaml::Value = serde_yaml::from_str(&content).unwrap_or(serde_yaml::Value::Mapping({
        let mut m = serde_yaml::Mapping::new();
        m.insert(serde_yaml::Value::String("stocks".into()), serde_yaml::Value::Sequence(vec![]));
        m
    }));
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
    if let Some(parent) = path.parent() {
        std::fs::create_dir_all(parent).map_err(|e| e.to_string())?;
    }
    std::fs::write(&path, out).map_err(|e| e.to_string())?;

    let conn = Connection::open(db_path()).map_err(|e| e.to_string())?;
    clean_stock_data(&conn, &code);
    Ok(format!("✅ 已移除 {}", code))
}

fn clean_stock_data(conn: &rusqlite::Connection, code: &str) {
    for table in &[
        "stock_realtime", "stock_fund_flow", "stock_finance", "stock_news",
        "stock_trend", "stock_alert", "stock_history", "stock_limit_up",
        "stock_technical", "stock_pattern", "stock_chan_theory",
        "stock_portfolio", "stock_llm_report", "stock_score",
    ] {
        conn.execute(&format!("DELETE FROM {} WHERE code=?1", table), rusqlite::params![code]).ok();
    }
}

#[tauri::command]
pub fn batch_remove_stocks(codes: Vec<String>) -> Result<String, String> {
    eprintln!("[batch_remove_stocks] called with {} codes: {:?}", codes.len(), codes);
    if codes.is_empty() {
        return Err("请选择至少一只股票".to_string());
    }
    let path = stock_list_path();
    eprintln!("[batch_remove_stocks] stock_list_path: {:?}", path);
    let content = std::fs::read_to_string(&path).map_err(|e| e.to_string())?;
    let mut value: serde_yaml::Value = serde_yaml::from_str(&content).map_err(|e| e.to_string())?;
    let removed_count = if let Some(stocks) = value["stocks"].as_sequence_mut() {
        let len_before = stocks.len();
        stocks.retain(|v| !codes.contains(&v["code"].as_str().unwrap_or("").to_string()));
        len_before - stocks.len()
    } else {
        0
    };
    if removed_count == 0 {
        return Err("未找到匹配的股票".to_string());
    }
    let out = serde_yaml::to_string(&value).map_err(|e| e.to_string())?;
    std::fs::write(&path, out).map_err(|e| e.to_string())?;

    let conn = Connection::open(db_path()).map_err(|e| e.to_string())?;
    for code in &codes {
        clean_stock_data(&conn, code);
    }
    Ok(format!("✅ 已批量移除 {} 只股票", removed_count))
}

#[derive(Serialize, Deserialize)]
pub struct StockInput {
    pub code: String,
    pub name: String,
    pub industry: String,
}

#[tauri::command]
pub fn batch_add_stocks(stocks: Vec<StockInput>) -> Result<String, String> {
    if stocks.is_empty() {
        return Err("请提供至少一只股票".to_string());
    }
    let path = stock_list_path();
    let entries = load_stock_list().unwrap_or_default();
    let existing: std::collections::HashSet<String> = entries.iter().map(|e| e.code.clone()).collect();
    let mut added = 0;
    let mut skipped = 0;

    let content = std::fs::read_to_string(&path).unwrap_or_default();
    let mut value: serde_yaml::Value = serde_yaml::from_str(&content).unwrap_or(serde_yaml::Value::Mapping({
        let mut m = serde_yaml::Mapping::new();
        m.insert(serde_yaml::Value::String("stocks".into()), serde_yaml::Value::Sequence(vec![]));
        m
    }));

    for s in &stocks {
        if existing.contains(&s.code) {
            skipped += 1;
            continue;
        }
        let new_item = serde_yaml::Value::Mapping({
            let mut m = serde_yaml::Mapping::new();
            m.insert(serde_yaml::Value::String("code".into()), serde_yaml::Value::String(s.code.clone()));
            m.insert(serde_yaml::Value::String("name".into()), serde_yaml::Value::String(s.name.clone()));
            m.insert(serde_yaml::Value::String("industry".into()), serde_yaml::Value::String(s.industry.clone()));
            m
        });
        if let Some(stocks) = value["stocks"].as_sequence_mut() {
            stocks.push(new_item);
        }
        added += 1;
    }

    if added == 0 {
        return Ok("所有股票已在列表中，无需添加".to_string());
    }
    let out = serde_yaml::to_string(&value).map_err(|e| e.to_string())?;
    if let Some(parent) = path.parent() {
        std::fs::create_dir_all(parent).map_err(|e| e.to_string())?;
    }
    std::fs::write(&path, out).map_err(|e| e.to_string())?;
    Ok(format!("✅ 成功添加 {} 只股票{}", added, if skipped > 0 { format!("，{} 只已存在已跳过", skipped) } else { String::new() }))
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
    let output = backend_cmd_async()
        .arg("script").arg("portfolio_analysis.py").arg(&code)
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
pub fn update_stock_score_from_llm(code: String, suggestion: String, risk_level: String) -> Result<String, String> {
    let conn = Connection::open(&db_path()).map_err(|e| e.to_string())?;
    let now = chrono::Local::now().format("%Y-%m-%d %H:%M:%S").to_string();
    conn.execute(
        "INSERT OR REPLACE INTO stock_score (code, score, suggestion, risk_level, updated_at) VALUES (?1, ?2, ?3, ?4, ?5)",
        rusqlite::params![code, 0, suggestion, risk_level, now],
    ).map_err(|e| e.to_string())?;
    Ok(format!("✅ 已更新 {} 的建议", code))
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
    let output = backend_cmd_async()
        .arg("script").arg("stock_insight.py").arg("--code").arg(&code)
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

#[tauri::command]
pub fn test_export_msg(message_id: i32, format: String) -> Result<String, String> {
    use std::io::Write;

    let conn = Connection::open(db_path()).map_err(|e| format!("DB:{}", e))?;
    let (content, _, session_title): (String, String, String) = conn
        .query_row(
            "SELECT m.content, m.created_at, s.title \
             FROM agent_message m JOIN agent_session s ON m.session_id = s.id WHERE m.id = ?1",
            rusqlite::params![message_id],
            |row| Ok((row.get(0)?, row.get(1)?, row.get(2)?)),
        )
        .map_err(|e| format!("消息不存在({})", e))?;

    let name: String = session_title.chars().filter(|c| c.is_alphanumeric() || *c == '_').take(20).collect();
    let ts = chrono::Local::now().format("%Y%m%d_%H%M%S");
    let filename = format!("{}_{}_{}.{}", name, message_id, ts, format);

    let downloads = dirs::download_dir().unwrap_or_else(|| std::path::PathBuf::from("."));
    let dir = downloads.join("衡势价值导出");
    std::fs::create_dir_all(&dir).map_err(|e| format!("目录:{}", e))?;
    let path = dir.join(&filename);

    let md = format!("# {}\n\n{}\n", session_title, content);
    let mut f = std::fs::File::create(&path).map_err(|e| format!("文件:{}", e))?;
    f.write_all(md.as_bytes()).map_err(|e| format!("写入:{}", e))?;

    let _ = std::process::Command::new("open").arg("-R").arg(&path).spawn();
    Ok(path.to_string_lossy().to_string())
}

#[tauri::command]
#[allow(unused_variables)]
pub fn export_agent_message(
    app: tauri::AppHandle,
    session_id: String,
    message_id: i32,
    format: String,
) -> Result<String, String> {
    use std::io::Write;

    let conn = Connection::open(db_path()).map_err(|e| format!("DB:{}", e))?;
    let (content, tool_calls_raw, created_at, session_title): (String, Option<String>, String, String) = conn
        .query_row(
            "SELECT m.content, m.tool_calls, m.created_at, s.title \
             FROM agent_message m JOIN agent_session s ON m.session_id = s.id WHERE m.id = ?1",
            rusqlite::params![message_id],
            |row| Ok((row.get(0)?, row.get(1)?, row.get(2)?, row.get(3)?)),
        )
        .map_err(|e| format!("消息不存在({})", e))?;
    let tool_calls_raw = tool_calls_raw.unwrap_or_default();

    let safe_title: String = session_title.chars().filter(|c| c.is_alphanumeric() || *c == '_' || *c == '-').take(20).collect();
    let timestamp = chrono::Local::now().format("%Y%m%d_%H%M%S");
    let default_name = format!("{}_{}_{}.{}", safe_title, message_id, timestamp, format);

    // 保存到下载目录 + Finder 打开（不考虑对话框）
    let d = dirs::download_dir().unwrap_or_else(|| std::path::PathBuf::from("."));
    let dir = d.join("衡势价值导出");
    std::fs::create_dir_all(&dir).map_err(|e| format!("目录:{}", e))?;
    let save_path = dir.join(&default_name);

    let mut file = std::fs::File::create(&save_path).map_err(|e| format!("文件创建失败: {}", e))?;

    if format == "html" {
        let tc_html = if tool_calls_raw != "[]" && tool_calls_raw != "null" {
            format!("<h2>工具调用</h2><pre>{}</pre>", tool_calls_raw)
        } else { String::new() };
        let body_html = comrak::markdown_to_html(&content, &comrak::Options::default());
        write!(file, "<!DOCTYPE html><html lang=\"zh-CN\"><head><meta charset=\"UTF-8\"><title>{}</title>
<style>
  body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Noto Sans SC', sans-serif; max-width: 900px; margin: 40px auto; padding: 0 24px; color: #1f2937; line-height: 1.8; font-size: 15px; }}
  h1 {{ font-size: 26px; border-bottom: 2px solid #e5e7eb; padding-bottom: 12px; }}
  h2 {{ font-size: 20px; margin-top: 32px; border-bottom: 1px solid #f3f4f6; padding-bottom: 6px; }}
  h3 {{ font-size: 17px; margin-top: 24px; }}
  p {{ margin: 12px 0; }}
  code {{ background: #f3f4f6; padding: 2px 6px; border-radius: 4px; font-size: 13px; }}
  pre {{ background: #1e1e2e; color: #cdd6f4; padding: 16px; border-radius: 8px; overflow-x: auto; font-size: 13px; line-height: 1.6; }}
  pre code {{ background: none; padding: 0; }}
  table {{ border-collapse: collapse; width: 100%; margin: 16px 0; }}
  th, td {{ border: 1px solid #e5e7eb; padding: 8px 12px; text-align: left; font-size: 13px; }}
  th {{ background: #f9fafb; font-weight: 600; }}
  hr {{ border: none; border-top: 1px solid #e5e7eb; margin: 24px 0; }}
  blockquote {{ border-left: 4px solid #3b82f6; margin: 12px 0; padding: 8px 16px; background: #f9fafb; }}
  ul, ol {{ padding-left: 24px; }}
  .meta {{ color: #6b7280; font-size: 13px; margin-bottom: 24px; }}
</style>
</head><body><h1>{}</h1><div class=\"meta\">生成时间: {}</div>{}{}</body></html>",
            session_title, session_title, created_at, body_html, tc_html
        ).map_err(|e| format!("写入失败: {}", e))?;
    } else {
        let tc_md = if tool_calls_raw != "[]" && tool_calls_raw != "null" {
            format!("\n## 工具调用\n\n```json\n{}\n```\n", tool_calls_raw)
        } else { String::new() };
        write!(file, "# {}\n\n**生成时间**: {}\n\n{}{}\n", session_title, created_at, content, tc_md)
            .map_err(|e| format!("写入失败: {}", e))?;
    }

    let _ = std::process::Command::new("open").arg("-R").arg(&save_path).spawn();
    Ok(save_path.to_string_lossy().to_string())
}

#[cfg(target_os = "macos")]
fn try_save_dialog(_app: &tauri::AppHandle, default_name: &str, _format: &str) -> Option<std::path::PathBuf> {
    let script = format!(
        "POSIX path of (choose file name with prompt \"导出分析结果\" default name \"{}\")",
        default_name.replace("\"", "\\\"")
    );
    std::process::Command::new("osascript")
        .arg("-e")
        .arg(&script)
        .output()
        .ok()
        .and_then(|o| {
            if o.status.success() {
                let p = String::from_utf8_lossy(&o.stdout).trim().to_string();
                if !p.is_empty() { Some(std::path::PathBuf::from(p)) } else { None }
            } else { None }
        })
}

#[cfg(not(target_os = "macos"))]
fn try_save_dialog(_app: &tauri::AppHandle, _default_name: &str, _format: &str) -> Option<std::path::PathBuf> {
    None
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