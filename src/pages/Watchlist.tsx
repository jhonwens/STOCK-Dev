import { useState, useEffect } from "react";
import {
  runCandidateLlm,
  saveCandidateAnalysis,
  loadCandidateAnalysis,
  exportCandidateMd,
} from "../services/api";
import { getFeatureFlags } from "../services/feature_flag";
import UpgradeModal from "../components/UpgradeModal";
import type { CandidateRecommendation, CandidateStock, FeatureFlags } from "../types";
import RecommendDetailDrawer from "./components/RecommendDetailDrawer";

export default function Watchlist() {
  const [recommendation, setRecommendation] = useState<CandidateRecommendation | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [cacheTime, setCacheTime] = useState("");
  const [selectedStock, setSelectedStock] = useState<CandidateStock | null>(null);
  const [showDrawer, setShowDrawer] = useState(false);
  const [mdStatus, setMdStatus] = useState("");

  const [flags, setFlags] = useState<FeatureFlags | null>(null);
  const [showUpgrade, setShowUpgrade] = useState(false);
  const [upgradeReason, setUpgradeReason] = useState("");

  useEffect(() => {
    getFeatureFlags().then(setFlags);
  }, []);

  const canExport = flags?.limits.export_pro_report ?? false;

  useEffect(() => {
    loadCandidateAnalysis().then((res) => {
      if (res && res !== "{}") {
        try {
          const p = JSON.parse(res);
          if (p.data && p.updated_at) {
            setRecommendation(p.data);
            setCacheTime(p.updated_at);
          }
        } catch {}
      }
    });
  }, []);

  const handleAiAnalyze = async () => {
    setLoading(true);
    setError("");
    setMdStatus("");
    try {
      const res = await runCandidateLlm();
      try {
        const data = JSON.parse(res);
        if (data.error) {
          setError(data.error);
        } else {
          setRecommendation(data);
          saveCandidateAnalysis(res).catch(() => {});
        }
      } catch (e) {
        // LLM 返回非 JSON 文本（如"加仓"）时，展示原始内容而非崩溃
        setError(`❌ LLM 返回格式异常: ${String(e).replace("SyntaxError: JSON Parse error: ", "").slice(0, 50)}`);
      }
    } catch (e) {
      setError(String(e));
    }
    setLoading(false);
  };

  const handleExportMd = async () => {
    if (!canExport) {
      setUpgradeReason("导出候选推荐报告是 Pro 会员功能。升级 Pro 即可一键导出完整报告。");
      setShowUpgrade(true);
      return;
    }
    if (!recommendation) return;
    try {
      const path = await exportCandidateMd(JSON.stringify(recommendation));
      setMdStatus(`✅ 已保存: ${path}`);
    } catch (e) {
      setMdStatus(`❌ 导出失败: ${e}`);
    }
  };

  const handleCardClick = (stock: CandidateStock) => {
    setSelectedStock(stock);
    setShowDrawer(true);
  };

  const renderCard = (stock: CandidateStock, index: number, colorScheme: "short" | "long") => {
    const borderColor = colorScheme === "short" ? "#7c5cfc" : "#2e7d32";
    const bgGradient = colorScheme === "short"
      ? "linear-gradient(135deg, #f5f0ff, #f0f4ff)"
      : "linear-gradient(135deg, #e8f5e9, #f1f8e9)";

    return (
      <div
        key={stock.code}
        onClick={() => handleCardClick(stock)}
        style={{
          background: bgGradient,
          borderRadius: 12,
          border: `1px solid ${borderColor}33`,
          padding: 16,
          cursor: "pointer",
          transition: "box-shadow 0.2s, transform 0.15s",
          boxShadow: "0 1px 4px rgba(0,0,0,0.06)",
        }}
        onMouseEnter={(e) => { e.currentTarget.style.boxShadow = "0 4px 12px rgba(0,0,0,0.1)"; e.currentTarget.style.transform = "translateY(-2px)"; }}
        onMouseLeave={(e) => { e.currentTarget.style.boxShadow = "0 1px 4px rgba(0,0,0,0.06)"; e.currentTarget.style.transform = "none"; }}
      >
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 8 }}>
          <div>
            <span style={{ fontSize: 13, fontWeight: 700, color: borderColor }}>
              {"⭐".repeat(Math.ceil(stock.overall_score / 20))}
            </span>
            <span style={{ fontSize: 12, color: "#666", marginLeft: 4 }}>
              {stock.overall_score}/100
            </span>
          </div>
          <span style={{ fontSize: 11, color: "#999" }}>#{stock.rank}</span>
        </div>
        <div style={{ fontSize: 16, fontWeight: 600, marginBottom: 4 }}>{stock.name}</div>
        <div style={{ fontSize: 12, color: "#666", marginBottom: 8, lineHeight: 1.5 }}>
          {stock.recommend_reason.length > 40
            ? stock.recommend_reason.slice(0, 40) + "..."
            : stock.recommend_reason}
        </div>
        <div style={{ fontSize: 11, color: "#888" }}>
          建议区间: {stock.suggested_price_range[0].toFixed(2)} - {stock.suggested_price_range[1].toFixed(2)}
        </div>
        <div style={{ fontSize: 11, color: "#e53935", marginTop: 2 }}>
          ⚠ {stock.risk_warning.length > 20 ? stock.risk_warning.slice(0, 20) + "..." : stock.risk_warning}
        </div>
        <button
          onClick={(e) => { e.stopPropagation(); handleCardClick(stock); }}
          style={{
            marginTop: 10, padding: "6px 14px", fontSize: 12,
            background: "transparent", border: `1px solid ${borderColor}`,
            color: borderColor, borderRadius: 6, cursor: "pointer",
            width: "100%", fontWeight: 500,
          }}
        >
          查看详情
        </button>
      </div>
    );
  };

  const renderCategory = (data: { summary: string; top5: CandidateStock[] } | undefined, title: string, colorScheme: "short" | "long") => {
    if (!data) return null;
    return (
      <div style={{ marginBottom: 28 }}>
        <div style={{
          fontSize: 18, fontWeight: 700, marginBottom: 4,
          color: colorScheme === "short" ? "#7c5cfc" : "#2e7d32",
        }}>
          {title}
        </div>
        {data.summary && (
          <div style={{
            fontSize: 13, color: "#555", marginBottom: 14,
            padding: "10px 14px", background: "#f8f9fa", borderRadius: 8,
            lineHeight: 1.6,
          }}>
            💡 {data.summary}
          </div>
        )}
        <div style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fill, minmax(240px, 1fr))",
          gap: 14,
        }}>
          {(data.top5 || []).map((stock, i) => renderCard(stock, i, colorScheme))}
        </div>
      </div>
    );
  };

  return (
    <div>
      <div style={{
        display: "flex", justifyContent: "space-between", alignItems: "center",
        marginBottom: 20, flexWrap: "wrap", gap: 8,
      }}>
        <div>
          <h2 style={{ fontSize: 22, fontWeight: 700, margin: 0 }}>🎯 候选推荐</h2>
          {cacheTime && (
            <div style={{ fontSize: 12, color: "#888", marginTop: 2 }}>
              上次分析: {cacheTime}
            </div>
          )}
        </div>
        <div style={{ display: "flex", gap: 8 }}>
          <button
            onClick={handleAiAnalyze}
            disabled={loading}
            style={{
              padding: "8px 18px", fontSize: 13, fontWeight: 600,
              background: "linear-gradient(135deg, #7c5cfc, #5b8def)",
              color: "#fff", border: "none", borderRadius: 8,
              cursor: loading ? "not-allowed" : "pointer", opacity: loading ? 0.6 : 1,
            }}
          >
            {loading ? "⏳ 分析中..." : "🤖 AI 推荐"}
          </button>
          {recommendation && (
            <button
              onClick={handleExportMd}
              disabled={!canExport}
              style={{
                padding: "8px 18px", fontSize: 13, fontWeight: 500,
                background: "#fff",
                border: `1px solid ${canExport ? "var(--border)" : "#e0e0e0"}`,
                color: canExport ? "inherit" : "#999",
                borderRadius: 8, cursor: canExport ? "pointer" : "not-allowed",
                opacity: canExport ? 1 : 0.6,
              }}
            >
              {canExport ? "💾 保存报告" : "🔒 保存报告（Pro）"}
            </button>
          )}
        </div>
      </div>

      {error && (
        <div style={{
          padding: "12px 16px", background: "#fef2f2", border: "1px solid #fecaca",
          borderRadius: 8, color: "#dc2626", fontSize: 13, marginBottom: 16,
        }}>
          {error}
        </div>
      )}

      {mdStatus && (
        <div style={{
          padding: "10px 14px", background: "#f0fdf4", border: "1px solid #bbf7d0",
          borderRadius: 8, color: "#16a34a", fontSize: 13, marginBottom: 16,
        }}>
          {mdStatus}
        </div>
      )}

      {loading && (
        <div style={{
          padding: 40, textAlign: "center", color: "#888", fontSize: 14,
        }}>
          ⏳ LLM 正在分析候选股票...
        </div>
      )}

      {!loading && !recommendation && !error && (
        <div style={{
          padding: 60, textAlign: "center", color: "#aaa", fontSize: 14,
        }}>
          点击「AI 推荐」按钮，系统将从股票池中分析并推荐最适合的股票
        </div>
      )}

      {!loading && recommendation && (
        <div>
          {renderCategory(recommendation.short_term, "📈 中短期持有 Top 5", "short")}
          {renderCategory(recommendation.long_term, "📊 长期价值投资 Top 5", "long")}
        </div>
      )}

      {showDrawer && selectedStock && (
        <RecommendDetailDrawer
          stock={selectedStock}
          onClose={() => { setShowDrawer(false); setSelectedStock(null); }}
        />
      )}

      <UpgradeModal
        open={showUpgrade}
        reason={upgradeReason}
        onClose={() => setShowUpgrade(false)}
      />
    </div>
  );
}