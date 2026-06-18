import { useState, useEffect } from "react";
// ⚠️ Plan 修订: Tauri 2.x 应使用 @tauri-apps/api/core（不是 /tauri）
// 与现有 src/services/api.ts 保持一致
import { invoke } from "@tauri-apps/api/core";
import SessionList, { AgentSession } from "../components/agent/SessionList";

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
      <SessionList
        sessions={sessions}
        currentId={currentSessionId}
        onSelect={setCurrentSessionId}
        onRefresh={loadSessions}
        onCreate={handleNewSession}
      />

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
