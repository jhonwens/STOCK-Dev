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

    # tool calling 能力弱的模型，使用 auto-output 绕过
    # 注意：minimax 现在的 tool calling 已经稳定，不再加入此名单。
    # 只有 tool calling 已知有严重问题的模型才放这里。
    WEAK_TOOL_MODELS = set()

    def __init__(self, max_steps: int = 5, step_timeout: int = 60, total_timeout: int = 300):
        self.skills = SkillRegistry()
        self.max_steps = max_steps
        self.step_timeout = step_timeout
        self.total_timeout = total_timeout
        self.llm = LLMClient()
        self.model_name = self.llm.get_active_model_name()
        self._auto_output = any(w in self.model_name.lower() for w in self.WEAK_TOOL_MODELS)

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
                # 必须将 assistant 的 tool_calls 消息加入 messages（OpenAI 协议要求：
                # tool result 必须跟在对应的 assistant tool_calls 消息之后，否则模型
                # 无法将结果与调用关联，可能导致重复调用或返回空内容）
                assistant_msg = {
                    "role": "assistant",
                    "content": content if content else None,
                }
                assistant_msg["tool_calls"] = [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments,
                        },
                    }
                    for tc in tool_calls
                ]
                messages.append(assistant_msg)

                step_signatures: list = []
                for tc in tool_calls:
                    try:
                        args = json.loads(tc.function.arguments)
                    except (json.JSONDecodeError, AttributeError):
                        args = {}
                    sig = (tc.function.name, tuple(sorted(args.items())))
                    step_signatures.append(sig)

                recent_step_signatures.append(tuple(step_signatures))
                if (
                    len(recent_step_signatures) >= 4
                    and len(set(recent_step_signatures[-4:])) == 1
                ):
                    yield SSEEvent("error", {
                        "content": "AI 陷入了重复调用，已自动终止。请换个问法或稍后重试。"
                    })
                    yield SSEEvent("done", {
                        "step": step,
                        "duration_ms": int((time.time() - start_time) * 1000)
                    })
                    return

                tool_results = []
                search_found_codes: list = []
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

                    preview = result[:500] + ("..." if len(result) > 500 else "")

                    yield SSEEvent("tool_result", {
                        "name": func_name,
                        "status": status,
                        "result_preview": preview,
                        "duration_ms": duration_ms
                    })

                    messages.append({
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": result[:8000]
                    })

                    # analyze_stock: 无论成功/失败，有内容就给 LLM 展示
                    # 其他 tool: 只有成功且较长 (>100) 时才 auto-output
                    if func_name == "analyze_stock":
                        if result.strip():
                            tool_results.append((func_name, result))
                    elif status == "success" and len(result) > 100:
                        tool_results.append((func_name, result))

                    # search_stock 找到股票后，提取代码自动调用 analyze_stock
                    if (
                        func_name == "search_stock"
                        and status == "success"
                        and not result.startswith("未找到")
                    ):
                        for line in result.split("\n"):
                            line = line.strip()
                            if line.startswith("- ") and len(line) > 2:
                                code = line[2:].split()[0].strip()
                                if code.isdigit() and len(code) == 6:
                                    search_found_codes.append(code)

                # 仅弱模型需要自动链式调用（强模型能自己正确调 analyze_stock）
                if search_found_codes and self._auto_output and not tool_results:
                    code = search_found_codes[0]
                    yield SSEEvent("tool_call", {
                        "name": "analyze_stock",
                        "args": {"code": code},
                        "status": "running"
                    })
                    t0 = time.time()
                    try:
                        result = self.skills.call("analyze_stock", {"code": code})
                        status = "success"
                    except Exception as e:
                        result = f"Error: {str(e)}"
                        status = "error"
                    duration_ms = int((time.time() - t0) * 1000)
                    yield SSEEvent("tool_result", {
                        "name": "analyze_stock",
                        "status": status,
                        "result_preview": result[:500],
                        "duration_ms": duration_ms
                    })
                    if result.strip():
                        tool_results.append(("analyze_stock", result))

                # 弱模型: tool 结果直接输出，不等 LLM 决策（绕过 tool calling 缺陷）
                # 强模型: 让 LLM 对结果进行加工、总结、追问
                if tool_results and self._auto_output:
                    combined = "\n\n---\n\n".join(
                        f"### {name} 结果\n{r}" for name, r in tool_results
                    )
                    yield SSEEvent("final_answer", {
                        "content": combined,
                        "markdown": True
                    })
                    yield SSEEvent("done", {
                        "step": step,
                        "duration_ms": int((time.time() - start_time) * 1000)
                    })
                    return

                continue

            # 情况 2: LLM 直接回答
            if not content:
                content = "分析完成，AI 模型未返回具体内容。请尝试更具体的提问。"
            yield SSEEvent("final_answer", {
                "content": content,
                "markdown": True
            })
            yield SSEEvent("done", {
                "step": step,
                "duration_ms": int((time.time() - start_time) * 1000)
            })
            return

        # max_steps 用完 — 将最后一步的 tool 结果作为最终输出，避免返回空
        partial = ""
        for r in messages[::-1]:
            if isinstance(r, dict) and r.get("role") == "tool" and r.get("content"):
                partial = r["content"]
                break
        if partial:
            partial = partial[:3000] + "\n\n---\n\n*分析达到最大步骤限制，以上为部分结果。*"
            yield SSEEvent("final_answer", {
                "content": partial,
                "markdown": True
            })
        else:
            yield SSEEvent("error", {
                "content": f"分析步骤已用完（{self.max_steps} 步），未能生成完整答案。请换个问法或拆分问题。"
            })
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
