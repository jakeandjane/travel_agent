"""用户偏好数据模型"""

from typing import List, Optional
from pydantic import BaseModel, Field


class UserProfile(BaseModel):
    """用户偏好档案"""
    user_id: str = Field(..., description="用户ID")
    dietary_restrictions: List[str] = Field(default=[], description="饮食禁忌")
    travel_style: List[str] = Field(default=[], description="旅行风格 (如: 历史文化, 自然风光, 美食探店)")
    budget_level: str = Field(default="适中", description="预算水平 (经济/适中/高端)")
    visited_cities: List[str] = Field(default=[], description="已去过的城市")
    preferred_activities: List[str] = Field(default=[], description="偏好活动")
    accommodation_preference: str = Field(default="", description="住宿偏好")

    def to_injection_text(self) -> str:
        """生成注入 prompt 的用户偏好文本"""
        lines = ["\n**用户偏好:**"]

        if self.visited_cities:
            lines.append(f"- 已去过城市: {', '.join(self.visited_cities)}")

        if self.travel_style:
            lines.append(f"- 旅行风格: {', '.join(self.travel_style)}")

        if self.budget_level:
            lines.append(f"- 预算水平: {self.budget_level}")

        if self.dietary_restrictions:
            lines.append(f"- 饮食禁忌: {', '.join(self.dietary_restrictions)}")

        if self.preferred_activities:
            lines.append(f"- 偏好活动: {', '.join(self.preferred_activities)}")

        if self.accommodation_preference:
            lines.append(f"- 住宿偏好: {self.accommodation_preference}")

        return "\n".join(lines) if len(lines) > 1 else ""
