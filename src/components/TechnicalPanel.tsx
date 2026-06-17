import type { TechnicalIndicators } from "../types";
import { runLlmAnalysis } from "../services/api";

export default function TechnicalPanel({ indicators, code, name }: { indicators: TechnicalIndicators; code: string; name: string }) {
  return (
    <div style={{ padding: "12px 16px" }}>
      <div style={{ display: "flex", gap: 8, marginBottom: 12, flexWrap: "wrap" }}>
        <span style={{ fontSize: 12, color: "var(--text-secondary)" }}>📈 EMA: <b>{indicators.ema20}</b> / {indicators.ema60} / {indicators.ema120}</span>
        <span style={{ fontSize: 12, color: "var(--text-secondary)" }}>📊 MACD: DIF <b>{indicators.macd.DIF}</b> DEA {indicators.macd.DEA} {indicators.macd.golden_cross ? "✅金叉" : ""}</span>
        <span style={{ fontSize: 12, color: indicators.kdj.overbought ? "var(--down)" : "var(--text-secondary)" }}>🎲 KDJ: K{indicators.kdj.K} D{indicators.kdj.D} J{indicators.kdj.J}{indicators.kdj.overbought ? " ⚠️超买" : ""}</span>
        <span style={{ fontSize: 12, color: indicators.rsi.overbought ? "var(--down)" : "var(--text-secondary)" }}>📉 RSI(14): {indicators.rsi.RSI}</span>
        <span style={{ fontSize: 12, color: indicators.boll.overbought ? "var(--warn)" : "var(--text-secondary)" }}>📦 BOLL: {indicators.boll.upper}/{indicators.boll.mid}/{indicators.boll.lower}</span>
      </div>
      <button onClick={() => runLlmAnalysis(`stock:${code}`)} style={{ padding: "6px 12px", background: "var(--primary)", color: "#fff", border: "none", borderRadius: 6, cursor: "pointer", fontSize: 12 }}>
        💬 问 AI: {name} 分析
      </button>
    </div>
  );
}