use crate::license::{read_license, LicenseInfo};
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::path::PathBuf;

/// 单个等级对应的功能上限
#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct TierLimits {
    pub max_holdings: i32,
    pub max_watchlist: i32,
    pub export_pro_report: bool,
}

/// 运行时 Feature Flag 汇总（前端可直接消费）
#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct FeatureFlags {
    /// 当前生效的等级（lowercase：free/pro/vip）
    pub tier: String,
    pub limits: TierLimits,
    /// 是否已激活 License
    pub is_licensed: bool,
    /// 已激活的 License 信息（未激活时为 None）
    pub license: Option<LicenseInfo>,
}

#[derive(Debug, Deserialize)]
struct FlagConfig {
    #[allow(dead_code)]
    version: String,
    defaults: FlagDefaults,
    tiers: HashMap<String, TierLimits>,
}

#[derive(Debug, Deserialize)]
struct FlagDefaults {
    tier: String,
    #[allow(dead_code)]
    enable_ai: bool,
    #[allow(dead_code)]
    enable_export: bool,
}

fn config_path() -> PathBuf {
    let manifest = PathBuf::from(env!("CARGO_MANIFEST_DIR"));
    let root = manifest
        .parent()
        .map(PathBuf::from)
        .unwrap_or_else(|| PathBuf::from("."));
    root.join("backend")
        .join("stock-analyst")
        .join("config")
        .join("feature_flag.yaml")
}

/// 加载 Feature Flag：读 yaml + 当前 License，决定实际生效的 tier & limits
pub fn load_flags() -> Result<FeatureFlags, String> {
    let path = config_path();
    let content = std::fs::read_to_string(&path).map_err(|e| {
        format!(
            "读取 feature_flag.yaml 失败 ({}): {}",
            path.display(),
            e
        )
    })?;
    let cfg: FlagConfig =
        serde_yaml::from_str(&content).map_err(|e| format!("解析 feature_flag.yaml 失败: {}", e))?;

    let license = read_license();
    let (tier, is_licensed) = match license.as_ref() {
        Some(info) => (info.tier.to_lowercase(), true),
        None => (cfg.defaults.tier.to_lowercase(), false),
    };
    let limits = cfg.tiers.get(&tier).cloned().ok_or_else(|| {
        format!(
            "feature_flag.yaml 中未找到等级 `{}` 对应的 limits",
            tier
        )
    })?;

    Ok(FeatureFlags {
        tier,
        limits,
        is_licensed,
        license,
    })
}
