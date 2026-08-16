"""旅行规划API路由"""

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from ...models.schemas import (
    TripRequest,
    TripPlanResponse,
    PlanHistoryResponse,
    PlanSummary,
    RefineRequest,
    RefineResponse,
    ErrorResponse
)
from ...agents.trip_planner_agent import get_trip_planner_agent
from ...memory.plan_store import get_plan_store

router = APIRouter(prefix="/trip", tags=["旅行规划"])


@router.post(
    "/plan",
    response_model=TripPlanResponse,
    summary="生成旅行计划",
    description="根据用户输入的旅行需求,生成详细的旅行计划"
)
async def plan_trip(request: TripRequest):
    """
    生成旅行计划

    Args:
        request: 旅行请求参数

    Returns:
        旅行计划响应
    """
    try:
        print(f"\n{'='*60}")
        print(f"📥 收到旅行规划请求:")
        print(f"   城市: {request.city}")
        print(f"   日期: {request.start_date} - {request.end_date}")
        print(f"   天数: {request.travel_days}")
        print(f"{'='*60}\n")

        # 获取Agent实例
        print("🔄 获取多智能体系统实例...")
        agent = get_trip_planner_agent()

        # 生成旅行计划
        print("🚀 开始生成旅行计划...")
        trip_plan = await agent.plan_trip(request)

        print("✅ 旅行计划生成成功,准备返回响应\n")

        plan_id = getattr(trip_plan, "plan_id", agent._last_plan_id)

        return TripPlanResponse(
            success=True,
            message="旅行计划生成成功",
            data=trip_plan,
            plan_id=plan_id
        )

    except RuntimeError as e:
        print(f"❌ 服务不可用: {str(e)}")
        raise HTTPException(status_code=503, detail=str(e))
    except ValueError as e:
        print(f"❌ 数据错误: {str(e)}")
        raise HTTPException(status_code=502, detail=str(e))
    except Exception as e:
        print(f"❌ 服务器内部错误: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/plan/stream",
    summary="生成旅行计划（SSE流式）",
    description="通过Server-Sent Events实时返回旅行计划生成进度"
)
async def plan_trip_stream(request: TripRequest):
    """
    生成旅行计划（SSE流式输出）

    Args:
        request: 旅行请求参数

    Returns:
        SSE事件流
    """
    agent = get_trip_planner_agent()
    return StreamingResponse(
        agent.plan_trip_stream(request),
        media_type="text/event-stream"
    )


@router.get(
    "/plans",
    response_model=PlanHistoryResponse,
    summary="获取用户历史计划列表",
    description="根据 user_id 查询历史生成的所有计划"
)
async def list_plans(user_id: str):
    """获取用户历史计划列表"""
    try:
        plan_store = get_plan_store()
        records = plan_store.list_by_user(user_id)

        summaries = [
            PlanSummary(
                plan_id=r.plan_id,
                city=r.city,
                travel_days=r.travel_days,
                start_date=r.request.get("start_date", ""),
                end_date=r.request.get("end_date", ""),
                preferences=r.preferences,
                created_at=r.created_at,
            )
            for r in records
        ]

        return PlanHistoryResponse(
            success=True,
            plans=summaries,
            total=len(summaries)
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/plan/{plan_id}",
    summary="获取单个计划详情",
    description="根据 plan_id 获取完整计划"
)
async def get_plan(plan_id: str):
    """获取单个计划"""
    plan_store = get_plan_store()
    record = plan_store.get(plan_id)
    if record is None:
        raise HTTPException(status_code=404, detail=f"计划不存在: {plan_id}")

    return {
        "success": True,
        "plan_id": record.plan_id,
        "created_at": record.created_at,
        "plan": record.plan,
    }


@router.post(
    "/plan/{plan_id}/refine",
    response_model=RefineResponse,
    summary="微调旅行计划（快速建议）",
    description="对已有计划进行AI辅助微调——输入自然语言修改请求，AI 快速给出建议，不自动修改计划"
)
async def refine_plan(plan_id: str, request: RefineRequest):
    """
    微调已有旅行计划（快速模式 — 仅给建议，不修改）

    返回建议文字，末尾询问是否要应用修改。
    用户确认后再调用 POST /apply 执行完整修改。
    """
    try:
        # 1. 加载计划
        plan_store = get_plan_store()
        record = plan_store.get(plan_id)
        if record is None:
            raise HTTPException(status_code=404, detail=f"计划不存在: {plan_id}")

        print(f"\n{'='*60}")
        print(f"💬 收到微调建议请求: plan_id={plan_id}")
        print(f"   用户消息: {request.message[:100]}...")
        print(f"{'='*60}")

        # 2. 快速建议（直接 LLM，无工具调用）
        from ...agents.refinement_agent import get_refinement_agent
        refine_agent = get_refinement_agent()

        result = await refine_agent.advise(
            plan_json=record.plan,
            user_message=request.message,
        )

        return RefineResponse(
            success=True,
            reply=result["reply"],
            changes=result.get("changes", []),
            modified_plan=None  # 快速模式不返回修改后计划
        )

    except HTTPException:
        raise
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=502, detail=str(e))
    except Exception as e:
        print(f"❌ 微调建议失败: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/plan/{plan_id}/apply",
    response_model=RefineResponse,
    summary="应用微调修改",
    description="根据之前的建议，调用高德工具搜索替代方案，执行完整计划修改"
)
async def apply_refinement(plan_id: str, request: RefineRequest):
    """
    执行完整的计划微调（完整模式 — 调用工具 + 修改计划）

    会调用高德工具搜索替代方案，修改计划并保存。
    """
    try:
        plan_store = get_plan_store()
        record = plan_store.get(plan_id)
        if record is None:
            raise HTTPException(status_code=404, detail=f"计划不存在: {plan_id}")

        print(f"\n{'='*60}")
        print(f"🔧 收到应用修改请求: plan_id={plan_id}")
        print(f"   用户消息: {request.message[:100]}...")
        print(f"{'='*60}")

        # 2. 完整修改（FunctionCallAgent + 高德工具）
        from ...agents.refinement_agent import get_refinement_agent
        refine_agent = get_refinement_agent()

        result = await refine_agent.refine(
            plan_json=record.plan,
            user_message=request.message,
        )

        # 3. 解析 modified_plan
        from ...models.schemas import TripPlan
        try:
            modified_plan = TripPlan(**result["modified_plan"])
        except Exception as pe:
            print(f"   ⚠️ modified_plan 解析警告（使用原始dict）: {pe}")
            modified_plan = result["modified_plan"]

        # 4. 保存
        from ...models.schemas import TripRequest
        original_req = TripRequest(**record.request)
        new_plan_id = plan_store.save(original_req, TripPlan(**result["modified_plan"])
                                      if isinstance(modified_plan, TripPlan)
                                      else TripPlan(**result["modified_plan"]),
                                      record.user_id)
        print(f"   💾 微调后计划已保存: {new_plan_id}")

        return RefineResponse(
            success=True,
            reply=result.get("reply", ""),
            changes=result.get("changes", []),
            modified_plan=modified_plan if isinstance(modified_plan, TripPlan) else None
        )

    except HTTPException:
        raise
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=502, detail=str(e))
    except Exception as e:
        print(f"❌ 应用修改失败: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/health",
    summary="健康检查",
    description="检查旅行规划服务是否正常"
)
async def health_check():
    """健康检查"""
    try:
        agent = get_trip_planner_agent()

        return {
            "status": "healthy",
            "service": "trip-planner",
            "agents": {
                "attraction": agent.attraction_agent.name,
                "weather": agent.weather_agent.name,
                "hotel": agent.hotel_agent.name,
                "restaurant": agent.restaurant_agent.name,
                "planner": agent.planner_agent.name,
            },
            "amap_tools_count": len(agent.amap_tool.get_expanded_tools()) if agent.amap_tool.get_expanded_tools() else 0
        }
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail=f"服务不可用: {str(e)}"
        )

