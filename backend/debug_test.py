"""逐步调试 — 排查Agent查询为什么返回空数据"""
import asyncio
import sys
sys.path.insert(0, '.')

async def main():
    print("=" * 60)
    print("Step 1: 初始化 Agent")
    print("=" * 60)
    from app.agents.trip_planner_agent import MultiAgentTripPlanner
    from app.models.schemas import TripRequest

    planner = MultiAgentTripPlanner()
    print(f"\nattraction_agent tools: {planner.attraction_agent.list_tools()}")
    print(f"weather_agent tools: {planner.weather_agent.list_tools()}")
    print(f"hotel_agent tools: {planner.hotel_agent.list_tools()}")
    print(f"restaurant_agent tools: {planner.restaurant_agent.list_tools()}")
    print(f"\namap_tool expanded: {planner.amap_tool._available_tools}")

    request = TripRequest(
        city="北京", start_date="2026-08-10", end_date="2026-08-11",
        travel_days=2, transportation="地铁", accommodation="经济型酒店",
        preferences=["历史文化"], free_text_input="", user_id="test_user_1"
    )

    print("\n" + "=" * 60)
    print("Step 2: 测试单个 Agent 查询 (景点)")
    print("=" * 60)
    try:
        query = f"请搜索北京的历史文化相关景点，返回详细信息（名称、地址、坐标、评分、门票价格）"
        print(f"Query: {query}")
        print("Running attraction_agent...")
        # Use to_thread for true async
        result = await asyncio.to_thread(planner.attraction_agent.run, query)
        print(f"\nResult type: {type(result)}")
        print(f"Result length: {len(str(result))}")
        print(f"Result (first 500 chars): {str(result)[:500]}")
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()

    print("\n" + "=" * 60)
    print("Step 3: 测试单个 Agent 查询 (天气)")
    print("=" * 60)
    try:
        query = f"请查询北京未来2天的天气信息"
        print(f"Query: {query}")
        result = await asyncio.to_thread(planner.weather_agent.run, query)
        print(f"\nResult type: {type(result)}")
        print(f"Result (first 300 chars): {str(result)[:300]}")
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()

    print("\n" + "=" * 60)
    print("Step 4: 运行完整 plan_trip 流程")
    print("=" * 60)
    try:
        trip_plan = await planner.plan_trip(request)
        print(f"\ncity: {trip_plan.city}")
        print(f"days: {len(trip_plan.days)}")
        print(f"budget: {trip_plan.budget}")
        if trip_plan.days:
            d = trip_plan.days[0]
            print(f"Day 0: {len(d.attractions)} attractions, {len(d.meals)} meals, hotel={d.hotel}")
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()

asyncio.run(main())
