from typing import Callable, Dict, Any
from dataclasses import dataclass

@dataclass
class Skill:
    """单个 skill（工具）"""
    name: str
    description: str
    parameters: Dict[str, str]  # 参数名 -> 类型描述
    required: list
    func: Callable

    def to_openai_tool(self) -> Dict[str, Any]:
        """转换为 OpenAI function calling 格式"""
        properties = {}
        for param_name, param_desc in self.parameters.items():
            properties[param_name] = {
                "type": "string",
                "description": param_desc
            }
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": properties,
                    "required": self.required
                }
            }
        }

    def __call__(self, **kwargs) -> str:
        return self.func(**kwargs)


class SkillRegistry:
    """Skill 注册表"""

    def __init__(self):
        # 注册 6 个 skill（实现见后续 Task，本 Task 先占位）
        from backend.ai.skill_impl import (
            analyze_stock, analyze_portfolio, recommend_candidates,
            analyze_market, analyze_industry, search_stock
        )
        self.skills = {
            "analyze_stock": Skill(
                name="analyze_stock",
                description="对单只股票进行 12 维深度分析，包括基本面/技术/估值/资金等",
                parameters={"code": "股票代码，如 688256"},
                required=["code"],
                func=analyze_stock
            ),
            "analyze_portfolio": Skill(
                name="analyze_portfolio",
                description="分析用户的持仓组合，给出风险评估和调仓建议",
                parameters={},
                required=[],
                func=analyze_portfolio
            ),
            "recommend_candidates": Skill(
                name="recommend_candidates",
                description="从候选池中推荐短期+长期投资标的",
                parameters={},
                required=[],
                func=recommend_candidates
            ),
            "analyze_market": Skill(
                name="analyze_market",
                description="分析当前 A 股大盘整体走势、情绪、资金流向",
                parameters={},
                required=[],
                func=analyze_market
            ),
            "analyze_industry": Skill(
                name="analyze_industry",
                description="分析某个行业（如半导体、新能源）的发展前景",
                parameters={"industry_name": "行业名称，如'半导体'、'新能源'"},
                required=["industry_name"],
                func=analyze_industry
            ),
            "search_stock": Skill(
                name="search_stock",
                description="根据股票代码或名称查询股票信息",
                parameters={"query": "股票代码（如 688256）或名称（如'宁德时代'）"},
                required=["query"],
                func=search_stock
            ),
        }

    def to_openai_tools(self) -> list:
        """转换为 OpenAI tools 格式"""
        return [skill.to_openai_tool() for skill in self.skills.values()]

    def call(self, name: str, args: Dict[str, Any]) -> str:
        """调用指定 skill"""
        if name not in self.skills:
            return f"Error: skill '{name}' not found"
        try:
            return self.skills[name](**args)
        except Exception as e:
            return f"Error executing {name}: {str(e)}"
