# 衡势价值 · 产品化设计 v1.0

> 日期：2026-06-17
> 作者：Brainstorming 流程产出
> 状态：待实施

## 一、产品定位

**衡势价值** —— AI 驱动的中长线价值投资助手

| 维度 | 决策 |
|------|------|
| 产品形态 | 桌面客户端（Tauri 2.x） |
| 目标用户 | 中长线价值投资者（重持仓复盘） |
| 商业模式 | 订阅制（月/年付费） |
| 部署形态 | 完全本地运行，订阅状态通过本地 License 验证 |
| 数据归属 | 100% 本地（隐私优先） |

## 二、设计原则

1. **本地优先**：数据、计算、缓存全部本地
2. **会员可分**：免费/付费能力清晰隔离，但**默认开发期全部开放**
3. **零侵入升级**：未来接入云端鉴权时无需重构，仅替换 License 校验源
4. **品牌统一**：用户能识别"这是衡势价值的产品"，不是"个人 demo"

## 三、会员分级

| 等级 | 名称 | 主要权益 | 定价（占位） |
|------|------|---------|-------------|
| Free | 免费版 | 持仓 ≤ 5 只、自选股 ≤ 10、MD 导出受限 | ¥0 |
| Pro | 专业版 | 持仓 ≤ 50、自选股 ≤ 100、MD 导出全开放 | ¥39/月 |
| VIP | 至尊版 | 持仓/自选股不限、全部 Pro 权益 | ¥99/月 |

**v1 限额度维度**（仅 3 项）：
- 持仓数量上限
- 自选股数量上限
- MD 报告导出（仅 Pro 及以上）

**v1 不限**：
- AI 分析次数（依赖用户自有 LLM Key，做限制无意义）
- 候选推荐生成次数（数据本地，无云端成本）

## 四、License 机制

### 4.1 激活码格式

```
HSP-{TIER}-{SEG1}-{SEG2}-{SEG3}-{CHECK}
  ├── HSP：HengShi Pro 前缀
  ├── TIER：FREE / PRO / VIP
  ├── SEG1/2/3：4 位字母数字混合
  └── CHECK：CRC32(前段) mod 0x10000，4 位 hex
例：HSP-PRO-A8K3-9F2E-7D11-X4Y6
```

### 4.2 存储位置

- 路径：`~/.hengshi-value/license.dat`（macOS/Linux），`%APPDATA%/hengshi-value/license.dat`（Windows）
- 编码：JSON + base64（不加密，可解码，但需主动改文件）

### 4.3 文件结构

```json
{
  "key": "HSP-PRO-A8K3-9F2E-7D11-X4Y6",
  "tier": "pro",
  "issued_at": "2026-06-01",
  "expired_at": "2027-06-01",
  "device_id": "abc123"
}
```

### 4.4 激活码生成器

- 路径：`backend/stock-analyst/scripts/license_gen.py`
- 调用：`python license_gen.py PRO 365` → 输出 1 个 PRO 一年期激活码
- 提供 5-10 个内置测试码写入 README

## 五、Feature Flag 系统

### 5.1 配置文件

路径：`backend/stock-analyst/config/feature_flag.yaml`

```yaml
version: "1.0"
defaults:
  tier: pro            # 开发期默认全开
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

### 5.2 加载流程

```
[App 启动]
  → Rust 读 feature_flag.yaml
  → 读 license.dat
  → 若 license 缺失或过期 → 用 defaults.tier
  → 合并 tier 限值
  → 通过 invoke('get_feature_flags') 暴露给前端
```

**默认 tier 行为约定**：
- **开发期**（dev 模式）：`defaults.tier = pro`，无 license 时直接获得 Pro 权益（开发调试用）
- **正式发版**（release 模式）：通过 Tauri build flag 切换 `defaults.tier = free`，无 license 时为 Free
- v1 通过修改 `feature_flag.yaml` 手动切换；Phase 3 接入云端鉴权后此约束自动消失

**v1 不引入 usage_stats 表**：限额度是**静态配置**（YAML 中的数字），仅在用户尝试超额操作时拦截，无需统计调用次数。Phase 3 接云端 LLM 配额时再引入 usage_stats 表。

### 5.3 前端使用

```typescript
// src/services/feature_flag.ts
export async function getFeatureFlags(): Promise<FeatureFlags> {
  return invoke("get_feature_flags");
}

// 组件内
const flags = await getFeatureFlags();
if (!flags.export_pro_report) {
  // 禁用导出按钮 + 弹升级 Modal
}
```

## 六、UI 框架

### 6.1 侧边栏（保留 5 个一级入口 + 会员状态块）

```
┌─ ⚖️ 衡势价值 ────────┐
│  衡势价值  v1.0      │  ← logo + 版本号
│  ──────────────────  │
│  导航                 │
│   📊 股票池概览       │
│   📁 持仓分析         │
│   🎯 候选推荐         │
│   📈 个股分析         │
│  ──────────────────  │
│  👤 会员等级：Pro     │  ← 新增：会员状态块
│  📅 到期：2027-06-01 │
│  ──────────────────  │
│  ⚙️ 设置              │
│  ──────────────────  │
│  v1.0.0  © 衡势价值  │  ← 品牌版权
└──────────────────────┘
```

### 6.2 会员中心（新增页 /membership）

**布局**：
- 顶部大字号展示当前等级 + 到期日
- 「激活码兑换」输入框 + 兑换按钮
- 「立即升级」按钮（v1 = 占位弹窗"请联系销售"）
- 等级对比表（Free/Pro/VIP 权益对比）
- 额度使用情况卡片（持仓 N/M、自选股 N/M）

### 6.3 升级 Modal

- 触发场景：用户点击被限功能按钮
- 内容：当前等级 → 推荐升级等级 + 权益对比
- 行动按钮：「去升级」「取消」
- 跳转：点击去升级 → /membership

### 6.4 首启动欢迎页（/onboarding）

- 首次启动（无 license.dat）显示
- 4 步走：
  1. 品牌介绍（衡势价值 · 副标题）
  2. 功能概览（4 大功能 + 截图占位）
  3. LLM 配置引导（跳转设置页）
  4. 试用 / 激活（试用 = 默认 Pro 30 天 / 激活 = 输入激活码）
- 完成后写入 `onboarding_completed=true` 到 local 配置

### 6.5 关于页（/about）

- 版本号、构建时间、官方联系方式占位
- 版权信息
- 检查更新按钮（v1 = 占位）

## 七、品牌统一

| 元素 | 内容 |
|------|------|
| 产品名 | 衡势价值 |
| 英文名 | HengShi Value |
| Logo | ⚖️（天秤） |
| 副标题 | AI 驱动的中长线价值投资助手 |
| 主色 | #5b8def → #7c5fc（现有渐变） |
| 版本号格式 | v1.0.0（语义化版本） |
| 启动欢迎语 | "让价值被看见，让持仓更稳健" |

## 八、技术实现要点

### 8.1 职责分配

| 模块 | 职责 |
|------|------|
| Rust (commands.rs) | License 读写、Feature Flag 加载、SQLite 额度写入 |
| Python (license_gen.py) | 激活码生成器（仅 dev 用） |
| Frontend (services/) | UI 渲染、状态管理、Modal 触发 |
| Config (YAML) | Feature Flag 默认值、Tier 权益定义 |

### 8.2 新增 Rust 命令

```rust
#[tauri::command]
pub fn get_feature_flags() -> Result<FeatureFlags, String> { ... }

#[tauri::command]
pub fn activate_license(key: String) -> Result<LicenseInfo, String> { ... }

#[tauri::command]
pub fn deactivate_license() -> Result<(), String> { ... }

#[tauri::command]
pub fn get_license_info() -> Result<LicenseInfo, String> { ... }

#[tauri::command]
pub fn get_usage_stats() -> Result<UsageStats, String> { ... }

#[tauri::command]
pub fn check_onboarding_status() -> Result<bool, String> { ... }

#[tauri::command]
pub fn set_onboarding_completed() -> Result<(), String> { ... }
```

### 8.3 前端模块

| 文件 | 职责 |
|------|------|
| src/services/license.ts | License API 封装 |
| src/services/feature_flag.ts | Feature Flag 加载 + 缓存 |
| src/services/usage.ts | 额度统计 API 封装 |
| src/components/UpgradeModal.tsx | 升级弹窗组件 |
| src/components/UsageBadge.tsx | 额度徽章 |
| src/pages/Membership.tsx | 会员中心 |
| src/pages/Onboarding.tsx | 首启动欢迎 |
| src/pages/About.tsx | 关于页 |

### 8.4 限额度触发点

| 触发点 | 位置 | 行为 |
|--------|------|------|
| 添加第 6 只持仓 | Portfolio.tsx | 禁用「+添加持仓」按钮 + 弹升级 Modal |
| 添加第 11 只自选股 | Watchlist.tsx | 同上 |
| 导出 MD 报告 | Portfolio/Fundamental.tsx | 禁用「📥导出MD」按钮 + 弹升级 Modal |

## 九、目录结构

```
STOCK-Dev/
├── src/
│   ├── pages/
│   │   ├── Dashboard.tsx
│   │   ├── Portfolio.tsx
│   │   ├── Watchlist.tsx
│   │   ├── Fundamental.tsx
│   │   ├── Settings.tsx
│   │   ├── Membership.tsx       ← 新增
│   │   ├── Onboarding.tsx       ← 新增
│   │   └── About.tsx            ← 新增
│   ├── components/
│   │   ├── Sidebar.tsx          ← 改：加会员状态块
│   │   ├── UpgradeModal.tsx     ← 新增
│   │   ├── UsageBadge.tsx       ← 新增
│   │   └── ...
│   ├── services/
│   │   ├── api.ts
│   │   ├── license.ts           ← 新增
│   │   ├── feature_flag.ts      ← 新增
│   │   └── usage.ts             ← 新增
│   └── types/
│       └── index.ts             ← 改：加 License/Tier 类型
├── src-tauri/
│   ├── src/
│   │   ├── commands.rs          ← 改：加 license 命令
│   │   ├── license.rs           ← 新增
│   │   └── feature_flag.rs      ← 新增
├── backend/
│   └── stock-analyst/
│       ├── config/
│       │   ├── feature_flag.yaml    ← 新增
│       │   └── tiers.yaml           ← 新增
│       ├── scripts/
│       │   ├── license_gen.py       ← 新增
│       │   └── feature_flag.py      ← 新增
│       └── data/
│           └── stock_data.db        ← 加表 usage_stats
└── docs/
    └── superpowers/
        ├── specs/
        │   └── 2026-06-17-hengshi-product-design.md
        ├── plans/
        └── tests/
```

## 十、实施阶段

### Phase 1：会员体系骨架（本次实施）

- Feature Flag 配置系统（YAML + Rust 加载）
- License 文件读写（Rust 模块）
- 激活码生成器（Python 脚本）
- 会员中心页面 /membership
- 侧边栏会员状态块
- 升级 Modal 组件
- 3 个额度限制接入（持仓/自选股/MD 导出）
- 首启动欢迎页
- 关于页 + 品牌信息
- 内置 5-10 个测试激活码

### Phase 2：体验优化（后续，暂不在本次范围）

- 页面臃肿/层级整合
- 5 个页面交互流程优化
- 信息密度调整
- 视觉一致性优化

### Phase 3：云端化（v2 后续）

- 在线鉴权服务
- 跨设备同步
- 云端 LLM 代理
- 真实付费接入

## 十一、风险与约束

1. **离线 license 验证的安全局限**：本地校验可被绕过。v1 接受此约束，作为可分发的"试用版"运行
2. **跨平台路径**：License 文件路径需分别处理 macOS / Windows / Linux
3. **YAML 依赖**：Rust 端需引入 serde_yaml 解析（已存在）
4. **首次启动引导**：避免打扰老用户，提供跳过选项
5. **降级体验**：限额度被触发时升级 Modal 不阻塞主流程，提供"继续试用"选项
