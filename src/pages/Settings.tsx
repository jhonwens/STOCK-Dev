import { useState, useEffect } from "react";
import {
  loadLlmModels,
  saveLlmModel,
  deleteLlmModel,
  setActiveLlmModel,
  testLlmConnection,
} from "../services/api";

interface LlmModel {
  id: string;
  name: string;             // 用户起的别名
  provider: string;         // dashscope / deepseek / openai / custom
  api_base: string;
  api_key: string;
  model: string;
  temperature: number;
  enabled: boolean;
  created_at: string;
}

const PROVIDER_PRESETS: { label: string; base: string; defaultModel: string }[] = [
  { label: "通义千问 (DashScope)", base: "https://dashscope.aliyuncs.com/compatible-mode/v1", defaultModel: "qwen3.5-35b-a3b" },
  { label: "DeepSeek", base: "https://api.deepseek.com/v1", defaultModel: "deepseek-chat" },
  { label: "OpenAI 兼容", base: "https://api.openai.com/v1", defaultModel: "gpt-4o-mini" },
];

function maskKey(key: string): string {
  if (!key || key.length < 8) return "****";
  return key.slice(0, 4) + "****" + key.slice(-4);
}

function detectProvider(apiBase: string): string {
  const b = (apiBase || "").toLowerCase();
  if (b.includes("dashscope")) return "通义千问";
  if (b.includes("deepseek")) return "DeepSeek";
  if (b.includes("openai")) return "OpenAI";
  return "自定义";
}

function genId(): string {
  return "m_" + Math.random().toString(36).slice(2, 10) + Date.now().toString(36);
}

const card = { background: "#fff", borderRadius: 12, padding: 20, boxShadow: "0 1px 3px rgba(0,0,0,0.1)" };
const label = { display: "block", fontSize: 13, fontWeight: 500, marginBottom: 4 };
const input = { width: "100%", padding: "8px 12px", border: "1px solid var(--border)", borderRadius: 6, fontSize: 13, outline: "none" as const };

export default function Settings() {
  const [models, setModels] = useState<LlmModel[]>([]);
  const [editing, setEditing] = useState<LlmModel | null>(null);
  const [isAdding, setIsAdding] = useState(false);
  const [status, setStatus] = useState("");
  const [testing, setTesting] = useState(false);
  const [activeId, setActiveId] = useState<string | null>(null);

  useEffect(() => {
    loadLlmModels().then(raw => {
      try {
        const list: LlmModel[] = JSON.parse(raw || "[]");
        setModels(list);
        setActiveId(list.find(m => m.enabled)?.id || null);
      } catch {
        setModels([]);
      }
    }).catch(() => setModels([]));
  }, []);

  const showStatus = (msg: string) => {
    setStatus(msg);
    setTimeout(() => setStatus(""), 4000);
  };

  const handleSave = async () => {
    if (!editing) return;
    if (!editing.name.trim()) { showStatus("⚠️ 请填写模型别名"); return; }
    if (!editing.api_key) { showStatus("⚠️ 请填写 API Key"); return; }
    if (!editing.model.trim()) { showStatus("⚠️ 请填写模型名称"); return; }
    showStatus("⏳ 保存中...");
    try {
      await saveLlmModel(editing);
      const list = await loadLlmModels();
      const parsed: LlmModel[] = JSON.parse(list || "[]");
      setModels(parsed);
      setActiveId(parsed.find(m => m.enabled)?.id || null);
      setEditing(null);
      setIsAdding(false);
      showStatus("✅ 模型已保存");
    } catch (e) {
      showStatus(`❌ 保存失败: ${e}`);
    }
  };

  const handleDelete = async (id: string) => {
    if (!confirm("确定要删除此模型配置吗？")) return;
    try {
      await deleteLlmModel(id);
      const list = await loadLlmModels();
      const parsed: LlmModel[] = JSON.parse(list || "[]");
      setModels(parsed);
      setActiveId(parsed.find(m => m.enabled)?.id || null);
      showStatus("✅ 模型已删除");
    } catch (e) {
      showStatus(`❌ 删除失败: ${e}`);
    }
  };

  const handleSetActive = async (id: string) => {
    try {
      await setActiveLlmModel(id);
      const list = await loadLlmModels();
      const parsed: LlmModel[] = JSON.parse(list || "[]");
      setModels(parsed);
      setActiveId(id);
      showStatus("✅ 已切换为当前激活模型");
    } catch (e) {
      showStatus(`❌ 切换失败: ${e}`);
    }
  };

  const handleTest = async () => {
    if (!editing || !editing.api_key) { showStatus("⚠️ 请先填写 API Key"); return; }
    setTesting(true);
    showStatus("⏳ 测试连接中...");
    try {
      const res = await testLlmConnection(
        editing.api_base,
        editing.api_key,
        editing.model
      );
      showStatus(res.startsWith("✅") ? res : `❌ ${res}`);
    } catch (e) {
      showStatus(`❌ 测试失败: ${e}`);
    } finally {
      setTesting(false);
    }
  };

  const startAdd = () => {
    setEditing({
      id: genId(),
      name: "",
      provider: "通义千问",
      api_base: PROVIDER_PRESETS[0].base,
      api_key: "",
      model: PROVIDER_PRESETS[0].defaultModel,
      temperature: 0.7,
      enabled: false,
      created_at: new Date().toISOString(),
    });
    setIsAdding(true);
  };

  const startEdit = (m: LlmModel) => {
    setEditing({ ...m });
    setIsAdding(false);
  };

  const onProviderChange = (preset: string) => {
    if (!editing) return;
    const p = PROVIDER_PRESETS.find(x => x.label === preset);
    setEditing({
      ...editing,
      provider: preset,
      api_base: p?.base || editing.api_base,
      model: p?.defaultModel || editing.model,
    });
  };

  return (
    <div>
      <h2 style={{ fontSize: 22, fontWeight: 700, marginBottom: 24 }}>⚙️ 设置管理</h2>

      <div style={{ display: "flex", flexDirection: "column", gap: 16, maxWidth: 760 }}>
        {/* 多模型管理卡片 */}
        <div style={card}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
            <h3 style={{ fontSize: 16, fontWeight: 600 }}>🤖 LLM 模型管理</h3>
            <button
              onClick={startAdd}
              style={{ padding: "6px 14px", background: "var(--primary)", color: "#fff", border: "none", borderRadius: 6, cursor: "pointer", fontSize: 13 }}
            >
              + 添加模型
            </button>
          </div>

          {/* 当前激活模型提示 */}
          {activeId && (
            <div style={{
              padding: "8px 14px", marginBottom: 12, background: "#f0f9ff",
              border: "1px solid #bae6fd", borderRadius: 8, fontSize: 12, color: "#0369a1",
            }}>
              📌 当前激活：
              <strong>{models.find(m => m.id === activeId)?.name || "-"}</strong>
              （{models.find(m => m.id === activeId)?.model}）
            </div>
          )}

          {/* 模型列表 */}
          {models.length === 0 && !editing ? (
            <div style={{ padding: 24, textAlign: "center", color: "var(--text-secondary)", fontSize: 13, background: "#fafbfc", borderRadius: 8 }}>
              尚未配置任何模型，点击右上角"+ 添加模型"开始
            </div>
          ) : (
            <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
              {models.map(m => (
                <div
                  key={m.id}
                  style={{
                    display: "flex", alignItems: "center", gap: 12,
                    padding: 12,
                    background: m.id === activeId ? "#f0f9ff" : "#fafbfc",
                    border: m.id === activeId ? "1px solid #bae6fd" : "1px solid #e5e7eb",
                    borderRadius: 8,
                  }}
                >
                  <div style={{ flex: 1 }}>
                    <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                      <span style={{ fontSize: 14, fontWeight: 600 }}>{m.name}</span>
                      {m.id === activeId && (
                        <span style={{
                          fontSize: 10, padding: "2px 8px", background: "#0ea5e9",
                          color: "#fff", borderRadius: 10, fontWeight: 600,
                        }}>
                          激活中
                        </span>
                      )}
                      <span style={{ fontSize: 11, color: "var(--text-secondary)" }}>
                        {detectProvider(m.api_base)}
                      </span>
                    </div>
                    <div style={{ fontSize: 12, color: "var(--text-secondary)", marginTop: 2, fontFamily: "monospace" }}>
                      {m.model} · temp={m.temperature} · key={maskKey(m.api_key)}
                    </div>
                  </div>
                  <div style={{ display: "flex", gap: 6 }}>
                    {m.id !== activeId && (
                      <button
                        onClick={() => handleSetActive(m.id)}
                        style={{ padding: "4px 10px", fontSize: 12, background: "#fff", border: "1px solid var(--border)", borderRadius: 4, cursor: "pointer" }}
                      >
                        启用
                      </button>
                    )}
                    <button
                      onClick={() => startEdit(m)}
                      style={{ padding: "4px 10px", fontSize: 12, background: "#fff", border: "1px solid var(--border)", borderRadius: 4, cursor: "pointer" }}
                    >
                      编辑
                    </button>
                    <button
                      onClick={() => handleDelete(m.id)}
                      style={{ padding: "4px 10px", fontSize: 12, background: "#fff", border: "1px solid #fecaca", color: "#dc2626", borderRadius: 4, cursor: "pointer" }}
                    >
                      删除
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* 编辑表单 */}
          {editing && (
            <div style={{ marginTop: 16, padding: 16, background: "#f9fafb", borderRadius: 8, border: "1px solid #e5e7eb" }}>
              <div style={{ fontSize: 14, fontWeight: 600, marginBottom: 12 }}>
                {isAdding ? "➕ 添加新模型" : "✏️ 编辑模型"}
              </div>
              <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
                <div>
                  <label style={label}>模型别名（便于识别）</label>
                  <input
                    value={editing.name}
                    onChange={e => setEditing({ ...editing, name: e.target.value })}
                    style={input}
                    placeholder="例如：通义千问主用"
                  />
                </div>
                <div>
                  <label style={label}>服务商（快速填充）</label>
                  <select
                    value={editing.provider}
                    onChange={e => onProviderChange(e.target.value)}
                    style={input}
                  >
                    {PROVIDER_PRESETS.map(p => (
                      <option key={p.label} value={p.label}>{p.label}</option>
                    ))}
                    <option value="自定义">自定义</option>
                  </select>
                </div>
                <div>
                  <label style={label}>API Base URL</label>
                  <input
                    value={editing.api_base}
                    onChange={e => setEditing({ ...editing, api_base: e.target.value })}
                    style={input}
                  />
                </div>
                <div>
                  <label style={label}>API Key</label>
                  <input
                    type="password"
                    value={editing.api_key}
                    onChange={e => setEditing({ ...editing, api_key: e.target.value })}
                    style={input}
                    placeholder="sk-..."
                  />
                </div>
                <div style={{ display: "flex", gap: 12 }}>
                  <div style={{ flex: 1 }}>
                    <label style={label}>模型名称</label>
                    <input
                      value={editing.model}
                      onChange={e => setEditing({ ...editing, model: e.target.value })}
                      style={input}
                    />
                  </div>
                  <div style={{ flex: 1 }}>
                    <label style={label}>Temperature: {editing.temperature}</label>
                    <input
                      type="range" min="0" max="1" step="0.1"
                      value={editing.temperature}
                      onChange={e => setEditing({ ...editing, temperature: parseFloat(e.target.value) })}
                      style={{ width: "100%" }}
                    />
                  </div>
                </div>

                {status && (
                  <div style={{
                    padding: "8px 12px", borderRadius: 6, fontSize: 13,
                    background: status.startsWith("✅") ? "#e8f5e9" : status.startsWith("❌") ? "#fef2f2" : status.startsWith("⚠️") ? "#fff3cd" : "#e8f0fe",
                  }}>
                    {status}
                  </div>
                )}

                <div style={{ display: "flex", gap: 8, justifyContent: "flex-end", marginTop: 4 }}>
                  <button
                    onClick={() => { setEditing(null); setIsAdding(false); setStatus(""); }}
                    style={{ padding: "8px 16px", background: "#fff", border: "1px solid var(--border)", borderRadius: 6, cursor: "pointer", fontSize: 13 }}
                  >
                    取消
                  </button>
                  <button
                    onClick={handleTest} disabled={testing}
                    style={{ padding: "8px 16px", background: "#fff", border: "1px solid var(--border)", borderRadius: 6, cursor: "pointer", fontSize: 13 }}
                  >
                    {testing ? "测试中..." : "测试连接"}
                  </button>
                  <button
                    onClick={handleSave}
                    style={{ padding: "8px 16px", background: "var(--primary)", color: "#fff", border: "none", borderRadius: 6, cursor: "pointer", fontSize: 13 }}
                  >
                    保存
                  </button>
                </div>
              </div>
            </div>
          )}

          {/* 全局状态条（不在编辑时） */}
          {!editing && status && (
            <div style={{
              marginTop: 12, padding: "8px 12px", borderRadius: 6, fontSize: 13,
              background: status.startsWith("✅") ? "#e8f5e9" : "#fef2f2",
            }}>
              {status}
            </div>
          )}
        </div>

        {/* 帮助说明 */}
        <div style={{ ...card, background: "#fafbfc", padding: 14 }}>
          <div style={{ fontSize: 12, color: "var(--text-secondary)", lineHeight: 1.6 }}>
            💡 <strong>使用说明</strong>：可以配置多个不同服务商的 LLM 模型（如同时配置通义千问 + DeepSeek），
            通过点击列表中"启用"按钮切换当前激活模型。所有 AI 分析（持仓、候选、个股）将使用当前激活的模型调用。
          </div>
        </div>
      </div>
    </div>
  );
}
