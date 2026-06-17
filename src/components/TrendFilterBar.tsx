import type { TechnicalIndicators } from "../types";

export default function TrendFilterBar({ indicators }: { indicators: TechnicalIndicators }) {
  const steps = [
    { label: "① 定方向", status: indicators.multi_head ? "多头" : "震荡", ok: indicators.multi_head, color: indicators.multi_head ? "var(--up)" : "var(--warn)" },
    { label: "② 看阶段", status: indicators.macd.above_zero ? "健康" : "需关注", ok: indicators.macd.above_zero, color: indicators.macd.above_zero ? "var(--up)" : "var(--warn)" },
    { label: "③ 评估能量", status: "中等", ok: true, color: "var(--warn)" },
    { label: "④ 确认级别", status: indicators.macd.above_zero ? "同级别趋势" : "小级别反弹", ok: indicators.macd.above_zero, color: indicators.macd.above_zero ? "var(--up)" : "var(--down)" },
  ];

  return (
    <div style={{ display: "flex", gap: 8, padding: "12px 16px", background: "#f8f9fa" }}>
      {steps.map((s) => (
        <div key={s.label} style={{ flex: 1, padding: 8, borderRadius: 8, textAlign: "center", background: s.ok ? "#f0fdf4" : "#fff3cd", border: `1px solid ${s.color}` }}>
          <div style={{ fontSize: 11, color: "var(--text-secondary)" }}>{s.label}</div>
          <div style={{ fontWeight: 600, fontSize: 13, color: s.color }}>{s.status}</div>
        </div>
      ))}
    </div>
  );
}