import pytest
from unittest.mock import MagicMock, patch
from backend.ai.agent import StockAgent, SSEEvent

def test_sse_event_format():
    """SSEEvent 数据类格式"""
    evt = SSEEvent(event="thinking", data={"step": 1, "content": "test"})
    assert evt.event == "thinking"
    assert evt.data == {"step": 1, "content": "test"}

def test_agent_run_simple_chat():
    """测试 Agent 单轮无 tool call 流程"""
    # 模拟 LLM 返回（无 tool_call，直接给最终答案）
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = "你好，我是衡势价值"
    mock_response.choices[0].message.tool_calls = None

    with patch("backend.ai.agent.LLMClient") as MockClient:
        mock_client = MockClient.return_value
        mock_client.chat.return_value = mock_response

        agent = StockAgent(max_steps=5)
        events = list(agent.run("你好", history=[], session_id="test"))

        # 应该至少有 1 个 final_answer 事件
        final_events = [e for e in events if e.event == "final_answer"]
        assert len(final_events) == 1
        assert "你好" in final_events[0].data["content"]

def test_agent_run_with_tool_call():
    """测试 Agent 触发 tool_call 流程"""
    # 第一次返回 tool_call，第二次返回 final_answer
    mock_resp1 = MagicMock()
    mock_resp1.choices = [MagicMock()]
    mock_resp1.choices[0].message.content = ""
    mock_resp1.choices[0].message.tool_calls = [MagicMock()]
    mock_resp1.choices[0].message.tool_calls[0].function.name = "search_stock"
    mock_resp1.choices[0].message.tool_calls[0].function.arguments = '{"query": "宁德时代"}'

    mock_resp2 = MagicMock()
    mock_resp2.choices = [MagicMock()]
    mock_resp2.choices[0].message.content = "宁德时代是 300750"
    mock_resp2.choices[0].message.tool_calls = None

    with patch("backend.ai.agent.LLMClient") as MockClient:
        mock_client = MockClient.return_value
        mock_client.chat.side_effect = [mock_resp1, mock_resp2]

        agent = StockAgent(max_steps=5)
        events = list(agent.run("宁德时代是什么", history=[], session_id="test"))

        # 期望事件顺序: thinking, tool_call, tool_result, thinking, final_answer, done
        event_types = [e.event for e in events]
        assert "thinking" in event_types
        assert "tool_call" in event_types
        assert "tool_result" in event_types
        assert "final_answer" in event_types
        # final_answer 之后会 yield done 作为流结束标记
        assert event_types[-1] == "done"
        # final_answer 在 done 之前
        assert event_types.index("final_answer") < event_types.index("done")

def test_agent_repeat_detection_breaks_loop():
    """测试重复调用同一 skill 触发熔断"""
    # Mock LLM 让它连续返回相同的 tool_call
    mock_resp = MagicMock()
    mock_resp.choices = [MagicMock()]
    mock_resp.choices[0].message.content = ""
    mock_resp.choices[0].message.tool_calls = [MagicMock()]
    mock_resp.choices[0].message.tool_calls[0].function.name = "search_stock"
    mock_resp.choices[0].message.tool_calls[0].function.arguments = '{"query": "test"}'

    with patch("backend.ai.agent.LLMClient") as MockClient:
        mock_client = MockClient.return_value
        mock_client.chat.return_value = mock_resp  # 每次返回相同 tool_call

        agent = StockAgent(max_steps=10)  # 给足 10 步，应该 3 步就熔断
        events = list(agent.run("查一下 test", history=[], session_id="test"))

        event_types = [e.event for e in events]
        # 应该包含 error 事件
        assert "error" in event_types
        # 实际执行步数应该 <= 4（3 步重复 + 1 步熔断）
        done_events = [e for e in events if e.event == "done"]
        assert len(done_events) == 1
        assert done_events[0].data["step"] <= 4
        # 错误信息应该提示重复
        error_events = [e for e in events if e.event == "error"]
        assert any("重复" in e.data["content"] for e in error_events)
