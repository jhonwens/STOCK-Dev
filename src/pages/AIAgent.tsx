import { useState, useEffect } from "react";
// ⚠️ Plan 修订: Tauri 2.x 应使用 @tauri-apps/api/core（不是 /tauri）
// 与现有 src/services/api.ts 保持一致
import { invoke } from "@tauri-apps/api/core";

interface AgentSession {
  id: string;
  title: string;
  createdAt: string;
  updatedAt: string;
  messageCount: number;
  isPinned: boolean;
  lastMessage?: string;
}

export default function AIAgent() {
  const [sessions, setSessions] = useState<AgentSession[]>([]);
  const [currentSessionId, setCurrentSessionId] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    loadSessions();
  }, []);

  async function loadSessions() {
    try {
      const list = await invoke<AgentSession[]>("agent_list_sessions");
      setSessions(list);
    } catch (e) {
      console.error("Load sessions failed:", e);
    }
  }

  async function handleNewSession() {
    try {
      setLoading(true);
      const session = await invoke<AgentSession>("agent_create_session", { title: null });
      setSessions([session, ...sessions]);
      setCurrentSessionId(session.id);
    } catch (e) {
      console.error("Create session failed:", e);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex h-full">
      {/* 左侧会话列表 */}
      <aside className="w-60 border-r border-gray-200 flex flex-col">
        <div className="p-3 border-b">
          <button
            onClick={handleNewSession}
            disabled={loading}
            className="w-full py-2 px-3 rounded bg-blue-500 text-white text-sm hover:bg-blue-600 disabled:opacity-50"
          >
            ➕ 新建会话
          </button>
        </div>
        <div className="flex-1 overflow-y-auto p-2">
          {sessions.map((s) => (
            <div
              key={s.id}
              onClick={() => setCurrentSessionId(s.id)}
              className={`p-2 mb-1 rounded cursor-pointer text-sm ${
                s.id === currentSessionId
                  ? "bg-blue-100 text-blue-900"
                  : "hover:bg-gray-100"
              }`}
            >
              <div className="font-medium truncate">{s.title}</div>
              <div className="text-xs text-gray-500">
                {new Date(s.updatedAt).toLocaleString("zh-CN")}
              </div>
            </div>
          ))}
        </div>
      </aside>

      {/* 右侧对话区 */}
      <main className="flex-1 flex flex-col">
        {currentSessionId ? (
          <div className="flex-1 flex items-center justify-center text-gray-400">
            {/* 消息区 - 后续 Task 实现 */}
            <p>请输入问题开始对话</p>
          </div>
        ) : (
          <div className="flex-1 flex items-center justify-center text-gray-400">
            <p>请选择会话或创建新会话</p>
          </div>
        )}
      </main>
    </div>
  );
}
