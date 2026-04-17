"""Seed demo data: SOP for left knee bearing replacement.

Uses raw SQL to avoid ORM column mismatches with actual DB schema.
"""
import asyncio
import json
import sys
import os
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from app.core.database import AsyncSessionLocal


DEMO_SOP_NAME = "ATOM-01 左膝关节轴承更换"

DEMO_STEPS = [
    {
        "step_index": 1,
        "title": "安全确认",
        "description": "断电并确认维保隔离，确保机器人处于安全停机状态",
        "target_part": "left_knee",
        "expected_action": "verify",
        "is_critical": 1,
        "hints": json.dumps(["确认电源指示灯熄灭", "检查急停按钮已锁定"]),
        "tools_required": None,
    },
    {
        "step_index": 2,
        "title": "工具准备",
        "description": "确认 M3 内六角扳手、轴承拔取器、润滑脂就位",
        "target_part": None,
        "expected_action": "prepare",
        "is_critical": 0,
        "hints": json.dumps(["所需工具：M3 内六角扳手、轴承拔取器、锂基润滑脂"]),
        "tools_required": json.dumps(["hex_wrench_m3", "bearing_puller", "grease"]),
    },
    {
        "step_index": 3,
        "title": "外壳拆卸",
        "description": "拆卸左膝关节保护外壳 (4 颗 M3 螺丝)",
        "target_part": "left_knee_cover",
        "expected_action": "remove_screws",
        "is_critical": 0,
        "hints": json.dumps(["按对角线顺序拆卸螺丝", "注意保管垫片"]),
        "tools_required": json.dumps(["hex_wrench_m3"]),
    },
    {
        "step_index": 4,
        "title": "轴承定位",
        "description": "定位磨损轴承，记录磨损状态",
        "target_part": "left_knee_bearing",
        "expected_action": "inspect",
        "is_critical": 0,
        "hints": json.dumps(["检查滚珠表面是否有凹坑", "记录磨损照片作为证据"]),
        "tools_required": None,
    },
    {
        "step_index": 5,
        "title": "轴承更换",
        "description": "拔取旧轴承，安装新轴承 (6205-2RS)，涂润滑脂",
        "target_part": "left_knee_bearing",
        "expected_action": "replace",
        "is_critical": 1,
        "hints": json.dumps(["拔取时保持垂直用力，避免损伤轴座", "新轴承安装前涂抹薄层润滑脂"]),
        "tools_required": json.dumps(["bearing_puller"]),
    },
    {
        "step_index": 6,
        "title": "回装验证",
        "description": "回装外壳，通电，关节活动度测试 (±90°全范围旋转)",
        "target_part": "left_knee",
        "expected_action": "verify",
        "is_critical": 1,
        "hints": json.dumps(["螺丝按对角线顺序紧固", "通电后先低速空载运行 5 分钟"]),
        "tools_required": json.dumps(["hex_wrench_m3"]),
    },
]


async def seed_demo_data():
    now = datetime.now(timezone.utc).isoformat()
    async with AsyncSessionLocal() as session:
        # Check if SOP already exists
        result = await session.execute(
            text("SELECT id FROM sops WHERE name = :name"),
            {"name": DEMO_SOP_NAME},
        )
        row = result.first()
        if row:
            print(f"Demo SOP already exists: id={row[0]}")
            return row[0]

        # Insert SOP
        result = await session.execute(
            text("""
                INSERT INTO sops (name, description, applicable_model, category, difficulty_level, estimated_time, created_at, updated_at)
                VALUES (:name, :desc, :model, :cat, :diff, :time, :ca, :ua)
            """),
            {
                "name": DEMO_SOP_NAME,
                "desc": "左膝关节主轴承磨损导致过热，需拆卸外壳并更换轴承",
                "model": "ATOM-01",
                "cat": "关节维保",
                "diff": "intermediate",
                "time": 2700,
                "ca": now,
                "ua": now,
            },
        )
        sop_id = result.lastrowid

        # Insert steps
        for step in DEMO_STEPS:
            await session.execute(
                text("""
                    INSERT INTO sop_steps (sop_id, step_index, title, description, target_part, expected_action, is_critical, hints, tools_required, created_at, updated_at)
                    VALUES (:sop_id, :si, :title, :desc, :tp, :ea, :ic, :hints, :tr, :ca, :ua)
                """),
                {
                    "sop_id": sop_id,
                    "si": step["step_index"],
                    "title": step["title"],
                    "desc": step["description"],
                    "tp": step["target_part"],
                    "ea": step["expected_action"],
                    "ic": step["is_critical"],
                    "hints": step["hints"],
                    "tr": step["tools_required"],
                    "ca": now,
                    "ua": now,
                },
            )

        await session.commit()
        print(f"✅ Demo SOP seeded: id={sop_id} name={DEMO_SOP_NAME}")
        return sop_id


if __name__ == "__main__":
    asyncio.run(seed_demo_data())
