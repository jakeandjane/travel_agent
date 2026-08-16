"""完整端到端测试 — 使用 AmapDirectTool"""
import asyncio
import sys
sys.path.insert(0, '.')

async def main():
    print("=" * 60)
    print("端到端测试: 北京2日游")
    print("=" * 60)
    from app.agents.trip_planner_agent import MultiAgentTripPlanner
    from app.models.schemas import TripRequest

    print("\n初始化 Agent 系统...")
    planner = MultiAgentTripPlanner()

    request = TripRequest(
        city="北京", start_date="2026-08-10", end_date="2026-08-11",
        travel_days=2, transportation="地铁", accommodation="经济型酒店",
        preferences=["历史文化"], free_text_input="", user_id="test_user_1"
    )

    try:
        trip_plan = await planner.plan_trip(request)
        print(f"\n{'='*60}")
        print(f"📊 结果摘要")
        print(f"{'='*60}")
        print(f"城市: {trip_plan.city}")
        print(f"日期: {trip_plan.start_date} ~ {trip_plan.end_date}")
        print(f"天数: {len(trip_plan.days)}")

        for d in trip_plan.days:
            print(f"\n--- {d.date} (Day {d.day_index + 1}) ---")
            print(f"  描述: {d.description}")
            print(f"  交通: {d.transportation}")
            print(f"  住宿: {d.accommodation}")
            if d.hotel:
                h = d.hotel
                print(f"  酒店: {h.name} | {h.address} | ¥{h.estimated_cost}/晚 | 评分{h.rating}")
            print(f"  景点 ({len(d.attractions)}个):")
            for a in d.attractions:
                print(f"    - {a.name} | {a.address} | ¥{a.ticket_price} | ⭐{a.rating} | {a.time_start} | {a.visit_duration}分钟")
            print(f"  餐饮 ({len(d.meals)}个):")
            for m in d.meals:
                print(f"    - [{m.type}] {m.name} | ¥{m.estimated_cost} | {m.time_start}")

        if trip_plan.weather_info:
            print(f"\n  天气:")
            for w in trip_plan.weather_info:
                print(f"    {w.date}: 白天{w.day_weather} {w.day_temp}° / 夜间{w.night_weather} {w.night_temp}°")

        if trip_plan.budget:
            b = trip_plan.budget
            print(f"\n💰 预算:")
            print(f"  景点门票: ¥{b.total_attractions}")
            print(f"  酒店住宿: ¥{b.total_hotels}")
            print(f"  餐饮费用: ¥{b.total_meals}")
            print(f"  交通费用: ¥{b.total_transportation}")
            print(f"  ═══════════════")
            print(f"  总费用:   ¥{b.total}")

        print(f"\n💡 建议: {trip_plan.overall_suggestions[:200]}...")

        print(f"\n{'='*60}")
        print(f"✅ 端到端测试成功!")
        print(f"{'='*60}")

    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()

asyncio.run(main())
