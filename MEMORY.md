# 项目记忆

## AI Agent 最终答案消失问题 (v5-v7 → v8 修复)

### 现象
智能分析对话中 Agent 显示 `thinking`/`tool_call` 事件，但最终答案消息消失。

### 根因

**1. 后端：缺少 assistant tool_calls 消息（`backend/ai/agent.py`）**

OpenAI tool calling 协议要求 message 序列为：
```
assistant (含 tool_calls) → tool (含 tool_call_id) → ...
```
原代码在 LLM 返回 `tool_calls` 后，直接把 tool result 追加到 `messages`，**没有先插入 assistant 的 `tool_calls` 消息**。这导致后续 LLM 调用无法正确关联工具结果，最终返回空内容或重复调用。

修复：每次 tool_calls 时先 `messages.append(assistant_msg_with_tool_calls)`，再追加 tool results。

**2. 构建流程：`cargo tauri build` 不自动重建 PyInstaller 二进制**

`tauri.conf.json` 的 `resources` 引用的是 `resources/backend-runner`（预编译的 PyInstaller 可执行文件）。修改 `backend/ai/` 下的 Python 代码后，必须手动执行：
```bash
pyinstaller backend-runner.spec
cp dist/backend-runner resources/backend-runner
```
然后再 `cargo tauri build`。否则打包的 .dmg 中仍是旧版 Python 代码。

**3. 前端：`onDone` 依赖 DB 保存且无兜底（`src/pages/AIAgent.tsx`）**

原 `onDone` 中 `loadMessages` 从 DB 重载消息后立即清除 `streamingContent`。如果 DB 没有成功保存（如 `assistant_saved` 事件未收到），答案就彻底消失。

修复：
- `finalAnswerRef`：`useRef` 保存最终答案内容
- `onFinalAnswer`：同时写 `streamingContent` 和 `messages` 状态（临时消息，正 ID 绕过 `id > 0` 过滤）
- `onDone`：加载完 DB 后检查 `messageId > 0`，如果 DB 没有则从 `finalAnswerRef` 恢复
- 使用 `sessionIdSnapshot` 防止闭包捕获的 `currentSessionId` 在异步过程中变化

### 验证方式
```bash
# 直接测试 PyInstaller 编译后的二进制
resources/backend-runner script agent_bridge_cli.py streaming <db_path> <session_id> "分析一下平安银行"
# 观察输出中必须有 final_answer 和 assistant_saved 事件
```

### 涉及文件
- `backend/ai/agent.py` — ReAct 循环，添加 assistant tool_calls 消息
- `src/pages/AIAgent.tsx` — 前端消息持久化兜底
- `src-tauri/tauri.conf.json` — resources 引用路径
- `backend-runner.spec` — PyInstaller 打包配置
- `resources/backend-runner` — 预编译的 PyInstaller 可执行文件（需手动重建）

## API Key 被打包进 .app 问题 (v8 → v9 修复)

### 现象
`tauri.conf.json` 的 `resources` 中配置了 `"../config": "config"`，导致 `config/llm_config.json`（内含 api_key）被完整打包进 `.app/Contents/Resources/config/`。任何人都可以从 .dmg 中提取出用户的 API key。

### 修复
1. `src-tauri/tauri.conf.json` — 从 resources 中去掉 `"../config": "config"`
2. `src-tauri/src/main.rs` — 删掉从包内复制 `llm_config.json` 到用户数据目录的逻辑（该目录也不再存在于包内）
3. 用户配置改为仅通过前端设置页面 `save_llm_config` 保存到 `~/Library/Application Support/com.hengshi-value.app/config/llm_config.json`，首次启动时该目录为空

### 教训
- **永远不要将用户凭据/配置目录放进 Tauri 的 `resources`**。`resources` 是只读的、随 .app 分发的，其中所有文件都对用户可见。
- 需要预先填充的配置文件，应在首次启动时通过默认值生成，或在文档中指导用户首次打开设置页面填写。

### 涉及文件
- `src-tauri/tauri.conf.json` — resources 定义
- `src-tauri/src/main.rs` — 启动时配置初始化逻辑
