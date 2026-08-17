export interface ToolCall {
  name: string;
  args: Record<string, any>;
  status: "running" | "success" | "error";
  resultPreview?: string;
  durationMs?: number;
}

interface Props {
  toolCall: ToolCall;
}

export default function ToolCallCard({ toolCall }: Props) {
  const tc = toolCall;
  return (
    <div style={{
      background: "#f8f6ff", border: "1px solid #e4dcf5",
      borderRadius: 8, padding: "8px 12px", marginBottom: 6,
      fontSize: 13, animation: "slideUp 0.2s ease",
    }}>
      <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
        <span style={{ fontSize: 14 }}>🔧</span>
        <span style={{ fontFamily: "ui-monospace, monospace", fontWeight: 500, fontSize: 12 }}>{tc.name}</span>
        <span style={{ color: "var(--text-tertiary)", fontSize: 11 }}>{JSON.stringify(tc.args)}</span>
        <span style={{ marginLeft: "auto", display: "flex", alignItems: "center", gap: 4 }}>
          {tc.status === "running" && (
            <span style={{ display: "flex", alignItems: "center", gap: 3 }}>
              <span className="typing-dot" style={{ width: 4, height: 4 }} />
              <span className="typing-dot" style={{ width: 4, height: 4 }} />
              <span className="typing-dot" style={{ width: 4, height: 4 }} />
            </span>
          )}
          {tc.status === "success" && <span style={{ color: "#16a34a", fontSize: 12 }}>✓ 完成</span>}
          {tc.status === "error" && <span style={{ color: "#dc2626", fontSize: 12 }}>✗ 失败</span>}
          {tc.durationMs && <span style={{ fontSize: 10, color: "var(--text-tertiary)" }}>{tc.durationMs}ms</span>}
        </span>
      </div>
      {tc.resultPreview && (
        <pre style={{
          marginTop: 6, fontSize: 11, color: "var(--text-secondary)",
          whiteSpace: "pre-wrap", maxHeight: 100, overflowY: "auto",
          lineHeight: 1.5, fontFamily: "inherit",
          background: "rgba(0,0,0,0.02)",
          padding: 6, borderRadius: 4,
        }}>
          {tc.resultPreview}
        </pre>
      )}
    </div>
  );
}
