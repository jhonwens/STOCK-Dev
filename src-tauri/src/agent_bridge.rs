use serde::{Deserialize, Serialize};
use std::process::Command;
// ⚠️ Plan 修订: 不要硬编码 current_dir("/Users/ws/...")，用 current_dir(project_root())
use crate::commands::project_root;

#[derive(Serialize, Deserialize, Debug)]
struct PyRequest {
    action: String,
    args: Vec<String>,
    kwargs: serde_json::Value,
}

fn run_python(request: &PyRequest) -> Result<String, String> {
    let json = serde_json::to_string(request).map_err(|e| e.to_string())?;
    let output = Command::new("python3")
        .arg("-m")
        .arg("backend.ai.agent_bridge")
        .arg(&json)
        .current_dir(project_root())
        .output()
        .map_err(|e| format!("Failed to spawn python: {}", e))?;

    if !output.status.success() {
        return Err(format!(
            "Python error: {}",
            String::from_utf8_lossy(&output.stderr)
        ));
    }
    Ok(String::from_utf8_lossy(&output.stdout).to_string())
}

// 业务函数
pub fn session_create(db_path: &str, title: Option<String>) -> Result<serde_json::Value, String> {
    let req = PyRequest {
        action: "session_create".into(),
        args: vec![db_path.to_string()],
        kwargs: serde_json::json!({ "title": title }),
    };
    let out = run_python(&req)?;
    serde_json::from_str(&out).map_err(|e| e.to_string())
}

pub fn session_list(db_path: &str) -> Result<Vec<serde_json::Value>, String> {
    let req = PyRequest {
        action: "session_list".into(),
        args: vec![db_path.to_string()],
        kwargs: serde_json::json!({}),
    };
    let out = run_python(&req)?;
    serde_json::from_str(&out).map_err(|e| e.to_string())
}

pub fn session_rename(db_path: &str, id: &str, title: &str) -> Result<(), String> {
    let req = PyRequest {
        action: "session_rename".into(),
        args: vec![db_path.to_string(), id.to_string()],
        kwargs: serde_json::json!({ "title": title }),
    };
    run_python(&req)?;
    Ok(())
}

pub fn session_delete(db_path: &str, id: &str) -> Result<(), String> {
    let req = PyRequest {
        action: "session_delete".into(),
        args: vec![db_path.to_string(), id.to_string()],
        kwargs: serde_json::json!({}),
    };
    run_python(&req)?;
    Ok(())
}

pub fn session_pin(db_path: &str, id: &str, pinned: bool) -> Result<(), String> {
    let req = PyRequest {
        action: "session_pin".into(),
        args: vec![db_path.to_string(), id.to_string()],
        kwargs: serde_json::json!({ "pinned": pinned }),
    };
    run_python(&req)?;
    Ok(())
}

pub fn message_list(db_path: &str, session_id: &str) -> Result<Vec<serde_json::Value>, String> {
    let req = PyRequest {
        action: "message_list".into(),
        args: vec![db_path.to_string(), session_id.to_string()],
        kwargs: serde_json::json!({}),
    };
    let out = run_python(&req)?;
    serde_json::from_str(&out).map_err(|e| e.to_string())
}
