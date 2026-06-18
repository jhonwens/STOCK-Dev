"""LLMClientV2 单元测试"""
import json
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch, mock_open

from backend.ai.llm_client_v2 import LLMClientV2


# ----------------------------------------------------------------
# Fixtures
# ----------------------------------------------------------------

@pytest.fixture
def mock_config():
    return {
        "id": "m_test",
        "name": "test-model",
        "api_base": "https://api.test.com/v1",
        "api_key": "sk-test-12345",
        "model": "test-model-v1",
        "temperature": 0.5,
        "enabled": True,
    }


@pytest.fixture
def mock_config_list(tmp_path):
    """生成临时 llm_config.json 列表"""
    config_file = tmp_path / "llm_config.json"
    config_file.write_text(json.dumps([
        {
            "id": "m_disabled",
            "name": "disabled",
            "api_base": "https://a.com/v1",
            "api_key": "sk-a",
            "model": "a",
            "enabled": False,
        },
        {
            "id": "m_active",
            "name": "active",
            "api_base": "https://b.com/v1",
            "api_key": "sk-b",
            "model": "b",
            "enabled": True,
        },
    ]))
    return config_file


# ----------------------------------------------------------------
# 测试 1: 配置加载
# ----------------------------------------------------------------

def test_load_config_picks_enabled(mock_config_list):
    """_load_config 应正确选择 enabled=true 的模型"""
    with patch("backend.ai.llm_client_v2._find_config_path", return_value=mock_config_list):
        config = LLMClientV2._load_config()
    assert config is not None
    assert config["id"] == "m_active"
    assert config["enabled"] is True


def test_load_config_no_file():
    """配置文件不存在时返回 None"""
    with patch("backend.ai.llm_client_v2._find_config_path", return_value=Path("/nonexistent/llm_config.json")):
        config = LLMClientV2._load_config()
    assert config is None


def test_load_config_legacy_dict_format(tmp_path):
    """旧版单 dict 格式也应支持"""
    config_file = tmp_path / "llm_config.json"
    config_file.write_text(json.dumps({
        "api_base": "https://c.com/v1",
        "api_key": "sk-c",
        "model": "c",
    }))
    with patch("backend.ai.llm_client_v2._find_config_path", return_value=config_file):
        config = LLMClientV2._load_config()
    assert config is not None
    assert config["model"] == "c"


def test_init_raises_when_no_config():
    """无配置时应抛错"""
    with patch("backend.ai.llm_client_v2._find_config_path", return_value=Path("/nonexistent")):
        with pytest.raises(ValueError, match="No enabled LLM model"):
            LLMClientV2()


def test_init_uses_passed_config(mock_config):
    """传入 config 时应直接使用，不读文件"""
    client = LLMClientV2(config=mock_config)
    assert client.model == "test-model-v1"
    assert client.config["api_key"] == "sk-test-12345"


# ----------------------------------------------------------------
# 测试 2: chat() 透传参数
# ----------------------------------------------------------------

def test_chat_minimal_args(mock_config):
    """最少参数时也能调用"""
    client = LLMClientV2(config=mock_config)
    fake_response = MagicMock()
    with patch.object(client.client.chat.completions, "create", return_value=fake_response) as mock_create:
        result = client.chat(messages=[{"role": "user", "content": "hi"}])
        assert result is fake_response
        # 验证只传了 model 和 messages
        call_kwargs = mock_create.call_args.kwargs
        assert call_kwargs["model"] == "test-model-v1"
        assert call_kwargs["messages"] == [{"role": "user", "content": "hi"}]
        assert "tools" not in call_kwargs
        assert "temperature" not in call_kwargs
        assert "stream" not in call_kwargs


def test_chat_with_tools(mock_config):
    """传 tools 时应正确转发"""
    client = LLMClientV2(config=mock_config)
    tools = [
        {
            "type": "function",
            "function": {
                "name": "search_stock",
                "description": "search",
                "parameters": {"type": "object", "properties": {}, "required": []},
            },
        }
    ]
    fake_response = MagicMock()
    with patch.object(client.client.chat.completions, "create", return_value=fake_response) as mock_create:
        result = client.chat(
            messages=[{"role": "user", "content": "找一下茅台"}],
            tools=tools,
            tool_choice="auto",
        )
        call_kwargs = mock_create.call_args.kwargs
        assert call_kwargs["tools"] == tools
        assert call_kwargs["tool_choice"] == "auto"


def test_chat_with_temperature_and_max_tokens(mock_config):
    """temperature 和 max_tokens 应正确传递"""
    client = LLMClientV2(config=mock_config)
    with patch.object(client.client.chat.completions, "create", return_value=MagicMock()) as mock_create:
        client.chat(
            messages=[{"role": "user", "content": "hi"}],
            temperature=0.9,
            max_tokens=2048,
        )
        call_kwargs = mock_create.call_args.kwargs
        assert call_kwargs["temperature"] == 0.9
        assert call_kwargs["max_tokens"] == 2048


def test_chat_streaming(mock_config):
    """stream=True 时应透传 stream 参数"""
    client = LLMClientV2(config=mock_config)
    with patch.object(client.client.chat.completions, "create", return_value=MagicMock()) as mock_create:
        client.chat(
            messages=[{"role": "user", "content": "hi"}],
            stream=True,
        )
        call_kwargs = mock_create.call_args.kwargs
        assert call_kwargs["stream"] is True


# ----------------------------------------------------------------
# 测试 3: response 协议验证（mock 返回 OpenAI 风格 response）
# ----------------------------------------------------------------

def test_chat_response_has_tool_calls_attr(mock_config):
    """验证返回的 response 对象有 OpenAI 风格的 tool_calls 属性（agent 依赖）"""
    from types import SimpleNamespace

    client = LLMClientV2(config=mock_config)

    # 构造一个真实结构的 OpenAI 风格 response
    fake_response = SimpleNamespace(
        choices=[
            SimpleNamespace(
                message=SimpleNamespace(
                    content="",
                    tool_calls=[
                        SimpleNamespace(
                            id="call_1",
                            function=SimpleNamespace(
                                name="search_stock",
                                arguments='{"query": "x"}',
                            ),
                        )
                    ],
                )
            )
        ]
    )

    with patch.object(client.client.chat.completions, "create", return_value=fake_response):
        result = client.chat(
            messages=[{"role": "user", "content": "test"}],
            tools=[{"type": "function", "function": {"name": "search_stock"}}],
        )
        # 模拟 agent.py 访问 response.choices[0].message.tool_calls
        msg = result.choices[0].message
        assert msg.content == ""
        assert msg.tool_calls[0].function.name == "search_stock"
        assert msg.tool_calls[0].function.arguments == '{"query": "x"}'
