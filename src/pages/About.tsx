import { useEffect, useState } from "react";
import { getFeatureFlags } from "../services/feature_flag";

interface AppInfo {
  version: string;
  tier: string;
  is_licensed: boolean;
}

export default function About() {
  const [info, setInfo] = useState<AppInfo | null>(null);

  useEffect(() => {
    getFeatureFlags().then(f => setInfo({
      version: "1.0.0",
      tier: f.tier,
      is_licensed: f.is_licensed,
    }));
  }, []);

  return (
    <div style={{ maxWidth: 720, margin: "0 auto" }}>
      <h2 style={{ fontSize: 22, fontWeight: 700, marginBottom: 20 }}>ℹ️ 关于</h2>

      <div style={{
        background: "linear-gradient(135deg, #1a1e2e, #2a2f4a)",
        color: "#fff", borderRadius: 16, padding: 32, marginBottom: 20,
        textAlign: "center",
      }}>
        <img
          src="/src/assets/logo-128.png"
          alt="衡势价值"
          style={{ width: 80, height: 80, borderRadius: 18, marginBottom: 12, boxShadow: "0 4px 12px rgba(0,0,0,0.3)" }}
        />
        <div style={{ fontSize: 24, fontWeight: 700, letterSpacing: 1 }}>衡势价值</div>
        <div style={{ fontSize: 13, color: "rgba(255,255,255,0.6)", marginTop: 4 }}>
          AI 驱动的中长线价值投资助手
        </div>
      </div>

      <div style={{
        background: "#fff", borderRadius: 12, padding: 20, marginBottom: 16,
        boxShadow: "0 1px 3px rgba(0,0,0,0.08)",
      }}>
        <div style={{ fontSize: 14, fontWeight: 600, marginBottom: 12 }}>📦 产品信息</div>
        <Row label="产品名称" value="衡势价值 / HengShi Value" />
        <Row label="当前版本" value={info?.version || "v1.0.0"} />
        <Row label="构建日期" value="2026-06-17" />
        <Row label="技术栈" value="Tauri 2 + React 19 + Rust + Python" />
        <Row label="会员等级" value={info?.tier.toUpperCase() || "-"} />
        <Row label="激活状态" value={info?.is_licensed ? "已激活" : "未激活（开发期默认 Pro）"} />
      </div>

      <div style={{
        background: "#fff", borderRadius: 12, padding: 20, marginBottom: 16,
        boxShadow: "0 1px 3px rgba(0,0,0,0.08)",
      }}>
        <div style={{ fontSize: 14, fontWeight: 600, marginBottom: 12 }}>📞 联系我们</div>
        <Row label="商务合作" value="contact@hengshi-value.example" />
        <Row label="问题反馈" value="feedback@hengshi-value.example" />
        <Row label="官方网站" value="https://hengshi-value.example（占位）" />
      </div>

      <div style={{
        background: "#fff", borderRadius: 12, padding: 20, marginBottom: 16,
        boxShadow: "0 1px 3px rgba(0,0,0,0.08)",
      }}>
        <div style={{ fontSize: 14, fontWeight: 600, marginBottom: 12 }}>🔄 检查更新</div>
        <button style={{
          padding: "8px 16px", border: "1px solid #e0e0e0",
          borderRadius: 8, background: "#fff", cursor: "pointer", fontSize: 12,
        }}>检查更新</button>
        <div style={{ fontSize: 11, color: "#999", marginTop: 6 }}>
          v1 暂未实装更新检查
        </div>
      </div>

      <div style={{
        background: "#f8f9fa", borderRadius: 10, padding: 14,
        textAlign: "center", color: "#999", fontSize: 11, lineHeight: 1.6,
      }}>
        © 2026 衡势价值 · 让价值被看见，让持仓更稳健
        <br />
        本产品仅供学习研究使用，不构成任何投资建议
      </div>
    </div>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div style={{
      display: "flex", padding: "6px 0",
      borderBottom: "1px solid #f0f0f0", fontSize: 13,
    }}>
      <span style={{ width: 100, color: "#888" }}>{label}</span>
      <span style={{ flex: 1, color: "#333" }}>{value}</span>
    </div>
  );
}
