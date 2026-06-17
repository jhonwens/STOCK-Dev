import { useState, useCallback, useEffect } from "react";
import { useSearchParams } from "react-router-dom";
import {
  searchStock,
  runStockInsight,
  saveStockInsight,
  loadStockInsight,
  exportStockInsightMd,
} from "../services/api";
import type { StockInsightResult, StockSearchResult, BuyPointLevel } from "../types";

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

function renderBuyPointCard(label: string, color: string, level: BuyPointLevel | undefined) {
  if (!level) return null;
  const stars = level.confidence === "高" ? "⭐⭐⭐" : level.confidence === "中" ? "⭐⭐" : "⭐";
  return (
    <div style={{
      padding: "14px 16px", marginBottom: 10,
      borderLeft: `4px solid ${color}`,
      background: "#fff", borderRadius: 8,
      boxShadow: "0 1px 4px rgba(0,0,0,0.06)",
    }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 6 }}>
        <span style={{ fontWeight: 600, fontSize: 14, color }}>{label}</span>
        <span style={{ fontSize: 12, color: "#888" }}>{stars}</span>
      </div>
      <div style={{ fontSize: 13, color: "#333", marginBottom: 6, lineHeight: 1.5 }}>{level.point}</div>
      <div style={{ fontSize: 12, color: "#16a34a", fontWeight: 500 }}>
        建议区间: {level.price_range[0].toFixed(0)} — {level.price_range[1].toFixed(0)}
      </div>
      {level.detail && level.detail !== "..." && (
        <div style={{ fontSize: 12, color: "#666", marginTop: 6, lineHeight: 1.6 }}>{level.detail}</div>
      )}
    </div>
  );
}

const addButtonStyle: React.CSSProperties = {
  padding: "6px 14px", fontSize: 12, background: "#fff3e0",
  color: "#e65100", border: "1px solid #ffcc80",
  borderRadius: 6, cursor: "pointer", fontWeight: 500,
};
const exportButtonStyle: React.CSSProperties = {
  padding: "6px 14px", fontSize: 12, background: "#e8f5e9",
  color: "#2e7d32", border: "1px solid #a5d6a7",
  borderRadius: 6, cursor: "pointer", fontWeight: 500,
};

export default function StockInsight() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [query, setQuery] = useState("");
  const [searchResults, setSearchResults] = useState<StockSearchResult[]>([]);
  const [searchLoading, setSearchLoading] = useState(false);
  const [searched, setSearched] = useState(false);
  const [selectedCode, setSelectedCode] = useState("");
  const [selectedName, setSelectedName] = useState("");
  const [insight, setInsight] = useState<StockInsightResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [cacheTime, setCacheTime] = useState("");
  const [mdStatus, setMdStatus] = useState("");
  const [addStatus, setAddStatus] = useState("");

  useEffect(() => {
    const code = searchParams.get("code");
    const name = searchParams.get("name");
    if (code && name) {
      setQuery(name);
      setSelectedCode(code);
      setSelectedName(name);
      loadStockInsight(code).then((cached) => {
        if (cached && cached !== "{}") {
          const p = JSON.parse(cached);
          if (p.data && p.updated_at) {
            setInsight(p.data);
            setCacheTime(p.updated_at);
          }
        }
      }).catch(() => {});
    }
  }, []);

  const handleSearch = useCallback(async () => {
    if (!query.trim()) return;
    setSearchLoading(true);
    setSearched(true);
    setSearchResults([]);
    setSelectedCode("");
    setSelectedName("");
    setInsight(null);
    setCacheTime("");
    setError("");
    setSearchParams({});
    try {
      const res = await searchStock(query.trim());
      const data = JSON.parse(res);
      setSearchResults(data || []);
    } catch (e) {
      setError(String(e));
    }
    setSearchLoading(false);
  }, [query]);

  const selectStock = async (stock: StockSearchResult) => {
    setSelectedCode(stock.code);
    setSelectedName(stock.name);
    setSearchResults([]);
    setSearched(false);
    setQuery(stock.name);
    setInsight(null);
    setError("");
    setMdStatus("");
    setSearchParams({ code: stock.code, name: stock.name });
    try {
      const cached = await loadStockInsight(stock.code);
      if (cached && cached !== "{}") {
        const p = JSON.parse(cached);
        if (p.data && p.updated_at) {
          setInsight(p.data);
          setCacheTime(p.updated_at);
        }
      }
    } catch {}
  };

  const handleAnalyze = async () => {
    if (!selectedCode) return;
    setLoading(true);
    setError("");
    setMdStatus("");
    try {
      const res = await runStockInsight(selectedCode);
      const data = JSON.parse(res);
      if (data.error) {
        setError(data.error);
      } else {
        setInsight(data);
        saveStockInsight(selectedCode, res).catch(() => {});
      }
    } catch (e) {
      setError(String(e));
    }
    setLoading(false);
  };

  const handleExport = async () => {
    if (!insight || !selectedCode) return;
    try {
      const path = await exportStockInsightMd(selectedCode, selectedName, JSON.stringify(insight));
      setMdStatus(`✅ 已保存: ${path}`);
    } catch (e) {
      setMdStatus(`❌ 导出失败: ${e}`);
    }
  };

  const handleAddWatchlist = async () => {
    if (!selectedCode || !selectedName) return;
    try {
      const { invoke } = await import("@tauri-apps/api/core");
      await invoke("add_portfolio_stock", {
        code: selectedCode, name: selectedName,
        costPrice: 0, shares: 0, category: "候选",
      });
      setAddStatus("✅ 已加入自选股");
    } catch (e) {
      setAddStatus(`❌ 加入失败: ${e}`);
    }
  };

  const bpa = insight?.buy_point_analysis;

  const gridStyle: React.CSSProperties = {
    display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(260px, 1fr))",
    gap: 12, marginTop: 16,
  };
  const cardStyle: React.CSSProperties = {
    padding: 14, background: "#f8f9fa", borderRadius: 10, border: "1px solid #eee",
    fontSize: 13, lineHeight: 1.7,
  };

  return (
    <div>
      <h2 style={{ fontSize: 22, fontWeight: 700, margin: "0 0 16px" }}>📈 个股深度分析</h2>

      <div style={{ display: "flex", gap: 8, marginBottom: 12, flexWrap: "wrap" }}>
        <div style={{ flex: 1, minWidth: 200, display: "flex", gap: 6 }}>
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleSearch()}
            placeholder="输入股票名称或代码"
            style={{
              flex: 1, padding: "8px 12px", fontSize: 14,
              border: "1px solid var(--border)", borderRadius: 8, outline: "none",
            }}
          />
          <button onClick={handleSearch} disabled={searchLoading} style={{
            padding: "8px 16px", fontSize: 13,
            background: searchLoading ? "#eee" : "#fff",
            border: "1px solid var(--border)", borderRadius: 8, cursor: searchLoading ? "not-allowed" : "pointer",
          }}>{searchLoading ? "搜索中..." : "搜索"}</button>
        </div>
        <button onClick={handleAnalyze} disabled={!selectedCode || loading} style={{
          padding: "8px 18px", fontSize: 13, fontWeight: 600,
          background: !selectedCode ? "#ddd" : "linear-gradient(135deg, #7c5cfc, #5b8def)",
          color: "#fff", border: "none", borderRadius: 8,
          cursor: !selectedCode || loading ? "not-allowed" : "pointer",
          opacity: !selectedCode || loading ? 0.6 : 1,
        }}>
          {loading ? "⏳ 分析中..." : "🤖 AI 分析"}
        </button>
        {insight && (
          <>
            <button onClick={handleExport} style={exportButtonStyle}>💾 导出报告</button>
            <button onClick={handleAddWatchlist} style={addButtonStyle}>➕ 加入自选</button>
          </>
        )}
      </div>

      {searchResults.length > 0 && (
        <div style={{
          marginBottom: 12, border: "1px solid var(--border)",
          borderRadius: 8, overflow: "hidden",
        }}>
          {searchResults.map((s) => (
            <div key={s.code} onClick={() => selectStock(s)}
              style={{
                padding: "10px 14px", cursor: "pointer", fontSize: 13,
                borderBottom: "1px solid #f0f0f0",
              }}
              onMouseEnter={(e) => { e.currentTarget.style.background = "#f5f0ff"; }}
              onMouseLeave={(e) => { e.currentTarget.style.background = "transparent"; }}
            >
              {s.name} ({s.code}) — {s.industry}
            </div>
          ))}
        </div>
      )}

      {searched && searchResults.length === 0 && !searchLoading && (
        <div style={{ padding: "10px 14px", background: "#f8f9fa", border: "1px solid #e0e0e0", borderRadius: 8, color: "#888", fontSize: 13, marginBottom: 12 }}>
          未找到匹配的股票，请尝试其他关键词
        </div>
      )}

      {selectedCode && !insight && !loading && (
        <div style={{ padding: "10px 14px", background: "#f0fdf4", border: "1px solid #bbf7d0", borderRadius: 8, color: "#16a34a", fontSize: 13, marginBottom: 12 }}>
          ✅ 已选择: {selectedName} ({selectedCode}) — 点击「AI 分析」开始深度分析
        </div>
      )}

      {cacheTime && (
        <div style={{ fontSize: 12, color: "#888", marginBottom: 8 }}>
          上次分析: {cacheTime} · <span style={{ color: "#7c5cfc", cursor: "pointer" }} onClick={handleAnalyze}>重新分析</span>
        </div>
      )}

      {error && (
        <div style={{ padding: "10px 14px", background: "#fef2f2", border: "1px solid #fecaca", borderRadius: 8, color: "#dc2626", fontSize: 13, marginBottom: 12 }}>
          {error}
        </div>
      )}

      {mdStatus && (
        <div style={{ padding: "10px 14px", background: "#f0fdf4", border: "1px solid #bbf7d0", borderRadius: 8, color: "#16a34a", fontSize: 13, marginBottom: 12 }}>
          {mdStatus}
        </div>
      )}

      {addStatus && (
        <div style={{ padding: "10px 14px", background: "#fff7ed", border: "1px solid #fed7aa", borderRadius: 8, color: "#c2410c", fontSize: 13, marginBottom: 12 }}>
          {addStatus}
        </div>
      )}

      {loading && (
        <div style={{ padding: 40, textAlign: "center", color: "#888", fontSize: 14 }}>
          ⏳ LLM 正在分析 {selectedName}...
        </div>
      )}

      {insight && (
        <div>
          <div style={{
            display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(140px, 1fr))",
            gap: 10, marginBottom: 20,
          }}>
            {[
              { label: "名称", value: insight.basic_info.name },
              { label: "代码", value: insight.basic_info.code },
              { label: "行业", value: insight.basic_info.industry },
              { label: "现价", value: insight.basic_info.price.toFixed(2), color: insight.basic_info.change_pct >= 0 ? "#dc2626" : "#16a34a" },
              { label: "涨跌幅", value: `${insight.basic_info.change_pct >= 0 ? "+" : ""}${insight.basic_info.change_pct.toFixed(2)}%`, color: insight.basic_info.change_pct >= 0 ? "#dc2626" : "#16a34a" },
              { label: "PE", value: insight.basic_info.pe.toFixed(1) },
              { label: "PB", value: insight.basic_info.pb.toFixed(1) },
            ].map((item) => (
              <div key={item.label} style={{ background: "#f0f7ff", borderRadius: 8, padding: "10px 12px" }}>
                <div style={{ fontSize: 11, color: "#888", marginBottom: 2 }}>{item.label}</div>
                <div style={{ fontSize: 15, fontWeight: 600, color: item.color || "#333" }}>{item.value}</div>
              </div>
            ))}
          </div>

          <div style={{ marginBottom: 20 }}>
            <div style={{ fontSize: 16, fontWeight: 700, marginBottom: 10, color: "#16a34a" }}>🎯 买入点分析</div>
            {bpa?.summary && (
              <div style={{
                fontSize: 13, color: "#555", marginBottom: 12,
                padding: "10px 14px", background: "#f0fdf4", borderRadius: 8,
                border: "1px solid #bbf7d0", lineHeight: 1.6,
              }}>
                💡 {bpa.summary}
              </div>
            )}
            {renderBuyPointCard("🟢 短期买入点", "#16a34a", bpa?.short_term)}
            {renderBuyPointCard("🟡 中期买入点", "#ca8a04", bpa?.mid_term)}
            {renderBuyPointCard("🔵 长期买入点", "#2563eb", bpa?.long_term)}
            {bpa?.position_suggestion && (
              <div style={{
                padding: "10px 14px", background: "#f8f9fa", borderRadius: 8,
                fontSize: 13, color: "#333", marginTop: 8,
              }}>
                <strong>仓位建议：</strong>{bpa.position_suggestion}
              </div>
            )}
            {bpa?.key_indicators && (
              <div style={{
                display: "flex", gap: 12, marginTop: 8, fontSize: 12,
              }}>
                <span style={{ color: "#16a34a" }}>支撑: {bpa.key_indicators.support_level.toFixed(0)}</span>
                <span style={{ color: "#dc2626" }}>阻力: {bpa.key_indicators.resistance_level.toFixed(0)}</span>
                <span style={{ color: "#888" }}>止损: {bpa.key_indicators.stop_loss.toFixed(0)}</span>
              </div>
            )}
          </div>

          <div style={{ fontSize: 16, fontWeight: 700, marginBottom: 4 }}>📊 12 维深度分析</div>
          <div style={gridStyle}>
            {Object.entries(DIMENSION_LABELS).map(([key, label]) => {
              const val = insight.analysis_12dim?.[key];
              if (!val || val === "...") return null;
              return (
                <div key={key} style={cardStyle}>
                  <div style={{ fontWeight: 600, marginBottom: 6, fontSize: 13 }}>{label}</div>
                  <div style={{ color: "#555", lineHeight: 1.6, whiteSpace: "pre-wrap", fontSize: 12 }}>
                    {val.length > 150 ? val.slice(0, 150) + "..." : val}
                  </div>
                </div>
              );
            })}
          </div>

          {insight.risk_warning && (
            <div style={{
              marginTop: 20, padding: "12px 16px", background: "#fef2f2",
              border: "1px solid #fecaca", borderRadius: 8,
            }}>
              <div style={{ fontWeight: 600, fontSize: 13, color: "#dc2626", marginBottom: 4 }}>⚠️ 风险提示</div>
              <div style={{ fontSize: 13, color: "#7f1d1d", lineHeight: 1.6 }}>{insight.risk_warning}</div>
            </div>
          )}
        </div>
      )}

      {!loading && !insight && !error && !cacheTime && (
        <div style={{ padding: 60, textAlign: "center", color: "#aaa", fontSize: 14 }}>
          输入股票名称，点击「AI 分析」获取深度分析报告
        </div>
      )}
    </div>
  );
}