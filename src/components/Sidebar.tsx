import { memo } from "react";
import { NavLink } from "react-router-dom";

interface NavItem {
  path: string;
  label: string;
  icon: string;
}

const groups: { title: string; items: NavItem[] }[] = [
  {
    title: "股票分析",
    items: [
      { path: "/", label: "股票池概览", icon: "📊" },
      { path: "/portfolio", label: "持仓分析", icon: "📁" },
      { path: "/watchlist", label: "候选推荐", icon: "🎯" },
    ],
  },
  {
    title: "智能分析",
    items: [
      { path: "/ai-analyst", icon: "🤖", label: "智能分析" },
    ],
  },
  {
    title: "系统",
    items: [
      { path: "/membership", label: "会员中心", icon: "👤" },
      { path: "/about", label: "关于", icon: "ℹ️" },
      { path: "/settings", label: "设置", icon: "⚙️" },
    ],
  },
];

const NavGroup = memo(function NavGroup({ title, items }: { title: string; items: NavItem[] }) {
  return (
    <div style={{ marginBottom: 8 }}>
      <div style={{
        fontSize: 10, fontWeight: 700,
        color: "rgba(255,255,255,0.25)",
        textTransform: "uppercase", letterSpacing: "1.5px",
        padding: "0 8px", marginBottom: 4, marginTop: 4,
      }}>
        {title}
      </div>
      {items.map(({ path, label, icon }) => (
        <NavLink
          key={path}
          to={path}
          end={path === "/"}
          style={({ isActive }) => ({
            display: "flex", alignItems: "center", gap: 10,
            padding: "9px 12px", borderRadius: 8, fontSize: 13,
            textDecoration: "none", marginBottom: 1,
            color: isActive ? "#fff" : "rgba(255,255,255,0.5)",
            background: isActive
              ? "linear-gradient(135deg, rgba(91,141,239,0.18), rgba(124,92,252,0.12))"
              : "transparent",
            fontWeight: isActive ? 500 : 400,
            border: isActive ? "1px solid rgba(91,141,239,0.12)" : "1px solid transparent",
            boxShadow: isActive ? "0 1px 4px rgba(91,141,239,0.1)" : "none",
          })}
        >
          <span style={{ fontSize: 15, width: 20, textAlign: "center" }}>{icon}</span>
          <span>{label}</span>
        </NavLink>
      ))}
    </div>
  );
});

const Sidebar = memo(function Sidebar() {
  return (
    <nav style={{
      width: 220,
      background: "linear-gradient(180deg, #0f1219 0%, #1a1e2e 100%)",
      boxShadow: "2px 0 24px rgba(0,0,0,0.2)",
      display: "flex", flexDirection: "column",
      flexShrink: 0, zIndex: 10,
    }}>
      <div style={{
        padding: "20px 16px 14px",
        borderBottom: "1px solid rgba(255,255,255,0.04)",
      }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <div style={{
            width: 28, height: 28, borderRadius: 8,
            background: "linear-gradient(135deg, #3b82f6, #8b5cf6)",
            display: "flex", alignItems: "center", justifyContent: "center",
            fontSize: 14, flexShrink: 0,
          }}>
            ⚡
          </div>
          <div>
            <div style={{ fontSize: 14, fontWeight: 700, color: "#fff", letterSpacing: "0.3px" }}>
              衡势价值
            </div>
            <div style={{ fontSize: 10, color: "rgba(255,255,255,0.3)", marginTop: 0 }}>
              AI 股票分析
            </div>
          </div>
        </div>
      </div>

      <div style={{ padding: "12px 12px 0", flex: 1, display: "flex", flexDirection: "column", overflowY: "auto" }}>
        {groups.map((g) => (
          <NavGroup key={g.title} title={g.title} items={g.items} />
        ))}
      </div>

      <div style={{
        padding: "12px 16px",
        borderTop: "1px solid rgba(255,255,255,0.04)",
        fontSize: 10, color: "rgba(255,255,255,0.15)",
        textAlign: "center",
      }}>
        v0.1.0
      </div>
    </nav>
  );
});

export default Sidebar;