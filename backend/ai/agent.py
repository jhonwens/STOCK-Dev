"""Stock Agent 引擎 - ReAct 循环"""
import json
import time
from dataclasses import dataclass, field
from typing import List, Dict, Any, Iterator, Optional
from pathlib import Path

from backend.ai.skills import SkillRegistry
from backend.ai.llm_client_v2 import LLMClientV2 as LLMClient


@dataclass
class SSEEvent:
    """SSE 事件"""
    event: str
    data: Dict[str, Any]
    id: Optional[str] = None

    def to_sse(self) -> str:
        """转换为 SSE 格式字符串"""
        lines = []
        if self.id:
            lines.append(f"id: {self.id}")
        lines.append(f"event: {self.event}")
        for k, v in self.data.items():
            lines.append(f"data: {json.dumps({k: v}, ensure_ascii=False)}")
        return "\n".join(lines) + "\n\n"


class StockAgent:
    """AI 投资顾问 Agent"""

    def __init__(self, max_steps: int = 5, step_timeout: int = 60, total_timeout: int = 300):
        self.skills = SkillRegistry()
        self.max_steps = max_steps
        self.step_timeout = step_timeout
        self.total_timeout = total_timeout
        # 现有 stock-analyst LLMClient.__init__ 不接受 config 参数
        # plan 中预设的 LLMClient(load_llm_config()) 接口仅在测试 mock 中成立
        # 这里实例化无参版本（CLI 实际运行时真实 LLM 缺少 tools 支持，见报告）
        self.llm = LLMClient()

    def run(self, user_message: str, history: list, session_id: str) -> Iterator[SSEEvent]:
        """ReAct 循环主入口"""
        start_time = time.time()
        messages = self._build_messages(user_message, history)

        # 重复调用熔断：记录最近 3 步的 tool_call 签名，
        # 若完全一致则判定 LLM 进入死循环，主动终止以避免耗尽 max_steps
        recent_step_signatures: list = []

        for step in range(1, self.max_steps + 1):
            # 超时检查
            if time.time() - start_time > self.total_timeout:
                yield SSEEvent("error", {"content": f"总超时 ({self.total_timeout}s)"})
                return

            yield SSEEvent("thinking", {
                "step": step,
                "content": f"步骤 {step}: 思考中..."
            })

            # 调用 LLM
            try:
                response = self.llm.chat(
                    messages=messages,
                    tools=self.skills.to_openai_tools(),
                    tool_choice="auto",
                )
            except Exception as e:
                yield SSEEvent("error", {"content": f"LLM 调用失败: {str(e)}"})
                return

            msg = response.choices[0].message
            tool_calls = msg.tool_calls
            content = msg.content or ""

            # 情况 1: LLM 决定调用 skill
            if tool_calls:
                # 收集本步所有 tool_call 的签名 (name, sorted_args_items)
                step_signatures: list = []
                for tc in tool_calls:
                    try:
                        args = json.loads(tc.function.arguments)
                    except (json.JSONDecodeError, AttributeError):
                        args = {}
                    sig = (tc.function.name, tuple(sorted(args.items())))
                    step_signatures.append(sig)

                # 重复熔断检测：最近 3 步签名完全一致即触发
                recent_step_signatures.append(tuple(step_signatures))
                if (
                    len(recent_step_signatures) >= 3
                    and len(set(recent_step_signatures[-3:])) == 1
                ):
                    yield SSEEvent("error", {
                        "content": "检测到重复调用同一 skill，已自动熔断。请换个问题或换个模型。"
                    })
                    yield SSEEvent("done", {
                        "step": step,
                        "duration_ms": int((time.time() - start_time) * 1000)
                    })
                    return

                for tc in tool_calls:
                    func_name = tc.function.name
                    try:
                        func_args = json.loads(tc.function.arguments)
                    except json.JSONDecodeError:
                        func_args = {}

                    yield SSEEvent("tool_call", {
                        "name": func_name,
                        "args": func_args,
                        "status": "running"
                    })

                    t0 = time.time()
                    try:
                        result = self.skills.call(func_name, func_args)
                        status = "success"
                    except Exception as e:
                        result = f"Error: {str(e)}"
                        status = "error"
                    duration_ms = int((time.time() - t0) * 1000)

                    # 截断结果预览（避免 SSE 单事件过大）
                    preview = result[:500] + ("..." if len(result) > 500 else "")

                    yield SSEEvent("tool_result", {
                        "name": func_name,
                        "status": status,
                        "result_preview": preview,
                        "duration_ms": duration_ms
                    })

                    # 把工具结果加入 messages（OpenAI tool message 格式）
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": result[:8000]  # 限制长度
                    })

                # 继续循环，让 LLM 综合
                continue

            # 情况 2: LLM 直接回答
            yield SSEEvent("final_answer", {
                "content": content,
                "markdown": True
            })
            yield SSEEvent("done", {
                "step": step,
                "duration_ms": int((time.time() - start_time) * 1000)
            })
            return

        # max_steps 用完
        yield SSEEvent("error", {"content": f"达到最大步数 ({self.max_steps})"})
        yield SSEEvent("done", {
            "step": self.max_steps,
            "duration_ms": int((time.time() - start_time) * 1000)
        })

    def _build_messages(self, user_message: str, history: list) -> list:
        """构造 LLM 消息列表"""
        from backend.ai.prompts.agent_system import SYSTEM_PROMPT

        messages = [{"role": "system", "content": SYSTEM_PROMPT}]

        # 加历史（最近 10 条）
        for h in history[-10:]:
            messages.append({
                "role": h["role"],
                "content": h["content"]
            })

        messages.append({"role": "user", "content": user_message})
        return messages
