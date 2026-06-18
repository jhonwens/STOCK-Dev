import { useState, useEffect, useRef } from "react";
// ⚠️ Plan 修订: Tauri 2.x 应使用 @tauri-apps/api/core（不是 /tauri）
// 与现有 src/services/api.ts 保持一致
import { invoke } from "@tauri-apps/api/core";
import { UnlistenFn } from "@tauri-apps/api/event";
import { sendMessage, AgentMessage, ToolCall as TCToolCall } from "../services/agent";
import SessionList, { AgentSession } from "../components/agent/SessionList";
import MessageList, { Message } from "../components/agent/MessageList";
import InputBox from "../components/agent/InputBox";

export default function AIAgent() {
  const [sessions, setSessions] = useState<AgentSession[]>([]);
  const [currentSessionId, setCurrentSessionId] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [loading, setLoading] = useState(false);
  const [streamingContent, setStreamingContent] = useState("");
  const [activeToolCalls, setActiveToolCalls] = useState<TCToolCall[]>([]);
  const unlistenersRef = useRef<UnlistenFn[]>([]);

  useEffect(() => {
    loadSessions();
  }, []);

  useEffect(() => {
    if (currentSessionId) {
      loadMessages(currentSessionId);
    } else {
      setMessages([]);
    }
  }, [currentSessionId]);

  // 切会话/卸载时清理监听器，避免泄漏与重复触发
  useEffect(() => {
    return () => {
      unlistenersRef.current.forEach((fn) => fn());
      unlistenersRef.current = [];
    };
  }, [currentSessionId]);

  async function loadSessions() {
    try {
      const list = await invoke<AgentSession[]>("agent_list_sessions");
      setSessions(list);
    } catch (e) {
      console.error("Load sessions failed:", e);
    }
  }

  async function loadMessages(sessionId: string) {
    try {
      const list = await invoke<AgentMessage[]>("agent_get_messages", { sessionId });
      const mapped: Message[] = list.map((m) => ({
        id: m.id,
        sessionId: m.sessionId,
        role: m.role as Message["role"],
        content: m.content || "",
        toolCalls: m.toolCalls,
        createdAt: m.createdAt,
      }));
      setMessages(mapped);
    } catch (e) {
      console.error("Load messages failed:", e);
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

  async function handleSend(text: string) {
    if (!currentSessionId) {
      alert("请先选择或创建会话");
      return;
    }

    setStreamingContent("");
    setActiveToolCalls([]);
    setLoading(true);

    // 立即在 UI 中显示用户消息
    const tempUserMsg: Message = {
      id: -Date.now(),
      sessionId: currentSessionId,
      role: "user",
      content: text,
      createdAt: new Date().toISOString(),
    };
    setMessages([...messages, tempUserMsg]);

    // 清理上一轮 listener，避免重复触发
    unlistenersRef.current.forEach((fn) => fn());
    unlistenersRef.current = [];

    try {
      const unlisteners = await sendMessage(currentSessionId, text, {
        onThinking: (step, content) => {
          console.log(`Step ${step}: ${content}`);
        },
        onToolCall: (tc) => {
          setActiveToolCalls((prev) => [...prev, tc]);
        },
        onToolResult: (name, status, preview, durationMs) => {
          setActiveToolCalls((prev) =>
            prev.map((tc) =>
              tc.name === name && tc.status === "running"
                ? { ...tc, status: status as any, resultPreview: preview, durationMs }
                : tc
            )
          );
        },
        onFinalAnswer: (content) => {
          setStreamingContent(content);
        },
        onError: (error) => {
          alert(`Agent 错误: ${error}`);
        },
        onDone: async (_messageId) => {
          // 完成后清理 listener
          unlistenersRef.current.forEach((fn) => fn());
          unlistenersRef.current = [];
          // 重新加载消息历史
          await loadMessages(currentSessionId);
          setStreamingContent("");
          setActiveToolCalls([]);
          setLoading(false);
          // 同步刷新 session 列表（last_message 变了）
          await loadSessions();
        },
      });
      unlistenersRef.current = unlisteners;
    } catch (e) {
      console.error("Send failed:", e);
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

      <main className="flex-1 flex flex-col">
        {currentSessionId ? (
          <>
            <MessageList
              messages={messages}
              streamingContent={streamingContent}
              activeToolCalls={activeToolCalls}
            />
            <InputBox onSend={handleSend} disabled={loading} />
          </>
        ) : (
          <div className="flex-1 flex items-center justify-center text-gray-400">
            <p>请选择会话或创建新会话</p>
          </div>
        )}
      </main>
    </div>
  );
}
