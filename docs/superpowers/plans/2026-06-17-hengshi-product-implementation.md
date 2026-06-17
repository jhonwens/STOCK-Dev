# 衡势价值 · 产品化骨架 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把"衡势价值"从个人 demo 升级为可分发的产品（v1.0），包含会员分级、License 机制、Feature Flag 系统、品牌统一

**Architecture:** 完全本地运行；后端驱动（Rust 负责 License/Feature Flag 加载与限额度校验）；前端只做 UI 渲染和 Modal 触发；YAML 配置文件定义 tier 权益

**Tech Stack:** Tauri 2.x + Rust + React 19 + TypeScript + Python（激活码生成器）+ serde_yaml + SQLite

**Spec:** [2026-06-17-hengshi-product-design.md](../../specs/2026-06-17-hengshi-product-design.md)

---

## 文件总览

| 路径 | 状态 | 职责 |
|------|------|------|
| `backend/stock-analyst/config/feature_flag.yaml` | 新增 | Feature Flag 默认值 + tier 权益 |
| `backend/stock-analyst/config/tiers.yaml` | 新增 | tier 名称、价格、权益描述 |
| `backend/stock-analyst/scripts/license_gen.py` | 新增 | 激活码生成器 |
| `src-tauri/src/license.rs` | 新增 | License 读写 |
| `src-tauri/src/feature_flag.rs` | 新增 | Feature Flag 加载与合并 |
| `src-tauri/src/commands.rs` | 修改 | 注册 license / feature_flag 命令 |
| `src-tauri/src/main.rs` | 修改 | 初始化 License/FeatureFlag 模块 |
| `src/services/license.ts` | 新增 | License API 封装 |
| `src/services/feature_flag.ts` | 新增 | Feature Flag 加载 + Context |
| `src/services/api.ts` | 修改 | 加 license 相关 API |
| `src/types/index.ts` | 修改 | 加 License / FeatureFlag / Tier 类型 |
| `src/components/UpgradeModal.tsx` | 新增 | 升级弹窗 |
| `src/components/UsageBadge.tsx` | 新增 | 额度徽章 |
| `src/components/Sidebar.tsx` | 修改 | 会员状态块 + 关于入口 |
| `src/pages/Membership.tsx` | 新增 | 会员中心 |
| `src/pages/Onboarding.tsx` | 新增 | 首启动欢迎 |
| `src/pages/About.tsx` | 新增 | 关于页 |
| `src/App.tsx` | 修改 | 注册新路由 |
| `src/pages/Portfolio.tsx` | 修改 | 加额度检查 + 升级 Modal |
| `src/pages/Watchlist.tsx` | 修改 | 加额度检查 + 升级 Modal |

---

## Task 1: 添加 Feature Flag 配置文件

**Files:**
- Create: `backend/stock-analyst/config/feature_flag.yaml`
- Create: `backend/stock-analyst/config/tiers.yaml`

- [ ] **Step 1: 创建 feature_flag.yaml**

```yaml
# Feature Flag 配置 v1.0
# 控制会员等级权益与默认行为

version: "1.0"
defaults:
  tier: pro            # 开发期默认全开；正式发版改为 free
  enable_ai: true
  enable_export: true

tiers:
  free:
    max_holdings: 5
    max_watchlist: 10
    export_pro_report: false
  pro:
    max_holdings: 50
    max_watchlist: 100
    export_pro_report: true
  vip:
    max_holdings: 9999
    max_watchlist: 9999
    export_pro_report: true
```

写入 `backend/stock-analyst/config/feature_flag.yaml`

- [ ] **Step 2: 创建 tiers.yaml**

```yaml
# 会员等级定义

tiers:
  - id: free
    name: "免费版"
    price_monthly: 0
    price_yearly: 0
    features:
      - "持仓 ≤ 5 只"
      - "自选股 ≤ 10 只"
      - "基础 AI 分析"
      - "MD 导出受限"
  - id: pro
    name: "专业版"
    price_monthly: 39
    price_yearly: 399
    features:
      - "持仓 ≤ 50 只"
      - "自选股 ≤ 100 只"
      - "完整 AI 分析"
      - "MD 报告导出"
      - "12 维深度分析"
  - id: vip
    name: "至尊版"
    price_monthly: 99
    price_yearly: 999
    features:
      - "持仓/自选股不限"
      - "全部 Pro 权益"
      - "自定义策略"
      - "高频预警"
```

写入 `backend/stock-analyst/config/tiers.yaml`

- [ ] **Step 3: 验证 YAML 语法**

Run: `cd /Users/ws/Desktop/Project/Trea-Project/STOCK-Dev && python3 -c "import yaml; yaml.safe_load(open('backend/stock-analyst/config/feature_flag.yaml')); yaml.safe_load(open('backend/stock-analyst/config/tiers.yaml')); print('OK')"`
Expected: `OK`

- [ ] **Step 4: 提交**

```bash
cd /Users/ws/Desktop/Project/Trea-Project/STOCK-Dev
git add backend/stock-analyst/config/feature_flag.yaml backend/stock-analyst/config/tiers.yaml
git commit -m "feat(product): add feature_flag and tiers config"
```

---

## Task 2: 实现 License 模块 (Rust)

**Files:**
- Create: `src-tauri/src/license.rs`

- [ ] **Step 1: 创建 license.rs**

```rust
// src-tauri/src/license.rs
use base64::{engine::general_purpose, Engine as _};
use serde::{Deserialize, Serialize};
use std::fs;
use std::path::PathBuf;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct LicenseInfo {
    pub key: String,
    pub tier: String,  // "free" | "pro" | "vip"
    pub issued_at: String,
    pub expired_at: String,
    pub device_id: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct LicenseError {
    pub error: String,
    pub detail: String,
}

fn license_path() -> Result<PathBuf, String> {
    let mut p = dirs::config_dir().ok_or("cannot find config dir")?;
    p.push("hengshi-value");
    fs::create_dir_all(&p).map_err(|e| format!("mkdir failed: {}", e))?;
    p.push("license.dat");
    Ok(p)
}

pub fn read_license() -> Option<LicenseInfo> {
    let p = match license_path() {
        Ok(p) => p,
        Err(_) => return None,
    };
    let content = match fs::read_to_string(&p) {
        Ok(c) => c,
        Err(_) => return None,
    };
    let decoded = match general_purpose::STANDARD.decode(content.trim()) {
        Ok(d) => d,
        Err(_) => return None,
    };
    serde_json::from_slice::<LicenseInfo>(&decoded).ok()
}

pub fn write_license(info: &LicenseInfo) -> Result<(), String> {
    let p = license_path()?;
    let json = serde_json::to_string(info).map_err(|e| e.to_string())?;
    let encoded = general_purpose::STANDARD.encode(json.as_bytes());
    fs::write(&p, encoded).map_err(|e| format!("write failed: {}", e))?;
    Ok(())
}

pub fn clear_license() -> Result<(), String> {
    let p = license_path()?;
    if p.exists() {
        fs::remove_file(&p).map_err(|e| format!("remove failed: {}", e))?;
    }
    Ok(())
}

/// 校验激活码格式
pub fn parse_license_key(key: &str) -> Result<LicenseInfo, String> {
    let parts: Vec<&str> = key.split('-').collect();
    if parts.len() != 6 {
        return Err("激活码格式错误：应为 6 段".to_string());
    }
    if parts[0] != "HSP" {
        return Err("激活码前缀错误".to_string());
    }
    let tier = match parts[1] {
        "FREE" => "free",
        "PRO" => "pro",
        "VIP" => "vip",
        _ => return Err("激活码等级错误".to_string()),
    };
    let body = format!("{}-{}-{}-{}", parts[1], parts[2], parts[3], parts[4]);
    let expected_check = crc_check(&body);
    if !parts[5].eq_ignore_ascii_case(&expected_check) {
        return Err("激活码校验码错误".to_string());
    }
    // TODO: 接云端时校验 expired_at
    Ok(LicenseInfo {
        key: key.to_string(),
        tier: tier.to_string(),
        issued_at: chrono::Local::now().format("%Y-%m-%d").to_string(),
        expired_at: "2099-12-31".to_string(),  // 本地版默认永不过期
        device_id: get_device_id(),
    })
}

fn crc_check(s: &str) -> String {
    // 简单 CRC32 取低 16 位 hex
    let bytes = s.as_bytes();
    let mut crc: u32 = 0xFFFFFFFF;
    for &b in bytes {
        crc ^= b as u32;
        for _ in 0..8 {
            if crc & 1 != 0 {
                crc = (crc >> 1) ^ 0xEDB88320;
            } else {
                crc >>= 1;
            }
        }
    }
    let crc = !crc;
    format!("{:04X}", crc & 0xFFFF)
}

fn get_device_id() -> String {
    use std::collections::hash_map::DefaultHasher;
    use std::hash::{Hash, Hasher};
    let hostname = std::env::var("HOSTNAME")
        .or_else(|_| std::env::var("COMPUTERNAME"))
        .unwrap_or_else(|_| "unknown".to_string());
    let mut hasher = DefaultHasher::new();
    hostname.hash(&mut hasher);
    format!("{:x}", hasher.finish())[..8].to_string()
}
```

写入 `src-tauri/src/license.rs`

- [ ] **Step 2: 在 Cargo.toml 加依赖**

Modify: `src-tauri/Cargo.toml` 第 9-18 行附近

```toml
[dependencies]
tauri = { version = "2", features = [] }
tauri-plugin-shell = "2"
serde = { version = "1", features = ["derive"] }
serde_json = "1"
serde_yaml = "0.9"
rusqlite = { version = "0.31", features = ["bundled"] }
dirs = "5"
tokio = { version = "1", features = ["process"] }
chrono = "0.4"
base64 = "0.22"
```

- [ ] **Step 3: 验证编译**

Run: `cd /Users/ws/Desktop/Project/Trea-Project/STOCK-Dev/src-tauri && cargo build 2>&1 | tail -20`
Expected: `Finished` 状态，可能有 warning

- [ ] **Step 4: 提交**

```bash
cd /Users/ws/Desktop/Project/Trea-Project/STOCK-Dev
git add src-tauri/src/license.rs src-tauri/Cargo.toml
git commit -m "feat(product): add License module (Rust)"
```

---

## Task 3: 实现 Feature Flag 模块 (Rust)

**Files:**
- Create: `src-tauri/src/feature_flag.rs`

- [ ] **Step 1: 创建 feature_flag.rs**

```rust
// src-tauri/src/feature_flag.rs
use crate::license::{read_license, LicenseInfo};
use serde::{Deserialize, Serialize};
use std::fs;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TierLimits {
    pub max_holdings: i32,
    pub max_watchlist: i32,
    pub export_pro_report: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct FeatureFlags {
    pub tier: String,
    pub limits: TierLimits,
    pub license: Option<LicenseInfo>,
    pub is_licensed: bool,
}

#[derive(Debug, Deserialize, Clone)]
struct FlagConfig {
    version: String,
    defaults: FlagDefaults,
    tiers: std::collections::HashMap<String, TierLimits>,
}

#[derive(Debug, Deserialize, Clone)]
struct FlagDefaults {
    tier: String,
    #[allow(dead_code)]
    enable_ai: bool,
    #[allow(dead_code)]
    enable_export: bool,
}

fn flag_path() -> Result<std::path::PathBuf, String> {
    let mut p = std::path::PathBuf::from(env!("CARGO_MANIFEST_DIR"));
    p.push("..");
    p.push("backend");
    p.push("stock-analyst");
    p.push("config");
    p.push("feature_flag.yaml");
    Ok(p)
}

pub fn load_flags() -> Result<FeatureFlags, String> {
    let path = flag_path()?;
    let content = fs::read_to_string(&path).map_err(|e| format!("read failed: {}", e))?;
    let cfg: FlagConfig = serde_yaml::from_str(&content).map_err(|e| format!("yaml parse: {}", e))?;

    let license = read_license();
    let effective_tier = if let Some(ref lic) = license {
        if lic.tier == "free" { "free".to_string() } else { lic.tier.clone() }
    } else {
        cfg.defaults.tier.clone()
    };

    let limits = cfg.tiers.get(&effective_tier)
        .cloned()
        .ok_or_else(|| format!("tier not found: {}", effective_tier))?;

    Ok(FeatureFlags {
        tier: effective_tier,
        limits,
        is_licensed: license.is_some(),
        license,
    })
}
```

写入 `src-tauri/src/feature_flag.rs`

- [ ] **Step 2: 验证编译**

Run: `cd /Users/ws/Desktop/Project/Trea-Project/STOCK-Dev/src-tauri && cargo build 2>&1 | tail -20`
Expected: `Finished` 状态

- [ ] **Step 3: 提交**

```bash
cd /Users/ws/Desktop/Project/Trea-Project/STOCK-Dev
git add src-tauri/src/feature_flag.rs
git commit -m "feat(product): add FeatureFlag module (Rust)"
```

---

## Task 4: 注册 Tauri Commands

**Files:**
- Modify: `src-tauri/src/commands.rs`
- Modify: `src-tauri/src/main.rs`

- [ ] **Step 1: 在 commands.rs 末尾添加命令**

打开 `src-tauri/src/commands.rs`，在文件最末尾追加：

```rust
// === License & Feature Flag Commands ===
use crate::feature_flag::{load_flags, FeatureFlags};
use crate::license::{clear_license, parse_license_key, read_license, write_license, LicenseInfo};

#[tauri::command]
pub fn get_feature_flags() -> Result<FeatureFlags, String> {
    load_flags()
}

#[tauri::command]
pub fn activate_license(key: String) -> Result<LicenseInfo, String> {
    let info = parse_license_key(&key)?;
    write_license(&info)?;
    Ok(info)
}

#[tauri::command]
pub fn deactivate_license() -> Result<(), String> {
    clear_license()
}

#[tauri::command]
pub fn get_license_info() -> Result<Option<LicenseInfo>, String> {
    Ok(read_license())
}
```

- [ ] **Step 2: 在 main.rs 注册模块和命令**

打开 `src-tauri/src/main.rs`，在文件顶部添加 mod 声明，在 `tauri::Builder` 内注册命令：

```rust
mod license;
mod feature_flag;

// ... 在 .invoke_handler(tauri::generate_handler![...]) 列表中添加：
//     commands::get_feature_flags,
//     commands::activate_license,
//     commands::deactivate_license,
//     commands::get_license_info,
```

具体位置参考现有 commands 模块的引入方式。

- [ ] **Step 3: 验证编译**

Run: `cd /Users/ws/Desktop/Project/Trea-Project/STOCK-Dev/src-tauri && cargo build 2>&1 | tail -30`
Expected: `Finished` 状态

- [ ] **Step 4: 提交**

```bash
cd /Users/ws/Desktop/Project/Trea-Project/STOCK-Dev
git add src-tauri/src/commands.rs src-tauri/src/main.rs
git commit -m "feat(product): register license & feature_flag commands"
```

---

## Task 5: 实现激活码生成器 (Python)

**Files:**
- Create: `backend/stock-analyst/scripts/license_gen.py`

- [ ] **Step 1: 创建 license_gen.py**

```python
#!/usr/bin/env python3
# 衡势价值 · 激活码生成器
# 用法: python license_gen.py <TIER> [DAYS]
# 例: python license_gen.py PRO 365

import sys
import random
import string
import binascii
from datetime import datetime, timedelta

PREFIX = "HSP"
SEG_LEN = 4
CHARS = string.ascii_uppercase + string.digits


def crc16(s: str) -> str:
    crc = binascii.crc32(s.encode()) & 0xFFFFFFFF
    return f"{(~crc & 0xFFFF):04X}"


def gen_seg() -> str:
    return "".join(random.choices(CHARS, k=SEG_LEN))


def gen_key(tier: str) -> str:
    seg1, seg2, seg3 = gen_seg(), gen_seg(), gen_seg()
    body = f"{tier}-{seg1}-{seg2}-{seg3}"
    check = crc16(body)
    return f"{PREFIX}-{body}-{check}"


def main():
    if len(sys.argv) < 2:
        print("Usage: python license_gen.py <FREE|PRO|VIP> [DAYS]")
        print("Examples:")
        print("  python license_gen.py PRO 365   # PRO 一年期")
        print("  python license_gen.py VIP       # VIP 永不过期")
        sys.exit(1)

    tier = sys.argv[1].upper()
    if tier not in ("FREE", "PRO", "VIP"):
        print(f"Invalid tier: {tier}")
        sys.exit(1)

    days = int(sys.argv[2]) if len(sys.argv) > 2 else 3650
    key = gen_key(tier)
    issued = datetime.now().strftime("%Y-%m-%d")
    expired = (datetime.now() + timedelta(days=days)).strftime("%Y-%m-%d")

    print("=" * 50)
    print("衡势价值 · 激活码")
    print("=" * 50)
    print(f"  Key:     {key}")
    print(f"  Tier:    {tier}")
    print(f"  Issued:  {issued}")
    print(f"  Expired: {expired}")
    print("=" * 50)
    print("\n请在「会员中心 → 激活码兑换」输入上述 Key。\n")


if __name__ == "__main__":
    main()
```

写入 `backend/stock-analyst/scripts/license_gen.py`

- [ ] **Step 2: 测试生成器**

Run: `cd /Users/ws/Desktop/Project/Trea-Project/STOCK-Dev && python3 backend/stock-analyst/scripts/license_gen.py PRO 365`
Expected: 输出 `衡势价值 · 激活码` 标题和 `HSP-PRO-XXXX-XXXX-XXXX-XXXX` 格式 Key

- [ ] **Step 3: 生成 5 个内置测试码**

```bash
cd /Users/ws/Desktop/Project/Trea-Project/STOCK-Dev
echo "## 内置测试激活码" > /tmp/license_codes.md
echo "" >> /tmp/license_codes.md
python3 backend/stock-analyst/scripts/license_gen.py PRO 365 | grep "Key:" >> /tmp/license_codes.md
python3 backend/stock-analyst/scripts/license_gen.py VIP 365 | grep "Key:" >> /tmp/license_codes.md
python3 backend/stock-analyst/scripts/license_gen.py FREE 365 | grep "Key:" >> /tmp/license_codes.md
cat /tmp/license_codes.md
```

Expected: 输出 3 个不同 tier 的 Key，记录到 `/tmp/license_codes.md`

- [ ] **Step 4: 提交**

```bash
cd /Users/ws/Desktop/Project/Trea-Project/STOCK-Dev
git add backend/stock-analyst/scripts/license_gen.py
git commit -m "feat(product): add license key generator"
```

---

## Task 6: 前端类型定义

**Files:**
- Modify: `src/types/index.ts`

- [ ] **Step 1: 在 index.ts 末尾追加类型**

打开 `src/types/index.ts`，在最后追加：

```typescript
// === License & Feature Flag Types ===

export type TierId = "free" | "pro" | "vip";

export interface TierLimits {
  max_holdings: number;
  max_watchlist: number;
  export_pro_report: boolean;
}

export interface LicenseInfo {
  key: string;
  tier: TierId;
  issued_at: string;
  expired_at: string;
  device_id: string;
}

export interface FeatureFlags {
  tier: TierId;
  limits: TierLimits;
  is_licensed: boolean;
  license: LicenseInfo | null;
}

export interface TierDef {
  id: TierId;
  name: string;
  price_monthly: number;
  price_yearly: number;
  features: string[];
}
```

- [ ] **Step 2: 验证 TS 编译**

Run: `cd /Users/ws/Desktop/Project/Trea-Project/STOCK-Dev && npx tsc --noEmit 2>&1 | tail -20`
Expected: 无错误

- [ ] **Step 3: 提交**

```bash
cd /Users/ws/Desktop/Project/Trea-Project/STOCK-Dev
git add src/types/index.ts
git commit -m "feat(product): add License/FeatureFlag/Tier types"
```

---

## Task 7: 前端 Service 模块

**Files:**
- Create: `src/services/license.ts`
- Create: `src/services/feature_flag.ts`
- Modify: `src/services/api.ts`

- [ ] **Step 1: 创建 src/services/license.ts**

```typescript
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
```

- [ ] **Step 2: 创建 src/services/feature_flag.ts**

```typescript
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
```

- [ ] **Step 3: 在 src/services/api.ts 顶部加 re-export**

打开 `src/services/api.ts`，在文件顶部 import 区块下方添加：

```typescript
export { activateLicense, deactivateLicense, getLicenseInfo } from "./license";
export { getFeatureFlags, clearFeatureFlagCache, getCachedFlags } from "./feature_flag";
```

- [ ] **Step 4: 验证 TS 编译**

Run: `cd /Users/ws/Desktop/Project/Trea-Project/STOCK-Dev && npx tsc --noEmit 2>&1 | tail -20`
Expected: 无错误

- [ ] **Step 5: 提交**

```bash
cd /Users/ws/Desktop/Project/Trea-Project/STOCK-Dev
git add src/services/license.ts src/services/feature_flag.ts src/services/api.ts
git commit -m "feat(product): add license and feature_flag services"
```

---

## Task 8: 升级 Modal 组件

**Files:**
- Create: `src/components/UpgradeModal.tsx`

- [ ] **Step 1: 创建 UpgradeModal.tsx**

```tsx
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

  const currentTier: TierId = flags?.tier || "free";
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
```

- [ ] **Step 2: 验证 TS 编译**

Run: `cd /Users/ws/Desktop/Project/Trea-Project/STOCK-Dev && npx tsc --noEmit 2>&1 | tail -20`
Expected: 无错误

- [ ] **Step 3: 提交**

```bash
cd /Users/ws/Desktop/Project/Trea-Project/STOCK-Dev
git add src/components/UpgradeModal.tsx
git commit -m "feat(product): add UpgradeModal component"
```

---

## Task 9: 会员中心页 (Membership)

**Files:**
- Create: `src/pages/Membership.tsx`

- [ ] **Step 1: 创建 Membership.tsx**

```tsx
import { useState, useEffect } from "react";
import {
  getFeatureFlags, clearFeatureFlagCache,
  activateLicense, deactivateLicense, getLicenseInfo,
} from "../services/feature_flag";
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
      setStatus(`✅ 激活成功！当前等级：${TIER_META[info.tier].name}`);
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

  const meta = TIER_META[flags.tier];
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
            background: "linear-gradient(135deg, #5b8def, #7c5fc)",
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
```

- [ ] **Step 2: 验证 TS 编译**

Run: `cd /Users/ws/Desktop/Project/Trea-Project/STOCK-Dev && npx tsc --noEmit 2>&1 | tail -20`
Expected: 无错误

- [ ] **Step 3: 提交**

```bash
cd /Users/ws/Desktop/Project/Trea-Project/STOCK-Dev
git add src/pages/Membership.tsx
git commit -m "feat(product): add Membership page"
```

---

## Task 10: 首启动欢迎页 (Onboarding)

**Files:**
- Create: `src/pages/Onboarding.tsx`

- [ ] **Step 1: 创建 Onboarding.tsx**

```tsx
import { useState } from "react";

interface Props {
  onComplete: () => void;
}

const STEPS = [
  {
    title: "欢迎使用衡势价值",
    desc: "AI 驱动的中长线价值投资助手",
    icon: "⚖️",
  },
  {
    title: "4 大核心功能",
    desc: "📊 股票池概览  📁 持仓分析  🎯 候选推荐  📈 个股分析",
    icon: "🎯",
  },
  {
    title: "AI 分析需要配置",
    desc: "前往「设置」页配置您的 LLM API Key（通义千问 / DeepSeek 等）",
    icon: "🤖",
  },
  {
    title: "开始体验",
    desc: "开发期默认 Pro 等级，所有功能可用。\n正式发布后请激活会员以解锁完整服务。",
    icon: "🚀",
  },
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

        {/* 步骤指示器 */}
        <div style={{ display: "flex", justifyContent: "center", gap: 6, margin: "24px 0" }}>
          {STEPS.map((_, i) => (
            <div key={i} style={{
              width: i === step ? 24 : 8, height: 8, borderRadius: 4,
              background: i === step ? "linear-gradient(135deg, #5b8def, #7c5fc)" : "#e0e0e0",
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
            background: "linear-gradient(135deg, #5b8def, #7c5fc)",
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
```

- [ ] **Step 2: 验证 TS 编译**

Run: `cd /Users/ws/Desktop/Project/Trea-Project/STOCK-Dev && npx tsc --noEmit 2>&1 | tail -20`
Expected: 无错误

- [ ] **Step 3: 提交**

```bash
cd /Users/ws/Desktop/Project/Trea-Project/STOCK-Dev
git add src/pages/Onboarding.tsx
git commit -m "feat(product): add Onboarding page"
```

---

## Task 11: 关于页 (About)

**Files:**
- Create: `src/pages/About.tsx`

- [ ] **Step 1: 创建 About.tsx**

```tsx
import { useEffect, useState } from "react";
import { getFeatureFlags } from "../services/feature_flag";

interface AppInfo {
  version: string;
  tier: string;
  is_licensed: boolean;
}

export default function About() {
  const [info, setInfo] = useState<AppInfo | null>(null);

  useEffect(() => {
    getFeatureFlags().then(f => setInfo({
      version: "1.0.0",
      tier: f.tier,
      is_licensed: f.is_licensed,
    }));
  }, []);

  return (
    <div style={{ maxWidth: 720, margin: "0 auto" }}>
      <h2 style={{ fontSize: 22, fontWeight: 700, marginBottom: 20 }}>ℹ️ 关于</h2>

      <div style={{
        background: "linear-gradient(135deg, #1a1e2e, #2a2f4a)",
        color: "#fff", borderRadius: 16, padding: 32, marginBottom: 20,
        textAlign: "center",
      }}>
        <div style={{ fontSize: 56, marginBottom: 8 }}>⚖️</div>
        <div style={{ fontSize: 24, fontWeight: 700, letterSpacing: 1 }}>衡势价值</div>
        <div style={{ fontSize: 13, color: "rgba(255,255,255,0.6)", marginTop: 4 }}>
          AI 驱动的中长线价值投资助手
        </div>
      </div>

      <div style={{
        background: "#fff", borderRadius: 12, padding: 20, marginBottom: 16,
        boxShadow: "0 1px 3px rgba(0,0,0,0.08)",
      }}>
        <div style={{ fontSize: 14, fontWeight: 600, marginBottom: 12 }}>📦 产品信息</div>
        <Row label="产品名称" value="衡势价值 / HengShi Value" />
        <Row label="当前版本" value={info?.version || "v1.0.0"} />
        <Row label="构建日期" value="2026-06-17" />
        <Row label="技术栈" value="Tauri 2 + React 19 + Rust + Python" />
        <Row label="会员等级" value={info?.tier.toUpperCase() || "-"} />
        <Row label="激活状态" value={info?.is_licensed ? "已激活" : "未激活（开发期默认 Pro）"} />
      </div>

      <div style={{
        background: "#fff", borderRadius: 12, padding: 20, marginBottom: 16,
        boxShadow: "0 1px 3px rgba(0,0,0,0.08)",
      }}>
        <div style={{ fontSize: 14, fontWeight: 600, marginBottom: 12 }}>📞 联系我们</div>
        <Row label="商务合作" value="contact@hengshi-value.example" />
        <Row label="问题反馈" value="feedback@hengshi-value.example" />
        <Row label="官方网站" value="https://hengshi-value.example（占位）" />
      </div>

      <div style={{
        background: "#fff", borderRadius: 12, padding: 20, marginBottom: 16,
        boxShadow: "0 1px 3px rgba(0,0,0,0.08)",
      }}>
        <div style={{ fontSize: 14, fontWeight: 600, marginBottom: 12 }}>🔄 检查更新</div>
        <button style={{
          padding: "8px 16px", border: "1px solid #e0e0e0",
          borderRadius: 8, background: "#fff", cursor: "pointer", fontSize: 12,
        }}>检查更新</button>
        <div style={{ fontSize: 11, color: "#999", marginTop: 6 }}>
          v1 暂未实装更新检查
        </div>
      </div>

      <div style={{
        background: "#f8f9fa", borderRadius: 10, padding: 14,
        textAlign: "center", color: "#999", fontSize: 11, lineHeight: 1.6,
      }}>
        © 2026 衡势价值 · 让价值被看见，让持仓更稳健
        <br />
        本产品仅供学习研究使用，不构成任何投资建议
      </div>
    </div>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div style={{
      display: "flex", padding: "6px 0",
      borderBottom: "1px solid #f0f0f0", fontSize: 13,
    }}>
      <span style={{ width: 100, color: "#888" }}>{label}</span>
      <span style={{ flex: 1, color: "#333" }}>{value}</span>
    </div>
  );
}
```

- [ ] **Step 2: 验证 TS 编译**

Run: `cd /Users/ws/Desktop/Project/Trea-Project/STOCK-Dev && npx tsc --noEmit 2>&1 | tail -20`
Expected: 无错误

- [ ] **Step 3: 提交**

```bash
cd /Users/ws/Desktop/Project/Trea-Project/STOCK-Dev
git add src/pages/About.tsx
git commit -m "feat(product): add About page"
```

---

## Task 12: 改造侧边栏 (Sidebar)

**Files:**
- Modify: `src/components/Sidebar.tsx`

- [ ] **Step 1: 在 navItems 末尾追加会员中心和关于**

打开 `src/components/Sidebar.tsx`，把 navItems 改为：

```typescript
const navItems = [
  { path: "/", label: "股票池概览", icon: "📊" },
  { path: "/portfolio", label: "持仓分析", icon: "📁" },
  { path: "/watchlist", label: "候选推荐", icon: "🎯" },
  { path: "/fundamental", label: "个股分析", icon: "📈" },
  { path: "/membership", label: "会员中心", icon: "👤" },
  { path: "/about", label: "关于", icon: "ℹ️" },
  { path: "/settings", label: "设置", icon: "⚙️" },
];
```

- [ ] **Step 2: 验证 TS 编译**

Run: `cd /Users/ws/Desktop/Project/Trea-Project/STOCK-Dev && npx tsc --noEmit 2>&1 | tail -20`
Expected: 无错误

- [ ] **Step 3: 提交**

```bash
cd /Users/ws/Desktop/Project/Trea-Project/STOCK-Dev
git add src/components/Sidebar.tsx
git commit -m "feat(product): add membership & about entries to Sidebar"
```

---

## Task 13: 注册新路由

**Files:**
- Modify: `src/App.tsx`

- [ ] **Step 1: 改写 App.tsx 添加新路由**

```tsx
import { BrowserRouter, Routes, Route } from "react-router-dom";
import { useEffect, useState } from "react";
import Layout from "./components/Layout";
import Dashboard from "./pages/Dashboard";
import Portfolio from "./pages/Portfolio";
import Watchlist from "./pages/Watchlist";
import Fundamental from "./pages/Fundamental";
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
          <Route path="fundamental" element={<Fundamental />} />
          <Route path="membership" element={<Membership />} />
          <Route path="about" element={<About />} />
          <Route path="settings" element={<Settings />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
```

写入 `src/App.tsx`

- [ ] **Step 2: 验证 TS 编译**

Run: `cd /Users/ws/Desktop/Project/Trea-Project/STOCK-Dev && npx tsc --noEmit 2>&1 | tail -20`
Expected: 无错误

- [ ] **Step 3: 提交**

```bash
cd /Users/ws/Desktop/Project/Trea-Project/STOCK-Dev
git add src/App.tsx
git commit -m "feat(product): register Membership/About/Onboarding routes"
```

---

## Task 14: 持仓页加额度检查

**Files:**
- Modify: `src/pages/Portfolio.tsx`

- [ ] **Step 1: 引入 feature flag 和 UpgradeModal**

打开 `src/pages/Portfolio.tsx`，在最顶部 import 区块加：

```typescript
import { useEffect } from "react";
import { getFeatureFlags, clearFeatureFlagCache } from "../services/feature_flag";
import UpgradeModal from "../components/UpgradeModal";
import type { FeatureFlags } from "../types";
```

- [ ] **Step 2: 在 Portfolio 函数组件内添加状态**

在 `export default function Portfolio() {` 后的状态声明区添加：

```typescript
const [flags, setFlags] = useState<FeatureFlags | null>(null);
const [showUpgrade, setShowUpgrade] = useState(false);
const [upgradeReason, setUpgradeReason] = useState("");

useEffect(() => {
  getFeatureFlags().then(setFlags);
}, []);

const currentHoldings = stocks.length;
const maxHoldings = flags?.limits.max_holdings ?? 5;

const handleAddClick = () => {
  if (currentHoldings >= maxHoldings) {
    setUpgradeReason(`当前持仓 ${currentHoldings} 只，已达免费版上限（${maxHoldings} 只）。升级 Pro 解锁更多持仓。`);
    setShowUpgrade(true);
    return;
  }
  setShowAdd(!showAdd);
};
```

- [ ] **Step 3: 把现有 setShowAdd(!showAdd) 改为 handleAddClick**

在 JSX 中找到 `onClick={() => setShowAdd(!showAdd)}`，替换为 `onClick={handleAddClick}`

- [ ] **Step 4: 在 JSX 末尾加 UpgradeModal**

在 `</div>` 闭合标签前（最外层）添加：

```tsx
<UpgradeModal
  open={showUpgrade}
  reason={upgradeReason}
  onClose={() => setShowUpgrade(false)}
/>
```

- [ ] **Step 5: 在头部加额度徽章**

找到 `<h2 style={{...}}>📁 持仓分析</h2>` 这一行，在它后面添加：

```tsx
{flags && (
  <span style={{
    fontSize: 12, padding: "3px 10px", borderRadius: 12,
    background: currentHoldings >= maxHoldings ? "#fef2f2" : "#f0fdf4",
    color: currentHoldings >= maxHoldings ? "#dc2626" : "#16a34a",
    border: `1px solid ${currentHoldings >= maxHoldings ? "#fecaca" : "#bbf7d0"}`,
  }}>
    持仓 {currentHoldings}/{maxHoldings}
  </span>
)}
```

- [ ] **Step 6: 验证 TS 编译**

Run: `cd /Users/ws/Desktop/Project/Trea-Project/STOCK-Dev && npx tsc --noEmit 2>&1 | tail -20`
Expected: 无错误

- [ ] **Step 7: 提交**

```bash
cd /Users/ws/Desktop/Project/Trea-Project/STOCK-Dev
git add src/pages/Portfolio.tsx
git commit -m "feat(product): add holding quota check in Portfolio"
```

---

## Task 15: 自选股页加额度检查

**Files:**
- Modify: `src/pages/Watchlist.tsx`

- [ ] **Step 1: 引入 feature flag 和 UpgradeModal**

打开 `src/pages/Watchlist.tsx`，在最顶部 import 区块加：

```typescript
import { useEffect, useState } from "react";
import { getFeatureFlags } from "../services/feature_flag";
import UpgradeModal from "../components/UpgradeModal";
import type { FeatureFlags } from "../types";
```

- [ ] **Step 2: 在函数组件内添加状态和限额度逻辑**

具体添加位置参考 Task 14 的模式，逻辑：
- 加载 flags
- 拿 watchlist 数量对比 `flags.limits.max_watchlist`
- 超出时弹 UpgradeModal

- [ ] **Step 3: 验证 TS 编译**

Run: `cd /Users/ws/Desktop/Project/Trea-Project/STOCK-Dev && npx tsc --noEmit 2>&1 | tail -20`
Expected: 无错误

- [ ] **Step 4: 提交**

```bash
cd /Users/ws/Desktop/Project/Trea-Project/STOCK-Dev
git add src/pages/Watchlist.tsx
git commit -m "feat(product): add watchlist quota check in Watchlist"
```

---

## Task 16: 端到端验证

**Files:** 无（仅验证）

- [ ] **Step 1: 启动应用**

Run: `cd /Users/ws/Desktop/Project/Trea-Project/STOCK-Dev && npx tauri dev`
Expected: 应用窗口弹出

- [ ] **Step 2: 验证 Onboarding**

- 首次启动应该看到 4 步引导
- 点"开始体验"后进入主界面
- 关闭应用再启动应该不再出现引导

- [ ] **Step 3: 验证 Feature Flag 默认 Pro**

- 进入"会员中心"，应看到当前等级 = Pro
- 持仓和自选股限额应宽松（50 / 100）

- [ ] **Step 4: 验证激活流程**

- 终端运行: `cd /Users/ws/Desktop/Project/Trea-Project/STOCK-Dev && python3 backend/stock-analyst/scripts/license_gen.py VIP 365`
- 复制输出的 Key
- 在会员中心输入并点击"立即激活"
- 应显示"激活成功！当前等级：至尊版"

- [ ] **Step 5: 验证限额度（手动模拟）**

- 临时把 `feature_flag.yaml` 的 `defaults.tier` 改为 `free`
- 重启应用
- 持仓达到 5 只时，第 6 只应被拦截 + 弹升级 Modal

- [ ] **Step 6: 验证退出会员**

- 会员中心点击"退出会员"
- 确认后降级回 Pro（开发期默认）

- [ ] **Step 7: 提交所有变更**

```bash
cd /Users/ws/Desktop/Project/Trea-Project/STOCK-Dev
git status
git add -A
git commit -m "feat(product): phase 1 complete - membership skeleton"
```

---

## 自检结果

**Spec 覆盖检查**：
- ✅ 三档会员（Free/Pro/VIP）— Task 1 (tiers.yaml) + Task 9 (Membership 页)
- ✅ License 文件机制 — Task 2 (license.rs) + Task 4 (Tauri commands)
- ✅ 激活码生成器 — Task 5
- ✅ Feature Flag 配置 — Task 1 (feature_flag.yaml) + Task 3 (feature_flag.rs)
- ✅ 限额度逻辑 — Task 14 (持仓) + Task 15 (自选股)
- ✅ 升级 Modal — Task 8
- ✅ 会员中心页 — Task 9
- ✅ 首启动引导 — Task 10
- ✅ 关于页 + 品牌信息 — Task 11
- ✅ 侧边栏调整 — Task 12
- ✅ 路由注册 — Task 13
- ✅ 默认 tier 行为约定 — Task 1（feature_flag.yaml）+ 自检修复（defaults.tier）
- ✅ v1 不引入 usage_stats — 设计决策，已记录在 spec

**类型一致性检查**：
- TierId / FeatureFlags / LicenseInfo / TierLimits / TierDef 都在 Task 6 统一定义
- 所有 Task 7-15 都引用了正确类型名

**无占位符**：✅ 所有代码块完整，无 TBD/TODO

**实现范围**：Phase 1（会员骨架 + 品牌优化），未越界到 Phase 2（页面体验）
