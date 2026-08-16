"""LLM Agent静态定义（用于工具清单API，不触发实际调用）"""

AGENTS = [
    {
        "name": "attraction",
        "display_name": "景点搜索专家",
        "description": "根据城市和用户偏好搜索合适的景点",
        "tools_used": ["maps_text_search"],
        "agent_type": "FunctionCallAgent",
        "max_tool_iterations": 3,
    },
    {
        "name": "weather",
        "display_name": "天气查询专家",
        "description": "查询指定城市的天气信息",
        "tools_used": ["maps_weather"],
        "agent_type": "FunctionCallAgent",
        "max_tool_iterations": 2,
    },
    {
        "name": "hotel",
        "display_name": "酒店推荐专家",
        "description": "搜索和推荐合适的酒店",
        "tools_used": ["maps_text_search"],
        "agent_type": "FunctionCallAgent",
        "max_tool_iterations": 2,
    },
    {
        "name": "restaurant",
        "display_name": "美食推荐专家",
        "description": "搜索和推荐当地特色餐厅",
        "tools_used": ["maps_text_search"],
        "agent_type": "FunctionCallAgent",
        "max_tool_iterations": 2,
    },
    {
        "name": "planner",
        "display_name": "行程规划专家",
        "description": "整合景点、天气、酒店、餐厅信息，生成完整旅行计划",
        "tools_used": [],
        "agent_type": "FunctionCallAgent (tool_calling disabled)",
        "max_tool_iterations": 0,
    },
]
