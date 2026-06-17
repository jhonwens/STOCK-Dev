import { Outlet } from "react-router-dom";
import Sidebar from "./Sidebar";
import LLMChat from "./LLMChat";

export default function Layout() {
  return (
    <div style={{ display: "flex", height: "100vh", overflow: "hidden" }}>
      <Sidebar />
      <main style={{ flex: 1, overflow: "auto", padding: 24 }}>
        <Outlet />
      </main>
      <LLMChat />
    </div>
  );
}