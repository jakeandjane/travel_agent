"""多智能体旅行规划系统"""

import json
import time
import asyncio
from typing import List
from hello_agents import FunctionCallAgent
from ..tools.amap_direct import AmapDirectTool
from ..services.llm_service import get_llm
from ..models.schemas import TripRequest, TripPlan
from ..config import get_settings
from ..memory.plan_store import get_plan_store

# ============ 常量 ============

CACHE_TTL = 600          # 缓存有效期：10分钟
QUERY_TIMEOUT = 45       # 并行查询超时：45秒（含LLM+API调用）
PLANNER_TIMEOUT = 120    # 规划超时：120秒（DeepSeek处理大prompt需要更多时间）
MAX_RETRIES = 3          # 最大重试次数
RETRY_DELAY = 1.0        # 重试间隔：1秒

# ============ Agent提示词 ============

ATTRACTION_AGENT_PROMPT = """你是景点搜索专家。根据用户需求使用高德地图工具搜索指定城市的景点。
返回搜索到的景点列表，每条包含：名称、地址、经纬度坐标、评分、门票价格、建议游览时间。"""

WEATHER_AGENT_PROMPT = """你是天气查询专家。使用高德地图工具查询指定城市的天气信息。
返回每天的天气状况、白天/夜间温度、风力等信息。"""

HOTEL_AGENT_PROMPT = """你是酒店推荐专家。使用高德地图工具搜索指定城市的酒店。
返回酒店列表，每条包含：名称、地址、评分、价格范围、类型。"""

RESTAURANT_AGENT_PROMPT = """你是美食推荐专家。使用高德地图工具搜索指定城市的特色餐厅。
返回餐厅列表，每条包含：店名、地址、人均消费、推荐菜品、评分。"""

PLANNER_AGENT_PROMPT = """你是行程规划专家。根据提供的景点、天气、酒店、餐厅信息，生成详细的旅行计划。

请严格按照以下JSON格式返回旅行计划：

```json
{
  "city": "城市名称",
  "start_date": "YYYY-MM-DD",
  "end_date": "YYYY-MM-DD",
  "days": [
    {
      "date": "YYYY-MM-DD",
      "day_index": 0,
      "description": "第1天行程概述",
      "transportation": "交通方式",
      "accommodation": "住宿类型",
      "hotel": {
        "name": "酒店名称",
        "address": "酒店地址",
        "location": {"longitude": 116.397, "latitude": 39.916},
        "price_range": "300-500元",
        "rating": "4.5",
        "type": "经济型酒店",
        "estimated_cost": 400
      },
      "attractions": [
        {
          "name": "景点名称",
          "address": "详细地址",
          "location": {"longitude": 116.397, "latitude": 39.916},
          "visit_duration": 120,
          "description": "景点描述",
          "category": "景点类别",
          "ticket_price": 60,
          "rating": 4.5,
          "time_start": "09:00"
        }
      ],
      "meals": [
        {"type": "breakfast", "name": "早餐店名", "address": "地址", "time_start": "07:30", "estimated_cost": 30},
        {"type": "lunch", "name": "午餐店名", "address": "地址", "time_start": "12:00", "estimated_cost": 60},
        {"type": "dinner", "name": "晚餐店名", "address": "地址", "time_start": "18:00", "estimated_cost": 100}
      ]
    }
  ],
  "weather_info": [
    {
      "date": "YYYY-MM-DD",
      "day_weather": "晴",
      "night_weather": "多云",
      "day_temp": 25,
      "night_temp": 15,
      "wind_direction": "南风",
      "wind_power": "1-3级"
    }
  ],
  "overall_suggestions": "总体旅行建议",
  "budget": {
    "total_attractions": 180,
    "total_hotels": 1200,
    "total_meals": 480,
    "total_transportation": 200,
    "total": 2060
  }
}
```

**重要要求：**
1. 每天安排2-3个景点，坐标必须来自搜索数据
2. 每天必须包含早中晚三餐，给出具体店名和地址
3. 每天推荐一个酒店（从酒店信息中选择）
4. 考虑景点之间的距离和交通合理性
5. 每个景点和餐饮给出 time_start 字段（HH:MM格式，如"09:00"）
6. weather_info 必须包含每一天的天气，温度为纯数字（不含°C）
7. 预算包含分项明细
8. 景点的 ticket_price 和 rating 要尽可能来自搜索数据
"""


class MultiAgentTripPlanner:
    """多智能体旅行规划系统"""

    def __init__(self):
        """初始化多智能体系统"""
        print("🔄 开始初始化多智能体旅行规划系统...")

        try:
            settings = get_settings()
            self.llm = get_llm()

            # 内存缓存: {(cache_key): (timestamp, result)}
            self._cache = {}
            self._last_plan_id = None  # 最近一次生成的 plan_id

            # 创建共享的高德地图直连工具（只创建一次，无需MCP子进程）
            print("  - 创建高德地图直连工具...")
            self.amap_tool = AmapDirectTool(api_key=settings.amap_api_key)
            tool_count = len(self.amap_tool.get_expanded_tools()) if self.amap_tool.get_expanded_tools() else 0
            print(f"    展开子工具数量: {tool_count}")

            # 创建景点搜索Agent
            print("  - 创建景点搜索Agent...")
            self.attraction_agent = FunctionCallAgent(
                name="景点搜索专家",
                llm=self.llm,
                system_prompt=ATTRACTION_AGENT_PROMPT,
                enable_tool_calling=True,
                max_tool_iterations=3
            )
            self.attraction_agent.add_tool(self.amap_tool)

            # 创建天气查询Agent
            print("  - 创建天气查询Agent...")
            self.weather_agent = FunctionCallAgent(
                name="天气查询专家",
                llm=self.llm,
                system_prompt=WEATHER_AGENT_PROMPT,
                enable_tool_calling=True,
                max_tool_iterations=2
            )
            self.weather_agent.add_tool(self.amap_tool)

            # 创建酒店推荐Agent
            print("  - 创建酒店推荐Agent...")
            self.hotel_agent = FunctionCallAgent(
                name="酒店推荐专家",
                llm=self.llm,
                system_prompt=HOTEL_AGENT_PROMPT,
                enable_tool_calling=True,
                max_tool_iterations=2
            )
            self.hotel_agent.add_tool(self.amap_tool)

            # 创建餐厅推荐Agent（独立Agent，不复用attraction_agent）
            print("  - 创建餐厅推荐Agent...")
            self.restaurant_agent = FunctionCallAgent(
                name="美食推荐专家",
                llm=self.llm,
                system_prompt=RESTAURANT_AGENT_PROMPT,
                enable_tool_calling=True,
                max_tool_iterations=2
            )
            self.restaurant_agent.add_tool(self.amap_tool)

            # 创建行程规划Agent（纯LLM生成，不需要工具）
            print("  - 创建行程规划Agent...")
            self.planner_agent = FunctionCallAgent(
                name="行程规划专家",
                llm=self.llm,
                system_prompt=PLANNER_AGENT_PROMPT,
                enable_tool_calling=False
            )

            print(f"✅ 多智能体系统初始化成功")
            print(f"   景点搜索Agent: {len(self.attraction_agent.list_tools())} 个工具")
            print(f"   天气查询Agent: {len(self.weather_agent.list_tools())} 个工具")
            print(f"   酒店推荐Agent: {len(self.hotel_agent.list_tools())} 个工具")
            print(f"   餐厅推荐Agent: {len(self.restaurant_agent.list_tools())} 个工具")
            print(f"   行程规划Agent: {len(self.planner_agent.list_tools())} 个工具 (纯LLM)")

        except Exception as e:
            print(f"❌ 多智能体系统初始化失败: {str(e)}")
            import traceback
            traceback.print_exc()
            raise

    async def plan_trip(self, request: TripRequest) -> TripPlan:
        """
        使用多智能体协作生成旅行计划

        Args:
            request: 旅行请求

        Returns:
            旅行计划
        """
        try:
            print(f"\n{'='*60}")
            print(f"🚀 开始多智能体协作规划旅行...")
            print(f"目的地: {request.city}")
            print(f"日期: {request.start_date} 至 {request.end_date}")
            print(f"天数: {request.travel_days}天")
            print(f"偏好: {', '.join(request.preferences) if request.preferences else '无'}")
            print(f"{'='*60}\n")

            # 步骤0: 加载用户偏好
            user_prefs_text = ""
            user_id = request.user_id
            if user_id:
                from ..memory.profile_manager import get_profile_manager
                pm = get_profile_manager()
                profile = pm.get_profile(user_id)
                user_prefs_text = profile.to_injection_text()
                if user_prefs_text:
                    print(f"📝 已加载用户偏好: {user_id}")

            # 步骤1: 并行查询4个数据源（30秒超时）
            print("📍 并行查询景点/天气/酒店/餐厅...")
            try:
                tasks = [
                    self._search_attractions_safe(request),
                    self._get_weather_safe(request),
                    self._search_hotels_safe(request),
                    self._search_restaurants_safe(request),
                ]
                results = await asyncio.wait_for(
                    asyncio.gather(*tasks, return_exceptions=True),
                    timeout=QUERY_TIMEOUT
                )
                attractions_data, weather_data, hotels_data, restaurants_data = [
                    r if not isinstance(r, Exception) else f"查询异常: {r}" for r in results
                ]
            except asyncio.TimeoutError:
                raise RuntimeError(f"外部查询超时（{QUERY_TIMEOUT}秒），请稍后重试")

            # 步骤2: 数据清洗
            print("🧹 清洗外部数据...")
            attractions_clean = self._clean_external_data(attractions_data, "景点")
            weather_clean = self._clean_external_data(weather_data, "天气")
            hotels_clean = self._clean_external_data(hotels_data, "酒店")
            restaurants_clean = self._clean_external_data(restaurants_data, "餐厅")

            # 步骤2.5: 查找相似历史计划（作为参考，非照搬）
            plan_store = get_plan_store()
            similar_plan = plan_store.find_similar(request)
            reference_text = self._build_reference_text(similar_plan) if similar_plan else ""

            # 步骤3: LLM规划（含重试 + 超时）
            print("📋 LLM生成行程计划...")
            planner_query = self._build_planner_query(
                request, attractions_clean, weather_clean,
                hotels_clean, restaurants_clean, user_prefs_text, reference_text
            )

            last_error = None
            for attempt in range(MAX_RETRIES):
                try:
                    planner_response = await asyncio.wait_for(
                        asyncio.to_thread(self.planner_agent.run, planner_query),
                        timeout=PLANNER_TIMEOUT
                    )
                    trip_plan = self._parse_response(planner_response, request)
                    last_error = None
                    break
                except asyncio.TimeoutError:
                    last_error = RuntimeError(f"行程规划超时（{PLANNER_TIMEOUT}秒）")
                    print(f"   超时(第{attempt + 1}/{MAX_RETRIES}次)")
                    if attempt < MAX_RETRIES - 1:
                        print("   正在重试...")
                except ValueError as e:
                    last_error = e
                    print(f"   解析失败(第{attempt + 1}/{MAX_RETRIES}次): {e}")
                    if attempt < MAX_RETRIES - 1:
                        print("   正在重试...")

            if last_error:
                raise RuntimeError(f"行程规划失败（已重试{MAX_RETRIES}次）: {last_error}")

            # 步骤4: 保存计划到历史
            plan_store = get_plan_store()
            plan_id = plan_store.save(request, trip_plan, user_id or "anonymous")
            self._last_plan_id = plan_id
            trip_plan.plan_id = plan_id  # 动态附加，供 route 层读取

            # 步骤5: 保存用户偏好（记录已访问城市）
            if user_id:
                try:
                    from ..memory.profile_manager import get_profile_manager
                    pm = get_profile_manager()
                    pm.add_visited_city(user_id, request.city)
                    print(f"💾 已更新用户偏好: {user_id} → {request.city}")
                except Exception as e:
                    print(f"   ⚠️ 保存偏好失败（不影响结果）: {e}")

            print(f"{'='*60}")
            print(f"✅ 旅行计划生成完成! plan_id={plan_id}")
            print(f"{'='*60}\n")

            return trip_plan

        except Exception as e:
            print(f"❌ 生成旅行计划失败: {str(e)}")
            import traceback
            traceback.print_exc()
            raise

    async def plan_trip_stream(self, request: TripRequest):
        """
        SSE流式版本 — 逐步yield处理进度事件

        事件类型:
        - query_start: 开始并行查询
        - query_complete: 查询完成
        - planning_start: 开始LLM规划
        - plan_complete: 规划完成
        - error: 发生错误
        """
        import json as _json

        def _sse(event: str, data: dict) -> str:
            return f"event: {event}\ndata: {_json.dumps(data, ensure_ascii=False)}\n\n"

        try:
            # 加载用户偏好
            user_prefs_text = ""
            user_id = request.user_id
            if user_id:
                from ..memory.profile_manager import get_profile_manager
                pm = get_profile_manager()
                profile = pm.get_profile(user_id)
                user_prefs_text = profile.to_injection_text()

            # 阶段1: 并行查询
            yield _sse("query_start", {"status": "正在搜索景点、天气、酒店、餐厅...", "city": request.city})

            try:
                tasks = [
                    self._search_attractions_safe(request),
                    self._get_weather_safe(request),
                    self._search_hotels_safe(request),
                    self._search_restaurants_safe(request),
                ]
                results = await asyncio.wait_for(
                    asyncio.gather(*tasks, return_exceptions=True),
                    timeout=QUERY_TIMEOUT
                )
                attractions_data, weather_data, hotels_data, restaurants_data = [
                    r if not isinstance(r, Exception) else f"查询异常: {r}" for r in results
                ]
            except asyncio.TimeoutError:
                yield _sse("error", {"message": f"外部查询超时（{QUERY_TIMEOUT}秒）"})
                return

            yield _sse("query_complete", {"status": "查询完成，开始清洗数据"})

            # 数据清洗
            attractions_clean = self._clean_external_data(attractions_data, "景点")
            weather_clean = self._clean_external_data(weather_data, "天气")
            hotels_clean = self._clean_external_data(hotels_data, "酒店")
            restaurants_clean = self._clean_external_data(restaurants_data, "餐厅")

            # 查找相似历史计划
            plan_store = get_plan_store()
            similar_plan = plan_store.find_similar(request)
            reference_text = self._build_reference_text(similar_plan) if similar_plan else ""

            # 阶段2: LLM规划
            yield _sse("planning_start", {"status": "AI正在生成旅行计划..."})

            planner_query = self._build_planner_query(
                request, attractions_clean, weather_clean,
                hotels_clean, restaurants_clean, user_prefs_text, reference_text
            )

            last_error = None
            trip_plan = None
            for attempt in range(MAX_RETRIES):
                try:
                    planner_response = await asyncio.wait_for(
                        asyncio.to_thread(self.planner_agent.run, planner_query),
                        timeout=PLANNER_TIMEOUT
                    )
                    trip_plan = self._parse_response(planner_response, request)
                    last_error = None
                    break
                except asyncio.TimeoutError:
                    last_error = RuntimeError(f"行程规划超时（{PLANNER_TIMEOUT}秒）")
                except ValueError as e:
                    last_error = e

            if last_error:
                yield _sse("error", {"message": f"行程规划失败（已重试{MAX_RETRIES}次）: {last_error}"})
                return

            # 保存计划
            plan_store = get_plan_store()
            plan_id = plan_store.save(request, trip_plan, user_id or "anonymous")
            self._last_plan_id = plan_id

            # 保存偏好
            if user_id:
                try:
                    from ..memory.profile_manager import get_profile_manager
                    pm = get_profile_manager()
                    pm.add_visited_city(user_id, request.city)
                except Exception:
                    pass

            # 阶段3: 完成
            yield _sse("plan_complete", {
                "status": "旅行计划生成完成",
                "plan": trip_plan.model_dump(),
                "plan_id": plan_id
            })

        except Exception as e:
            yield _sse("error", {"message": str(e)})

    # ============ 缓存与重试 ============

    def _cache_get(self, cache_key: str) -> str | None:
        """读取缓存，过期返回None"""
        if cache_key in self._cache:
            ts, result = self._cache[cache_key]
            if time.time() - ts < CACHE_TTL:
                print(f"   📦 缓存命中: {cache_key}")
                return result
            del self._cache[cache_key]
        return None

    def _cache_set(self, cache_key: str, result: str):
        """写入缓存"""
        self._cache[cache_key] = (time.time(), result)

    async def _retry_call(self, agent, query: str, cache_key: str) -> str:
        """
        带缓存+重试的Agent调用

        Args:
            agent: FunctionCallAgent 实例
            query: 查询字符串
            cache_key: 缓存键

        Returns:
            Agent 响应字符串
        """
        # 1. 检查缓存
        cached = self._cache_get(cache_key)
        if cached is not None:
            return cached

        # 2. 重试调用（asyncio.to_thread 实现真正的并行）
        last_error = None
        for attempt in range(MAX_RETRIES):
            try:
                result = await asyncio.to_thread(agent.run, query)
                self._cache_set(cache_key, result)
                return result
            except Exception as e:
                last_error = e
                print(f"   🔄 第{attempt + 1}/{MAX_RETRIES}次重试: {e}")
                if attempt < MAX_RETRIES - 1:
                    await asyncio.sleep(RETRY_DELAY)

        raise last_error  # 达到最大重试次数

    # ============ 安全查询方法（异常不中断其他并行任务） ============

    async def _search_attractions_safe(self, request: TripRequest) -> str:
        """安全搜索景点（含缓存+重试）"""
        try:
            keywords = request.preferences[0] if request.preferences else "景点"
            cache_key = f"attr:{request.city}:{keywords}"
            query = f"请搜索{request.city}的{keywords}相关景点，返回详细信息（名称、地址、坐标、评分、门票价格）"
            return await self._retry_call(self.attraction_agent, query, cache_key)
        except Exception as e:
            print(f"   ⚠️ 景点搜索失败（已重试{MAX_RETRIES}次）: {e}")
            return f"景点搜索暂时不可用: {e}"

    async def _get_weather_safe(self, request: TripRequest) -> str:
        """安全查询天气（含缓存+重试）"""
        try:
            cache_key = f"weather:{request.city}"
            query = f"请查询{request.city}未来{request.travel_days}天的天气信息"
            return await self._retry_call(self.weather_agent, query, cache_key)
        except Exception as e:
            print(f"   ⚠️ 天气查询失败（已重试{MAX_RETRIES}次）: {e}")
            return f"天气查询暂时不可用: {e}"

    async def _search_hotels_safe(self, request: TripRequest) -> str:
        """安全搜索酒店（含缓存+重试）"""
        try:
            cache_key = f"hotel:{request.city}:{request.accommodation}"
            query = f"请搜索{request.city}的{request.accommodation}，返回详细信息（名称、地址、评分、价格）"
            return await self._retry_call(self.hotel_agent, query, cache_key)
        except Exception as e:
            print(f"   ⚠️ 酒店搜索失败（已重试{MAX_RETRIES}次）: {e}")
            return f"酒店搜索暂时不可用: {e}"

    async def _search_restaurants_safe(self, request: TripRequest) -> str:
        """安全搜索餐厅（含缓存+重试）"""
        try:
            cache_key = f"rest:{request.city}"
            query = f"请搜索{request.city}的特色美食餐厅，返回具体店名、地址、人均消费、推荐菜品、评分"
            return await self._retry_call(self.restaurant_agent, query, cache_key)
        except Exception as e:
            print(f"   ⚠️ 餐厅搜索失败（已重试{MAX_RETRIES}次）: {e}")
            return f"餐厅搜索暂时不可用: {e}"

    # ============ 数据清洗 ============

    def _clean_external_data(self, data: str, data_type: str) -> str:
        """
        清洗外部API返回的原始数据，结构化提取关键信息

        Args:
            data: 原始返回数据
            data_type: 数据类型（景点/天气/酒店/餐厅）

        Returns:
            清洗后的结构化文本
        """
        if not data or "不可用" in str(data):
            return f"{data_type}信息暂时无法获取"

        # 尝试提取JSON
        json_str = None
        if "```json" in data:
            s = data.find("```json") + 7
            e = data.find("```", s)
            json_str = data[s:e].strip() if e > s else None
        elif "```" in data:
            s = data.find("```") + 3
            e = data.find("```", s)
            json_str = data[s:e].strip() if e > s else None

        try:
            if json_str:
                parsed = json.loads(json_str)

                if data_type in ("景点", "酒店", "餐厅"):
                    pois = (parsed.get("pois") or parsed.get("results") or [])
                    if pois:
                        lines = []
                        for poi in pois[:10]:
                            name = poi.get("name", "未知")
                            address = poi.get("address", "地址未知")
                            rating = (poi.get("rating") or
                                      poi.get("biz_ext", {}).get("rating", ""))
                            ptype = (poi.get("type") or
                                     poi.get("biz_ext", {}).get("type", ""))
                            cost = poi.get("cost") or poi.get("biz_ext", {}).get("cost", "")
                            parts = [f"- {name}"]
                            if rating:
                                parts.append(f"(评分:{rating})")
                            parts.append(f" | 地址:{address}")
                            if ptype:
                                parts.append(f" | 类型:{ptype}")
                            if cost:
                                parts.append(f" | 人均:{cost}")
                            lines.append("".join(parts))
                        return "\n".join(lines) if lines else str(data)[:500]

                elif data_type == "天气":
                    forecasts = (parsed.get("forecasts") or parsed.get("forecast") or [])
                    if forecasts:
                        lines = []
                        for fc in forecasts[:7]:
                            d = fc.get("date", "未知")
                            dw = fc.get("dayweather") or fc.get("day_weather", "")
                            nw = fc.get("nightweather") or fc.get("night_weather", "")
                            dt = fc.get("daytemp") or fc.get("day_temp", "")
                            nt = fc.get("nighttemp") or fc.get("night_temp", "")
                            lines.append(f"- {d}: 白天{dw}({dt}°) 夜间{nw}({nt}°)")
                        return "\n".join(lines) if lines else str(data)[:500]

        except (json.JSONDecodeError, AttributeError, Exception):
            pass

        # 降级：截断原始数据
        s = str(data)
        return s[:1000] if len(s) > 1000 else s

    # ============ 查询构建 ============

    def _build_planner_query(self, request, attractions, weather, hotels, restaurants, user_prefs="", reference_text=""):
        """构建给Planner Agent的完整查询"""
        query = f"""请根据以下信息生成{request.city}的{request.travel_days}天旅行计划{user_prefs}：

**基本信息:**
- 城市: {request.city}
- 日期: {request.start_date} 至 {request.end_date}
- 天数: {request.travel_days}天
- 交通方式: {request.transportation}
- 住宿: {request.accommodation}
- 偏好: {', '.join(request.preferences) if request.preferences else '无'}

**景点信息:**
{attractions}

**天气信息:**
{weather}

**酒店信息:**
{hotels}

**餐厅信息:**
{restaurants}

**要求:**
1. 每天安排2-3个景点，景点坐标必须真实准确
2. 每天必须包含早中晚三餐，根据餐厅信息推荐具体店名和地址
3. 每天推荐一个酒店（从酒店信息中选择）
4. 考虑景点之间的距离和交通合理性
5. 每个景点和餐饮给出 time_start 字段（HH:MM格式）
6. 返回完整的JSON格式数据
7. 预算包含分项明细: total_attractions(门票), total_hotels(住宿), total_meals(餐饮), total_transportation(交通), total(总费用)
8. weather_info 数组必须包含每一天的天气，温度为纯数字
"""
        if request.free_text_input:
            query += f"\n**额外要求:** {request.free_text_input}"

        if reference_text:
            query += f"\n{reference_text}"

        return query

    def _build_reference_text(self, record) -> str:
        """将历史计划格式化为参考文本（仅结构参考，非照搬）"""
        plan = record.plan
        lines = [
            "",
            "**📋 参考历史计划（仅供参考结构节奏，必须使用本次搜索到的最新数据重新规划）:**",
            f"上次({record.created_at[:10]})为 {record.city} 规划的 {record.travel_days}天 行程大致结构：",
        ]
        for day in plan.get("days", []):
            day_desc = day.get("description", "")
            items = []
            for attr in day.get("attractions", []):
                name = attr.get("name", "")
                ts = attr.get("time_start", "")
                items.append(f"{name}({ts})" if ts else name)
            lines.append(f"  - {day.get('date', '')}: {' → '.join(items) if items else day_desc}")

        lines.extend([
            "",
            "⚠️ 重要提示：",
            "1. 上述仅为结构参考——每个景点的名称/地址/坐标**必须**来自本次搜索结果",
            "2. 天气/预算**必须**基于当前实际数据重新计算",
            "3. 餐厅/酒店**必须**使用本次搜索到的数据，不可照搬历史",
        ])
        return "\n".join(lines)

    # ============ 响应解析 ============

    def _parse_response(self, response: str, request: TripRequest) -> TripPlan:
        """
        解析Agent响应为TripPlan对象

        Args:
            response: Agent响应文本
            request: 原始请求

        Returns:
            TripPlan对象

        Raises:
            ValueError: JSON解析失败
        """
        try:
            # 提取JSON
            if "```json" in response:
                s = response.find("```json") + 7
                e = response.find("```", s)
                json_str = response[s:e].strip()
            elif "```" in response:
                s = response.find("```") + 3
                e = response.find("```", s)
                json_str = response[s:e].strip()
            elif "{" in response and "}" in response:
                s = response.find("{")
                e = response.rfind("}") + 1
                json_str = response[s:e]
            else:
                raise ValueError("响应中未找到JSON数据")

            data = json.loads(json_str)
            return TripPlan(**data)

        except ValueError:
            raise
        except Exception as e:
            raise ValueError(f"解析旅行计划失败: {str(e)}")


# 全局多智能体系统实例
_multi_agent_planner = None


def get_trip_planner_agent() -> MultiAgentTripPlanner:
    """获取多智能体旅行规划系统实例（单例模式）"""
    global _multi_agent_planner

    if _multi_agent_planner is None:
        _multi_agent_planner = MultiAgentTripPlanner()

    return _multi_agent_planner
