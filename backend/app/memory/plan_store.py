"""计划存储管理器 — JSON文件持久化 + 内存缓存

存储完整的 TripPlan + TripRequest，支持：
- 按 plan_id 检索
- 按 user_id 列出历史
- 相似度匹配（同城市 + 偏好重叠）
"""

import json
import uuid
import datetime as _dt
from pathlib import Path
from typing import Optional
from pydantic import BaseModel, Field
from ..models.schemas import TripRequest, TripPlan


# ============ 存储模型 ============

class PlanRecord(BaseModel):
    """存储的计划记录（包含原始请求 + 计划结果 + 元数据）"""
    plan_id: str = Field(..., description="计划唯一ID")
    user_id: str = Field(default="anonymous", description="用户ID")
    created_at: str = Field(..., description="创建时间 ISO格式")
    city: str = Field(..., description="目的地城市（冗余，方便检索）")
    travel_days: int = Field(..., description="旅行天数（冗余，方便检索）")
    preferences: list[str] = Field(default=[], description="偏好标签（冗余，方便检索）")
    request: dict = Field(..., description="原始 TripRequest（dict）")
    plan: dict = Field(..., description="TripPlan 结果（dict）")


# ============ PlanStore ============

class PlanStore:
    """计划存储管理器（JSON文件持久化）"""

    def __init__(self, storage_dir: str = None):
        if storage_dir is None:
            storage_dir = Path(__file__).parent.parent.parent / "data" / "plans"
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        # 内存缓存: {plan_id: PlanRecord}
        self._cache: dict[str, PlanRecord] = {}

    def _file_path(self, plan_id: str) -> Path:
        return self.storage_dir / f"{plan_id}.json"

    def _generate_id(self) -> str:
        """生成唯一计划ID"""
        short_uuid = uuid.uuid4().hex[:8]
        return f"plan_{short_uuid}"

    # ============ 写入 ============

    def save(self, request: TripRequest, plan: TripPlan, user_id: str = "anonymous") -> str:
        """保存计划，返回 plan_id"""
        plan_id = self._generate_id()

        record = PlanRecord(
            plan_id=plan_id,
            user_id=user_id,
            created_at=_dt.datetime.now().isoformat(),
            city=request.city,
            travel_days=request.travel_days,
            preferences=request.preferences or [],
            request=request.model_dump(),
            plan=plan.model_dump(),
        )

        # 写入文件
        file_path = self._file_path(plan_id)
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(record.model_dump(), f, ensure_ascii=False, indent=2)

        # 写入缓存
        self._cache[plan_id] = record

        print(f"   💾 计划已保存: {plan_id} (城市:{request.city}, {request.travel_days}天)")
        return plan_id

    # ============ 读取 ============

    def get(self, plan_id: str) -> Optional[PlanRecord]:
        """按 plan_id 读取计划"""
        # 1. 缓存
        if plan_id in self._cache:
            return self._cache[plan_id]

        # 2. 文件
        file_path = self._file_path(plan_id)
        if file_path.exists():
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                record = PlanRecord(**data)
                self._cache[plan_id] = record
                return record
            except (json.JSONDecodeError, Exception) as e:
                print(f"   ⚠️ 读取计划失败 {plan_id}: {e}")
                return None

        return None

    def list_by_user(self, user_id: str, limit: int = 20) -> list[PlanRecord]:
        """列出用户的历史计划（按时间倒序）"""
        results = []

        for file_path in self.storage_dir.glob("plan_*.json"):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)

                if data.get("user_id") == user_id:
                    record = PlanRecord(**data)
                    self._cache[record.plan_id] = record  # 顺便填缓存
                    results.append(record)
            except (json.JSONDecodeError, Exception):
                continue

        # 按创建时间倒序
        results.sort(key=lambda r: r.created_at, reverse=True)
        return results[:limit]

    # ============ 相似度匹配 ============

    def find_similar(self, request: TripRequest, exclude_plan_id: str = None) -> Optional[PlanRecord]:
        """找到与请求最相似的历史计划

        匹配规则：
        - 同城市：+50 分
        - 偏好重叠：每个重叠标签 +15 分
        - 天数相近（差值 ≤1）：+10 分
        - 阈值：≥ 50 分才返回

        Args:
            request: 当前旅行请求
            exclude_plan_id: 排除的计划ID（避免匹配到刚保存的自己）

        Returns:
            最匹配的 PlanRecord，无匹配返回 None
        """
        candidates = []

        for file_path in self.storage_dir.glob("plan_*.json"):
            # 跳过刚保存的当前计划
            if exclude_plan_id and file_path.stem == exclude_plan_id:
                continue

            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)

                score = 0

                # 同城市
                if data.get("city", "") == request.city:
                    score += 50
                else:
                    continue  # 不同城市直接跳过

                # 偏好重叠
                req_prefs = set(request.preferences or [])
                rec_prefs = set(data.get("preferences", []))
                overlap = req_prefs & rec_prefs
                score += len(overlap) * 15

                # 天数相近
                rec_days = data.get("travel_days", 0)
                if abs(rec_days - request.travel_days) <= 1:
                    score += 10

                if score >= 50:
                    record = PlanRecord(**data)
                    candidates.append((score, record))

            except (json.JSONDecodeError, Exception):
                continue

        if not candidates:
            return None

        # 返回最高分且最近的一条
        candidates.sort(key=lambda x: (x[0], x[1].created_at), reverse=True)
        best = candidates[0][1]
        print(f"   📋 找到相似历史计划: {best.plan_id} (匹配度: {candidates[0][0]}分, 城市:{best.city})")
        return best

    def _all_plans(self) -> list[PlanRecord]:
        """获取所有计划（内部用）"""
        results = []
        for file_path in self.storage_dir.glob("plan_*.json"):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                results.append(PlanRecord(**data))
            except (json.JSONDecodeError, Exception):
                continue
        return results


# ============ 全局单例 ============

_plan_store: PlanStore | None = None


def get_plan_store() -> PlanStore:
    """获取 PlanStore 单例"""
    global _plan_store
    if _plan_store is None:
        _plan_store = PlanStore()
    return _plan_store
