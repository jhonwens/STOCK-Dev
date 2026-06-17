import { useState, useEffect, useMemo, Fragment } from "react";
import {
  getDashboardSummary, getPortfolio, getTechnicalIndicators,
  getMarketMovers, getStockList, runAnalysis,
  addStockToList, removeStockFromList,
} from "../services/api";
import type { StockSummary, StockItem, TechnicalIndicators, MarketOverview, StockListEntry } from "../types";
import TrendFilterBar from "../components/TrendFilterBar";
import TechnicalPanel from "../components/TechnicalPanel";

function fmtIndustryKey(raw: string): string {
  const parts = raw.split("/");
  return parts[0] || raw;
}

export default function Dashboard() {
  const [summary, setSummary] = useState<StockSummary | null>(null);
  const [movers, setMovers] = useState<MarketOverview | null>(null);
  const [stockList, setStockList] = useState<StockListEntry[]>([]);
  const [portfolio, setPortfolio] = useState<StockItem[]>([]);
  const [selected, setSelected] = useState<string | null>(null);
  const [indicators, setIndicators] = useState<TechnicalIndicators | null>(null);
  const [updating, setUpdating] = useState(false);
  const [expanded, setExpanded] = useState<Record<string, boolean> | null>(null);

  const [showAdd, setShowAdd] = useState(false);
  const [addCode, setAddCode] = useState("");
  const [addName, setAddName] = useState("");
  const [addIndustry, setAddIndustry] = useState("");
  const [addMsg, setAddMsg] = useState("");

  const loadAll = () => {
    getDashboardSummary().then(setSummary);
    getMarketMovers().then(setMovers);
    getStockList().then(setStockList);
    getPortfolio().then(setPortfolio);
  };

  useEffect(() => { loadAll(); }, []);

  const grouped = useMemo(() => {
    const codeToPrice = new Map<string, StockItem>();
    portfolio.forEach((p) => { codeToPrice.set(p.code, p); });
    const groups: Record<string, StockItem[]> = {};
    for (const entry of stockList) {
      const key = fmtIndustryKey(entry.industry);
      const priceInfo = codeToPrice.get(entry.code);
      groups[key] = groups[key] || [];
      groups[key].push({
        code: entry.code,
        name: entry.name,
        industry: entry.industry,
        price: priceInfo?.price ?? 0,
        change_pct: priceInfo?.change_pct ?? 0,
        score: priceInfo?.score ?? 0,
        suggestion: priceInfo?.suggestion ?? "",
        risk_level: priceInfo?.risk_level ?? "",
      });
    }
    return groups;
  }, [stockList, portfolio]);

  const industryKeys = Object.keys(grouped).sort();

  useEffect(() => {
    if (!expanded && industryKeys.length > 0) {
      const all: Record<string, boolean> = {};
      industryKeys.forEach((k) => { all[k] = true; });
      setExpanded(all);
    }
  }, [industryKeys, expanded]);

  const toggleIndustry = (key: string) => {
    setExpanded((prev) => ({ ...prev, [key]: !prev?.[key] }));
  };
  const expandAll = () => {
    const all: Record<string, boolean> = {};
    industryKeys.forEach((k) => { all[k] = true; });
    setExpanded(all);
  };
  const collapseAll = () => {
    const all: Record<string, boolean> = {};
    industryKeys.forEach((k) => { all[k] = false; });
    setExpanded(all);
  };

  const handleUpdate = async () => {
    setUpdating(true);
    await runAnalysis();
    setUpdating(false);
    loadAll();
  };

  const handleSelect = async (code: string) => {
    setSelected(code === selected ? null : code);
    if (code !== selected) {
      getTechnicalIndicators(code).then(setIndicators);
    }
  };

  const handleAddStock = async () => {
    if (!addCode || !addName || !addIndustry) {
      setAddMsg("请填写完整信息");
      return;
    }
    setAddMsg("");
    try {
      const res = await addStockToList(addCode.trim(), addName.trim(), addIndustry.trim());
      setAddMsg(res);
      setAddCode("");
      setAddName("");
      setAddIndustry("");
      setShowAdd(false);
      loadAll();
    } catch (e) {
      setAddMsg(`❌ ${e}`);
    }
  };

  const handleDelete = async (code: string, name: string) => {
    if (!confirm(`确定要从股票池移除 ${name}(${code}) 吗？`)) return;
    try {
      await removeStockFromList(code);
      loadAll();
    } catch (e) {
      alert(`删除失败: ${e}`);
    }
  };

  const inputStyle = {
    padding: "6px 10px", border: "1px solid var(--border)", borderRadius: 6, fontSize: 12, outline: "none" as const,
  };

  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 20 }}>
        <h2 style={{ fontSize: 22, fontWeight: 700 }}>股票池概览</h2>
        <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
          {movers && (
            <span style={{ fontSize: 12, color: "var(--text-secondary)" }}>
              更新: {movers.last_update.slice(5, 16)}
            </span>
          )}
          <button onClick={() => setShowAdd(!showAdd)} style={{
            padding: "8px 16px", background: "#fff", color: "var(--primary)",
            border: "1px solid var(--primary)", borderRadius: 8, cursor: "pointer",
            fontSize: 12, fontWeight: 500,
          }}>
            + 添加股票
          </button>
          <button onClick={handleUpdate} disabled={updating} style={{
            padding: "8px 18px", background: "var(--primary)", color: "#fff",
            border: "none", borderRadius: 8, cursor: updating ? "not-allowed" : "pointer",
            fontSize: 13, opacity: updating ? 0.6 : 1,
          }}>
            {updating ? "⏳ 更新中..." : "📡 数据更新"}
          </button>
        </div>
      </div>

      {showAdd && (
        <div style={{
          background: "#fff", borderRadius: 10, padding: 16, marginBottom: 16,
          boxShadow: "0 1px 4px rgba(0,0,0,0.1)", display: "flex", gap: 10, alignItems: "flex-end", flexWrap: "wrap",
        }}>
          <div><div style={{ fontSize: 11, marginBottom: 4, color: "var(--text-secondary)" }}>代码</div><input value={addCode} onChange={e => setAddCode(e.target.value)} placeholder="300750" style={inputStyle} /></div>
          <div><div style={{ fontSize: 11, marginBottom: 4, color: "var(--text-secondary)" }}>名称</div><input value={addName} onChange={e => setAddName(e.target.value)} placeholder="宁德时代" style={inputStyle} /></div>
          <div><div style={{ fontSize: 11, marginBottom: 4, color: "var(--text-secondary)" }}>行业</div><input value={addIndustry} onChange={e => setAddIndustry(e.target.value)} placeholder="AI/新能源" style={inputStyle} /></div>
          <button onClick={handleAddStock} style={{ padding: "7px 16px", background: "var(--primary)", color: "#fff", border: "none", borderRadius: 6, cursor: "pointer", fontSize: 12 }}>确认添加</button>
          {addMsg && <span style={{ fontSize: 12, color: "var(--text-secondary)" }}>{addMsg}</span>}
        </div>
      )}

      <div style={{ display: "flex", gap: 10, flexWrap: "wrap", marginBottom: 20 }}>
        {[
          { label: "行业板块", value: industryKeys.length, color: "var(--primary)" },
          { label: "关注股票", value: stockList.length, color: "#1a73e8" },
          { label: "上涨", value: portfolio.filter(s => s.change_pct > 0).length, color: "var(--up)" },
          { label: "下跌", value: portfolio.filter(s => s.change_pct < 0).length, color: "var(--down)" },
          { label: "预警", value: summary?.alert_count ?? 0, color: "var(--warn)" },
        ].map((card) => (
          <div key={card.label} style={{
            flex: 1, minWidth: 100, padding: "14px 16px", background: "#fff",
            borderRadius: 10, boxShadow: "0 1px 3px rgba(0,0,0,0.08)",
          }}>
            <div style={{ fontSize: 24, fontWeight: 700, color: card.color }}>{card.value}</div>
            <div style={{ fontSize: 12, color: "var(--text-secondary)", marginTop: 2 }}>{card.label}</div>
          </div>
        ))}
      </div>

      <div style={{ display: "flex", gap: 16, marginBottom: 20 }}>
        <div style={{ flex: 1, background: "#fff", borderRadius: 10, padding: 12, boxShadow: "0 1px 3px rgba(0,0,0,0.08)" }}>
          <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 8, color: "var(--up)" }}>涨幅 Top 10</div>
          {movers?.top_gainers.slice(0, 10).map((m, i) => (
            <div key={m.code} style={{ display: "flex", justifyContent: "space-between", padding: "4px 0", borderBottom: i < 9 ? "1px solid var(--border)" : "none", fontSize: 12 }}>
              <span>{m.name} <span style={{ color: "var(--text-secondary)" }}>{m.code}</span></span>
              <span style={{ color: m.change_pct >= 0 ? "var(--up)" : "var(--down)", fontWeight: 500 }}>
                {m.change_pct >= 0 ? "+" : ""}{m.change_pct.toFixed(2)}%
              </span>
            </div>
          ))}
        </div>
        <div style={{ flex: 1, background: "#fff", borderRadius: 10, padding: 12, boxShadow: "0 1px 3px rgba(0,0,0,0.08)" }}>
          <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 8, color: "var(--down)" }}>跌幅 Top 10</div>
          {movers?.top_losers.slice(0, 10).map((m, i) => (
            <div key={m.code} style={{ display: "flex", justifyContent: "space-between", padding: "4px 0", borderBottom: i < 9 ? "1px solid var(--border)" : "none", fontSize: 12 }}>
              <span>{m.name} <span style={{ color: "var(--text-secondary)" }}>{m.code}</span></span>
              <span style={{ color: m.change_pct >= 0 ? "var(--up)" : "var(--down)", fontWeight: 500 }}>
                {m.change_pct >= 0 ? "+" : ""}{m.change_pct.toFixed(2)}%
              </span>
            </div>
          ))}
        </div>
      </div>

      <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 10 }}>
        <span style={{ fontSize: 12, color: "var(--text-secondary)" }}>{stockList.length} 只股票</span>
        <div style={{ display: "flex", gap: 6 }}>
          <button onClick={expandAll} style={{ padding: "4px 12px", fontSize: 11, border: "1px solid var(--border)", borderRadius: 4, background: "#fff", cursor: "pointer" }}>展开全部</button>
          <button onClick={collapseAll} style={{ padding: "4px 12px", fontSize: 11, border: "1px solid var(--border)", borderRadius: 4, background: "#fff", cursor: "pointer" }}>折叠全部</button>
        </div>
      </div>

      {industryKeys.map((industry) => {
        const stocks = grouped[industry];
        const isOpen = expanded?.[industry] === true;
        const upCount = stocks.filter(s => s.change_pct > 0).length;
        const downCount = stocks.filter(s => s.change_pct < 0).length;

        return (
          <div key={industry} style={{ background: "#fff", borderRadius: 10, boxShadow: "0 1px 3px rgba(0,0,0,0.08)", marginBottom: 10, overflow: "hidden" }}>
            <div onClick={() => toggleIndustry(industry)} style={{ display: "flex", alignItems: "center", padding: "12px 16px", cursor: "pointer", userSelect: "none", borderBottom: isOpen ? "1px solid var(--border)" : "none", }}>
              <span style={{ marginRight: 8, fontSize: 14, transition: "transform 0.2s", transform: isOpen ? "rotate(90deg)" : "rotate(0deg)" }}>▶</span>
              <span style={{ fontWeight: 600, fontSize: 14, flex: 1 }}>{industry}</span>
              <span style={{ fontSize: 12, color: "var(--text-secondary)", marginRight: 10 }}>{stocks.length} 只</span>
              <span style={{ fontSize: 12, color: "var(--up)", marginRight: 8 }}>涨{upCount}</span>
              <span style={{ fontSize: 12, color: "var(--down)" }}>跌{downCount}</span>
            </div>
            {isOpen && (
              <table style={{ width: "100%", borderCollapse: "collapse" }}>
                <thead><tr style={{ background: "#f8f9fa" }}>
                  {["代码", "名称", "子行业", "现价", "涨跌幅", "评分", "建议", "风险", "操作"].map(h => (
                    <th key={h} style={{ padding: "7px 8px", borderBottom: "2px solid var(--border)", fontSize: 11, fontWeight: 600, color: "var(--text-secondary)", textAlign: "left" }}>{h}</th>
                  ))}
                </tr></thead>
                <tbody>
                  {stocks.map(s => (
                    <Fragment key={s.code}>
                      <tr onClick={() => handleSelect(s.code)} style={{ borderBottom: "1px solid #f0f0f0", cursor: "pointer", background: selected === s.code ? "#f0f7ff" : "transparent", fontSize: 13 }}>
                        <td style={{ padding: "6px 8px", fontFamily: "monospace" }}>{s.code}</td>
                        <td style={{ padding: "6px 8px", fontWeight: 500 }}>{s.name}</td>
                        <td style={{ padding: "6px 8px", color: "var(--text-secondary)", fontSize: 11 }}>{s.industry.split("/")[1] || ""}</td>
                        <td style={{ padding: "6px 8px" }}>{s.price ? s.price.toFixed(2) : "-"}</td>
                        <td style={{ padding: "6px 8px", fontWeight: 500, color: s.change_pct >= 0 ? "var(--up)" : "var(--down)", }}>
                          {s.price ? (s.change_pct >= 0 ? "+" : "") + s.change_pct.toFixed(2) + "%" : "-"}
                        </td>
                        <td style={{ padding: "6px 8px" }}>
                          {s.score > 0 ? (
                            <span style={{ padding: "1px 6px", borderRadius: 4, fontSize: 11, background: s.score >= 80 ? "#fce4e4" : s.score >= 50 ? "#fff3e0" : "#e8f5e9", color: s.score >= 80 ? "#c62828" : s.score >= 50 ? "#e65100" : "#2e7d32", }}>{s.score}</span>
                          ) : "-"}
                        </td>
                        <td style={{ padding: "6px 8px", fontWeight: 500, color: s.suggestion === "买入" ? "var(--up)" : s.suggestion === "卖出" ? "var(--down)" : "inherit" }}>
                          {s.suggestion || "-"}
                        </td>
                        <td style={{ padding: "6px 8px", color: s.risk_level === "低" ? "#2e7d32" : s.risk_level === "高" ? "var(--down)" : "inherit" }}>
                          {s.risk_level || "-"}
                        </td>
                        <td style={{ padding: "6px 8px" }}>
                          <span onClick={e => { e.stopPropagation(); handleDelete(s.code, s.name); }} style={{ fontSize: 11, color: "var(--down)", cursor: "pointer", textDecoration: "underline" }}>删除</span>
                        </td>
                      </tr>
                      {selected === s.code && indicators && (
                        <tr><td colSpan={9} style={{ padding: 0 }}>
                          <TrendFilterBar indicators={indicators} />
                          <TechnicalPanel indicators={indicators} code={s.code} name={s.name} />
                        </td></tr>
                      )}
                    </Fragment>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        );
      })}
    </div>
  );
}