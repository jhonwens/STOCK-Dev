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

// ⚠️ Plan 修订 (Batch 2 #6, 方案 A): 改从 "assistant_saved" 事件拿 message_id
// Python bridge save assistant message 后 emit 该事件
pub fn send_message_streaming<F>(
    db_path: &str,
    session_id: &str,
    text: &str,
    mut on_event: F,
) -> Result<i32, String>
where
    F: FnMut(&str, &serde_json::Value) + Send + 'static,
{
    use std::io::{BufRead, BufReader};
    use std::process::{Command, Stdio};

    let mut child = Command::new("python3")
        .arg("-m")
        .arg("backend.ai.agent_bridge")
        .arg("streaming")
        .arg(db_path)
        .arg(session_id)
        .arg(text)
        .current_dir(project_root())
        .stdout(Stdio::piped())
        .spawn()
        .map_err(|e| format!("Spawn failed: {}", e))?;

    let stdout = child.stdout.take().ok_or("No stdout")?;
    let reader = BufReader::new(stdout);

    let mut final_msg_id = 0;

    for line in reader.lines() {
        let line = line.map_err(|e| e.to_string())?;
        if line.is_empty() {
            continue;
        }
        // 每行是一个 JSON 事件：{"event": "...", "data": ...}
        if let Ok(evt) = serde_json::from_str::<serde_json::Value>(&line) {
            let event_type = evt["event"].as_str().unwrap_or("").to_string();
            let data = evt["data"].clone();
            on_event(&event_type, &data);

            // ⚠️ Plan 修订 (方案 A): 不再从 "done" 拿 message_id
            // 改从 "assistant_saved" 事件拿（Python bridge save 后 emit）
            if event_type == "assistant_saved" {
                if let Some(id) = data["message_id"].as_i64() {
                    final_msg_id = id as i32;
                }
            }
        }
    }

    child.wait().map_err(|e| e.to_string())?;
    Ok(final_msg_id)
}
