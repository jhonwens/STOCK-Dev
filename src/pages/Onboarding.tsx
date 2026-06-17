import { useState } from "react";

interface Props {
  onComplete: () => void;
}

const STEPS = [
  { title: "欢迎使用衡势价值", desc: "AI 驱动的中长线价值投资助手", icon: "⚖️" },
  { title: "4 大核心功能", desc: "📊 股票池概览  📁 持仓分析  🎯 候选推荐  📈 个股分析", icon: "🎯" },
  { title: "AI 分析需要配置", desc: "前往「设置」页配置您的 LLM API Key（通义千问 / DeepSeek 等）", icon: "🤖" },
  { title: "开始体验", desc: "开发期默认 Pro 等级，所有功能可用。\n正式发布后请激活会员以解锁完整服务。", icon: "🚀" },
];

export default function Onboarding({ onComplete }: Props) {
  const [step, setStep] = useState(0);
  const current = STEPS[step];
  const isLast = step === STEPS.length - 1;

  return (
    <div style={{
      position: "fixed", inset: 0, background: "linear-gradient(135deg, #1a1e2e, #2a2f4a)",
      display: "flex", alignItems: "center", justifyContent: "center", zIndex: 9999,
    }}>
      <div style={{
        background: "#fff", borderRadius: 20, padding: 40,
        maxWidth: 480, width: "90%", textAlign: "center",
        boxShadow: "0 20px 60px rgba(0,0,0,0.4)",
      }}>
        <div style={{ fontSize: 64, marginBottom: 16 }}>{current.icon}</div>
        <div style={{ fontSize: 24, fontWeight: 700, marginBottom: 10, color: "#333" }}>
          {current.title}
        </div>
        <div style={{ fontSize: 14, color: "#666", lineHeight: 1.7, whiteSpace: "pre-line", minHeight: 60 }}>
          {current.desc}
        </div>

        <div style={{ display: "flex", justifyContent: "center", gap: 6, margin: "24px 0" }}>
          {STEPS.map((_, i) => (
            <div key={i} style={{
              width: i === step ? 24 : 8, height: 8, borderRadius: 4,
              background: i === step ? "linear-gradient(135deg, #5b8def, #7c5cfc)" : "#e0e0e0",
              transition: "all 0.3s",
            }} />
          ))}
        </div>

        <div style={{ display: "flex", gap: 10 }}>
          {step > 0 && (
            <button onClick={() => setStep(step - 1)} style={{
              flex: 1, padding: "12px 0", border: "1px solid #e0e0e0",
              borderRadius: 10, background: "#fff", cursor: "pointer", fontSize: 13,
            }}>上一步</button>
          )}
          <button onClick={() => {
            if (isLast) onComplete();
            else setStep(step + 1);
          }} style={{
            flex: 1, padding: "12px 0", border: "none", borderRadius: 10,
            background: "linear-gradient(135deg, #5b8def, #7c5cfc)",
            color: "#fff", cursor: "pointer", fontSize: 13, fontWeight: 600,
          }}>
            {isLast ? "开始体验" : "下一步"}
          </button>
        </div>

        {!isLast && (
          <button onClick={onComplete} style={{
            marginTop: 12, padding: "6px 16px", border: "none",
            background: "transparent", color: "#999", cursor: "pointer", fontSize: 12,
          }}>跳过引导</button>
        )}
      </div>
    </div>
  );
}
