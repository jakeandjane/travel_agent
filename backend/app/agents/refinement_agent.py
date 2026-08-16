"""计划微调 Agent — 基于当前计划进行针对性修改

两种模式：
1. advise() — 快速建议（直接 LLM，无工具调用，10-30s）
2. refine() — 完整修改（FunctionCallAgent + 高德工具，60-90s）
"""

import json
import asyncio
from hello_agents import FunctionCallAgent
from ..tools.amap_direct import AmapDirectTool
from ..services.llm_service import get_llm
from ..config import get_settings

ADVISE_TIMEOUT = 30
REFINE_TIMEOUT = 90
MAX_TOOL_ITERATIONS = 5

ADVISE_PROMPT = """你是旅行计划微调助手。用户已有一份旅行计划，现在想做一些修改，你需要给出具体可行的修改建议。

## 你的角色

你是一个熟悉旅行规划、了解城市交通和地理的旅行顾问。你已经看到了用户的完整旅行计划。

## 回复要求

1. **理解用户需求**：用 1 句话确认你理解了用户想要改什么
2. **给出具体建议**：2-3 条可行的修改方案，考虑距离、天气、行程合理性
3. **最后询问**：在回复末尾加上 "需要我帮你应用这些修改吗？"

## 回复风格

- 简洁实用，控制在 300 字以内
- 用中文回复
- 像朋友聊天一样自然
- 不要输出 JSON，直接输出文字"""

FULL_REFINE_PROMPT = """你是旅行计划微调助手。用户已有一份旅行计划，现在希望局部修改。

## 你的能力

你可以使用高德地图工具：
- `maps_text_search` — 搜索替代景点/餐厅/酒店
- `maps_weather` — 查询天气
- `maps_geo` — 地址→经纬度
- `maps_search_detail` — POI详情（评分/价格）
- `maps_direction_walking_by_address` — 步行距离
- `maps_direction_driving_by_address` — 驾车距离
- `maps_direction_transit_integrated_by_address` — 公交路线

## 修改原则

1. **精准修改**：只改用户要求的部分，其他保持完全不变
2. **综合考虑实际因素**：
   - 距离：替换餐厅/酒店时必须检查到关键地点的步行/驾车距离
   - 天气：涉及"下雨""太热""室外"等关键词时查询当天天气
   - 评分/价格：优先推荐评分高、价格合理的替代
   - 顺路程度：新地点应与当天行程顺序合理
3. **诚实沟通**：找不到合适替代时如实告知并给出建议

## 输出格式（严格 JSON）

```json
{
  "reply": "用中文解释做了什么修改、为什么这样修改",
  "changes": ["修改1描述", "修改2描述"],
  "modified_plan": { ... 完整 TripPlan JSON ... }
}
```

## TripPlan 结构

```json
{
  "city": "城市", "start_date": "YYYY-MM-DD", "end_date": "YYYY-MM-DD",
  "days": [{
    "date": "YYYY-MM-DD", "day_index": 0, "description": "概述",
    "transportation": "交通", "accommodation": "住宿类型",
    "hotel": {"name":"", "address":"", "location":{"longitude":0,"latitude":0},
              "price_range":"", "rating":"", "type":"", "estimated_cost":0},
    "attractions": [{"name":"", "address":"", "location":{"longitude":0,"latitude":0},
              "visit_duration":0, "description":"", "category":"",
              "ticket_price":0, "rating":0, "time_start":"HH:MM"}],
    "meals": [{"type":"breakfast/lunch/dinner", "name":"", "address":"",
              "location":null, "time_start":"HH:MM", "estimated_cost":0}]
  }],
  "weather_info": [{"date":"", "day_weather":"", "night_weather":"",
              "day_temp":0, "night_temp":0, "wind_direction":"", "wind_power":""}],
  "overall_suggestions": "", "budget": {"total_attractions":0, "total_hotels":0,
              "total_meals":0, "total_transportation":0, "total":0}
}
```

⚠️ modified_plan 必须是**完整** TripPlan JSON，同步更新 weather_info 和 budget。"""


class RefinementAgent:
    """计划微调 Agent — 快速建议 + 完整修改"""

    def __init__(self):
        print("🔄 初始化计划微调 Agent...")
        try:
            settings = get_settings()
            self.llm = get_llm()
            self.amap_tool = AmapDirectTool(api_key=settings.amap_api_key)

            # 完整修改 Agent（带工具）
            self.agent = FunctionCallAgent(
                name="旅行计划微调助手",
                llm=self.llm,
                system_prompt=FULL_REFINE_PROMPT,
                enable_tool_calling=True,
                max_tool_iterations=MAX_TOOL_ITERATIONS,
            )
            self.agent.add_tool(self.amap_tool)
            print("✅ 计划微调 Agent 初始化成功")

        except Exception as e:
            print(f"❌ 计划微调 Agent 初始化失败: {e}")
            raise

    async def advise(self, plan_json: dict, user_message: str) -> dict:
        """
        快速建议模式 — 直接 LLM，不使用工具，10-30 秒

        Args:
            plan_json: 当前计划完整 JSON
            user_message: 用户修改请求（自然语言）

        Returns:
            {"reply": str, "changes": [], "modified_plan": None}
        """
        # 提取关键信息作为上下文
        city = plan_json.get("city", "")
        start_date = plan_json.get("start_date", "")
        end_date = plan_json.get("end_date", "")
        days_count = len(plan_json.get("days", []))

        # 提取每天的行程概要
        day_summaries = []
        for day in plan_json.get("days", []):
            day_idx = day.get("day_index", 0) + 1
            hotel_name = day.get("hotel", {}).get("name", "未知") if day.get("hotel") else "未指定"
            attr_names = [a.get("name", "") for a in day.get("attractions", [])]
            meal_summary = []
            for m in day.get("meals", []):
                meal_summary.append(f"{m.get('type','')}:{m.get('name','')}")
            day_summaries.append(
                f"第{day_idx}天({day.get('date','')}): "
                f"酒店={hotel_name}, "
                f"景点={' → '.join(attr_names)}, "
                f"餐饮={', '.join(meal_summary)}"
            )

        plan_summary = "\n".join(day_summaries)

        # 天气信息
        weather_str = ""
        for w in plan_json.get("weather_info", []):
            weather_str += f"{w.get('date','')}: 白天{w.get('day_weather','')} {w.get('day_temp','')}°C, "
            weather_str += f"夜间{w.get('night_weather','')} {w.get('night_temp','')}°C\n"

        prompt = f"""**当前计划:**
城市: {city}
日期: {start_date} 至 {end_date}（共 {days_count} 天）

行程概要:
{plan_summary}

天气信息:
{weather_str if weather_str else "无天气数据"}

**用户修改请求:**
{user_message}"""

        print(f"   💬 快速建议: {user_message[:80]}...")

        try:
            messages = [
                {"role": "system", "content": ADVISE_PROMPT},
                {"role": "user", "content": prompt}
            ]
            response = await asyncio.wait_for(
                asyncio.to_thread(self.llm.invoke, messages),
                timeout=ADVISE_TIMEOUT
            )
            print(f"   ✅ 建议完成 ({len(response)} 字)")
            return {
                "reply": response.strip(),
                "changes": [],
                "modified_plan": None
            }
        except asyncio.TimeoutError:
            raise RuntimeError(f"响应超时（{ADVISE_TIMEOUT}s），请简化请求后重试")
        except Exception as e:
            raise RuntimeError(f"建议生成失败: {e}")

    async def refine(self, plan_json: dict, user_message: str) -> dict:
        """
        完整修改模式 — FunctionCallAgent + 高德工具，60-90 秒

        Args:
            plan_json: 当前计划完整 JSON
            user_message: 用户修改请求（自然语言）

        Returns:
            {"reply": str, "changes": list, "modified_plan": dict}
        """
        plan_str = json.dumps(plan_json, ensure_ascii=False, indent=2)
        query = f"""**当前旅行计划:**
```json
{plan_str}
```

**用户修改请求:**
{user_message}

请根据修改请求，使用高德工具搜索替代方案，然后返回完整修改后计划。"""

        print(f"   🔧 完整修改: {user_message[:80]}...")

        try:
            response = await asyncio.wait_for(
                asyncio.to_thread(self.agent.run, query),
                timeout=REFINE_TIMEOUT
            )
            result = self._parse(response)
            print(f"   ✅ 修改完成: {len(result.get('changes', []))} 处修改")
            return result
        except asyncio.TimeoutError:
            raise RuntimeError(f"修改超时（{REFINE_TIMEOUT}s），请简化请求后重试")
        except Exception as e:
            raise RuntimeError(f"修改失败: {e}")

    def _parse(self, response: str) -> dict:
        """提取 JSON 并验证必要字段"""
        try:
            json_str = None
            if "```json" in response:
                s = response.find("```json") + 7
                e = response.find("```", s)
                json_str = response[s:e].strip() if e > s else None
            elif "```" in response:
                s = response.find("```") + 3
                e = response.find("```", s)
                json_str = response[s:e].strip() if e > s else None
            elif "{" in response:
                s = response.find("{")
                e = response.rfind("}") + 1
                json_str = response[s:e]

            if not json_str:
                raise ValueError("未找到 JSON")

            data = json.loads(json_str)

            if "reply" not in data or "modified_plan" not in data:
                raise ValueError("缺少 reply 或 modified_plan")

            data.setdefault("changes", [])
            return data
        except (json.JSONDecodeError, ValueError) as e:
            raise ValueError(f"解析失败: {e}")


# 全局单例
_refinement_agent = None


def get_refinement_agent() -> RefinementAgent:
    global _refinement_agent
    if _refinement_agent is None:
        _refinement_agent = RefinementAgent()
    return _refinement_agent
