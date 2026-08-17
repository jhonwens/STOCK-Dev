import { useState } from "react";
import { invoke } from "@tauri-apps/api/core";

function fmtDate(sqliteDt: string): string {
  if (!sqliteDt) return "";
  const d = new Date(sqliteDt.replace(" ", "T") + (sqliteDt.includes("Z") ? "" : "+08:00"));
  if (isNaN(d.getTime())) return sqliteDt.slice(0, 16);
  return d.toLocaleString("zh-CN", { month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit" });
}

export interface AgentSession {
  id: string;
  title: string;
  created_at: string;
  updated_at: string;
  message_count: number;
  is_pinned: boolean;
  last_message?: string;
}

interface Props {
  sessions: AgentSession[];
  currentId: string | null;
  onSelect: (id: string) => void;
  onRefresh: () => void;
  onCreate: () => void;
}

export default function SessionList({ sessions, currentId, onSelect, onRefresh, onCreate }: Props) {
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editingTitle, setEditingTitle] = useState("");

  async function handleRename(id: string, newTitle: string) {
    if (!newTitle.trim()) return;
    try {
      await invoke("agent_rename_session", { id, title: newTitle.trim() });
      setEditingId(null);
      onRefresh();
    } catch (e) {
      console.error("Rename failed:", e);
    }
  }

  async function handleDelete(id: string) {
    try {
      console.log("Deleting session:", id);
      await invoke("agent_delete_session", { id });
      console.log("Delete succeeded");
      onRefresh();
    } catch (e) {
      console.error("Delete failed:", e);
    }
  }

  async function handlePin(id: string, currentPinned: boolean) {
    try {
      await invoke("agent_pin_session", { id, pinned: !currentPinned });
      onRefresh();
    } catch (e) {
      console.error("Pin failed:", e);
    }
  }

  return (
    <aside style={{
      width: 260, flexShrink: 0,
      display: "flex", flexDirection: "column",
      background: "var(--session-bg)",
      borderRight: "1px solid var(--border)",
    }}>
      <div style={{ padding: "14px 14px 10px", borderBottom: "1px solid var(--border)" }}>
        <button
          onClick={onCreate}
          style={{
            width: "100%", padding: "10px 14px", borderRadius: 8,
            background: "linear-gradient(135deg, var(--primary), var(--primary-dark))",
            color: "#fff", fontSize: 13, fontWeight: 500,
            border: "none", cursor: "pointer",
            boxShadow: "0 1px 3px rgba(59,130,246,0.3)",
            transition: "all 0.15s ease",
          }}
        >
          <span style={{ marginRight: 6 }}>＋</span>新建会话
        </button>
      </div>
      <div style={{ flex: 1, overflowY: "auto", padding: "8px 10px" }}>
        {sessions.length === 0 && (
          <div style={{ textAlign: "center", color: "var(--text-tertiary)", fontSize: 13, padding: "32px 0" }}>
            暂无会话
          </div>
        )}
        {sessions.map((s) => (
          <div
            key={s.id}
            className="session-item"
            onClick={() => editingId !== s.id && onSelect(s.id)}
            onDoubleClick={() => { setEditingId(s.id); setEditingTitle(s.title); }}
            style={{
              padding: "10px 10px", marginBottom: 2, borderRadius: 8,
              cursor: "pointer", fontSize: 13,
              display: "flex", alignItems: "center", justifyContent: "space-between",
              background: s.id === currentId ? "var(--session-active)" : "transparent",
              color: s.id === currentId ? "#1e3a5f" : "var(--text)",
              transition: "all 0.15s ease",
            }}
          >
            <div style={{ flex: 1, minWidth: 0 }}>
              {editingId === s.id ? (
                <input
                  autoFocus
                  value={editingTitle}
                  onChange={(e) => setEditingTitle(e.target.value)}
                  onBlur={() => handleRename(s.id, editingTitle)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter") handleRename(s.id, editingTitle);
                    if (e.key === "Escape") setEditingId(null);
                  }}
                  style={{ width: "100%", padding: "4px 6px", fontSize: 13, border: "1px solid var(--primary)", borderRadius: 4, outline: "none" }}
                />
              ) : (
                <>
                  <div style={{
                    fontWeight: s.id === currentId ? 600 : 500,
                    overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap",
                    display: "flex", alignItems: "center", gap: 4,
                    fontSize: 13,
                  }}>
                    <span style={{ fontSize: 14 }}>{s.is_pinned ? "📌" : "💬"}</span>
                    {s.title}
                  </div>
                  <div style={{ fontSize: 11, color: "var(--text-tertiary)", marginTop: 2, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", paddingLeft: 20 }}>
                    {fmtDate(s.updated_at)}
                    {s.message_count > 0 && <span> · {s.message_count} 条</span>}
                  </div>
                </>
              )}
            </div>
            <div style={{ display: "flex", gap: 2, opacity: 0 }} className="session-actions">
              <button
                onClick={(e) => { e.stopPropagation(); handlePin(s.id, s.is_pinned); }}
                style={{ fontSize: 12, padding: "2px 4px", border: "none", background: "none", cursor: "pointer", borderRadius: 4, lineHeight: 1 }}
                title={s.is_pinned ? "取消置顶" : "置顶"}
              >📌</button>
              <button
                onClick={(e) => { e.stopPropagation(); handleDelete(s.id); }}
                style={{ fontSize: 12, padding: "2px 4px", border: "none", background: "none", cursor: "pointer", borderRadius: 4, lineHeight: 1 }}
                title="删除"
              >🗑️</button>
            </div>
          </div>
        ))}
      </div>
    </aside>
  );
}
