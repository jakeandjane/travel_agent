"""工具管理API路由 — 纯静态，不触发任何API调用"""

from fastapi import APIRouter
from ...tools.registry import (
    get_all_tools,
    get_amap_tools,
    get_agents,
    get_data_flow,
    get_readme,
    get_simple,
)

router = APIRouter(prefix="/tools", tags=["工具管理"])


@router.get("/", summary="工具清单概览")
async def tools_overview():
    """获取所有工具和Agent的概览"""
    return {"success": True, "data": get_all_tools()}


@router.get("/amap", summary="高德地图工具详情")
async def amap_tools():
    """获取高德地图工具的详细信息"""
    return {"success": True, "data": get_amap_tools()}


@router.get("/agents", summary="Agent详情")
async def agents():
    """获取所有Agent的详细信息"""
    return {"success": True, "data": get_agents()}


@router.get("/data-flow", summary="数据流向图")
async def data_flow():
    """获取数据流向图"""
    return {"success": True, "data": get_data_flow()}


@router.get("/readme", summary="完整工具文档")
async def readme():
    """获取完整的工具文档（Markdown格式）"""
    return {"success": True, "data": get_readme()}


@router.get("/simple", summary="简洁工具清单")
async def simple():
    """获取简洁工具清单"""
    return {"success": True, "data": get_simple()}
