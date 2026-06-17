import { invoke } from "@tauri-apps/api/core";
import type { LicenseInfo } from "../types";

export async function activateLicense(key: string): Promise<LicenseInfo> {
  return invoke("activate_license", { key });
}

export async function deactivateLicense(): Promise<void> {
  return invoke("deactivate_license");
}

export async function getLicenseInfo(): Promise<LicenseInfo | null> {
  return invoke("get_license_info");
}
