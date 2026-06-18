import { useState, useEffect, Fragment } from "react";
import {
  getPortfolioStocks, addPortfolioStock, removePortfolioStock,
  runPortfolioLlm, savePortfolioAnalysis, loadPortfolioAnalysis,
  exportPortfolioMd,
} from "../services/api";
import { getFeatureFlags } from "../services/feature_flag";
import UpgradeModal from "../components/UpgradeModal";
import type { PortfolioStock, FeatureFlags } from "../types";

interface RawIndicators {
  macd_dif?: number; macd_dea?: number; histogram?: number;
  macd_golden?: boolean; macd_death?: boolean; macd_above_zero?: boolean;
  rsi14?: number; k?: number; d?: number; j?: number; kdj_golden?: boolean;
  upper_band?: number; middle_band?: number; lower_band?: number;
  boll_position?: string; obv_trend?: string;
  ema20?: number; ema60?: number; ema120?: number;
  [k: string]: any;
}

interface RawData {
  price?: number; change_pct?: number; turnover?: number;
  pe?: number; pb?: number;
  ma5?: number; ma10?: number; ma20?: number;
  vol_ratio?: number; limit_up_count_20d?: number;
  main_inflow?: number; red_green_ratio?: string;
  indicators?: RawIndicators;
  [k: string]: any;
}

interface LlmAnalysis {
  overall_action?: "加仓" | "减仓" | "持有";
  short_term?: { action: string; percent: number; reason: string };
  mid_term?: { action: string; percent: number; reason: string };
  long_term?: { action: string; percent: number; reason: string };
  support?: number;
  resistance?: number;
  stop_loss?: number;
  _raw_data?: RawData;
  [k: string]: any;
}

function fmt(v: any, decimals = 2): string {
  if (v === null || v === undefined) return "-";
  if (typeof v === "number") return v.toFixed(decimals);
  return String(v);
}

function fmtPct(v: any): string {
  if (v === null || v === undefined) return "-";
  const n = Number(v);
  return (n >= 0 ? "+" : "") + n.toFixed(2) + "%";
}

function IndicatorCell({ label, value, color }: { label: string; value: any; color?: string }) {
  return (
    <td style={{ padding: "5px 8px", fontSize: 12, borderBottom: "1px solid #f0f0f0" }}>
      <span style={{ color: "var(--text-secondary)", marginRight: 4 }}>{label}</span>
      <span style={{ fontWeight: 600, color: color || "inherit" }}>{value}</span>
    </td>
  );
}

function IndicatorRow({ cells }: { cells: { label: string; value: any; color?: string }[] }) {
  return (
    <tr>
      {cells.map((c, i) => (
        <IndicatorCell key={i} label={c.label} value={c.value} color={c.color} />
      ))}
      {cells.length < 4 && <td colSpan={4 - cells.length} style={{ padding: "5px 8px", borderBottom: "1px solid #f0f0f0" }} />}
    </tr>
  );
}

const secTitle = (color = "var(--primary)") => ({
  fontSize: 13, fontWeight: 700, color, marginBottom: 6, marginTop: 14,
  borderBottom: "1px solid #eee", paddingBottom: 4,
});

function SellSignalList({ sellSignals }: { sellSignals: Record<string, string[]> }) {
  const periods = ["短期", "中期", "中长期"];
  const keys = periods.filter(p => sellSignals[p] && sellSignals[p].length > 0);
  if (keys.length === 0) return null;
  return (
    <div>
      {keys.map(k => (
        <div key={k} style={{ marginBottom: 6 }}>
          <div style={{ fontSize: 12, fontWeight: 600, color: "var(--down)", marginBottom: 2 }}>{k}</div>
          {sellSignals[k].map((s, i) => (
            <div key={i} style={{ padding: "1px 0 1px 12px", fontSize: 12, display: "flex", gap: 4, alignItems: "flex-start" }}>
              <span style={{ color: "var(--down)" }}>▼</span>
              <span>{s}</span>
            </div>
          ))}
        </div>
      ))}
    </div>
  );
}

function OldSignalFallback({ data }: { data: LlmAnalysis }) {
  const sellArr = data["卖出信号指标"] as string[] | undefined;
  if (!sellArr || sellArr.length === 0) return null;
  return (
    <div style={{ marginTop: 8, padding: "12px 16px", background: "#fef2f2", borderRadius: 8, border: "1px solid #fecaca" }}>
      <div style={{ fontSize: 14, fontWeight: 700, color: "var(--down)", marginBottom: 6 }}>🔴 卖出提示（旧格式）</div>
      {sellArr.map((item, i) => (
        <div key={i} style={{ padding: "2px 0", display: "flex", gap: 4 }}>
          <span style={{ color: "var(--down)" }}>▼</span>
          <span style={{ fontSize: 12 }}>{item}</span>
        </div>
      ))}
    </div>
  );
}

export default function Portfolio() {
  const [stocks, setStocks] = useState<PortfolioStock[]>([]);
  const [selected, setSelected] = useState<PortfolioStock | null>(null);
  const [llmData, setLlmData] = useState<LlmAnalysis | null>(null);
  const [llmLoading, setLlmLoading] = useState(false);
  const [llmError, setLlmError] = useState("");
  const [cacheTime, setCacheTime] = useState("");
  const [mdStatus, setMdStatus] = useState("");

  const [showAdd, setShowAdd] = useState(false);
  const [addCode, setAddCode] = useState("");
  const [addName, setAddName] = useState("");
  const [addCost, setAddCost] = useState("");
  const [addShares, setAddShares] = useState("");
  const [addMsg, setAddMsg] = useState("");

  const [flags, setFlags] = useState<FeatureFlags | null>(null);
  const [showUpgrade, setShowUpgrade] = useState(false);
  const [upgradeReason, setUpgradeReason] = useState("");

  useEffect(() => {
    getFeatureFlags().then(setFlags);
  }, []);

  const maxHoldings = flags?.limits.max_holdings ?? 5;
  const currentHoldings = stocks.length;
  const canAddMore = currentHoldings < maxHoldings;

  const handleAddClick = () => {
    if (!canAddMore) {
      setUpgradeReason(
        `当前持仓 ${currentHoldings} 只，已达当前等级上限（${maxHoldings} 只）。升级 Pro 解锁更多持仓。`
      );
      setShowUpgrade(true);
      return;
    }
    setShowAdd(!showAdd);
  };

  const load = () => getPortfolioStocks().then(setStocks);
  useEffect(() => { load(); }, []);

  const handleAdd = async () => {
    if (!addCode || !addName || !addCost || !addShares) { setAddMsg("请填写完整信息"); return; }
    setAddMsg("");
    try {
      const res = await addPortfolioStock(addCode.trim(), addName.trim(), parseFloat(addCost), parseInt(addShares), "持仓");
      setAddMsg(res);
      setAddCode(""); setAddName(""); setAddCost(""); setAddShares("");
      setShowAdd(false);
      load();
    } catch (e) { setAddMsg(`❌ ${e}`); }
  };

  const handleDelete = async (id: number, name: string) => {
    if (!confirm(`确定移除 ${name}？`)) return;
    await removePortfolioStock(id);
    if (selected?.id === id) { setSelected(null); setLlmData(null); }
    load();
  };

  const handleSelect = async (s: PortfolioStock) => {
    if (selected?.id === s.id) {
      setSelected(null);
      setLlmData(null);
      return;
    }
    setSelected(s);
    setLlmData(null);
    setLlmError("");
    setCacheTime("");
    setMdStatus("");
    setLlmLoading(true);
    try {
      const cached = await loadPortfolioAnalysis(s.code);
      if (cached && cached !== "{}") {
        const p = JSON.parse(cached);
        if (p.data && p.updated_at) {
          setLlmData(p.data);
          setCacheTime(p.updated_at);
        }
      }
    } catch {}
    setLlmLoading(false);
  };

  const handleAiAnalyze = async () => {
    const s = selected;
    if (!s) return;
    setLlmLoading(true);
    setLlmError("");
    setMdStatus("");
    try {
      const res = await runPortfolioLlm(s.code);
      try {
        setLlmData(JSON.parse(res));
        setCacheTime("");
        savePortfolioAnalysis(s.code, res).catch(() => {});
      } catch (e) {
        setLlmError(`❌ LLM 返回格式异常: ${String(e).replace("SyntaxError: JSON Parse error: ", "").slice(0, 50)}`);
      }
    } catch (e) {
      setLlmError(`❌ 分析失败: ${e}`);
    }
    setLlmLoading(false);
  };

  const handleExportMd = async () => {
    if (!selected || !llmData) return;
    setMdStatus("");
    try {
      const path = await exportPortfolioMd(selected.code, selected.name, JSON.stringify(llmData));
      setMdStatus(`✅ 已保存: ${path}`);
    } catch (e) {
      setMdStatus(`❌ 导出失败: ${e}`);
    }
  };

  const rd = llmData?._raw_data;
  const ind = rd?.indicators;

  const rowSpan = { padding: "8px 10px", fontSize: 13 };
  const th = {
    padding: "7px 8px", borderBottom: "2px solid var(--border)",
    fontSize: 11, fontWeight: 600, color: "var(--text-secondary)", textAlign: "left" as const,
  };
  const inputStyle = {
    padding: "6px 10px", border: "1px solid var(--border)", borderRadius: 6, fontSize: 12, outline: "none" as const,
  };
  const btnBase = {
    padding: "6px 14px", border: "none", borderRadius: 6, cursor: "pointer", fontSize: 12, fontWeight: 500,
  };

  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
        <h2 style={{ fontSize: 22, fontWeight: 700 }}>📁 持仓分析</h2>
        {flags && (
          <span style={{
            fontSize: 12, padding: "3px 10px", borderRadius: 12,
            background: canAddMore ? "#f0fdf4" : "#fef2f2",
            color: canAddMore ? "#16a34a" : "#dc2626",
            border: `1px solid ${canAddMore ? "#bbf7d0" : "#fecaca"}`,
            marginLeft: 8,
          }}>
            持仓 {currentHoldings}/{maxHoldings}
          </span>
        )}
        <button onClick={handleAddClick} style={{
          padding: "8px 16px", background: "var(--primary)", color: "#fff",
          border: "none", borderRadius: 8, cursor: "pointer", fontSize: 12,
        }}>
          + 添加持仓
        </button>
      </div>

      {showAdd && (
        <div style={{ background: "#fff", borderRadius: 10, padding: 16, marginBottom: 16, boxShadow: "0 1px 4px rgba(0,0,0,0.1)", display: "flex", gap: 10, alignItems: "flex-end", flexWrap: "wrap" }}>
          <div><div style={{ fontSize: 11, marginBottom: 4, color: "var(--text-secondary)" }}>代码</div><input value={addCode} onChange={e => setAddCode(e.target.value)} placeholder="300750" style={inputStyle} /></div>
          <div><div style={{ fontSize: 11, marginBottom: 4, color: "var(--text-secondary)" }}>名称</div><input value={addName} onChange={e => setAddName(e.target.value)} placeholder="宁德时代" style={inputStyle} /></div>
          <div><div style={{ fontSize: 11, marginBottom: 4, color: "var(--text-secondary)" }}>成本价</div><input value={addCost} onChange={e => setAddCost(e.target.value)} placeholder="180.50" style={{ ...inputStyle, width: 80 }} /></div>
          <div><div style={{ fontSize: 11, marginBottom: 4, color: "var(--text-secondary)" }}>持仓数量</div><input value={addShares} onChange={e => setAddShares(e.target.value)} placeholder="100" style={{ ...inputStyle, width: 80 }} /></div>
          <button onClick={handleAdd} style={{ padding: "7px 16px", background: "var(--primary)", color: "#fff", border: "none", borderRadius: 6, cursor: "pointer", fontSize: 12 }}>确认</button>
          {addMsg && <span style={{ fontSize: 12 }}>{addMsg}</span>}
        </div>
      )}

      <div style={{ background: "#fff", borderRadius: 10, boxShadow: "0 1px 3px rgba(0,0,0,0.08)", overflow: "hidden" }}>
        <table style={{ width: "100%", borderCollapse: "collapse" }}>
          <thead><tr style={{ background: "#f8f9fa" }}>
            {["代码", "名称", "现价", "涨跌幅", "成本价", "数量", "盈亏", "评分", "建议", "风险", "操作"].map(h => (
              <th key={h} style={th}>{h}</th>
            ))}
          </tr></thead>
          <tbody>
            {stocks.map(s => {
              const profit = s.price > 0 ? (s.price - s.cost_price) * s.shares : 0;
              const isOpen = selected?.id === s.id;
              return (
                <Fragment key={s.id}>
                  <tr onClick={() => handleSelect(s)} style={{
                    cursor: "pointer", borderBottom: isOpen ? "none" : "1px solid #eee",
                    background: isOpen ? "#f0f7ff" : "transparent",
                  }}>
                    <td style={{ ...rowSpan, fontFamily: "monospace" }}>{s.code}</td>
                    <td style={{ ...rowSpan, fontWeight: 500 }}>{s.name}</td>
                    <td style={rowSpan}>{s.price > 0 ? s.price.toFixed(2) : "-"}</td>
                    <td style={{ ...rowSpan, color: s.change_pct >= 0 ? "var(--up)" : "var(--down)", fontWeight: 500 }}>
                      {s.price > 0 ? fmtPct(s.change_pct) : "-"}
                    </td>
                    <td style={rowSpan}>{s.cost_price.toFixed(2)}</td>
                    <td style={rowSpan}>{s.shares}</td>
                    <td style={{ ...rowSpan, color: profit >= 0 ? "var(--up)" : "var(--down)", fontWeight: 500 }}>
                      {s.price > 0 ? (profit >= 0 ? "+" : "") + profit.toFixed(2) : "-"}
                    </td>
                    <td style={rowSpan}>{s.score > 0 ? s.score : "-"}</td>
                    <td style={{ ...rowSpan, fontWeight: 500 }}>{s.suggestion || "-"}</td>
                    <td style={rowSpan}>{s.risk_level || "-"}</td>
                    <td style={rowSpan}>
                      <span onClick={e => { e.stopPropagation(); handleDelete(s.id, s.name); }} style={{ fontSize: 11, color: "var(--down)", cursor: "pointer", textDecoration: "underline" }}>删除</span>
                    </td>
                  </tr>

                  {isOpen && (
                    <tr><td colSpan={11} style={{ padding: 0, borderBottom: "1px solid #eee" }}>
                      <div style={{ padding: "16px 20px", background: "#fafbfc" }}>
                        {/* Header with buttons */}
                        <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 10, flexWrap: "wrap" }}>
                          <span style={{ fontSize: 18, fontWeight: 700 }}>{s.name}</span>
                          <span style={{ fontSize: 13, color: "var(--text-secondary)", fontFamily: "monospace" }}>{s.code}</span>
                          <span style={{ fontSize: 16, fontWeight: 700, color: s.change_pct >= 0 ? "var(--up)" : "var(--down)" }}>
                            {s.price.toFixed(2)}
                          </span>
                          <span style={{ fontSize: 13, fontWeight: 600, color: s.change_pct >= 0 ? "var(--up)" : "var(--down)" }}>
                            {fmtPct(s.change_pct)}
                          </span>
                          <span style={{ fontSize: 12, color: "var(--text-secondary)" }}>
                            成本 {s.cost_price.toFixed(2)} × {s.shares}股
                          </span>
                          <span style={{ fontSize: 12, fontWeight: 600, color: profit >= 0 ? "var(--up)" : "var(--down)" }}>
                            盈亏 {profit >= 0 ? "+" : ""}{profit.toFixed(2)}
                          </span>

                          <div style={{ flex: 1 }} />

                          <button onClick={handleAiAnalyze} disabled={llmLoading} style={{
                            ...btnBase, background: "linear-gradient(135deg, #667eea, #764ba2)", color: "#fff",
                            opacity: llmLoading ? 0.6 : 1,
                          }}>🤖 AI 分析</button>

                          {llmData && (
                            <button onClick={handleExportMd} style={{
                              ...btnBase, background: "#fff", border: "1px solid var(--border)", color: "#333",
                            }}>📥 导出MD</button>
                          )}
                        </div>

                        {/* Cache info */}
                        {cacheTime && llmData && (
                          <div style={{ fontSize: 11, color: "var(--text-secondary)", marginBottom: 8 }}>
                            📌 上次分析结果（{cacheTime}）— 点击「AI 分析」基于最新数据重新分析
                          </div>
                        )}

                        {/* MD save status */}
                        {mdStatus && (
                          <div style={{ fontSize: 12, color: mdStatus.startsWith("✅") ? "#2e7d32" : "var(--down)", marginBottom: 8 }}>
                            {mdStatus}
                          </div>
                        )}

                        {/* Loading */}
                        {llmLoading && (
                          <div style={{ textAlign: "center", padding: "30px 0", fontSize: 13, color: "var(--text-secondary)" }}>
                            ⏳ {cacheTime ? "AI 正在分析 " : "加载中..."}{s.name}，请稍候{!cacheTime ? "" : ""}
                          </div>
                        )}

                        {/* Error */}
                        {llmError && (
                          <div style={{ textAlign: "center", padding: "20px 0", fontSize: 12, color: "var(--down)" }}>
                            {llmError}
                          </div>
                        )}

                        {/* No data yet */}
                        {!llmData && !llmLoading && !llmError && (
                          <div style={{ textAlign: "center", padding: "20px 0", fontSize: 13, color: "var(--text-secondary)" }}>
                            💡 点击「AI 分析」获取技术面+基本面综合分析报告
                          </div>
                        )}

                        {/* LLM Analysis Data */}
                        {llmData && !llmLoading && (
                          <>
                            {llmData.overall_action && (
                              <div style={{
                                display: "flex", alignItems: "center", gap: 16,
                                padding: "14px 18px", marginBottom: 14,
                                background: llmData.overall_action === "加仓" ? "#f0fdf4" : llmData.overall_action === "减仓" ? "#fef2f2" : "#f8f9fa",
                                border: `1px solid ${
                                  llmData.overall_action === "加仓" ? "#bbf7d0" : llmData.overall_action === "减仓" ? "#fecaca" : "#e0e0e0"
                                }`,
                                borderRadius: 10,
                              }}>
                                <span style={{
                                  fontSize: 28, fontWeight: 700,
                                  color: llmData.overall_action === "加仓" ? "#16a34a" : llmData.overall_action === "减仓" ? "#dc2626" : "#888",
                                }}>
                                  {llmData.overall_action === "加仓" ? "🟢" : llmData.overall_action === "减仓" ? "🔴" : "⚪"}
                                </span>
                                <div>
                                  <div style={{ fontSize: 18, fontWeight: 700, color: "#333" }}>
                                    总体建议：{llmData.overall_action}
                                  </div>
                                  <div style={{ fontSize: 12, color: "#888", marginTop: 2 }}>
                                    基于技术面、量能、资金流向的综合判断
                                  </div>
                                </div>
                              </div>
                            )}

                            {rd && (
                              <>
                                <div style={secTitle("#1565c0")}>📊 技术指标</div>
                                <table style={{ width: "100%", borderCollapse: "collapse", marginBottom: 8, background: "#fff", borderRadius: 6 }}>
                                  <tbody>
                                    <IndicatorRow cells={[
                                      { label: "MA5", value: fmt(rd?.ma5), color: rd?.ma5 !== undefined && s.price > rd.ma5 ? "var(--up)" : "var(--down)" },
                                      { label: "MA10", value: fmt(rd?.ma10) },
                                      { label: "MA20", value: fmt(rd?.ma20), color: rd?.ma20 !== undefined && s.price > rd.ma20 ? "var(--up)" : "var(--down)" },
                                      { label: "换手率", value: rd?.turnover ? `${rd.turnover}%` : "-" },
                                    ]} />
                                    <IndicatorRow cells={[
                                      { label: "量比", value: fmt(rd?.vol_ratio) },
                                      { label: "20日涨停", value: rd?.limit_up_count_20d !== undefined ? `${rd.limit_up_count_20d}次` : "-" },
                                      { label: "K线形态", value: rd?.red_green_ratio || "-" },
                                      { label: "主力净流入", value: rd?.main_inflow ? `${(rd.main_inflow / 10000).toFixed(0)}万` : "-", color: (rd?.main_inflow || 0) >= 0 ? "var(--up)" : "var(--down)" },
                                    ]} />
                                    <IndicatorRow cells={[
                                      { label: "MACD DIF", value: fmt(ind?.macd_dif) },
                                      { label: "MACD DEA", value: fmt(ind?.macd_dea) },
                                      { label: "柱状图", value: fmt(ind?.histogram), color: (ind?.histogram || 0) >= 0 ? "var(--up)" : "var(--down)" },
                                      { label: "零轴上", value: ind?.macd_above_zero ? "是" : "否", color: ind?.macd_above_zero ? "var(--up)" : "var(--down)" },
                                    ]} />
                                    <IndicatorRow cells={[
                                      { label: "K", value: fmt(ind?.k) },
                                      { label: "D", value: fmt(ind?.d) },
                                      { label: "J", value: fmt(ind?.j), color: (ind?.j || 0) > 100 ? "var(--down)" : (ind?.j || 0) < 0 ? "var(--up)" : "inherit" },
                                      { label: "KDJ金叉", value: ind?.kdj_golden ? "是" : "否", color: ind?.kdj_golden ? "var(--up)" : "inherit" },
                                    ]} />
                                    <IndicatorRow cells={[
                                      { label: "RSI(14)", value: fmt(ind?.rsi14), color: (ind?.rsi14 || 0) > 70 ? "var(--down)" : (ind?.rsi14 || 0) < 30 ? "var(--up)" : "inherit" },
                                      { label: "BOLL上轨", value: fmt(ind?.upper_band) },
                                      { label: "BOLL中轨", value: fmt(ind?.middle_band), color: s.price > (ind?.middle_band || 0) ? "var(--up)" : "var(--down)" },
                                      { label: "BOLL下轨", value: fmt(ind?.lower_band) },
                                    ]} />
                                    <IndicatorRow cells={[
                                      { label: "BOLL位置", value: ind?.boll_position || "-" },
                                      { label: "OBV趋势", value: ind?.obv_trend || "-", color: ind?.obv_trend === "rising" ? "var(--up)" : ind?.obv_trend === "falling" ? "var(--down)" : "inherit" },
                                      { label: "PE", value: fmt(rd?.pe) },
                                      { label: "PB", value: fmt(rd?.pb) },
                                    ]} />
                                  </tbody>
                                </table>
                              </>
                            )}

                            {llmData.short_term && (
                              <div style={{ marginTop: 12 }}>
                                <div style={{ fontSize: 14, fontWeight: 700, marginBottom: 8 }}>🎯 操作建议</div>
                                {[
                                  { key: "short_term", label: "短期", icon: "🟢", color: "#16a34a" },
                                  { key: "mid_term", label: "中期", icon: "🟡", color: "#ca8a04" },
                                  { key: "long_term", label: "长期", icon: "🔵", color: "#2563eb" },
                                ].map(({ key, label, icon, color }) => {
                                  const item = llmData[key] as { action?: string; percent?: number; reason?: string } | undefined;
                                  if (!item) return null;
                                  const isAdd = item.action === "加仓";
                                  const isSell = item.action === "减仓";
                                  return (
                                    <div key={key} style={{
                                      display: "flex", alignItems: "center", gap: 12,
                                      padding: "10px 14px", marginBottom: 8,
                                      background: isAdd ? "#f0fdf4" : isSell ? "#fef2f2" : "#f8f9fa",
                                      borderLeft: `4px solid ${color}`,
                                      borderRadius: 8,
                                    }}>
                                      <span style={{ fontSize: 18 }}>{icon}</span>
                                      <div style={{ flex: 1 }}>
                                        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                                          <span style={{ fontSize: 13, fontWeight: 600, color }}>{label}</span>
                                          <span style={{
                                            fontSize: 13, fontWeight: 700,
                                            color: isAdd ? "#16a34a" : isSell ? "#dc2626" : "#888",
                                          }}>
                                            {item.action}
                                          </span>
                                          {item.percent ? (
                                            <span style={{
                                              fontSize: 15, fontWeight: 700,
                                              color: isAdd ? "#16a34a" : isSell ? "#dc2626" : "#888",
                                            }}>
                                              {item.percent}%
                                            </span>
                                          ) : null}
                                        </div>
                                        {item.reason && (
                                          <div style={{ fontSize: 12, color: "#666", marginTop: 2, lineHeight: 1.5 }}>
                                            {item.reason}
                                          </div>
                                        )}
                                      </div>
                                    </div>
                                  );
                                })}
                              </div>
                            )}

                            {(llmData.support || llmData.resistance || llmData.stop_loss) && (
                              <div style={{
                                display: "flex", gap: 12, marginTop: 10,
                                padding: "10px 14px", background: "#f8f9fa",
                                borderRadius: 8, border: "1px solid #e0e0e0",
                                fontSize: 12,
                              }}>
                                {llmData.support ? (
                                  <span style={{ color: "#16a34a", fontWeight: 600 }}>
                                    📉 支撑: {llmData.support.toFixed(0)}
                                  </span>
                                ) : null}
                                {llmData.resistance ? (
                                  <span style={{ color: "#dc2626", fontWeight: 600 }}>
                                    📈 阻力: {llmData.resistance.toFixed(0)}
                                  </span>
                                ) : null}
                                {llmData.stop_loss ? (
                                  <span style={{ color: "#888", fontWeight: 600 }}>
                                    🛑 止损: {llmData.stop_loss.toFixed(0)}
                                  </span>
                                ) : null}
                              </div>
                            )}
                          </>
                        )}
                      </div>
                    </td></tr>
                  )}
                </Fragment>
              );
            })}
            {stocks.length === 0 && (
              <tr><td colSpan={11} style={{ padding: 30, textAlign: "center", color: "var(--text-secondary)", fontSize: 13 }}>暂无持仓数据，点击「添加持仓」开始</td></tr>
            )}
          </tbody>
        </table>
      </div>

      <UpgradeModal
        open={showUpgrade}
        reason={upgradeReason}
        onClose={() => setShowUpgrade(false)}
      />
    </div>
  );
}