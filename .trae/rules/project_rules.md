# 项目规范 — IPB Dev

本文档是项目执行的最高规范，所有任务都必须严格遵守。

---

## 一、文件归档路径规范

### 1.1 正式单元测试（pytest）
```
tests/
├── conftest.py              # pytest fixture（数据库 session 等）
├── test_*.py                # 模块单元测试（如 test_transformer.py）
└── ...
```
**用途：** pytest 自动化测试，永久保留

### 1.2 临时调试/验证脚本
```
dev_tools/
├── checkers/               # 数据核对脚本（check_*.py）
├── debuggers/              # 调试脚本（debug_*.py）
└── tests/                  # 临时测试脚本（test_*.py）
```
**用途：** 调试排查、临时验证，用完即弃（不提交到仓库）
**注意：** 所有临时调试脚本必须放在此处，禁止留在项目根目录

### 1.3 设计文档（Spec）
```
docs/{产品线}/specs/
├── 01-architecture-design.md
├── 02-data-model-design.md
├── 03-field-mapping.md
├── 04-api-design.md
├── 05-security-design.md
└── {日期}-{需求名}-design.md
```
**用途：** 需求分析、方案设计、技术规格说明

### 1.4 实施方案（Plan）
```
docs/{产品线}/plans/
└── {日期}-{需求名}-implementation.md
```
**用途：** 实施步骤、任务分解、进度跟踪

### 1.5 需求变更记录
```
docs/{产品线}/
└── 需求变更记录_{YYYYMMDD}.md
```
**用途：** 每次需求变更都要新建一条记录，说明变更内容、原因、影响

### 1.6 AI 提示词配置
```
backend/ai/prompts/
├── business_types.md       # 业务类型定义（LLM 分类依据）
├── schema_definition.md     # 数据库表结构定义
└── sql_rules.md            # SQL 生成规则
```
**用途：** 智能问数模块的 LLM prompt 配置，与代码分离

### 1.7 测试报告
```
docs/{产品线}/tests/
└── {日期}-{模块名}-test-report.md
```
**用途：** 手工测试、集成测试的记录报告

---

## 二、代码规范

### 2.1 新增 Python 模块
- 必须有 `__init__.py`
- 放在 `backend/` 对应模块下
- 跨模块导入使用相对导入或 `from backend.xxx import xxx`

### 2.2 API 路由
- 统一放在 `backend/api/router.py` 或 `backend/api/routes/` 下
- 遵循 RESTful 规范

### 2.3 AI 模块（智能问数）
- 核心逻辑在 `backend/ai/` 下
- prompt 配置在 `backend/ai/prompts/` 下（Markdown 文件）
- prompt 加载器：`backend/ai/prompt_loader.py`
- 禁止在 Python 代码中硬编码大段 prompt 文本

---

## 三、任务执行规范

### 3.1 接到需求后的第一步
1. **理解需求** — 明确要做什么
2. **查找规范** — 确认属于哪类归档路径
3. **如果是 Spec/Plan** — 先创建文档再执行
4. **如果是代码修改** — 先分析影响范围再动手

### 3.2 调试脚本规范
- 调试时创建的临时脚本 → `dev_tools/tests/` 或 `dev_tools/debuggers/`
- 调试完成后 → 清理调试脚本，不留在项目根目录
- 确认根目录没有 `*.py` 临时文件

### 3.3 代码修改规范
- 优先修改现有文件，而非创建新文件
- 新文件必须放对目录，不能随手放在根目录
- 涉及 lint/typecheck 的必须运行验证

### 3.4 提交前检查
- [ ] 临时调试脚本已清理
- [ ] 新文件已归档到正确目录
- [ ] 代码符合项目规范

---

## 四、文档命名规范

### 4.1 日期格式
- 文件名中的日期：`YYYY-MM-DD` 或 `YYYYMMDD`
- 例：`2026-05-08-ai-query-llm-design.md`
- 例：`需求变更记录_20260508.md`

### 4.2 命名要素
- **设计文档**：`{日期}-{功能名}-design.md`
- **实施方案**：`{日期}-{功能名}-implementation.md`
- **需求变更**：`需求变更记录_{YYYYMMDD}.md`
- **测试报告**：`{日期}-{模块名}-test-report.md`

---

## 五、目录结构总览

```
IPB-Dev/
├── backend/
│   ├── ai/
│   │   ├── prompts/           ← AI prompt 配置（Markdown）
│   │   ├── prompt_loader.py   ← prompt 加载器
│   │   ├── intent.py          ← 意图分析
│   │   ├── query_generator.py ← SQL 生成
│   │   └── ...
│   ├── api/
│   │   └── router.py
│   └── core/
│       └── database.py
├── docs/
│   ├── ipb-product/           ← IPB 产品线
│   │   ├── specs/             ← 设计文档
│   │   ├── plans/             ← 实施方案
│   │   └── tests/             ← 测试报告
│   └── superpowers/           ← 仪表盘/AI 问数
│       ├── specs/
│       └── plans/
├── dev_tools/                 ← 调试/验证脚本
│   ├── checkers/
│   ├── debuggers/
│   └── tests/
└── tests/                     ← pytest 单元测试
    ├── conftest.py
    └── test_*.py
```

---

## 六、违反规范的后果

以下行为是被禁止的：
- ❌ 临时调试脚本留在项目根目录（如 `_debug_*.py`）
- ❌ 大段 prompt 文本硬编码在 `.py` 文件中
- ❌ 新建文件随手放在根目录而不归档到正确路径
- ❌ 修改代码后不验证 lint/typecheck

---

*本文档是项目执行的最高准则，每次任务都必须遵守。*
