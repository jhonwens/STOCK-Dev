import { useState, useEffect } from "react";
import { saveLlmConfig, loadLlmConfig } from "../services/api";

function maskKey(key: string): string {
  if (!key || key.length < 8) return "****";
  return key.slice(0, 4) + "****" + key.slice(-4);
}

interface LlmConfig {
  api_base?: string;
  api_key?: string;
  model?: string;
  temperature?: number;
}

export default function Settings() {
  const [apiUrl, setApiUrl] = useState("");
  const [apiKey, setApiKey] = useState("");
  const [model, setModel] = useState("");
  const [temperature, setTemperature] = useState(0.7);
  const [status, setStatus] = useState("");
  const [loadedConfig, setLoadedConfig] = useState<LlmConfig | null>(null);

  useEffect(() => {
    loadLlmConfig().then(raw => {
      if (!raw || raw === "{}") return;
      try {
        const cfg: LlmConfig = JSON.parse(raw);
        setLoadedConfig(cfg);
        if (cfg.api_base) setApiUrl(cfg.api_base);
        if (cfg.api_key) setApiKey(cfg.api_key);
        if (cfg.model) setModel(cfg.model);
        if (cfg.temperature !== undefined) setTemperature(cfg.temperature);
      } catch { /* ignore */ }
    }).catch(() => {});
  }, []);

  const handleTest = async () => {
    if (!apiKey) { setStatus("⚠️ 请先输入 API Key"); return; }
    setStatus("⏳ 测试连接中...");
    try {
      const res = await fetch(`${apiUrl}/chat/completions`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${apiKey}`,
        },
        body: JSON.stringify({
          model,
          messages: [{ role: "user", content: "你好，回复OK表示连接成功" }],
          max_tokens: 10,
        }),
      });
      if (res.ok) {
        setStatus("✅ 连接成功！LLM 服务正常");
      } else {
        const err = await res.text();
        setStatus(`❌ 连接失败: ${err.slice(0, 100)}`);
      }
    } catch {
      setStatus("❌ 连接失败: 网络错误或 API 地址不正确");
    }
  };

  const handleSave = async () => {
    if (!apiKey) { setStatus("⚠️ 请先输入 API Key"); return; }
    setStatus("⏳ 保存中...");
    try {
      const result = await saveLlmConfig(apiUrl, apiKey, model, temperature);
      setStatus(result);
      setLoadedConfig({ api_base: apiUrl, api_key: apiKey, model, temperature });
    } catch (e) {
      setStatus(`❌ 保存失败: ${e}`);
    }
  };

  const card = { background: "#fff", borderRadius: 12, padding: 20, boxShadow: "0 1px 3px rgba(0,0,0,0.1)" };
  const label = { display: "block", fontSize: 13, fontWeight: 500, marginBottom: 4 };
  const input = { width: "100%", padding: "8px 12px", border: "1px solid var(--border)", borderRadius: 6, fontSize: 13, outline: "none" as const };

  return (
    <div>
      <h2 style={{ fontSize: 22, fontWeight: 700, marginBottom: 24 }}>⚙️ 设置管理</h2>

      <div style={{ display: "flex", flexDirection: "column", gap: 16, maxWidth: 600 }}>
        {/* 当前配置信息 */}
        {loadedConfig && (
          <div style={{ ...card, padding: 16, background: "#fafbfc", border: "1px solid #e0e0e0" }}>
            <h3 style={{ fontSize: 14, fontWeight: 600, marginBottom: 10, color: "var(--text-secondary)" }}>📌 当前已配置的模型</h3>
            <div style={{ display: "flex", gap: 20, flexWrap: "wrap" }}>
              <div>
                <span style={{ fontSize: 11, color: "var(--text-secondary)" }}>模型</span>
                <div style={{ fontSize: 14, fontWeight: 600 }}>{(loadedConfig.api_base || "").includes("dashscope") ? "通义千问" : (loadedConfig.api_base || "").includes("deepseek") ? "DeepSeek" : "自定义"}</div>
              </div>
              <div>
                <span style={{ fontSize: 11, color: "var(--text-secondary)" }}>模型名称</span>
                <div style={{ fontSize: 14, fontWeight: 600, fontFamily: "monospace" }}>{loadedConfig.model || "-"}</div>
              </div>
              <div>
                <span style={{ fontSize: 11, color: "var(--text-secondary)" }}>Temperature</span>
                <div style={{ fontSize: 14, fontWeight: 600 }}>{loadedConfig.temperature ?? 0.7}</div>
              </div>
              <div>
                <span style={{ fontSize: 11, color: "var(--text-secondary)" }}>API Key</span>
                <div style={{ fontSize: 14, fontWeight: 600, fontFamily: "monospace" }}>{maskKey(loadedConfig.api_key || "")}</div>
              </div>
            </div>
          </div>
        )}

        <div style={card}>
          <h3 style={{ fontSize: 16, fontWeight: 600, marginBottom: 12 }}>🤖 LLM 配置</h3>
          <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
            <div>
              <label style={label}>API Base URL</label>
              <input value={apiUrl} onChange={(e) => setApiUrl(e.target.value)} style={input} />
            </div>
            <div>
              <label style={label}>API Key</label>
              <input type="password" value={apiKey} onChange={(e) => setApiKey(e.target.value)} style={input} />
            </div>
            <div style={{ display: "flex", gap: 12 }}>
              <div style={{ flex: 1 }}>
                <label style={label}>模型名称</label>
                <input value={model} onChange={(e) => setModel(e.target.value)} style={input} />
              </div>
              <div style={{ flex: 1 }}>
                <label style={label}>Temperature: {temperature}</label>
                <input type="range" min="0" max="1" step="0.1" value={temperature} onChange={(e) => setTemperature(parseFloat(e.target.value))} style={{ width: "100%" }} />
              </div>
            </div>
            {status && (
              <div style={{ padding: "8px 12px", borderRadius: 6, fontSize: 13, background: status.startsWith("✅") ? "#e8f5e9" : status.startsWith("❌") ? "#fef2f2" : status.startsWith("⚠️") ? "#fff3cd" : "#e8f0fe" }}>
                {status}
              </div>
            )}
            <div style={{ display: "flex", gap: 8, justifyContent: "flex-end", marginTop: 8 }}>
              <button onClick={handleTest} style={{ padding: "8px 16px", background: "#fff", border: "1px solid var(--border)", borderRadius: 6, cursor: "pointer", fontSize: 13 }}>
                测试连接
              </button>
              <button onClick={handleSave} style={{ padding: "8px 16px", background: "var(--primary)", color: "#fff", border: "none", borderRadius: 6, cursor: "pointer", fontSize: 13 }}>
                保存
              </button>
            </div>
          </div>
        </div>

        <div style={card}>
          <h3 style={{ fontSize: 16, fontWeight: 600, marginBottom: 12 }}>📂 股票池管理</h3>
          <p style={{ fontSize: 13, color: "var(--text-secondary)" }}>添加、编辑或删除持仓股和候选股。在后续迭代中实现完整的 CRUD 界面。</p>
        </div>
      </div>
    </div>
  );
}