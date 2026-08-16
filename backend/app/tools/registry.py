"""工具注册表 — 纯静态，不触发任何API调用"""

from .amap_tools import AMAP_TOOLS
from .llm_tools import AGENTS


def get_all_tools() -> dict:
    """获取所有工具概览"""
    return {
        "amap_tools": {
            "total": len(AMAP_TOOLS),
            "categories": list(set(t["category"] for t in AMAP_TOOLS)),
            "tools": [{"name": t["name"], "description": t["description"]} for t in AMAP_TOOLS],
        },
        "llm_agents": {
            "total": len(AGENTS),
            "agents": [{"name": a["name"], "display_name": a["display_name"], "description": a["description"]} for a in AGENTS],
        },
    }


def get_amap_tools() -> list:
    """获取高德地图工具详情"""
    return AMAP_TOOLS


def get_agents() -> list:
    """获取Agent详情"""
    return AGENTS


def get_data_flow() -> dict:
    """获取数据流向图（结构化描述）"""
    return {
        "pipeline": [
            {"step": 1, "name": "加载用户偏好", "input": "user_id", "output": "UserProfile → 偏好文本", "source": "data/profiles/{user_id}.json"},
            {"step": 2, "name": "并行查询", "input": "TripRequest", "output": "原始查询结果×4", "agents": ["attraction", "weather", "hotel", "restaurant"]},
            {"step": 3, "name": "数据清洗", "input": "原始查询结果", "output": "结构化文本", "method": "_clean_external_data"},
            {"step": 4, "name": "LLM规划", "input": "清洗后数据 + 用户偏好", "output": "JSON旅行计划", "agent": "planner"},
            {"step": 5, "name": "保存偏好", "input": "user_id + city", "output": "更新visited_cities", "destination": "data/profiles/{user_id}.json"},
        ],
        "external_apis": ["高德地图API（直连 HTTP）", "LLM API（DeepSeek，OpenAI 兼容）"],
    }


def get_readme() -> str:
    """获取完整工具文档（Markdown）"""
    lines = [
        "# 旅行规划助手 — 工具与Agent文档",
        "",
        "## 高德地图工具（直连 HTTP）",
        "",
        "| 工具名 | 功能 | 参数 |",
        "|--------|------|------|",
    ]
    for t in AMAP_TOOLS:
        params = ", ".join(f"{k}: {v}" for k, v in t["parameters"].items())
        lines.append(f"| `{t['name']}` | {t['description']} | {params} |")

    lines += [
        "",
        "## LLM Agent",
        "",
        "| Agent | 名称 | 使用工具 | 说明 |",
        "|-------|------|----------|------|",
    ]
    for a in AGENTS:
        tools = ", ".join(a["tools_used"]) if a["tools_used"] else "无（纯LLM生成）"
        lines.append(f"| `{a['name']}` | {a['display_name']} | {tools} | {a['description']} |")

    return "\n".join(lines)


def get_simple() -> list:
    """获取简洁工具清单"""
    return [
        {"type": "amap", "name": t["name"], "desc": t["description"]}
        for t in AMAP_TOOLS
    ] + [
        {"type": "agent", "name": a["name"], "desc": a["description"]}
        for a in AGENTS
    ]
