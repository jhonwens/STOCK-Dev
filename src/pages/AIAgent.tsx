import { useState, useEffect, useRef } from "react";
import { invoke } from "@tauri-apps/api/core";
import { UnlistenFn } from "@tauri-apps/api/event";
import { sendMessage, ToolCall as TCToolCall } from "../services/agent";
import SessionList, { AgentSession } from "../components/agent/SessionList";
import MessageList, { Message } from "../components/agent/MessageList";
import InputBox from "../components/agent/InputBox";
import ErrorBoundary from "../components/agent/ErrorBoundary";

export default function AIAgent() {
  const [sessions, setSessions] = useState<AgentSession[]>([]);
  const [currentSessionId, setCurrentSessionId] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [loading, setLoading] = useState(false);
  const [streamingContent, setStreamingContent] = useState("");
  const [activeToolCalls, setActiveToolCalls] = useState<TCToolCall[]>([]);
  const unlistenersRef = useRef<UnlistenFn[]>([]);
  const finalAnswerRef = useRef("");
  const newSessionTitleRef = useRef<string | null>(null);
  useEffect(() => { loadSessions(); }, []);

  useEffect(() => {
    if (currentSessionId) {
      loadMessages(currentSessionId);
    } else {
      setMessages([]);
    }
  }, [currentSessionId]);

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
      const list = await invoke<any[]>("agent_get_messages", { sessionId });
      const mapped: Message[] = list.map((m) => ({
        id: m.id,
        sessionId: m.session_id,
        role: m.role as Message["role"],
        content: m.content || "",
        toolCalls: m.tool_calls,
        createdAt: m.created_at,
      }));
      setMessages(mapped);
    } catch (e) {
      console.error("Load messages failed:", e);
    }
  }

  async function handleNewSession() {
    try {
      setLoading(true);
      const now = new Date();
      const ts = `${now.getMonth()+1}-${String(now.getDate()).padStart(2,"0")} ${String(now.getHours()).padStart(2,"0")}:${String(now.getMinutes()).padStart(2,"0")}`;
      const title = `新会话 ${ts}`;
      const session = await invoke<AgentSession>("agent_create_session", { title });
      newSessionTitleRef.current = title;
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

    // 新会话首次发送时立即以消息内容重命名
    if (newSessionTitleRef.current) {
      const title = text.length > 30 ? text.slice(0, 30) + "…" : text;
      try {
        await invoke("agent_rename_session", { id: currentSessionId, title });
        setSessions((prev) => prev.map((s) => s.id === currentSessionId ? { ...s, title } : s));
      } catch (e) {
        console.error("Rename session failed:", e);
      }
      newSessionTitleRef.current = null;
    }

    const tempUserMsg: Message = {
      id: -Date.now(),
      sessionId: currentSessionId,
      role: "user",
      content: text,
      createdAt: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, tempUserMsg]);

    unlistenersRef.current.forEach((fn) => fn());
    unlistenersRef.current = [];

    let hasError = false;
    const sessionIdSnapshot = currentSessionId;

    try {
      const unlisteners = await sendMessage(currentSessionId, text, {
        onThinking: (step, content) => {
          setStreamingContent(`🧠 ${content}\n\n`);
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
          finalAnswerRef.current = content;
          setStreamingContent(content);
          // 同时写入临时消息，即使 DB 保存失败用户也能看到
          setMessages((prev) => {
            const exists = prev.some((m) => m.role === "assistant" && m.content === content);
            if (exists) return prev;
            return [...prev, {
              id: Date.now(),
              sessionId: sessionIdSnapshot!,
              role: "assistant",
              content,
              createdAt: new Date().toISOString(),
            }];
          });
        },
        onError: (error) => {
          hasError = true;
          if (error.includes("timeout") || error.includes("超时")) {
            setStreamingContent("⏱️ LLM 响应超时，请稍后重试");
          } else if (error.includes("API key") || error.includes("401") || error.includes("auth")) {
            setStreamingContent("🔑 API Key 无效，请到设置页检查 LLM 配置");
          } else {
            setStreamingContent(`❌ Agent 错误: ${error}`);
          }
        },
        onDone: async (messageId) => {
          unlistenersRef.current.forEach((fn) => fn());
          unlistenersRef.current = [];
          if (!hasError) {
            await loadMessages(sessionIdSnapshot!);
            // 检查 DB 是否包含答案（messageId > 0 说明 assitant_saved 被 Rust 收到）
            if (!messageId || messageId <= 0) {
              // DB 没有保存成功，从 ref 恢复
              const fallback = finalAnswerRef.current;
              if (fallback) {
                setMessages((prev) => {
                  const exists = prev.some((m) => m.role === "assistant" && m.content === fallback);
                  if (exists) return prev;
                  return [...prev, {
                    id: Date.now() + 1,
                    sessionId: sessionIdSnapshot!,
                    role: "assistant",
                    content: fallback,
                    createdAt: new Date().toISOString(),
                  }];
                });
              }
            }
            setStreamingContent("");
          }
          setActiveToolCalls([]);
          setLoading(false);
          if (!hasError) {
            await loadSessions();
          }
        },
      });
      unlistenersRef.current = unlisteners;
    } catch (e) {
      console.error("Send failed:", e);
      setStreamingContent(`❌ 发送失败: ${e}`);
      setLoading(false);
    }
  }

  // test export with actual command (MD/HTML buttons also call this)
  const currentSession = sessions.find((s) => s.id === currentSessionId);

  return (
    <ErrorBoundary>
    <div style={{ display: "flex", height: "100%", background: "var(--bg)" }}>
      <SessionList
        sessions={sessions}
        currentId={currentSessionId}
        onSelect={setCurrentSessionId}
        onRefresh={loadSessions}
        onCreate={handleNewSession}
      />

      <main style={{ flex: 1, display: "flex", flexDirection: "column", minWidth: 0 }}>
        {currentSessionId ? (
          <>
            <div style={{
              padding: "14px 20px",
              borderBottom: "1px solid var(--border)",
              background: "var(--card)",
              display: "flex", alignItems: "center", gap: 10,
              flexShrink: 0,
            }}>
              <span style={{ fontSize: 18 }}>🤖</span>
              <div>
                <div style={{ fontSize: 14, fontWeight: 600 }}>{currentSession?.title || "智能分析"}</div>
                <div style={{ fontSize: 11, color: "var(--text-tertiary)" }}>
                  {currentSession ? `${currentSession.message_count || 0} 条消息` : ""}
                </div>
              </div>
              <div style={{ marginLeft: "auto", fontSize: 11, color: "var(--text-tertiary)" }}>
                {loading && <span style={{ display: "flex", alignItems: "center", gap: 6 }}>
                  <span className="typing-dot" />
                  <span className="typing-dot" />
                  <span className="typing-dot" />
                </span>}
              </div>
            </div>

             <MessageList
               messages={messages}
               streamingContent={streamingContent}
               activeToolCalls={activeToolCalls}
             />
             <InputBox onSend={handleSend} disabled={loading} />
          </>
        ) : (
          <div style={{ flex: 1, display: "flex", alignItems: "center", justifyContent: "center" }}>
            <div style={{ textAlign: "center" }}>
              <div style={{ fontSize: 48, marginBottom: 16 }}>🤖</div>
              <h2 style={{ fontSize: 18, fontWeight: 600, color: "var(--text)", marginBottom: 8 }}>智能分析</h2>
              <p style={{ fontSize: 13, color: "var(--text-secondary)", maxWidth: 360, lineHeight: 1.6 }}>
                选择左侧会话开始分析，或创建新会话输入股票代码、市场趋势等问题
              </p>

            </div>
          </div>
        )}
      </main>
    </div>
    </ErrorBoundary>
  );
}
