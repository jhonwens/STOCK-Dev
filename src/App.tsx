import { BrowserRouter, Routes, Route } from "react-router-dom";
import { useEffect, useState } from "react";
import Layout from "./components/Layout";
import Dashboard from "./pages/Dashboard";
import Portfolio from "./pages/Portfolio";
import Watchlist from "./pages/Watchlist";
import Settings from "./pages/Settings";
import Membership from "./pages/Membership";
import About from "./pages/About";
import Onboarding from "./pages/Onboarding";

const ONBOARDING_KEY = "hengshi_onboarding_completed";

export default function App() {
  const [onboardingDone, setOnboardingDone] = useState<boolean | null>(null);

  useEffect(() => {
    setOnboardingDone(localStorage.getItem(ONBOARDING_KEY) === "true");
  }, []);

  const completeOnboarding = () => {
    localStorage.setItem(ONBOARDING_KEY, "true");
    setOnboardingDone(true);
  };

  if (onboardingDone === null) {
    return <div style={{ padding: 40, textAlign: "center", color: "#888" }}>加载中...</div>;
  }

  return (
    <BrowserRouter>
      {!onboardingDone && <Onboarding onComplete={completeOnboarding} />}
      <Routes>
        <Route element={<Layout />}>
          <Route index element={<Dashboard />} />
          <Route path="portfolio" element={<Portfolio />} />
          <Route path="watchlist" element={<Watchlist />} />
          <Route path="membership" element={<Membership />} />
          <Route path="about" element={<About />} />
          <Route path="settings" element={<Settings />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
