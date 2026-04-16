"""Seed demo data: SOP for left knee bearing replacement."""
import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select
from app.core.database import async_session_factory
from app.models.sop import SOP, SOPStep


DEMO_SOP = {
    "name": "ATOM-01 左膝关节轴承更换",
    "description": "左膝关节主轴承磨损导致过热，需拆卸外壳并更换轴承",
    "applicable_model": "ATOM-01",
    "category": "关节维保",
    "difficulty_level": "intermediate",
    "estimated_time": 45 * 60,
}

DEMO_STEPS = [
    {
        "step_index": 1,
        "title": "安全确认",
        "description": "断电并确认维保隔离，确保机器人处于安全停机状态",
        "target_part": "left_knee",
        "expected_action": "verify",
        "is_critical": True,
        "severity_level": "SAFETY_HALT",
        "hints": ["确认电源指示灯熄灭", "检查急停按钮已锁定"],
    },
    {
        "step_index": 2,
        "title": "工具准备",
        "description": "确认 M3 内六角扳手、轴承拔取器、润滑脂就位",
        "target_part": None,
        "expected_action": "prepare",
        "is_critical": False,
        "tools_required": ["hex_wrench_m3", "bearing_puller", "grease"],
        "hints": ["所需工具：M3 内六角扳手、轴承拔取器、锂基润滑脂"],
    },
    {
        "step_index": 3,
        "title": "外壳拆卸",
        "description": "拆卸左膝关节保护外壳 (4 颗 M3 螺丝)",
        "target_part": "left_knee_cover",
        "expected_action": "remove_screws",
        "is_critical": False,
        "tools_required": ["hex_wrench_m3"],
        "hints": ["按对角线顺序拆卸螺丝", "注意保管垫片"],
    },
    {
        "step_index": 4,
        "title": "轴承定位",
        "description": "定位磨损轴承，记录磨损状态",
        "target_part": "left_knee_bearing",
        "expected_action": "inspect",
        "is_critical": False,
        "hints": ["检查滚珠表面是否有凹坑", "记录磨损照片作为证据"],
    },
    {
        "step_index": 5,
        "title": "轴承更换",
        "description": "拔取旧轴承，安装新轴承 (6205-2RS)，涂润滑脂",
        "target_part": "left_knee_bearing",
        "expected_action": "replace",
        "is_critical": True,
        "severity_level": "SAFETY_HALT",
        "tools_required": ["bearing_puller"],
        "hints": ["拔取时保持垂直用力，避免损伤轴座", "新轴承安装前涂抹薄层润滑脂"],
    },
    {
        "step_index": 6,
        "title": "回装验证",
        "description": "回装外壳，通电，关节活动度测试 (±90°全范围旋转)",
        "target_part": "left_knee",
        "expected_action": "verify",
        "is_critical": True,
        "tools_required": ["hex_wrench_m3"],
        "hints": ["螺丝按对角线顺序紧固", "通电后先低速空载运行 5 分钟"],
    },
]


async def seed_demo_data():
    async with async_session_factory() as session:
        # Check if SOP already exists
        result = await session.execute(
            select(SOP).where(SOP.name == DEMO_SOP["name"])
        )
        existing = result.scalar_one_or_none()

        if existing:
            print(f"Demo SOP already exists: id={existing.id}")
            return existing.id

        sop = SOP(**DEMO_SOP)
        session.add(sop)
        await session.flush()

        for step_data in DEMO_STEPS:
            step = SOPStep(sop_id=sop.id, **step_data)
            session.add(step)

        await session.commit()
        print(f"✅ Demo SOP seeded: id={sop.id} name={DEMO_SOP['name']}")
        return sop.id


if __name__ == "__main__":
    asyncio.run(seed_demo_data())
