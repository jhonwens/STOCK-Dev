import { useState, useRef, useEffect } from "react";
import { runLlmAnalysis } from "../services/api";

interface Message {
  role: "user" | "assistant";
  content: string;
}

const quickQuestions = [
  "今天有什么操作建议？",
  "持仓中风险最高的股票是？",
  "推荐一只候选股",
  "市场整体风险如何？",
];

export default function LLMChat() {
  const [open, setOpen] = useState(false);
  const [messages, setMessages] = useState<Message[]>([{
    role: "assistant",
    content: "你好！我是你的 AI 股票分析师。我可以帮你分析持仓、候选股，回答关于市场的问题。有什么需要了解的？",
  }]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const sendMessage = async (text: string) => {
    if (!text.trim() || loading) return;
    setMessages((prev) => [...prev, { role: "user", content: text }]);
    setInput("");
    setLoading(true);
    try {
      const result = await runLlmAnalysis("chat");
      setMessages((prev) => [...prev, { role: "assistant", content: result }]);
    } catch {
      setMessages((prev) => [...prev, { role: "assistant", content: "抱歉，分析引擎暂时不可用，请检查 LLM 配置。" }]);
    }
    setLoading(false);
  };

  return (
    <>
      <button
        onClick={() => setOpen(!open)}
        style={{
          position: "fixed", bottom: 24, right: 24, zIndex: 1000,
          width: 56, height: 56, borderRadius: "50%", border: "none",
          background: "var(--primary)", color: "#fff", fontSize: 24,
          cursor: "pointer", boxShadow: "0 4px 12px rgba(26,115,232,0.4)",
        }}
      >
        💬
      </button>

      {open && (
        <div style={{
          position: "fixed", bottom: 88, right: 24, zIndex: 999,
          width: 400, height: 520, background: "#fff", borderRadius: 12,
          boxShadow: "0 8px 32px rgba(0,0,0,0.15)", display: "flex",
          flexDirection: "column", overflow: "hidden",
        }}>
          <div style={{ padding: "12px 16px", borderBottom: "1px solid var(--border)", fontWeight: 600, fontSize: 14 }}>
            🤖 AI 分析师
          </div>

          <div style={{ flex: 1, overflow: "auto", padding: 12, background: "#fafafa" }}>
            {messages.map((m, i) => (
              <div key={i} style={{ display: "flex", gap: 8, marginBottom: 12, flexDirection: m.role === "user" ? "row-reverse" : "row" }}>
                <div style={{ width: 28, height: 28, borderRadius: "50%", background: m.role === "user" ? "var(--up)" : "var(--primary)", color: "#fff", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 12, flexShrink: 0 }}>
                  {m.role === "user" ? "👤" : "🤖"}
                </div>
                <div style={{ maxWidth: "80%", background: m.role === "user" ? "var(--primary)" : "#fff", color: m.role === "user" ? "#fff" : "var(--text)", padding: "8px 12px", borderRadius: 12, fontSize: 13, lineHeight: 1.5, whiteSpace: "pre-wrap" }}>
                  {m.content}
                </div>
              </div>
            ))}
            {loading && <div style={{ textAlign: "center", color: "var(--text-secondary)", fontSize: 13 }}>AI 正在分析...</div>}
            <div ref={endRef} />
          </div>

          <div style={{ padding: "8px 12px", borderTop: "1px solid var(--border)", display: "flex", gap: 6, flexWrap: "wrap" }}>
            {quickQuestions.map((q) => (
              <button key={q} onClick={() => sendMessage(q)} style={{
                padding: "4px 10px", background: "#f0f0f0", border: "none",
                borderRadius: 12, fontSize: 11, color: "var(--text-secondary)", cursor: "pointer",
              }}>
                {q}
              </button>
            ))}
          </div>

          <div style={{ padding: "8px 12px", borderTop: "1px solid var(--border)", display: "flex", gap: 8 }}>
            <input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && sendMessage(input)}
              placeholder="输入你对股票的问题..."
              style={{ flex: 1, padding: "8px 12px", border: "1px solid var(--border)", borderRadius: 8, fontSize: 13, outline: "none" }}
            />
            <button onClick={() => sendMessage(input)} style={{ padding: "8px 16px", background: "var(--primary)", color: "#fff", border: "none", borderRadius: 8, cursor: "pointer", fontSize: 13 }}>
              发送
            </button>
          </div>
        </div>
      )}
    </>
  );
}