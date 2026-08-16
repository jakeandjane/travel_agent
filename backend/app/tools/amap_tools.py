"""高德地图工具静态定义（用于工具清单API，不触发实际调用）"""

AMAP_TOOLS = [
    {
        "name": "maps_text_search",
        "description": "POI文本搜索 - 根据关键词搜索兴趣点",
        "category": "search",
        "parameters": {
            "keywords": "搜索关键词",
            "city": "城市名称",
            "citylimit": "是否限制在城市范围内 (true/false)"
        }
    },
    {
        "name": "maps_weather",
        "description": "天气查询 - 查询指定城市的天气信息",
        "category": "weather",
        "parameters": {
            "city": "城市名称"
        }
    },
    {
        "name": "maps_geo",
        "description": "地理编码 - 地址转经纬度坐标",
        "category": "geo",
        "parameters": {
            "address": "地址",
            "city": "城市名称（可选）"
        }
    },
    {
        "name": "maps_search_detail",
        "description": "POI详情查询 - 根据POI ID获取详细信息",
        "category": "search",
        "parameters": {
            "id": "POI ID"
        }
    },
    {
        "name": "maps_direction_walking_by_address",
        "description": "步行路线规划 - 根据地址规划步行路线",
        "category": "route",
        "parameters": {
            "origin_address": "起点地址",
            "destination_address": "终点地址"
        }
    },
    {
        "name": "maps_direction_driving_by_address",
        "description": "驾车路线规划 - 根据地址规划驾车路线",
        "category": "route",
        "parameters": {
            "origin_address": "起点地址",
            "destination_address": "终点地址"
        }
    },
    {
        "name": "maps_direction_transit_integrated_by_address",
        "description": "公交路线规划 - 根据地址规划公共交通路线",
        "category": "route",
        "parameters": {
            "origin_address": "起点地址",
            "destination_address": "终点地址",
            "origin_city": "起点城市",
            "destination_city": "终点城市"
        }
    },
]
