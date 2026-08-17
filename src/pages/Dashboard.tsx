import { useState, useEffect, useMemo, useRef, Fragment } from "react";
import {
  getDashboardSummary, getPortfolio, getTechnicalIndicators,
  getMarketMovers, getStockList, runAnalysis,
  addStockToList, removeStockFromList, batchRemoveStocks, batchAddStocks,
} from "../services/api";
import type { StockSummary, StockItem, TechnicalIndicators, MarketOverview, StockListEntry } from "../types";
import TrendFilterBar from "../components/TrendFilterBar";
import TechnicalPanel from "../components/TechnicalPanel";

function fmtIndustryKey(raw: string): string {
  const parts = raw.split("/");
  return parts[0] || raw;
}

export default function Dashboard() {
  const mountedRef = useRef(true);
  const updatingRef = useRef(false);

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
  const [selectedCodes, setSelectedCodes] = useState<Set<string>>(new Set());
  const [showBatchImport, setShowBatchImport] = useState(false);
  const [batchImportText, setBatchImportText] = useState("");
  const [batchImportMsg, setBatchImportMsg] = useState("");
  // 内联确认弹窗：避免 Tauri WebView 中 confirm() 不可用的问题
  const [confirmDialog, setConfirmDialog] = useState<{
    title: string; message: string; onConfirm: () => void;
  } | null>(null);

  const safeSet = <T,>(setter: React.Dispatch<React.SetStateAction<T>>, value: T) => {
    if (mountedRef.current) setter(value);
  };

  const loadAll = () => {
    if (!mountedRef.current) return;
    Promise.all([
      getDashboardSummary().catch(() => null),
      getMarketMovers().catch(() => null),
      getStockList().catch(() => []),
      getPortfolio().catch(() => []),
    ]).then(([s, m, l, p]) => {
      if (!mountedRef.current) return;
      if (s) setSummary(s);
      if (l) setStockList(l);
      if (p) setPortfolio(p);
      if (m) setMovers(m);
    });
  };

  useEffect(() => {
    mountedRef.current = true;
    loadAll();
    return () => {
      mountedRef.current = false;
    };
  }, []);

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
    if (updatingRef.current) return;
    updatingRef.current = true;
    setUpdating(true);
    try {
      const r = await runAnalysis();
      console.log("[handleUpdate] 后端返回:", r);
    } catch (e) {
      console.error("[handleUpdate] 更新失败:", e);
    }
    if (!mountedRef.current) return;
    updatingRef.current = false;
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
    console.log(`[handleDelete] 尝试删除: ${code} ${name}`);
    try {
      const result = await removeStockFromList(code);
      console.log(`[handleDelete] 删除成功:`, result);
      loadAll();
    } catch (e) {
      console.error(`[handleDelete] 删除失败:`, e);
      const msg = `删除失败: ${e}`;
      console.error(msg);
      alert(msg);
    }
  };

  const toggleSelect = (code: string) => {
    setSelectedCodes(prev => {
      const next = new Set(prev);
      if (next.has(code)) next.delete(code); else next.add(code);
      return next;
    });
  };

  const toggleSelectAll = () => {
    if (selectedCodes.size === stockList.length) {
      setSelectedCodes(new Set());
    } else {
      setSelectedCodes(new Set(stockList.map(s => s.code)));
    }
  };

  // 按行业批量选择 / 取消：若本行业全部已选则取消，否则补齐
  const toggleSelectIndustry = (industry: string) => {
    const codes = (grouped[industry] || []).map(s => s.code);
    if (codes.length === 0) return;
    const allSelected = codes.every(c => selectedCodes.has(c));
    setSelectedCodes(prev => {
      const next = new Set(prev);
      if (allSelected) {
        codes.forEach(c => next.delete(c));
      } else {
        codes.forEach(c => next.add(c));
      }
      return next;
    });
  };

  // 行业级批量删除
  // - selectedOnly=true:  只删本行业已选股票（点击按钮时本行业有勾选）
  // - selectedOnly=false: 删本行业全部股票（无勾选时）
  const handleBatchDeleteIndustry = (industry: string, codes: string[], count: number, selectedOnly: boolean) => {
    if (codes.length === 0) { alert("该行业没有股票"); return; }
    const verb = selectedOnly ? "已选" : "全部";
    setConfirmDialog({
      title: selectedOnly ? "删除本行业已选" : "删除本行业",
      message: `确定要删除「${industry}」行业的${verb} ${count} 只股票吗？此操作不可撤销。`,
      onConfirm: async () => {
        setConfirmDialog(null);
        try {
          const r = await batchRemoveStocks(codes);
          console.log("[batchDeleteIndustry] success:", r);
          alert(r);
          // 清理可能已失效的勾选
          setSelectedCodes(prev => {
            const next = new Set(prev);
            codes.forEach(c => next.delete(c));
            return next;
          });
          loadAll();
        } catch (e) {
          console.error("[batchDeleteIndustry] error:", e);
          alert(`删除失败: ${e}`);
        }
      },
    });
  };

  const handleBatchDelete = () => {
    if (selectedCodes.size === 0) { alert("请先勾选要删除的股票"); return; }
    const codes = Array.from(selectedCodes);
    setConfirmDialog({
      title: "批量删除",
      message: `确定要删除已勾选的 ${codes.length} 只股票吗？此操作不可撤销。`,
      onConfirm: async () => {
        setConfirmDialog(null);
        try {
          const r = await batchRemoveStocks(codes);
          console.log("[batchDelete] success:", r);
          alert(r);
          setSelectedCodes(new Set());
          loadAll();
        } catch (e) {
          console.error("[batchDelete] error:", e);
          alert(`批量删除失败: ${e}`);
        }
      },
    });
  };

  const handleBatchImport = async () => {
    if (!batchImportText.trim()) { setBatchImportMsg("请输入股票数据"); return; }
    const lines = batchImportText.trim().split("\n").map(l => l.trim()).filter(Boolean);
    const stocks: { code: string; name: string; industry: string }[] = [];
    for (const line of lines) {
      const parts = line.split(/[\t,，\s]+/).filter(Boolean);
      if (parts.length >= 1) {
        stocks.push({
          code: parts[0].trim(),
          name: parts[1]?.trim() || parts[0].trim(),
          industry: parts[2]?.trim() || "其他",
        });
      }
    }
    if (stocks.length === 0) { setBatchImportMsg("未能解析有效的股票数据"); return; }
    try {
      const r = await batchAddStocks(stocks);
      alert(r);
      setShowBatchImport(false);
      setBatchImportText("");
      setBatchImportMsg("");
      loadAll();
    } catch (e) { alert(`导入失败: ${e}`); }
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
          <button onClick={() => setShowBatchImport(!showBatchImport)} style={{
            padding: "8px 16px", background: "#fff", color: "#8b5cf6",
            border: "1px solid #8b5cf6", borderRadius: 8, cursor: "pointer",
            fontSize: 12, fontWeight: 500,
          }}>
            📥 批量导入
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

      {showBatchImport && (
        <div style={{
          background: "#fff", borderRadius: 10, padding: 16, marginBottom: 16,
          boxShadow: "0 1px 4px rgba(0,0,0,0.1)",
        }}>
          <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 8 }}>批量导入股票</div>
          <div style={{ fontSize: 11, color: "var(--text-secondary)", marginBottom: 8 }}>
            每行一只股票，格式：代码 名称 行业（用空格或 Tab 分隔），行业可选
          </div>
          <textarea value={batchImportText} onChange={e => setBatchImportText(e.target.value)}
            placeholder={"300750 宁德时代 新能源\n000858 五粮液 白酒\n600519 贵州茅台 白酒"}
            style={{ ...inputStyle, width: "100%", minHeight: 100, resize: "vertical", fontFamily: "monospace", fontSize: 12 }}
          />
          <div style={{ display: "flex", gap: 8, marginTop: 8, alignItems: "center" }}>
            <button onClick={handleBatchImport} style={{ padding: "7px 16px", background: "#8b5cf6", color: "#fff", border: "none", borderRadius: 6, cursor: "pointer", fontSize: 12 }}>确认导入</button>
            <button onClick={() => { setShowBatchImport(false); setBatchImportText(""); setBatchImportMsg(""); }} style={{ padding: "7px 16px", background: "#fff", color: "#666", border: "1px solid var(--border)", borderRadius: 6, cursor: "pointer", fontSize: 12 }}>取消</button>
            {batchImportMsg && <span style={{ fontSize: 12, color: "var(--text-secondary)" }}>{batchImportMsg}</span>}
          </div>
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

      <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 10, alignItems: "center" }}>
        <span style={{ fontSize: 12, color: "var(--text-secondary)" }}>
          {stockList.length} 只股票
          {selectedCodes.size > 0 && (
            <span style={{ marginLeft: 8, color: "var(--primary)" }}>已选 {selectedCodes.size} 只</span>
          )}
        </span>
        <div style={{ display: "flex", gap: 6 }}>
          {selectedCodes.size > 0 && (
            <button onClick={handleBatchDelete} style={{ padding: "4px 12px", fontSize: 11, border: "1px solid #ef4444", borderRadius: 4, background: "#fef2f2", color: "#ef4444", cursor: "pointer", fontWeight: 500 }}>
              批量删除 ({selectedCodes.size})
            </button>
          )}
          <button onClick={expandAll} style={{ padding: "4px 12px", fontSize: 11, border: "1px solid var(--border)", borderRadius: 4, background: "#fff", cursor: "pointer" }}>展开全部</button>
          <button onClick={collapseAll} style={{ padding: "4px 12px", fontSize: 11, border: "1px solid var(--border)", borderRadius: 4, background: "#fff", cursor: "pointer" }}>折叠全部</button>
        </div>
      </div>

      {industryKeys.map((industry) => {
        const stocks = grouped[industry];
        const isOpen = expanded?.[industry] === true;
        const upCount = stocks.filter(s => s.change_pct > 0).length;
        const downCount = stocks.filter(s => s.change_pct < 0).length;
        const codes = stocks.map(s => s.code);
        // 本行业是否全部已选（用于"批量选"按钮文字切换）
        const industryAllSelected = codes.length > 0 && codes.every(c => selectedCodes.has(c));
        // 本行业已选数量（用于"删除"按钮文案/语义切换）
        const industrySelectedCount = codes.filter(c => selectedCodes.has(c)).length;

        return (
          <div key={industry} style={{ background: "#fff", borderRadius: 10, boxShadow: "0 1px 3px rgba(0,0,0,0.08)", marginBottom: 10, overflow: "hidden" }}>
            <div onClick={() => toggleIndustry(industry)} style={{ display: "flex", alignItems: "center", padding: "12px 16px", cursor: "pointer", userSelect: "none", borderBottom: isOpen ? "1px solid var(--border)" : "none", }}>
              <span style={{ marginRight: 8, fontSize: 14, transition: "transform 0.2s", transform: isOpen ? "rotate(90deg)" : "rotate(0deg)" }}>▶</span>
              <span style={{ fontWeight: 600, fontSize: 14, flex: 1 }}>{industry}</span>
              <span style={{ fontSize: 12, color: "var(--text-secondary)", marginRight: 10 }}>{stocks.length} 只</span>
              <span style={{ fontSize: 12, color: "var(--up)", marginRight: 8 }}>涨{upCount}</span>
              <span style={{ fontSize: 12, color: "var(--down)", marginRight: 12 }}>跌{downCount}</span>
              <span
                onClick={e => { e.stopPropagation(); toggleSelectIndustry(industry); }}
                style={{ fontSize: 11, color: industryAllSelected ? "var(--primary)" : "var(--text-secondary)", cursor: "pointer", padding: "2px 8px", borderRadius: 4, border: "1px solid " + (industryAllSelected ? "var(--primary)" : "var(--border)"), background: industryAllSelected ? "#eff6ff" : "#fff", marginRight: 6 }}
                title={industryAllSelected ? "取消选中本行业全部股票" : "选中本行业全部股票"}
              >
                {industryAllSelected ? "✓ 已选" : "☐ 批量选"}
              </span>
              <span
                onClick={e => {
                  e.stopPropagation();
                  // 行业级删除按钮：有已选时只删已选，否则删该行业全部
                  if (industrySelectedCount > 0) {
                    handleBatchDeleteIndustry(
                      industry,
                      codes.filter(c => selectedCodes.has(c)),
                      industrySelectedCount,
                      true
                    );
                  } else {
                    handleBatchDeleteIndustry(industry, codes, codes.length, false);
                  }
                }}
                style={{ fontSize: 11, color: "#ef4444", cursor: "pointer", textDecoration: "underline", padding: "2px 6px", borderRadius: 4, background: industrySelectedCount > 0 ? "#fee2e2" : "#fef2f2" }}
                title={industrySelectedCount > 0 ? `删除本行业已选的 ${industrySelectedCount} 只股票` : `删除本行业全部 ${codes.length} 只股票`}
              >
                {industrySelectedCount > 0 ? `删除已选 (${industrySelectedCount})` : `删除本行业`}
              </span>
            </div>
            {isOpen && (
              <table style={{ width: "100%", borderCollapse: "collapse" }}>
                <thead><tr style={{ background: "#f8f9fa" }}>
                  {["", "代码", "名称", "子行业", "现价", "涨跌幅", "评分", "建议", "风险", "操作"].map((h, i) => (
                    <th key={i} style={{ padding: "7px 4px", borderBottom: "2px solid var(--border)", fontSize: 11, fontWeight: 600, color: "var(--text-secondary)", textAlign: "left" }}>
                      {i === 0 ? <input type="checkbox" checked={selectedCodes.size === stockList.length && stockList.length > 0} onChange={toggleSelectAll} style={{ cursor: "pointer" }} /> : h}
                    </th>
                  ))}
                </tr></thead>
                <tbody>
                  {stocks.map(s => (
                    <Fragment key={s.code}>
                      <tr onClick={() => handleSelect(s.code)} style={{ borderBottom: "1px solid #f0f0f0", cursor: "pointer", background: selected === s.code ? "#f0f7ff" : "transparent", fontSize: 13 }}>
                        <td style={{ padding: "6px 4px", width: 30 }} onClick={e => e.stopPropagation()}>
                          <input type="checkbox" checked={selectedCodes.has(s.code)} onChange={() => toggleSelect(s.code)} style={{ cursor: "pointer" }} />
                        </td>
                        <td style={{ padding: "6px 4px", fontFamily: "monospace" }}>{s.code}</td>
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
                        <tr><td colSpan={10} style={{ padding: 0 }}>
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

      {confirmDialog && (
        <div
          onClick={() => setConfirmDialog(null)}
          style={{
            position: "fixed", inset: 0, background: "rgba(0,0,0,0.4)",
            display: "flex", alignItems: "center", justifyContent: "center", zIndex: 9999,
          }}
        >
          <div
            onClick={e => e.stopPropagation()}
            style={{
              background: "#fff", borderRadius: 10, padding: 24, minWidth: 360, maxWidth: 480,
              boxShadow: "0 10px 30px rgba(0,0,0,0.2)",
            }}
          >
            <div style={{ fontSize: 15, fontWeight: 600, marginBottom: 10 }}>{confirmDialog.title}</div>
            <div style={{ fontSize: 13, color: "var(--text-secondary)", marginBottom: 20, lineHeight: 1.6 }}>
              {confirmDialog.message}
            </div>
            <div style={{ display: "flex", gap: 8, justifyContent: "flex-end" }}>
              <button
                onClick={() => setConfirmDialog(null)}
                style={{ padding: "7px 18px", background: "#fff", color: "#666", border: "1px solid var(--border)", borderRadius: 6, cursor: "pointer", fontSize: 12 }}
              >取消</button>
              <button
                onClick={confirmDialog.onConfirm}
                style={{ padding: "7px 18px", background: "#ef4444", color: "#fff", border: "none", borderRadius: 6, cursor: "pointer", fontSize: 12, fontWeight: 500 }}
              >确认删除</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}