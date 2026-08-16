"""高德地图 Direct HTTP 工具（展开式 — 每个 API 端点作为独立子工具）

替代 MCPTool，不依赖 uvx/amap-mcp-server 外部进程。
使用 hello-agents 的 @tool_action 装饰器 + Tool 基类实现。
"""

import httpx
from typing import Any, Dict, List
from hello_agents.tools import Tool
from hello_agents.tools.base import tool_action


class AmapDirectTool(Tool):
    """高德地图 API 直接调用工具（可展开为 7 个子工具）

    每个子工具对应一个高德 Web API 端点，支持 Agent 直接通过
    function calling 调用，无需 MCP 中间层。
    """

    def __init__(self, api_key: str):
        """初始化高德地图工具

        Args:
            api_key: 高德地图 Web API Key
        """
        super().__init__(
            name="amap",
            description="高德地图服务：POI搜索、天气查询、地理编码、路线规划等",
            expandable=True
        )
        self.api_key = api_key
        self._base_url = "https://restapi.amap.com"

    # ============ 不需要展开的参数（父工具本身不直接调用） ============

    def get_parameters(self) -> list:
        """父工具参数（展开模式下不会被直接调用）"""
        from hello_agents.tools import ToolParameter
        return [ToolParameter(name="dummy", type="string", description="占位", required=False)]

    def run(self, parameters: Dict[str, Any]) -> str:
        """父工具不直接运行——所有调用都走子工具"""
        return "请使用展开后的子工具：maps_text_search, maps_weather, maps_geo 等"

    # ============ 子工具：通过 @tool_action 装饰 ============

    @tool_action("maps_text_search", "POI文本搜索 - 根据关键词搜索兴趣点（景点/酒店/餐厅等）")
    def text_search(self, keywords: str, city: str, citylimit: str = "true") -> str:
        """搜索 POI 兴趣点

        Args:
            keywords: 搜索关键词（如"故宫"、"酒店"、"川菜"）
            city: 城市名称（如"北京"、"上海"）
            citylimit: 是否限制在城市范围内 true/false
        """
        return self._get("/v3/place/text", {
            "keywords": keywords,
            "city": city,
            "citylimit": citylimit,
            "extensions": "all",
            "offset": "10",
        })

    @tool_action("maps_weather", "天气查询 - 查询指定城市的天气预报")
    def weather(self, city: str) -> str:
        """查询城市天气

        Args:
            city: 城市名称或行政区划代码（如"北京"、"310000"）
        """
        return self._get("/v3/weather/weatherInfo", {
            "city": city,
            "extensions": "all",
        })

    @tool_action("maps_geo", "地理编码 - 将地址转换为经纬度坐标")
    def geo_code(self, address: str, city: str = "") -> str:
        """地址转坐标

        Args:
            address: 详细地址（如"北京市朝阳区阜通东大街6号"）
            city: 城市名称（可选，提高准确率）
        """
        return self._get("/v3/geocode/geo", {
            "address": address,
            "city": city,
        })

    @tool_action("maps_search_detail", "POI详情 - 根据POI ID获取详细信息（评分/价格等）")
    def search_detail(self, id: str) -> str:
        """获取 POI 详情

        Args:
            id: POI ID（从 text_search 结果中获取）
        """
        return self._get("/v3/place/detail", {
            "id": id,
            "extensions": "all",
        })

    @tool_action("maps_direction_walking_by_address", "步行路线规划 - 根据起止地址规划步行路线")
    def direction_walking(self, origin_address: str, destination_address: str) -> str:
        """步行路线规划

        Args:
            origin_address: 起点地址
            destination_address: 终点地址
        """
        return self._get("/v3/direction/walking", {
            "origin": origin_address,
            "destination": destination_address,
        })

    @tool_action("maps_direction_driving_by_address", "驾车路线规划 - 根据起止地址规划驾车路线")
    def direction_driving(self, origin_address: str, destination_address: str) -> str:
        """驾车路线规划

        Args:
            origin_address: 起点地址
            destination_address: 终点地址
        """
        return self._get("/v3/direction/driving", {
            "origin": origin_address,
            "destination": destination_address,
            "strategy": "0",
        })

    @tool_action("maps_direction_transit_integrated_by_address",
                  "公交路线规划 - 根据起止地址规划公共交通（地铁/公交）路线")
    def direction_transit(self, origin_address: str, destination_address: str,
                          origin_city: str = "", destination_city: str = "") -> str:
        """公交路线规划

        Args:
            origin_address: 起点地址
            destination_address: 终点地址
            origin_city: 起点所在城市
            destination_city: 终点所在城市
        """
        return self._get("/v3/direction/transit/integrated", {
            "origin": origin_address,
            "destination": destination_address,
            "city": origin_city,
            "cityd": destination_city,
            "strategy": "0",
        })

    # ============ 底层 HTTP 调用 ============

    def _get(self, path: str, params: dict) -> str:
        """执行 HTTP GET 请求并返回格式化结果

        Args:
            path: API 路径（如 /v3/place/text）
            params: 查询参数（不含 key）

        Returns:
            JSON 字符串或错误描述
        """
        params["key"] = self.api_key
        url = f"{self._base_url}{path}"

        try:
            with httpx.Client(timeout=15.0) as client:
                resp = client.get(url, params=params)
                resp.raise_for_status()
                data = resp.json()

                if data.get("status") == "1":
                    return self._format_response(data)
                else:
                    return f"高德API返回错误: {data.get('info', '未知错误')}"

        except httpx.TimeoutException:
            return f"高德API请求超时: {path}"
        except httpx.HTTPError as e:
            return f"高德API网络错误: {e}"
        except Exception as e:
            return f"高德API调用异常: {e}"

    def _format_response(self, data: dict) -> str:
        """格式化高德 API 响应为紧凑 JSON 字符串

        保留核心字段，移除冗余信息（如重复的 status/infocode）
        """
        import json

        # 天气接口特殊处理
        if "forecasts" in data:
            return json.dumps({"forecasts": data["forecasts"]}, ensure_ascii=False)

        # POI 搜索/详情
        if "pois" in data:
            pois = data["pois"]
            simplified = []
            for p in pois[:10]:
                item = {
                    "name": p.get("name", ""),
                    "address": p.get("address", ""),
                    "location": p.get("location", ""),
                    "type": p.get("type", ""),
                }
                # 可选字段
                for field in ("tel", "distance", "rating", "biz_ext"):
                    if p.get(field):
                        item[field] = p[field]
                simplified.append(item)
            return json.dumps({"pois": simplified}, ensure_ascii=False)

        if "geocodes" in data:
            codes = []
            for g in data["geocodes"][:5]:
                codes.append({
                    "location": g.get("location", ""),
                    "formatted_address": g.get("formatted_address", ""),
                })
            return json.dumps({"geocodes": codes}, ensure_ascii=False)

        # 路线
        if "route" in data:
            route = data["route"]
            return json.dumps({
                "origin": route.get("origin", ""),
                "destination": route.get("destination", ""),
                "distance": route.get("distance", ""),
                "duration": route.get("duration", ""),
                "paths": route.get("paths", [])[:3],  # 最多保留 3 条路径
            }, ensure_ascii=False)

        # 兜底
        return json.dumps(data, ensure_ascii=False)[:2000]
