"""用户偏好管理API路由"""

from fastapi import APIRouter, HTTPException
from ...memory.profile_manager import get_profile_manager

router = APIRouter(prefix="/user", tags=["用户偏好"])


@router.get(
    "/profile/{user_id}",
    summary="获取用户偏好",
    description="根据用户ID获取偏好档案（visited_cities / travel_style / budget_level 等）"
)
async def get_profile(user_id: str):
    """获取用户偏好档案"""
    try:
        pm = get_profile_manager()
        profile = pm.get_profile(user_id)
        return profile.model_dump()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put(
    "/profile/{user_id}",
    summary="更新用户偏好",
    description="更新用户的偏好档案"
)
async def update_profile(user_id: str, updates: dict):
    """更新用户偏好"""
    try:
        pm = get_profile_manager()
        pm.update_preferences(user_id, **updates)
        profile = pm.get_profile(user_id)
        return profile.model_dump()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
