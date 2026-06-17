import type { CandidateStock } from "../../types";

interface Props {
  stock: CandidateStock;
  onClose: () => void;
}

const DIMENSION_LABELS: Record<string, string> = {
  "基本面": "🏢 基本面分析",
  "财务经营": "💰 财务经营分析",
  "行业趋势": "📈 行业价值趋势",
  "热点信息": "🔥 热点信息影响",
  "建议买入价格": "🎯 建议买入价格分布",
  "技术面": "📊 技术面综合评分",
  "估值对比": "💹 估值对比分析",
  "资金流向": "💧 资金流向分析",
  "机构持仓": "🏛️ 机构持仓变动",
  "风险指标": "⚠️ 风险指标",
  "同业对比": "🤝 同业竞争力对比",
  "催化事件": "📅 催化事件日历",
};

export default function RecommendDetailDrawer({ stock, onClose }: Props) {
  const dims = stock.analysis_12dim || {};
  const entries = Object.entries(DIMENSION_LABELS);

  return (
    <div
      onClick={onClose}
      style={{
        position: "fixed", inset: 0, zIndex: 1000,
        background: "rgba(0,0,0,0.4)",
        display: "flex", alignItems: "center", justifyContent: "center",
        padding: 20,
      }}
    >
      <div
        onClick={(e) => e.stopPropagation()}
        style={{
          background: "#fff", borderRadius: 16, maxWidth: 640, width: "100%",
          maxHeight: "85vh", overflow: "auto",
          boxShadow: "0 20px 60px rgba(0,0,0,0.15)",
        }}
      >
        <div style={{
          position: "sticky", top: 0, background: "#fff", zIndex: 1,
          padding: "20px 24px 12px",
          borderBottom: "1px solid var(--border)",
          display: "flex", justifyContent: "space-between", alignItems: "flex-start",
        }}>
          <div>
            <div style={{ fontSize: 18, fontWeight: 700 }}>
              {stock.name}
              <span style={{ fontSize: 13, color: "#888", fontWeight: 400, marginLeft: 8 }}>
                {stock.code}
              </span>
            </div>
            <div style={{ fontSize: 13, color: "#666", marginTop: 4 }}>
              ⭐ {stock.overall_score}/100 · {stock.holding_period}
            </div>
          </div>
          <button
            onClick={onClose}
            style={{
              background: "none", border: "none", fontSize: 22, cursor: "pointer",
              color: "#888", padding: "0 4px", lineHeight: 1,
            }}
          >
            ×
          </button>
        </div>

        <div style={{ padding: "16px 24px 24px" }}>
          <div style={{
            padding: "12px 16px", background: "#f0f7ff", borderRadius: 10,
            marginBottom: 16, fontSize: 13, lineHeight: 1.6, color: "#1a4d8f",
          }}>
            <strong>推荐理由：</strong>{stock.recommend_reason}
          </div>

          <div style={{
            display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10,
            marginBottom: 16, fontSize: 12,
          }}>
            <div style={{ padding: "8px 12px", background: "#f8f9fa", borderRadius: 8 }}>
              <span style={{ color: "#888" }}>建议买入区间</span>
              <div style={{ fontWeight: 600, color: "#16a34a", marginTop: 2 }}>
                {stock.suggested_price_range[0].toFixed(2)} — {stock.suggested_price_range[1].toFixed(2)}
              </div>
            </div>
            <div style={{ padding: "8px 12px", background: "#fef2f2", borderRadius: 8 }}>
              <span style={{ color: "#888" }}>风险提示</span>
              <div style={{ fontWeight: 500, color: "#dc2626", marginTop: 2, fontSize: 12 }}>
                {stock.risk_warning}
              </div>
            </div>
          </div>

          {entries.map(([key, label]) => {
            const val = dims[key];
            if (!val || val === "...") return null;
            return (
              <div key={key} style={{ marginBottom: 14 }}>
                <div style={{
                  fontSize: 14, fontWeight: 600, marginBottom: 6,
                  paddingBottom: 4, borderBottom: "1px solid #eee",
                }}>
                  {label}
                </div>
                <div style={{ fontSize: 13, color: "#444", lineHeight: 1.7, whiteSpace: "pre-wrap" }}>
                  {val}
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}