import { invoke } from "@tauri-apps/api/core";
import type { StockSummary, StockItem, TechnicalIndicators, MarketOverview, StockListEntry, PortfolioStock } from "../types";

export { activateLicense, deactivateLicense, getLicenseInfo } from "./license";
export { getFeatureFlags, clearFeatureFlagCache, getCachedFlags } from "./feature_flag";

export async function getDashboardSummary(): Promise<StockSummary> {
  return invoke("get_dashboard_summary");
}

export async function getMarketMovers(): Promise<MarketOverview> {
  return invoke("get_market_movers");
}

export async function getPortfolio(): Promise<StockItem[]> {
  return invoke("get_portfolio");
}

export async function getStockList(): Promise<StockListEntry[]> {
  return invoke("get_stock_list");
}

export async function getTechnicalIndicators(code: string): Promise<TechnicalIndicators> {
  return invoke("get_technical_indicators", { code });
}

export async function runAnalysis(): Promise<string> {
  return invoke("run_analysis");
}

export async function runLlmAnalysis(scope: string = "portfolio"): Promise<string> {
  return invoke("run_llm_analysis", { scope });
}

export async function saveLlmConfig(url: string, apiKey: string, model: string, temperature: number): Promise<string> {
  return invoke("save_llm_config", { url, apiKey, model, temperature });
}

export async function loadLlmConfig(): Promise<string> {
  return invoke("load_llm_config");
}

export async function addStockToList(code: string, name: string, industry: string): Promise<string> {
  return invoke("add_stock_to_list", { code, name, industry });
}

export async function removeStockFromList(code: string): Promise<string> {
  return invoke("remove_stock_from_list", { code });
}

export async function getPortfolioStocks(): Promise<PortfolioStock[]> {
  return invoke("get_portfolio_stocks");
}

export async function addPortfolioStock(code: string, name: string, costPrice: number, shares: number, category: string): Promise<string> {
  return invoke("add_portfolio_stock", { code, name, costPrice, shares, category });
}

export async function removePortfolioStock(id: number): Promise<string> {
  return invoke("remove_portfolio_stock", { id });
}

export async function runPortfolioLlm(code: string): Promise<string> {
  return invoke("run_portfolio_llm", { code });
}

export async function savePortfolioAnalysis(code: string, analysisJson: string): Promise<string> {
  return invoke("save_portfolio_analysis", { code, analysisJson });
}

export async function loadPortfolioAnalysis(code: string): Promise<string> {
  return invoke("load_portfolio_analysis", { code });
}

export async function exportPortfolioMd(code: string, name: string, analysisJson: string): Promise<string> {
  return invoke("export_portfolio_md", { code, name, analysisJson });
}

export async function runCandidateLlm(): Promise<string> {
  return invoke("run_candidate_llm");
}

export async function saveCandidateAnalysis(analysisJson: string): Promise<string> {
  return invoke("save_candidate_analysis", { analysisJson });
}

export async function loadCandidateAnalysis(): Promise<string> {
  return invoke("load_candidate_analysis");
}

export async function exportCandidateMd(analysisJson: string): Promise<string> {
  return invoke("export_candidate_md", { analysisJson });
}

export async function searchStock(query: string): Promise<string> {
  return invoke("search_stock", { query });
}

export async function runStockInsight(code: string): Promise<string> {
  return invoke("run_stock_insight", { code });
}

export async function saveStockInsight(code: string, analysisJson: string): Promise<string> {
  return invoke("save_stock_insight", { code, analysisJson });
}

export async function loadStockInsight(code: string): Promise<string> {
  return invoke("load_stock_insight", { code });
}

export async function exportStockInsightMd(code: string, name: string, analysisJson: string): Promise<string> {
  return invoke("export_stock_insight_md", { code, name, analysisJson });
}