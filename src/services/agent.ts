// ⚠️ Plan 修订: Tauri 2.x 应使用 @tauri-apps/api/core（不是 /tauri）
// 与现有 src/services/api.ts 保持一致
import { invoke } from "@tauri-apps/api/core";
import { listen, UnlistenFn } from "@tauri-apps/api/event";

export interface ToolCall {
  name: string;
  args: Record<string, any>;
  status: "running" | "success" | "error";
  resultPreview?: string;
  durationMs?: number;
}

export interface AgentSession {
  id: string;
  title: string;
  createdAt: string;
  updatedAt: string;
  messageCount: number;
  isPinned: boolean;
  lastMessage?: string;
}

export interface AgentMessage {
  id: number;
  sessionId: string;
  role: "user" | "assistant" | "tool";
  content: string;
  toolCalls?: ToolCall[];
  createdAt: string;
  tokenCount?: number;
  durationMs?: number;
}

export interface StreamEvent {
  event: "thinking" | "tool_call" | "tool_result" | "final_answer" | "done" | "error";
  data: any;
}

export interface AgentCallbacks {
  onThinking?: (step: number, content: string) => void;
  onToolCall?: (tc: ToolCall) => void;
  onToolResult?: (name: string, status: string, preview: string, durationMs: number) => void;
  onFinalAnswer?: (content: string) => void;
  onError?: (error: string) => void;
  onDone?: (messageId: number) => void;
}

export async function sendMessage(
  sessionId: string,
  text: string,
  callbacks: AgentCallbacks
): Promise<UnlistenFn[]> {
  // 监听事件
  const eventName = `agent_stream_${sessionId}`;
  const unlisteners: UnlistenFn[] = [];

  const unlisten1 = await listen<{ event: string; data: any }>(eventName, (e) => {
    const { event, data } = e.payload;
    switch (event) {
      case "thinking":
        callbacks.onThinking?.(data.step, data.content);
        break;
      case "tool_call":
        callbacks.onToolCall?.({
          name: data.name,
          args: data.args || {},
          status: "running"
        });
        break;
      case "tool_result":
        callbacks.onToolResult?.(data.name, data.status, data.result_preview || "", data.duration_ms || 0);
        break;
      case "final_answer":
        callbacks.onFinalAnswer?.(data.content);
        break;
      case "error":
        callbacks.onError?.(data.content);
        break;
    }
  });
  unlisteners.push(unlisten1);

  const unlisten2 = await listen<{ session_id: string; message_id: number }>(
    "agent_stream_done",
    (e) => {
      if (e.payload.session_id === sessionId) {
        callbacks.onDone?.(e.payload.message_id);
      }
    }
  );
  unlisteners.push(unlisten2);

  const unlisten3 = await listen<{ error: string }>("agent_stream_error", (e) => {
    callbacks.onError?.(e.payload.error);
  });
  unlisteners.push(unlisten3);

  // 触发 send
  await invoke("agent_send_message", { sessionId, text });

  // 返回 unlistener（调用方负责清理）
  return unlisteners;
}
