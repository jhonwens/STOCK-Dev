use serde::{Deserialize, Serialize};
// ⚠️ Plan 修订 (Batch 2 #1): 不要重新定义 db_path()。
// 现有 src-tauri/src/commands.rs 已有 project_root() + db_path() 工具函数，
// 支持 STOCK_DB_PATH 环境变量覆盖。
// 这里直接 use 即可：
use crate::commands::db_path;

#[derive(Serialize, Deserialize, Debug, Clone)]
pub struct AgentSession {
    pub id: String,
    pub title: String,
    pub created_at: String,
    pub updated_at: String,
    pub message_count: i32,
    pub is_pinned: bool,
    pub last_message: Option<String>,
}

#[derive(Serialize, Deserialize, Debug, Clone)]
pub struct AgentMessage {
    pub id: i32,
    pub session_id: String,
    pub role: String,
    pub content: Option<String>,
    pub tool_calls: Option<serde_json::Value>,
    pub created_at: String,
    pub token_count: Option<i32>,
    pub duration_ms: Option<i32>,
}

#[tauri::command]
pub fn agent_create_session(title: Option<String>) -> Result<serde_json::Value, String> {
    crate::agent_bridge::session_create(db_path().to_str().unwrap(), title)
}

#[tauri::command]
pub fn agent_list_sessions() -> Result<Vec<serde_json::Value>, String> {
    crate::agent_bridge::session_list(db_path().to_str().unwrap())
}

#[tauri::command]
pub fn agent_rename_session(id: String, title: String) -> Result<(), String> {
    crate::agent_bridge::session_rename(db_path().to_str().unwrap(), &id, &title)
}

#[tauri::command]
pub fn agent_delete_session(id: String) -> Result<(), String> {
    crate::agent_bridge::session_delete(db_path().to_str().unwrap(), &id)
}

#[tauri::command]
pub fn agent_pin_session(id: String, pinned: bool) -> Result<(), String> {
    crate::agent_bridge::session_pin(db_path().to_str().unwrap(), &id, pinned)
}

#[tauri::command]
pub fn agent_get_messages(session_id: String) -> Result<Vec<serde_json::Value>, String> {
    crate::agent_bridge::message_list(db_path().to_str().unwrap(), &session_id)
}
