import { NavLink } from "react-router-dom";

const navItems = [
  { path: "/", label: "股票池概览", icon: "📊" },
  { path: "/portfolio", label: "持仓分析", icon: "📁" },
  { path: "/watchlist", label: "候选推荐", icon: "🎯" },
  { path: "/fundamental", label: "个股分析", icon: "📈" },
  { path: "/membership", label: "会员中心", icon: "👤" },
  { path: "/about", label: "关于", icon: "ℹ️" },
  { path: "/settings", label: "设置", icon: "⚙️" },
];

export default function Sidebar() {
  return (
    <nav style={{
      width: 220,
      background: "linear-gradient(180deg, #1a1e2e 0%, #1e2235 100%)",
      boxShadow: "2px 0 16px rgba(0,0,0,0.12)",
      display: "flex", flexDirection: "column",
      flexShrink: 0, zIndex: 10,
    }}>
      <div style={{
        background: "linear-gradient(135deg, #1e2340, #22284a)",
        padding: "22px 16px 16px",
        borderBottom: "1px solid rgba(255,255,255,0.06)",
        boxShadow: "inset 0 1px 0 rgba(255,255,255,0.05), 0 2px 8px rgba(0,0,0,0.08)",
      }}>
        <div style={{ display: "flex", alignItems: "center", gap: 11 }}>
          <img
            src="/src/assets/logo-64.png"
            alt="衡势价值"
            style={{
              width: 32, height: 32,
            }}
          />
          <div>
            <div style={{ fontSize: 16, fontWeight: 700, color: "#fff", letterSpacing: "0.5px" }}>
              衡势价值
            </div>
            <div style={{ fontSize: 11, color: "rgba(255,255,255,0.35)", marginTop: 1 }}>
              AI 股票分析
            </div>
          </div>
        </div>
      </div>

      <div style={{ padding: "16px 12px 0", flex: 1, display: "flex", flexDirection: "column" }}>
        <div style={{
          fontSize: 11, fontWeight: 600,
          color: "rgba(255,255,255,0.35)",
          textTransform: "uppercase", letterSpacing: "1.2px",
          padding: "0 8px", marginBottom: 6,
        }}>
          导航
        </div>

        {navItems.map(({ path, label, icon }) => (
          <NavLink
            key={path}
            to={path}
            end={path === "/"}
            style={({ isActive }) => ({
              display: "flex", alignItems: "center", gap: 10,
              padding: "10px 12px", borderRadius: 8, fontSize: 13,
              textDecoration: "none", marginBottom: 2,
              color: isActive ? "#fff" : "rgba(255,255,255,0.5)",
              background: isActive
                ? "linear-gradient(135deg, rgba(91,141,239,0.18), rgba(124,92,252,0.12))"
                : "transparent",
              fontWeight: isActive ? 500 : 400,
              border: isActive ? "1px solid rgba(91,141,239,0.12)" : "1px solid transparent",
              boxShadow: isActive ? "0 1px 4px rgba(91,141,239,0.1)" : "none",
            })}
          >
            <span style={{ fontSize: 16, width: 20, textAlign: "center", filter: "none" }}>{icon}</span>
            <span>{label}</span>
          </NavLink>
        ))}
      </div>

      <div style={{
        padding: "14px 16px",
        borderTop: "1px solid rgba(255,255,255,0.05)",
        fontSize: 11, color: "rgba(255,255,255,0.2)",
        textAlign: "center",
      }}>
        v0.1.0
      </div>
    </nav>
  );
}