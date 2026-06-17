import { invoke } from "@tauri-apps/api/core";
import type { FeatureFlags } from "../types";

let cached: FeatureFlags | null = null;

export async function getFeatureFlags(): Promise<FeatureFlags> {
  if (cached) return cached;
  cached = await invoke<FeatureFlags>("get_feature_flags");
  return cached;
}

export function clearFeatureFlagCache(): void {
  cached = null;
}

export function getCachedFlags(): FeatureFlags | null {
  return cached;
}
