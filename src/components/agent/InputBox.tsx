import { useState } from "react";

interface Props {
  onSend: (text: string) => void;
  disabled?: boolean;
}

const EXAMPLES = [
  "688256 现在能买吗？",
  "我的持仓怎么样？",
  "推荐 5 只长期价值股",
  "半导体行业前景如何？",
  "今天大盘情绪怎样？",
  "寒武纪 300750 是什么股票？",
];

export default function InputBox({ onSend, disabled }: Props) {
  const [text, setText] = useState("");
  const [showExamples, setShowExamples] = useState(false);

  function handleSend() {
    if (!text.trim() || disabled) return;
    onSend(text.trim());
    setText("");
  }

  return (
    <div style={{
      borderTop: "1px solid var(--border)",
      background: "var(--card)",
      padding: "12px 20px 16px",
      boxShadow: "0 -1px 6px rgba(0,0,0,0.03)",
    }}>
      {showExamples && (
        <div style={{
          marginBottom: 10,
          display: "flex", flexWrap: "wrap", gap: 4,
          animation: "slideUp 0.2s ease",
        }}>
          {EXAMPLES.map((ex) => (
            <button
              key={ex}
              onClick={() => { setText(ex); setShowExamples(false); }}
              style={{
                fontSize: 11, padding: "5px 10px", borderRadius: 14,
                background: "#eff6ff", color: "#1d4ed8",
                border: "1px solid #bfdbfe", cursor: "pointer",
                transition: "all 0.15s ease",
              }}
            >
              {ex}
            </button>
          ))}
        </div>
      )}
      <div style={{ display: "flex", gap: 8, alignItems: "flex-end" }}>
        <div style={{ flex: 1, position: "relative" }}>
          <textarea
            value={text}
            onChange={(e) => setText(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); handleSend(); }
            }}
            placeholder="输入股票代码或问题... (Enter 发送)"
            disabled={disabled}
            style={{
              width: "100%", padding: "10px 14px",
              border: "1px solid #d1d5db", borderRadius: 10,
              resize: "none", fontSize: 13, lineHeight: 1.5,
              fontFamily: "inherit",
              outline: "none",
              transition: "border-color 0.15s ease",
            }}
            rows={2}
            onFocus={(e) => e.target.style.borderColor = "var(--primary)"}
            onBlur={(e) => e.target.style.borderColor = "#d1d5db"}
          />
          <button
            onClick={() => setShowExamples(!showExamples)}
            style={{
              position: "absolute", bottom: 8, left: 8,
              fontSize: 11, padding: "2px 8px", borderRadius: 10,
              background: "transparent", border: "none",
              cursor: "pointer", color: "var(--text-tertiary)",
            }}
          >
            💡
          </button>
        </div>
        <button
          onClick={handleSend}
          disabled={disabled || !text.trim()}
          style={{
            padding: "10px 20px",
            background: disabled || !text.trim() ? "#93c5fd" : "linear-gradient(135deg, var(--primary), var(--primary-dark))",
            color: "#fff",
            border: "none", borderRadius: 10,
            cursor: disabled || !text.trim() ? "not-allowed" : "pointer",
            fontSize: 13, fontWeight: 500,
            boxShadow: disabled || !text.trim() ? "none" : "0 1px 4px rgba(59,130,246,0.3)",
            transition: "all 0.15s ease",
            whiteSpace: "nowrap",
          }}
        >
          发送
        </button>
      </div>
    </div>
  );
}
