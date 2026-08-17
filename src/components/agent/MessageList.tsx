import { useEffect, useRef } from "react";
import MessageItem, { Message, ToolCall } from "./MessageItem";
import ToolCallCard from "./ToolCallCard";

export type { Message };

interface Props {
  messages: Message[];
  streamingContent?: string;
  activeToolCalls?: ToolCall[];
}

export default function MessageList({ messages, streamingContent, activeToolCalls }: Props) {
  const bottomRef = useRef<HTMLDivElement>(null);
  const MAX_VISIBLE = 100;
  const TRIM_TO = 50;
  const showTrimNotice = messages.length > MAX_VISIBLE;
  const visibleMessages = showTrimNotice ? messages.slice(-TRIM_TO) : messages;

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, streamingContent, activeToolCalls]);

  return (
    <div style={{ flex: 1, overflowY: "auto", padding: "20px 24px", background: "var(--chat-bg)" }}>
      {showTrimNotice && (
        <div style={{ textAlign: "center", fontSize: 11, color: "var(--text-tertiary)", marginBottom: 12, padding: "6px 12px", background: "var(--card)", borderRadius: 6, border: "1px solid var(--border)" }}>
          消息较多，仅显示最近 {TRIM_TO} 条（共 {messages.length} 条）
        </div>
      )}

      <div style={{ maxWidth: 800, margin: "0 auto" }}>
        {visibleMessages.map((m) => (
          <div key={m.id} className="message-enter">
            <MessageItem message={m} />
          </div>
        ))}

        {activeToolCalls && activeToolCalls.length > 0 && (
          <div style={{ marginBottom: 12 }}>
            {activeToolCalls.map((tc, i) => (
              <ToolCallCard key={i} toolCall={tc} />
            ))}
          </div>
        )}

        {streamingContent && (
          <div className="message-enter" style={{ display: "flex", justifyContent: "flex-start" }}>
            <div style={{
              maxWidth: "85%",
              background: "var(--card)",
              borderRadius: 12,
              padding: 16,
              boxShadow: "0 1px 3px rgba(0,0,0,0.04)",
            }}>
              <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 10, fontSize: 13, color: "var(--text-secondary)" }}>
                <span style={{
                  width: 24, height: 24, borderRadius: 6,
                  background: "linear-gradient(135deg, #8b5cf6, #6366f1)",
                  display: "flex", alignItems: "center", justifyContent: "center",
                  fontSize: 12, color: "#fff",
                }}>AI</span>
                <span style={{ fontWeight: 500, color: "var(--text)" }}>智能分析</span>
              </div>
              <div style={{ fontSize: 14, lineHeight: 1.7, whiteSpace: "pre-wrap", color: "var(--text)" }}>
                {streamingContent}
                <span style={{ display: "inline-flex", alignItems: "center", gap: 3, marginLeft: 4 }}>
                  <span className="typing-dot" />
                  <span className="typing-dot" />
                  <span className="typing-dot" />
                </span>
              </div>
            </div>
          </div>
        )}
      </div>

      <div ref={bottomRef} />
    </div>
  );
}
