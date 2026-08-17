import { useState, ReactNode } from "react";
import { invoke } from "@tauri-apps/api/core";
import ToolCallCard, { ToolCall } from "./ToolCallCard";

export type { ToolCall };

export interface Message {
  id: number;
  sessionId: string;
  role: "user" | "assistant" | "tool";
  content: string;
  toolCalls?: ToolCall[];
  createdAt: string;
}

interface Props {
  message: Message;
}

function renderBold(text: string): ReactNode[] {
  const parts = text.split(/(\*\*[^*]+\*\*)/g);
  return parts.map((p, i) => {
    if (p.startsWith("**") && p.endsWith("**")) {
      return <strong key={i}>{p.slice(2, -2)}</strong>;
    }
    return p;
  });
}

function renderInline(line: string): ReactNode {
  return <>{renderBold(line)}</>;
}

function renderMarkdown(content: string): ReactNode {
  const lines = content.split("\n");
  const elements: ReactNode[] = [];
  let inCodeBlock = false;
  let codeLines: string[] = [];
  let codeLang = "";

  function flushCode() {
    if (codeLines.length > 0) {
      elements.push(
        <pre key={`code-${elements.length}`} style={{
          background: "#1e1e2e", color: "#cdd6f4",
          padding: 12, borderRadius: 8, fontSize: 12,
          lineHeight: 1.5, overflowX: "auto",
          fontFamily: "'JetBrains Mono', 'Fira Code', monospace",
          margin: "8px 0",
        }}>
          <code>{codeLines.join("\n")}</code>
        </pre>
      );
      codeLines = [];
    }
  }

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];

    if (line.trimStart().startsWith("```")) {
      if (inCodeBlock) {
        flushCode();
        inCodeBlock = false;
        codeLang = "";
      } else {
        flushCode();
        inCodeBlock = true;
        codeLang = line.trimStart().slice(3).trim();
      }
      continue;
    }

    if (inCodeBlock) {
      codeLines.push(line);
      continue;
    }

    const trimmed = line.trim();

    if (!trimmed) {
      elements.push(<div key={i} style={{ height: 8 }} />);
      continue;
    }

    if (trimmed.startsWith("### ")) {
      elements.push(
        <div key={i} style={{
          fontSize: 15, fontWeight: 700, color: "var(--text)",
          marginTop: 16, marginBottom: 8, paddingBottom: 4,
          borderBottom: "1px solid var(--border)",
        }}>
          {renderInline(trimmed.slice(4))}
        </div>
      );
      continue;
    }

    if (trimmed.startsWith("## ")) {
      elements.push(
        <div key={i} style={{
          fontSize: 17, fontWeight: 700, color: "var(--text)",
          marginTop: 20, marginBottom: 8,
        }}>
          {renderInline(trimmed.slice(3))}
        </div>
      );
      continue;
    }

    if (trimmed.startsWith("- ") || trimmed.startsWith("* ")) {
      elements.push(
        <div key={i} style={{
          display: "flex", gap: 8, paddingLeft: 4,
          marginBottom: 4, fontSize: 14, lineHeight: 1.6,
        }}>
          <span style={{ color: "var(--primary)", flexShrink: 0, marginTop: 2 }}>•</span>
          <span style={{ flex: 1 }}>{renderInline(trimmed.slice(2))}</span>
        </div>
      );
      continue;
    }

    if (/^\d+[.)]\s/.test(trimmed)) {
      const idx = trimmed.search(/\s/);
      elements.push(
        <div key={i} style={{
          display: "flex", gap: 8, paddingLeft: 4,
          marginBottom: 4, fontSize: 14, lineHeight: 1.6,
        }}>
          <span style={{ color: "var(--text-secondary)", flexShrink: 0, minWidth: 20, textAlign: "right" }}>
            {trimmed.slice(0, idx).replace(".", "")}.
          </span>
          <span style={{ flex: 1 }}>{renderInline(trimmed.slice(idx + 1))}</span>
        </div>
      );
      continue;
    }

    if (trimmed.startsWith("|") && trimmed.endsWith("|") && lines[i + 1]?.trim().match(/^[\|\s:-]+$/)) {
      const headerCells = trimmed.split("|").filter(Boolean).map((c) => c.trim());
      const sepLine = lines[i + 1];
      const alignments = sepLine.split("|").filter(Boolean).map((c) => {
        const t = c.trim();
        if (t.startsWith(":") && t.endsWith(":")) return "center";
        if (t.endsWith(":")) return "right";
        return "left";
      });
      const rows: string[][] = [];
      let ri = i + 2;
      while (ri < lines.length && lines[ri].trim().startsWith("|") && lines[ri].trim().endsWith("|")) {
        rows.push(lines[ri].split("|").filter(Boolean).map((c) => c.trim()));
        ri++;
      }
      elements.push(
        <div key={i} style={{ overflowX: "auto", margin: "8px 0" }}>
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
            <thead>
              <tr>
                {headerCells.map((h, ci) => (
                  <th key={ci} style={{
                    textAlign: alignments[ci] || "left",
                    padding: "8px 10px", background: "#f3f4f6",
                    borderBottom: "2px solid var(--border)",
                    fontWeight: 600, color: "var(--text)",
                    whiteSpace: "nowrap",
                  }}>{renderInline(h)}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {rows.map((row, ri2) => (
                <tr key={ri2}>
                  {row.map((cell, ci) => (
                    <td key={ci} style={{
                      textAlign: alignments[ci] || "left",
                      padding: "6px 10px",
                      borderBottom: "1px solid var(--border)",
                      color: "var(--text)",
                    }}>{renderInline(cell)}</td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      );
      i = ri - 1;
      continue;
    }

    if (/^---/.test(trimmed)) {
      elements.push(
        <hr key={i} style={{ border: "none", borderTop: "1px solid var(--border)", margin: "12px 0" }} />
      );
      continue;
    }

    elements.push(
      <div key={i} style={{ fontSize: 14, lineHeight: 1.7, marginBottom: 4 }}>
        {renderInline(trimmed)}
      </div>
    );
  }

  flushCode();
  return elements;
}

export default function MessageItem({ message }: Props) {
  const [saveStatus, setSaveStatus] = useState("");

  async function handleExport(format: "md" | "html") {
    setSaveStatus(`...`);
    try {
      const path = await invoke<string>("export_agent_message", {
        sessionId: message.sessionId,
        messageId: message.id,
        format,
      });
      const name = path.split("/").pop() || path.split("\\").pop() || path;
      setSaveStatus(`✓ ${name}`);
      setTimeout(() => setSaveStatus(""), 5000);
    } catch (e) {
      const msg = String(e);
      if (msg.includes("取消了保存") || msg.includes("cancel")) {
        setSaveStatus("");
      } else {
        console.error("导出失败完整错误:", e);
        setSaveStatus(`✗ ${msg.slice(0, 120)}`);
        setTimeout(() => setSaveStatus(""), 15000);
      }
    }
  }

  if (message.role === "user") {
    return (
      <div style={{ display: "flex", justifyContent: "flex-end", marginBottom: 20 }}>
        <div style={{
          maxWidth: "75%",
          background: "linear-gradient(135deg, #3b82f6, #2563eb)",
          color: "#fff",
          padding: "10px 16px",
          borderRadius: "16px 16px 4px 16px",
          fontSize: 14,
          lineHeight: 1.6,
          boxShadow: "0 1px 4px rgba(59,130,246,0.2)",
          position: "relative",
        }}>
          {message.content}
          <div style={{
            fontSize: 10, color: "rgba(255,255,255,0.5)",
            textAlign: "right", marginTop: 4,
          }}>
            {message.createdAt ? new Date(message.createdAt).toLocaleTimeString("zh-CN", { hour: "2-digit", minute: "2-digit" }) : ""}
          </div>
        </div>
      </div>
    );
  }

  if (message.role === "tool") {
    return (
      <div style={{ marginBottom: 8 }}>
        {message.toolCalls?.map((tc, i) => (
          <ToolCallCard key={i} toolCall={tc} />
        ))}
      </div>
    );
  }

  if (message.role === "assistant" && message.id > 0) {
    return (
      <div style={{ display: "flex", justifyContent: "flex-start", marginBottom: 20 }}>
        <div style={{ display: "flex", gap: 10, maxWidth: "85%" }}>
          <div style={{
            width: 28, height: 28, borderRadius: 8, flexShrink: 0,
            background: "linear-gradient(135deg, #8b5cf6, #6366f1)",
            display: "flex", alignItems: "center", justifyContent: "center",
            fontSize: 12, color: "#fff", fontWeight: 700,
            marginTop: 2,
          }}>
            AI
          </div>
          <div style={{
            flex: 1,
            background: "var(--card)",
            borderRadius: 12,
            padding: 14,
            boxShadow: "0 1px 3px rgba(0,0,0,0.04)",
          }}>
            <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 10, fontSize: 13 }}>
              <span style={{ fontWeight: 600, color: "var(--text)" }}>智能分析</span>
              <span style={{ fontSize: 11, color: "var(--text-tertiary)" }}>
                {message.createdAt ? new Date(message.createdAt).toLocaleTimeString("zh-CN", { hour: "2-digit", minute: "2-digit" }) : ""}
              </span>
              <div style={{ marginLeft: "auto", display: "flex", gap: 4, alignItems: "center" }}>
                {saveStatus && (
                  <span style={{ fontSize: 10, color: saveStatus.startsWith("✓") ? "#16a34a" : "#dc2626", marginRight: 4 }}
                    title="已在 Finder 中打开导出目录">
                    {saveStatus}
                  </span>
                )}
                <button
                  onClick={() => handleExport("md")}
                  style={{ fontSize: 10, padding: "2px 6px", borderRadius: 4, background: "#f3f4f6", border: "1px solid #e5e7eb", cursor: "pointer", color: "var(--text-secondary)" }}
                  title="导出 Markdown"
                >
                  MD
                </button>
                <button
                  onClick={() => handleExport("html")}
                  style={{ fontSize: 10, padding: "2px 6px", borderRadius: 4, background: "#f3f4f6", border: "1px solid #e5e7eb", cursor: "pointer", color: "var(--text-secondary)" }}
                  title="导出 HTML"
                >
                  HTML
                </button>
              </div>
            </div>
            <div style={{ fontSize: 14, lineHeight: 1.7, color: "var(--text)" }}>
              {renderMarkdown(message.content)}
            </div>
          </div>
        </div>
      </div>
    );
  }

  return null;
}
