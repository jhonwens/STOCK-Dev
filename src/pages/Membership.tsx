import { useState, useEffect } from "react";
import {
  getFeatureFlags, clearFeatureFlagCache,
} from "../services/feature_flag";
import { activateLicense, deactivateLicense } from "../services/license";
import type { FeatureFlags, TierId, TierDef } from "../types";

const TIER_META: Record<TierId, { name: string; color: string }> = {
  free: { name: "免费版", color: "#888" },
  pro: { name: "专业版", color: "#16a34a" },
  vip: { name: "至尊版", color: "#7c5cfc" },
};

const TIER_LIST: TierDef[] = [
  { id: "free", name: "免费版", price_monthly: 0, price_yearly: 0,
    features: ["持仓 ≤ 5 只", "自选股 ≤ 10 只", "基础 AI 分析", "MD 导出受限"] },
  { id: "pro", name: "专业版", price_monthly: 39, price_yearly: 399,
    features: ["持仓 ≤ 50 只", "自选股 ≤ 100 只", "完整 AI 分析", "MD 报告导出", "12 维深度分析"] },
  { id: "vip", name: "至尊版", price_monthly: 99, price_yearly: 999,
    features: ["持仓/自选股不限", "全部 Pro 权益", "自定义策略", "高频预警"] },
];

export default function Membership() {
  const [flags, setFlags] = useState<FeatureFlags | null>(null);
  const [key, setKey] = useState("");
  const [status, setStatus] = useState("");

  const reload = async () => {
    clearFeatureFlagCache();
    const f = await getFeatureFlags();
    setFlags(f);
  };

  useEffect(() => { reload(); }, []);

  const handleActivate = async () => {
    if (!key.trim()) { setStatus("⚠️ 请输入激活码"); return; }
    setStatus("⏳ 激活中...");
    try {
      const info = await activateLicense(key.trim());
      setStatus(`✅ 激活成功！当前等级：${TIER_META[info.tier as TierId]?.name || info.tier}`);
      setKey("");
      await reload();
    } catch (e) {
      setStatus(`❌ 激活失败: ${e}`);
    }
  };

  const handleDeactivate = async () => {
    if (!confirm("确定要退出会员？将降级为免费版。")) return;
    try {
      await deactivateLicense();
      setStatus("✅ 已退出会员");
      await reload();
    } catch (e) {
      setStatus(`❌ 操作失败: ${e}`);
    }
  };

  if (!flags) return <div style={{ padding: 40, textAlign: "center", color: "#888" }}>加载中...</div>;

  const meta = TIER_META[flags.tier as TierId];
  const lic = flags.license;

  return (
    <div style={{ maxWidth: 960, margin: "0 auto" }}>
      <h2 style={{ fontSize: 22, fontWeight: 700, marginBottom: 20 }}>👤 会员中心</h2>

      {/* 当前状态卡片 */}
      <div style={{
        background: `linear-gradient(135deg, ${meta.color}15, ${meta.color}05)`,
        border: `1px solid ${meta.color}30`,
        borderRadius: 14, padding: 24, marginBottom: 20,
      }}>
        <div style={{ display: "flex", alignItems: "center", gap: 16, flexWrap: "wrap" }}>
          <div style={{
            width: 64, height: 64, borderRadius: 16,
            background: `linear-gradient(135deg, ${meta.color}, ${meta.color}aa)`,
            display: "flex", alignItems: "center", justifyContent: "center",
            fontSize: 32, color: "#fff", fontWeight: 700,
          }}>
            ⚖️
          </div>
          <div style={{ flex: 1, minWidth: 200 }}>
            <div style={{ fontSize: 14, color: "#666" }}>当前会员等级</div>
            <div style={{ fontSize: 26, fontWeight: 700, color: meta.color, marginTop: 2 }}>
              {meta.name}
            </div>
            {lic ? (
              <div style={{ fontSize: 12, color: "#888", marginTop: 4 }}>
                到期时间：{lic.expired_at} · 设备：{lic.device_id}
              </div>
            ) : (
              <div style={{ fontSize: 12, color: "#888", marginTop: 4 }}>
                未激活 · 当前为开发期默认 Pro
              </div>
            )}
          </div>
          {lic && (
            <button onClick={handleDeactivate} style={{
              padding: "8px 16px", background: "#fff", border: "1px solid #e0e0e0",
              borderRadius: 8, cursor: "pointer", fontSize: 12, color: "#666",
            }}>退出会员</button>
          )}
        </div>
      </div>

      {/* 激活码输入 */}
      <div style={{
        background: "#fff", borderRadius: 12, padding: 20, marginBottom: 20,
        boxShadow: "0 1px 3px rgba(0,0,0,0.08)",
      }}>
        <div style={{ fontSize: 14, fontWeight: 600, marginBottom: 10 }}>🔑 激活码兑换</div>
        <div style={{ display: "flex", gap: 10 }}>
          <input
            value={key}
            onChange={e => setKey(e.target.value)}
            placeholder="HSP-PRO-XXXX-XXXX-XXXX-XXXX"
            style={{
              flex: 1, padding: "10px 14px", border: "1px solid #e0e0e0",
              borderRadius: 8, fontSize: 13, fontFamily: "monospace", outline: "none",
            }}
          />
          <button onClick={handleActivate} style={{
            padding: "10px 24px", border: "none", borderRadius: 8,
            background: "linear-gradient(135deg, #5b8def, #7c5cfc)",
            color: "#fff", cursor: "pointer", fontSize: 13, fontWeight: 600,
          }}>立即激活</button>
        </div>
        {status && (
          <div style={{ marginTop: 10, fontSize: 12, color: status.startsWith("✅") ? "#16a34a" : status.startsWith("❌") ? "#dc2626" : "#666" }}>
            {status}
          </div>
        )}
        <div style={{ marginTop: 10, fontSize: 11, color: "#999" }}>
          💡 v1 测试阶段可使用内置测试码，正式版请联系销售获取
        </div>
      </div>

      {/* 等级对比 */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 14, marginBottom: 20 }}>
        {TIER_LIST.map(t => {
          const tMeta = TIER_META[t.id];
          const isCurrent = t.id === flags.tier;
          return (
            <div key={t.id} style={{
              background: "#fff", borderRadius: 12, padding: 18,
              border: `2px solid ${isCurrent ? tMeta.color : "#e0e0e0"}`,
              boxShadow: isCurrent ? `0 4px 12px ${tMeta.color}20` : "0 1px 3px rgba(0,0,0,0.05)",
              position: "relative",
            }}>
              {isCurrent && (
                <div style={{
                  position: "absolute", top: -10, left: 14,
                  fontSize: 10, padding: "2px 8px", borderRadius: 8,
                  background: tMeta.color, color: "#fff", fontWeight: 600,
                }}>当前等级</div>
              )}
              <div style={{ fontSize: 16, fontWeight: 700, color: tMeta.color, marginBottom: 4 }}>
                {t.name}
              </div>
              <div style={{ fontSize: 22, fontWeight: 700, marginBottom: 12 }}>
                {t.price_monthly === 0 ? "免费" : `¥${t.price_monthly}/月`}
              </div>
              <div style={{ fontSize: 12, color: "#666", lineHeight: 1.8 }}>
                {t.features.map((f, i) => (
                  <div key={i}>✓ {f}</div>
                ))}
              </div>
              {t.id !== "free" && t.id !== flags.tier && (
                <button style={{
                  width: "100%", marginTop: 14, padding: "8px 0",
                  border: "none", borderRadius: 6,
                  background: `linear-gradient(135deg, ${tMeta.color}, ${tMeta.color}cc)`,
                  color: "#fff", cursor: "pointer", fontSize: 12, fontWeight: 600,
                }}>升级</button>
              )}
            </div>
          );
        })}
      </div>

      {/* 联系方式占位 */}
      <div style={{
        background: "#f8f9fa", borderRadius: 10, padding: 16,
        textAlign: "center", color: "#666", fontSize: 12,
      }}>
        📧 商务合作 / 批量授权：contact@hengshi-value.example
        <br />
        💬 微信群：v1 测试阶段暂未开放
      </div>
    </div>
  );
}
