"""Seed 3 fault-case SOPs and their fault_sop_mapping entries."""
import asyncio
import sys
sys.path.insert(0, ".")

from sqlalchemy import select
from app.core.database import AsyncSessionLocal
from app.models.sop import SOP, SOPStep
from app.models.fault_sop_mapping import FaultSOPMapping


SOPS = [
    {
        "name": "关节过热应急处理",
        "description": "单关节温度超限的应急降温和恢复流程",
        "applicable_model": "ATOM-01",
        "category": "thermal",
        "difficulty_level": "low",
        "estimated_time": 900,
        "fault_type": "E001_OVERHEAT",
        "steps": [
            {"step_index": 1, "title": "停机断电", "description": "按下急停按钮，确认电源指示灯熄灭", "expected_action": "power_off", "is_critical": True, "severity_level": "SAFETY_HALT", "timeout_seconds": 60, "tools_required": []},
            {"step_index": 2, "title": "等待降温", "description": "等待关节温度降至50°C以下，使用红外测温仪监测", "expected_action": "wait_cool", "is_critical": False, "severity_level": "WARN", "timeout_seconds": 300, "tools_required": ["红外测温仪"]},
            {"step_index": 3, "title": "检查散热风扇", "description": "检查关节散热风扇是否正常工作，清理灰尘堵塞", "expected_action": "inspect_fan", "is_critical": False, "severity_level": "WARN", "timeout_seconds": 180, "tools_required": ["手电筒", "压缩空气罐"]},
            {"step_index": 4, "title": "重启验证", "description": "重新上电，运行30秒空载测试，确认温度不再异常升高", "expected_action": "verify_restart", "is_critical": True, "severity_level": "WARN", "timeout_seconds": 120, "tools_required": []},
        ],
    },
    {
        "name": "关节松动检修",
        "description": "关节位置偏差超限的拆装校准流程",
        "applicable_model": "ATOM-01",
        "category": "mechanical",
        "difficulty_level": "medium",
        "estimated_time": 1800,
        "fault_type": "E005_LOOSE",
        "steps": [
            {"step_index": 1, "title": "断电锁定", "description": "断电并锁定关节防止意外移动", "expected_action": "power_off_lock", "is_critical": True, "severity_level": "SAFETY_HALT", "timeout_seconds": 60, "tools_required": []},
            {"step_index": 2, "title": "拆卸外壳", "description": "使用十字螺丝刀拆卸关节保护外壳（4颗M3螺丝）", "expected_action": "remove_cover", "is_critical": False, "severity_level": "WARN", "timeout_seconds": 300, "tools_required": ["十字螺丝刀PH2"]},
            {"step_index": 3, "title": "检查紧固件", "description": "目视检查所有紧固螺栓，标记松动位置", "expected_action": "inspect_bolts", "is_critical": False, "severity_level": "WARN", "timeout_seconds": 180, "tools_required": ["记号笔", "手电筒"]},
            {"step_index": 4, "title": "按标准扭矩紧固", "description": "使用扭矩扳手按规定力矩（8Nm）紧固所有螺栓", "expected_action": "torque_bolts", "is_critical": True, "severity_level": "WARN", "timeout_seconds": 300, "tools_required": ["扭矩扳手(8Nm)"]},
            {"step_index": 5, "title": "间隙测量", "description": "使用塞尺测量关节间隙，记录数值（标准: 0.02-0.05mm）", "expected_action": "measure_gap", "is_critical": True, "severity_level": "WARN", "timeout_seconds": 180, "tools_required": ["塞尺(0.02-0.10mm)"]},
            {"step_index": 6, "title": "回装校准", "description": "回装外壳，上电运行校准程序，验证位置精度恢复", "expected_action": "reassemble_calibrate", "is_critical": True, "severity_level": "WARN", "timeout_seconds": 300, "tools_required": ["十字螺丝刀PH2"]},
        ],
    },
    {
        "name": "电压跌落复合故障处理",
        "description": "电源电压跌落引发多关节过热的系统级排查",
        "applicable_model": "ATOM-01",
        "category": "electrical",
        "difficulty_level": "high",
        "estimated_time": 2700,
        "fault_type": "E003_VOLTAGE_DROP",
        "steps": [
            {"step_index": 1, "title": "全机断电", "description": "切断总电源，确认所有指示灯熄灭", "expected_action": "full_power_off", "is_critical": True, "severity_level": "SAFETY_HALT", "timeout_seconds": 60, "tools_required": []},
            {"step_index": 2, "title": "检查电源模块", "description": "打开电源舱，目视检查电源模块外观（鼓包、烧焦、异味）", "expected_action": "inspect_psu", "is_critical": False, "severity_level": "WARN", "timeout_seconds": 180, "tools_required": ["手电筒"]},
            {"step_index": 3, "title": "测量各路电压", "description": "使用万用表测量主路24V、逻辑5V、伺服48V各路输出", "expected_action": "measure_voltage", "is_critical": True, "severity_level": "WARN", "timeout_seconds": 300, "tools_required": ["数字万用表"]},
            {"step_index": 4, "title": "更换/修复电源", "description": "根据测量结果更换故障电源模块或修复接线", "expected_action": "replace_psu", "is_critical": True, "severity_level": "WARN", "timeout_seconds": 600, "tools_required": ["备用电源模块", "螺丝刀套装"]},
            {"step_index": 5, "title": "上电验证电压", "description": "重新上电，确认各路电压恢复正常范围", "expected_action": "verify_voltage", "is_critical": True, "severity_level": "WARN", "timeout_seconds": 120, "tools_required": ["数字万用表"]},
            {"step_index": 6, "title": "逐关节检查温度", "description": "逐个检查之前过热关节的当前温度", "expected_action": "check_temps", "is_critical": False, "severity_level": "WARN", "timeout_seconds": 180, "tools_required": ["红外测温仪"]},
            {"step_index": 7, "title": "冷却处理", "description": "对仍超温的关节进行辅助降温", "expected_action": "cool_joints", "is_critical": False, "severity_level": "WARN", "timeout_seconds": 300, "tools_required": ["压缩空气罐"]},
            {"step_index": 8, "title": "全系统功能验证", "description": "运行全关节自检程序，确认各关节正常运动", "expected_action": "full_system_test", "is_critical": True, "severity_level": "WARN", "timeout_seconds": 300, "tools_required": []},
        ],
    },
]


async def seed():
    async with AsyncSessionLocal() as db:
        for sop_data in SOPS:
            fault_type = sop_data.pop("fault_type")
            steps_data = sop_data.pop("steps")

            # Check if SOP already exists
            existing = await db.execute(select(SOP).where(SOP.name == sop_data["name"]))
            if existing.scalar_one_or_none():
                print(f"  Skip (exists): {sop_data['name']}")
                continue

            sop = SOP(**sop_data)
            db.add(sop)
            await db.flush()

            for step_data in steps_data:
                step = SOPStep(sop_id=sop.id, **step_data)
                db.add(step)

            # Create fault_sop_mapping
            mapping = FaultSOPMapping(
                fault_type=fault_type,
                sop_id=sop.id,
                difficulty=sop_data["difficulty_level"],
                priority=1,
            )
            db.add(mapping)

            print(f"  Seeded: {sop_data['name']} ({len(steps_data)} steps)")

        await db.commit()
        print("Done: 3 SOPs + mappings seeded.")


if __name__ == "__main__":
    asyncio.run(seed())
