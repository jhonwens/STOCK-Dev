import { useState } from "react";
// ⚠️ Plan 修订: Tauri 2.x 应使用 @tauri-apps/api/core（不是 /tauri）
// 与现有 src/services/api.ts 保持一致
import { invoke } from "@tauri-apps/api/core";

export interface AgentSession {
  id: string;
  title: string;
  createdAt: string;
  updatedAt: string;
  messageCount: number;
  isPinned: boolean;
  lastMessage?: string;
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
    if (!confirm("确定删除该会话？")) return;
    try {
      await invoke("agent_delete_session", { id });
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
    <aside className="w-60 border-r border-gray-200 flex flex-col bg-gray-50">
      <div className="p-3 border-b">
        <button
          onClick={onCreate}
          className="w-full py-2 px-3 rounded bg-blue-500 text-white text-sm hover:bg-blue-600"
        >
          ➕ 新建会话
        </button>
      </div>
      <div className="flex-1 overflow-y-auto p-2">
        {sessions.length === 0 && (
          <div className="text-center text-gray-400 text-sm py-4">暂无会话</div>
        )}
        {sessions.map((s) => (
          <div
            key={s.id}
            onClick={() => editingId !== s.id && onSelect(s.id)}
            onDoubleClick={() => {
              setEditingId(s.id);
              setEditingTitle(s.title);
            }}
            className={`group p-2 mb-1 rounded cursor-pointer text-sm flex items-center justify-between ${
              s.id === currentId ? "bg-blue-100 text-blue-900" : "hover:bg-gray-100"
            }`}
          >
            <div className="flex-1 min-w-0">
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
                  className="w-full px-1 py-0.5 text-sm border border-blue-300 rounded"
                />
              ) : (
                <>
                  <div className="font-medium truncate flex items-center gap-1">
                    {s.isPinned && <span className="text-yellow-500">📌</span>}
                    {s.title}
                  </div>
                  <div className="text-xs text-gray-500 truncate">
                    {new Date(s.updatedAt).toLocaleString("zh-CN")}
                  </div>
                </>
              )}
            </div>
            <div className="opacity-0 group-hover:opacity-100 flex gap-1">
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  handlePin(s.id, s.isPinned);
                }}
                className="text-xs px-1"
                title={s.isPinned ? "取消置顶" : "置顶"}
              >
                📌
              </button>
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  handleDelete(s.id);
                }}
                className="text-xs px-1 text-red-500"
                title="删除"
              >
                🗑️
              </button>
            </div>
          </div>
        ))}
      </div>
    </aside>
  );
}
