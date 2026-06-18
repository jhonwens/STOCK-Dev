import pytest
from backend.ai.skill_impl import (
    analyze_stock, search_stock, analyze_market, analyze_industry
)

def test_search_stock_with_code():
    """测试股票代码查询（已知股：000001 平安银行）"""
    result = search_stock("000001")
    # 应该返回股票信息，至少包含"平安银行"或"000001"
    assert "000001" in result or "平安银行" in result

def test_search_stock_with_name():
    """测试股票名称查询"""
    result = search_stock("宁德时代")
    assert "宁德" in result or "300750" in result

def test_analyze_market():
    """测试大盘分析 - 应返回非空字符串"""
    result = analyze_market()
    assert len(result) > 50
    assert "大盘" in result or "上证" in result or "深证" in result

def test_analyze_industry():
    """测试行业分析"""
    result = analyze_industry("半导体")
    assert "半导体" in result
    assert len(result) > 100

def test_analyze_stock():
    """测试个股分析 - 真实调用会比较慢，这里用 30s timeout"""
    pytest.importorskip("openai")  # 跳过如果 openai 未装
    result = analyze_stock("000001")
    assert len(result) > 100
