import { useState, useEffect } from "react";
import { getFeatureFlags, clearFeatureFlagCache } from "../services/feature_flag";
import type { FeatureFlags, TierId } from "../types";

interface Props {
  open: boolean;
  reason?: string;
  onClose: () => void;
}

const TIER_META: Record<TierId, { name: string; color: string; bg: string; border: string }> = {
  free: { name: "免费版", color: "#888", bg: "#f8f9fa", border: "#e0e0e0" },
  pro: { name: "专业版", color: "#16a34a", bg: "#f0fdf4", border: "#bbf7d0" },
  vip: { name: "至尊版", color: "#7c5cfc", bg: "#faf5ff", border: "#e9d5ff" },
};

const TIER_PRICE: Record<TierId, string> = {
  free: "¥0",
  pro: "¥39/月",
  vip: "¥99/月",
};

export default function UpgradeModal({ open, reason, onClose }: Props) {
  const [flags, setFlags] = useState<FeatureFlags | null>(null);

  useEffect(() => {
    if (open) {
      clearFeatureFlagCache();
      getFeatureFlags().then(setFlags);
    }
  }, [open]);

  if (!open) return null;

  const currentTier: TierId = (flags?.tier as TierId) || "free";
  const currentMeta = TIER_META[currentTier];

  return (
    <div
      onClick={onClose}
      style={{
        position: "fixed", inset: 0, background: "rgba(0,0,0,0.5)",
        display: "flex", alignItems: "center", justifyContent: "center", zIndex: 9999,
      }}
    >
      <div
        onClick={e => e.stopPropagation()}
        style={{
          background: "#fff", borderRadius: 16, padding: 28,
          maxWidth: 480, width: "90%",
          boxShadow: "0 20px 60px rgba(0,0,0,0.3)",
        }}
      >
        <div style={{ fontSize: 20, fontWeight: 700, marginBottom: 8 }}>
          🚀 升级解锁更多功能
        </div>
        {reason && (
          <div style={{ fontSize: 13, color: "#666", marginBottom: 16, lineHeight: 1.6 }}>
            {reason}
          </div>
        )}

        <div style={{ display: "flex", gap: 10, marginBottom: 20 }}>
          {(["free", "pro", "vip"] as TierId[]).map(t => {
            const meta = TIER_META[t];
            const isCurrent = t === currentTier;
            return (
              <div
                key={t}
                style={{
                  flex: 1, padding: 14, borderRadius: 10,
                  background: isCurrent ? meta.bg : "#fafbfc",
                  border: `2px solid ${isCurrent ? meta.border : "#e0e0e0"}`,
                  position: "relative",
                }}
              >
                {isCurrent && (
                  <div style={{
                    position: "absolute", top: -8, right: 8,
                    fontSize: 10, padding: "2px 8px", borderRadius: 8,
                    background: meta.color, color: "#fff", fontWeight: 600,
                  }}>
                    当前
                  </div>
                )}
                <div style={{ fontSize: 14, fontWeight: 700, color: meta.color, marginBottom: 4 }}>
                  {meta.name}
                </div>
                <div style={{ fontSize: 12, color: "#666" }}>{TIER_PRICE[t]}</div>
              </div>
            );
          })}
        </div>

        <div style={{ display: "flex", gap: 10 }}>
          <button
            onClick={onClose}
            style={{
              flex: 1, padding: "10px 0", border: "1px solid #e0e0e0",
              borderRadius: 8, background: "#fff", cursor: "pointer", fontSize: 13,
            }}
          >
            稍后再说
          </button>
          <button
            onClick={() => { window.location.href = "/#/membership"; onClose(); }}
            style={{
              flex: 1, padding: "10px 0", border: "none",
              borderRadius: 8, background: "linear-gradient(135deg, #5b8def, #7c5cfc)",
              color: "#fff", cursor: "pointer", fontSize: 13, fontWeight: 600,
            }}
          >
            前往升级
          </button>
        </div>
      </div>
    </div>
  );
}
