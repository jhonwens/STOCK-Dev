use crate::commands::backend_cmd_sync;
use rusqlite::Connection;
use serde_json::json;

fn open_db(db_path: &str) -> Result<Connection, String> {
    Connection::open(db_path).map_err(|e| e.to_string())
}

fn ensure_table(conn: &Connection) -> Result<(), String> {
    conn.execute_batch("
        CREATE TABLE IF NOT EXISTS agent_session (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL DEFAULT '新会话',
            pinned INTEGER DEFAULT 0,
            is_pinned INTEGER DEFAULT 0,
            preview TEXT DEFAULT '',
            message_count INTEGER DEFAULT 0,
            last_message TEXT DEFAULT '',
            created_at DATETIME DEFAULT (datetime('now','localtime')),
            updated_at DATETIME DEFAULT (datetime('now','localtime'))
        );
        CREATE TABLE IF NOT EXISTS agent_message (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL DEFAULT '',
            tool_calls TEXT DEFAULT '[]',
            token_count INTEGER DEFAULT 0,
            duration_ms INTEGER DEFAULT 0,
            created_at DATETIME DEFAULT (datetime('now','localtime')),
            FOREIGN KEY (session_id) REFERENCES agent_session(id)
        );
    ").map_err(|e| e.to_string())?;
    // 幂等迁移：老 db 的表可能没有新加的列（逐列 ADD COLUMN，重复则忽略）
    let _ = conn.execute("ALTER TABLE agent_session ADD COLUMN message_count INTEGER DEFAULT 0", []);
    let _ = conn.execute("ALTER TABLE agent_session ADD COLUMN last_message TEXT DEFAULT ''", []);
    let _ = conn.execute("ALTER TABLE agent_session ADD COLUMN is_pinned INTEGER DEFAULT 0", []);
    let _ = conn.execute("ALTER TABLE agent_session ADD COLUMN preview TEXT DEFAULT ''", []);
    let _ = conn.execute("ALTER TABLE agent_message ADD COLUMN token_count INTEGER DEFAULT 0", []);
    Ok(())
}

pub fn session_create(db_path: &str, title: Option<String>) -> Result<serde_json::Value, String> {
    let conn = open_db(db_path)?;
    ensure_table(&conn)?;
    let uid = format!("{:x}", std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap_or_default().as_nanos());
    let title = title.unwrap_or_else(|| "新会话".to_string());
    conn.execute("INSERT INTO agent_session (id, title) VALUES (?1, ?2)", rusqlite::params![uid, title])
        .map_err(|e| e.to_string())?;
    Ok(json!({"id": uid, "title": title, "pinned": false}))
}

pub fn session_list(db_path: &str) -> Result<Vec<serde_json::Value>, String> {
    let conn = open_db(db_path)?;
    let mut stmt = conn.prepare(
        "SELECT id, title, pinned, created_at, updated_at FROM agent_session ORDER BY pinned DESC, updated_at DESC"
    ).map_err(|e| e.to_string())?;
    let rows = stmt.query_map([], |row| {
        Ok(json!({
            "id": row.get::<_, String>(0)?,
            "title": row.get::<_, String>(1)?,
            "pinned": row.get::<_, i32>(2)? != 0,
            "created_at": row.get::<_, String>(3)?,
            "updated_at": row.get::<_, String>(4)?,
        }))
    }).map_err(|e| e.to_string())?;
    let mut result = Vec::new();
    for row in rows {
        result.push(row.map_err(|e| e.to_string())?);
    }
    Ok(result)
}

pub fn session_rename(db_path: &str, id: &str, title: &str) -> Result<(), String> {
    let conn = open_db(db_path)?;
    conn.execute(
        "UPDATE agent_session SET title = ?1, updated_at = datetime('now','localtime') WHERE id = ?2",
        rusqlite::params![title, id],
    ).map_err(|e| e.to_string())?;
    Ok(())
}

pub fn session_delete(db_path: &str, id: &str) -> Result<(), String> {
    let conn = open_db(db_path)?;
    conn.execute("DELETE FROM agent_message WHERE session_id = ?1", rusqlite::params![id])
        .map_err(|e| e.to_string())?;
    conn.execute("DELETE FROM agent_session WHERE id = ?1", rusqlite::params![id])
        .map_err(|e| e.to_string())?;
    Ok(())
}

pub fn session_pin(db_path: &str, id: &str, pinned: bool) -> Result<(), String> {
    let conn = open_db(db_path)?;
    conn.execute(
        "UPDATE agent_session SET pinned = ?1, updated_at = datetime('now','localtime') WHERE id = ?2",
        rusqlite::params![if pinned { 1 } else { 0 }, id],
    ).map_err(|e| e.to_string())?;
    Ok(())
}

pub fn message_list(db_path: &str, session_id: &str) -> Result<Vec<serde_json::Value>, String> {
    let conn = open_db(db_path)?;
    let mut stmt = conn.prepare(
        "SELECT id, session_id, role, content, tool_calls, duration_ms, created_at \
         FROM agent_message WHERE session_id = ?1 ORDER BY id ASC"
    ).map_err(|e| e.to_string())?;
    let rows = stmt.query_map(rusqlite::params![session_id], |row| {
        let raw_tc: String = row.get(4).unwrap_or("[]".into());
        let tool_calls: serde_json::Value = serde_json::from_str(&raw_tc).unwrap_or(json!([]));
        Ok(json!({
            "id": row.get::<_, i32>(0)?,
            "session_id": row.get::<_, String>(1)?,
            "role": row.get::<_, String>(2)?,
            "content": row.get::<_, String>(3)?,
            "tool_calls": tool_calls,
            "duration_ms": row.get::<_, i32>(5).unwrap_or(0),
            "created_at": row.get::<_, String>(6)?,
        }))
    }).map_err(|e| e.to_string())?;
    let mut result = Vec::new();
    for row in rows {
        result.push(row.map_err(|e| e.to_string())?);
    }
    Ok(result)
}

pub fn export_message(
    db_path: &str,
    session_id: &str,
    message_id: i32,
    format: &str,
    output_dir: Option<&str>,
) -> Result<serde_json::Value, String> {
    let msg_id = message_id.to_string();
    let mut extra = vec![session_id, msg_id.as_str(), format];
    if let Some(dir) = output_dir {
        extra.push(dir);
    }
    let mut cmd = backend_cmd_sync();
    cmd.arg("script").arg("agent_handler.py");
    cmd.arg("export_message");
    cmd.arg(db_path);
    for arg in extra {
        cmd.arg(arg);
    }
    let output = cmd.output().map_err(|e| format!("Failed to spawn handler: {}", e))?;
    if !output.status.success() {
        let stderr = String::from_utf8_lossy(&output.stderr);
        return Err(format!("Handler error: {}", stderr.trim()));
    }
    let out = String::from_utf8_lossy(&output.stdout).to_string();
    serde_json::from_str(&out).map_err(|e| e.to_string())
}

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
    use std::process::Stdio;

    let mut child = backend_cmd_sync()
        .arg("script").arg("agent_bridge_cli.py")
        .arg("streaming")
        .arg(db_path)
        .arg(session_id)
        .arg(text)
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .spawn()
        .map_err(|e| format!("Spawn failed: {}", e))?;

    let stderr = child.stderr.take().ok_or("No stderr")?;
    std::thread::spawn(move || {
        use std::io::Read;
        let mut buf = String::new();
        let mut reader = std::io::BufReader::new(stderr);
        let _ = reader.read_to_string(&mut buf);
    });

    let stdout = child.stdout.take().ok_or("No stdout")?;
    let reader = BufReader::new(stdout);

    let mut final_msg_id = 0;

    for line in reader.lines() {
        let line = line.map_err(|e| e.to_string())?;
        if line.is_empty() {
            continue;
        }
        if let Ok(evt) = serde_json::from_str::<serde_json::Value>(&line) {
            let event_type = evt["event"].as_str().unwrap_or("").to_string();
            let data = evt["data"].clone();
            on_event(&event_type, &data);

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
