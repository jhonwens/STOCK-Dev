import pytest
from backend.ai.skills import Skill, SkillRegistry

def test_skill_registry_init():
    """测试 SkillRegistry 能正常初始化且包含 6 个 skill"""
    registry = SkillRegistry()
    assert len(registry.skills) == 6
    assert "analyze_stock" in registry.skills
    assert "analyze_portfolio" in registry.skills
    assert "recommend_candidates" in registry.skills
    assert "analyze_market" in registry.skills
    assert "analyze_industry" in registry.skills
    assert "search_stock" in registry.skills

def test_skill_to_openai_format():
    """测试 skill 转换为 OpenAI function calling 格式"""
    registry = SkillRegistry()
    tools = registry.to_openai_tools()
    assert len(tools) == 6
    first = tools[0]
    assert first["type"] == "function"
    assert "name" in first["function"]
    assert "description" in first["function"]
    assert "parameters" in first["function"]

def test_skill_call():
    """测试 skill 可被调用（mock 模式）"""
    from unittest.mock import patch
    registry = SkillRegistry()
    with patch.object(registry.skills["search_stock"], "func", return_value="寒武纪(688256)"):
        result = registry.call("search_stock", {"query": "寒武纪"})
        assert "寒武纪" in result
