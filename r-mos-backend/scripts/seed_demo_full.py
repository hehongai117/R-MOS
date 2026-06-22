"""
演示数据种子脚本 — 创建完整的客户演示数据。

用途:
    cd r-mos-backend
    python scripts/seed_demo_full.py           # 幂等运行
    python scripts/seed_demo_full.py --reset   # 清除演示数据后重建
"""
from __future__ import annotations

import argparse
import asyncio
import os
import sys
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, os.path.realpath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.core.migration_contract import assert_migration_contract
from app.core.security import hash_password

# Models
from app.models.user import User
from app.models.user_preference import UserPreference
from app.models.rbac import Permission, Role, RolePermission, UserRole
from app.models.robot_model import (
    RobotModel, RobotStatus, RobotVisibility, TeacherRobotBinding,
)
from app.models.robot_asset import RobotAsset, AssetType
from app.models.sop import SOP, SOPStep
from app.models.teaching import (
    Assignment, AssignmentAttempt, Course, Enrollment,
    GuidancePolicy, TeachingClass,
)
from app.models.task import Task
from app.models.training import TrainingSession, SessionStepRecord
from app.models.training_submission import TrainingSubmission
from app.models.skill_profile import StudentSkillProfile, StudentWeakStep
from app.models.knowledge_document import KnowledgeDocument
from app.models.fault import FaultCase
from app.models.fault_sop_mapping import FaultSOPMapping

engine = create_async_engine(settings.DATABASE_URL, echo=False)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

DEMO_DOMAIN = "@rmos.demo"

# ────────────────────────────────────────────────────────
# Data Definitions
# ────────────────────────────────────────────────────────

@dataclass(frozen=True)
class SeedUser:
    email: str
    password: str
    full_name: str
    role: str
    guidance_mode: str = "on_demand"


DEMO_USERS = (
    SeedUser("teacher1@rmos.demo", "Teacher@123", "张明远", "teacher"),
    SeedUser("student1@rmos.demo", "Student@123", "李思远", "student", "full_time"),
    SeedUser("student2@rmos.demo", "Student@123", "王雨萱", "student", "on_demand"),
    SeedUser("student3@rmos.demo", "Student@123", "陈浩然", "student", "on_demand"),
    SeedUser("student4@rmos.demo", "Student@123", "刘诗涵", "student", "full_time"),
    SeedUser("student5@rmos.demo", "Student@123", "赵天宇", "student", "silent"),
)

ROLE_SPECS = {"teacher": "教师", "student": "学生"}

PERMISSION_SPECS = {
    "agent:read": ("读取智能体知识与项目资产", "agent", "read"),
    "agent:execute": ("执行智能体知识与项目操作", "agent", "execute"),
    "teaching:read": ("读取教学域基础数据", "teaching", "read"),
    "assignment_attempts:read": ("读取作业尝试", "assignment_attempts", "read"),
}

ROLE_PERMISSION_KEYS = {
    "teacher": {"agent:read", "agent:execute", "teaching:read", "assignment_attempts:read"},
    "student": {"agent:read", "teaching:read", "assignment_attempts:read"},
}

# --- SOP Definitions ---

SOP_DEFS = [
    {
        "name": "ATOM-01 膝关节轴承更换",
        "description": "更换 ATOM-01 人形机器人膝关节轴承的标准操作流程，涵盖拆卸、检测、更换及校准全流程。",
        "category": "关节维保",
        "difficulty_level": "medium",
        "estimated_time": 2700,
        "steps": [
            {
                "step_index": 1, "title": "断电安全锁止",
                "description": "关闭机器人主电源，确认电容放电完成，挂安全锁止牌。",
                "target_part": "power_system", "expected_action": "power_off",
                "is_critical": True, "severity_level": "SAFETY_HALT",
                "timeout_seconds": 120, "allow_skip": False,
                "tools_required": ["安全锁止牌", "绝缘手套"],
                "hints": ["确认电容指示灯完全熄灭再操作"],
            },
            {
                "step_index": 2, "title": "准备工位与工具",
                "description": "清理工作台面，准备扭矩扳手、轴承拉拔器、千分尺等工具。",
                "target_part": None, "expected_action": "prepare",
                "is_critical": False, "severity_level": "INFO",
                "timeout_seconds": 300, "allow_skip": False,
                "tools_required": ["扭矩扳手", "轴承拉拔器", "千分尺", "清洁布"],
                "hints": ["按工具清单逐一核对"],
            },
            {
                "step_index": 3, "title": "目视检查轴承外观",
                "description": "检查膝关节轴承座有无裂纹、变色、润滑脂泄漏等异常。",
                "target_part": "left_knee_joint", "expected_action": "inspect",
                "is_critical": False, "severity_level": "WARN",
                "timeout_seconds": 300, "allow_skip": False,
                "tools_required": ["LED 手电筒", "放大镜"],
                "hints": ["重点关注轴承密封圈是否完好"],
            },
            {
                "step_index": 4, "title": "测量轴承间隙",
                "description": "使用千分尺测量轴承径向间隙，记录数值并与标准值比对。",
                "target_part": "left_knee_joint", "expected_action": "measure",
                "is_critical": False, "severity_level": "WARN",
                "timeout_seconds": 300, "allow_skip": False,
                "tools_required": ["千分尺"],
                "hints": ["标准间隙范围：0.02-0.05mm"],
                "action_params": {"standard_min": 0.02, "standard_max": 0.05, "unit": "mm"},
            },
            {
                "step_index": 5, "title": "拆卸旧轴承",
                "description": "使用轴承拉拔器拆卸磨损轴承，注意保持轴颈表面完整。",
                "target_part": "left_knee_joint", "expected_action": "execute",
                "is_critical": True, "severity_level": "WARN",
                "timeout_seconds": 600, "allow_skip": False,
                "tools_required": ["轴承拉拔器", "防护眼镜"],
                "hints": ["均匀施力，避免偏载拉拔"],
            },
            {
                "step_index": 6, "title": "安装新轴承",
                "description": "将新轴承加热至 80°C 后套装到位，使用扭矩扳手按规定力矩锁紧。",
                "target_part": "left_knee_joint", "expected_action": "replace",
                "is_critical": True, "severity_level": "WARN",
                "timeout_seconds": 600, "allow_skip": False,
                "tools_required": ["轴承加热器", "扭矩扳手"],
                "hints": ["锁紧力矩：25 N·m", "注意轴承安装方向"],
                "action_params": {"torque_nm": 25},
            },
            {
                "step_index": 7, "title": "校准关节零位",
                "description": "上电后进入校准模式，校准膝关节编码器零位。",
                "target_part": "left_knee_joint", "expected_action": "calibrate",
                "is_critical": False, "severity_level": "WARN",
                "timeout_seconds": 300, "allow_skip": False,
                "tools_required": ["校准软件"],
                "hints": ["校准完成后检查编码器读数是否为 0±0.1°"],
            },
            {
                "step_index": 8, "title": "全范围运动验证",
                "description": "在低速模式下运行关节全范围往返 3 次，检查运动平滑性和异响。",
                "target_part": "left_knee_joint", "expected_action": "verify",
                "is_critical": True, "severity_level": "WARN",
                "timeout_seconds": 300, "allow_skip": False,
                "tools_required": [],
                "hints": ["注意听是否有异常摩擦声"],
            },
        ],
    },
    {
        "name": "ATOM-01 肩关节伺服电机检测",
        "description": "对 ATOM-01 肩关节伺服电机进行电气参数检测和功能验证。",
        "category": "故障排查",
        "difficulty_level": "low",
        "estimated_time": 1200,
        "steps": [
            {
                "step_index": 1, "title": "断电并隔离",
                "description": "关闭机器人电源，断开肩关节伺服电机连接器。",
                "target_part": "power_system", "expected_action": "power_off",
                "is_critical": True, "severity_level": "SAFETY_HALT",
                "timeout_seconds": 120, "allow_skip": False,
                "tools_required": ["绝缘手套", "安全锁止牌"],
                "hints": ["确认连接器完全脱开"],
            },
            {
                "step_index": 2, "title": "准备检测设备",
                "description": "准备万用表、示波器和伺服驱动器测试仪。",
                "target_part": None, "expected_action": "prepare",
                "is_critical": False, "severity_level": "INFO",
                "timeout_seconds": 180, "allow_skip": False,
                "tools_required": ["万用表", "示波器", "伺服测试仪"],
                "hints": ["确保万用表电池充足"],
            },
            {
                "step_index": 3, "title": "检查绕组电阻",
                "description": "使用万用表测量 U/V/W 三相绕组电阻，三相阻值偏差应 <5%。",
                "target_part": "right_arm_pitch_joint", "expected_action": "inspect",
                "is_critical": False, "severity_level": "WARN",
                "timeout_seconds": 300, "allow_skip": False,
                "tools_required": ["万用表"],
                "hints": ["标准阻值：1.2Ω±5%"],
                "action_params": {"standard_resistance": 1.2, "tolerance_pct": 5},
            },
            {
                "step_index": 4, "title": "测量反电动势波形",
                "description": "手动旋转电机轴，用示波器观察反电动势波形是否对称、平滑。",
                "target_part": "right_arm_pitch_joint", "expected_action": "measure",
                "is_critical": False, "severity_level": "WARN",
                "timeout_seconds": 300, "allow_skip": False,
                "tools_required": ["示波器"],
                "hints": ["波形应为近似正弦，无尖峰"],
            },
            {
                "step_index": 5, "title": "上电功能验证",
                "description": "重新连接电机，上电运行自检程序，验证位置环和速度环响应。",
                "target_part": "right_arm_pitch_joint", "expected_action": "verify",
                "is_critical": True, "severity_level": "WARN",
                "timeout_seconds": 300, "allow_skip": False,
                "tools_required": ["伺服测试仪"],
                "hints": ["位置误差应 <0.5°"],
            },
        ],
    },
    {
        "name": "ATOM-01 全身热管理系统维护",
        "description": "对 ATOM-01 全身各关节散热系统进行检查、维护和性能验证，预防过热故障。",
        "category": "维护保养",
        "difficulty_level": "high",
        "estimated_time": 4200,
        "steps": [
            {
                "step_index": 1, "title": "全机断电冷却",
                "description": "关闭机器人全部电源，等待至少 15 分钟冷却至环境温度。",
                "target_part": "power_system", "expected_action": "power_off",
                "is_critical": True, "severity_level": "SAFETY_HALT",
                "timeout_seconds": 900, "allow_skip": False,
                "tools_required": ["红外温度枪"],
                "hints": ["用红外温度枪确认各关节温度 <35°C"],
            },
            {
                "step_index": 2, "title": "准备维保工具与耗材",
                "description": "准备导热硅脂、散热风扇、压缩空气罐、温度传感器校准工具。",
                "target_part": None, "expected_action": "prepare",
                "is_critical": False, "severity_level": "INFO",
                "timeout_seconds": 300, "allow_skip": False,
                "tools_required": ["导热硅脂", "压缩空气罐", "温度传感器校准仪", "十字螺丝刀"],
                "hints": ["检查导热硅脂保质期"],
            },
            {
                "step_index": 3, "title": "检查髋关节散热组件",
                "description": "拆开髋关节散热盖，检查散热片灰尘积累和风扇运转状况。",
                "target_part": "left_thigh_pitch_joint", "expected_action": "inspect",
                "is_critical": False, "severity_level": "WARN",
                "timeout_seconds": 600, "allow_skip": False,
                "tools_required": ["十字螺丝刀", "压缩空气罐"],
                "hints": ["散热片间隙无明显积灰为合格"],
            },
            {
                "step_index": 4, "title": "检查膝关节散热组件",
                "description": "检查膝关节散热片、导热垫和温度传感器连接状态。",
                "target_part": "left_knee_joint", "expected_action": "inspect",
                "is_critical": False, "severity_level": "WARN",
                "timeout_seconds": 600, "allow_skip": False,
                "tools_required": ["十字螺丝刀", "压缩空气罐"],
                "hints": ["导热垫如有硬化需更换"],
            },
            {
                "step_index": 5, "title": "检查肩关节散热组件",
                "description": "检查肩关节伺服电机散热风道是否通畅、风扇叶片是否完好。",
                "target_part": "right_arm_pitch_joint", "expected_action": "inspect",
                "is_critical": False, "severity_level": "WARN",
                "timeout_seconds": 600, "allow_skip": False,
                "tools_required": ["LED 手电筒"],
                "hints": ["确认风道无异物堵塞"],
            },
            {
                "step_index": 6, "title": "检查肘关节散热组件",
                "description": "检查肘关节散热结构和导热材料状态。",
                "target_part": "left_elbow_pitch_joint", "expected_action": "inspect",
                "is_critical": False, "severity_level": "WARN",
                "timeout_seconds": 400, "allow_skip": False,
                "tools_required": ["十字螺丝刀"],
                "hints": ["注意导热垫接触面是否平整"],
            },
            {
                "step_index": 7, "title": "测量各关节静态温升",
                "description": "上电后以 50% 负载运行 10 分钟，记录各关节温升曲线。",
                "target_part": None, "expected_action": "measure",
                "is_critical": False, "severity_level": "WARN",
                "timeout_seconds": 900, "allow_skip": False,
                "tools_required": ["红外温度枪", "数据记录仪"],
                "hints": ["温升 <20°C 为合格"],
                "action_params": {"max_temp_rise": 20, "unit": "celsius"},
            },
            {
                "step_index": 8, "title": "更换老化导热硅脂",
                "description": "对温升超标的关节重新涂抹导热硅脂，确保覆盖均匀无气泡。",
                "target_part": None, "expected_action": "execute",
                "is_critical": True, "severity_level": "WARN",
                "timeout_seconds": 600, "allow_skip": True,
                "tools_required": ["导热硅脂", "酒精清洁棉", "刮刀"],
                "hints": ["旧硅脂需完全清除后再涂新硅脂", "涂层厚度约 0.1mm"],
            },
            {
                "step_index": 9, "title": "校准温度传感器",
                "description": "使用校准仪对各关节温度传感器进行零点和增益校准。",
                "target_part": None, "expected_action": "calibrate",
                "is_critical": False, "severity_level": "WARN",
                "timeout_seconds": 600, "allow_skip": False,
                "tools_required": ["温度传感器校准仪"],
                "hints": ["校准偏差应 <±0.5°C"],
            },
            {
                "step_index": 10, "title": "全机热管理系统验证",
                "description": "全负载运行 20 分钟，验证所有关节温度均在安全范围内。",
                "target_part": None, "expected_action": "verify",
                "is_critical": True, "severity_level": "WARN",
                "timeout_seconds": 1500, "allow_skip": False,
                "tools_required": ["数据记录仪"],
                "hints": ["所有关节温度应 <65°C"],
                "action_params": {"max_temp": 65, "unit": "celsius"},
            },
        ],
    },
]

# --- Skill Profiles ---

SKILL_PROFILES = {
    "student1@rmos.demo": {
        "safety": 92, "procedure": 88, "precision": 85,
        "efficiency": 90, "tools": 87, "level": 4,
        "sessions": 18, "duration": 48600,
    },
    "student2@rmos.demo": {
        "safety": 78, "procedure": 75, "precision": 70,
        "efficiency": 72, "tools": 76, "level": 3,
        "sessions": 12, "duration": 32400,
    },
    "student3@rmos.demo": {
        "safety": 70, "procedure": 65, "precision": 55,
        "efficiency": 68, "tools": 62, "level": 2,
        "sessions": 15, "duration": 40500,
    },
    "student4@rmos.demo": {
        "safety": 75, "procedure": 72, "precision": 68,
        "efficiency": 65, "tools": 70, "level": 3,
        "sessions": 6, "duration": 16200,
    },
    "student5@rmos.demo": {
        "safety": 85, "procedure": 80, "precision": 78,
        "efficiency": 82, "tools": 75, "level": 3,
        "sessions": 10, "duration": 27000,
    },
}

# --- Training Session Plans ---
# (email, [(status, score), ...])
SESSION_PLANS: dict[str, list[tuple[str, float | None]]] = {
    "student1@rmos.demo": [
        ("submitted", 90), ("submitted", 91), ("submitted", 89),
        ("submitted", 92), ("submitted", 88),
    ],
    "student2@rmos.demo": [
        ("submitted", 73), ("submitted", 75), ("submitted", 77),
    ],
    "student3@rmos.demo": [
        ("submitted", 65), ("submitted", 68), ("submitted", 70), ("submitted", 69),
    ],
    "student4@rmos.demo": [
        ("submitted", 72), ("active", None),
    ],
    "student5@rmos.demo": [
        ("submitted", 78), ("submitted", 82), ("submitted", 80),
    ],
}

# --- Attempt Plans ---
# (email, assignment_index, attempt_status, score)
ATTEMPT_PLAN: list[tuple[str, int, str, float | None]] = [
    ("student1@rmos.demo", 0, "completed", 92),
    ("student1@rmos.demo", 1, "completed", 88),
    ("student2@rmos.demo", 0, "completed", 78),
    ("student2@rmos.demo", 1, "in_progress", None),
    ("student3@rmos.demo", 0, "completed", 65),
    ("student3@rmos.demo", 1, "completed", 71),
    ("student4@rmos.demo", 0, "in_progress", None),
    ("student5@rmos.demo", 0, "abandoned", None),
    ("student5@rmos.demo", 1, "completed", 85),
]

# --- Knowledge Documents ---
KNOWLEDGE_DOCS = [
    {
        "title": "ATOM-01 技术手册 v2.0",
        "doc_type": "manual",
        "status": "APPROVED",
        "content": (
            "ATOM-01 人形机器人技术手册\n\n"
            "一、概述\nATOM-01 是一款 22 自由度人形机器人，主要用于工业维保培训。"
            "整机高度 1.65m，重量 55kg，采用模块化关节设计。\n\n"
            "二、关节系统\n全身包含髋关节（6DOF）、膝关节（2DOF）、踝关节（4DOF）、"
            "肩关节（6DOF）、肘关节（4DOF）共 22 个伺服关节。\n\n"
            "三、电气系统\n主供电 48V DC，逻辑供电 5V/3.3V，关节驱动器采用 FOC 矢量控制。\n\n"
            "四、安全规范\n操作前必须断电并确认电容完全放电；带电操作需穿戴绝缘防护装备。"
        ),
        "fault_tags": [],
        "sop_tags": [],
        "risk_level": "R0",
    },
    {
        "title": "膝关节轴承更换指南",
        "doc_type": "guide",
        "status": "APPROVED",
        "content": (
            "膝关节轴承更换操作指南\n\n"
            "适用型号：ATOM-01 全系列\n"
            "更换周期：累计运行 2000 小时或发现异常振动时\n\n"
            "关键注意事项：\n"
            "1. 新轴承安装前需预热至 80°C，利用热膨胀便于套装\n"
            "2. 锁紧力矩严格按 25 N·m 执行，过大会导致预紧力过高\n"
            "3. 安装后需进行零位校准和全范围运动测试\n"
            "4. 旧轴承拆卸时使用专用拉拔器，禁止敲击"
        ),
        "fault_tags": ["E002_BEARING_WEAR"],
        "sop_tags": ["ATOM-01 膝关节轴承更换"],
        "risk_level": "R1",
    },
    {
        "title": "关节温度异常诊断规范",
        "doc_type": "spec",
        "status": "APPROVED",
        "content": (
            "关节温度异常诊断规范 v1.0\n\n"
            "一、温度阈值定义\n"
            "- 正常：<55°C\n- 预警：55-65°C\n- 报警：65-75°C\n- 紧急停机：>75°C\n\n"
            "二、常见原因\n"
            "1. 散热片灰尘积累（占比 40%）\n"
            "2. 导热硅脂老化干裂（占比 25%）\n"
            "3. 散热风扇故障（占比 20%）\n"
            "4. 过载运行（占比 15%）\n\n"
            "三、诊断流程\n"
            "先检查散热通道→再检查导热材料→最后检查电气参数"
        ),
        "fault_tags": ["E001_OVERHEAT"],
        "sop_tags": ["ATOM-01 全身热管理系统维护"],
        "risk_level": "R2",
    },
    {
        "title": "伺服电机选型参考",
        "doc_type": "guide",
        "status": "PENDING",
        "content": (
            "伺服电机选型参考（草稿）\n\n"
            "适用于 ATOM-01 关节替换用伺服电机的选型建议。\n"
            "关键参数：额定扭矩 ≥15 N·m，峰值扭矩 ≥30 N·m，"
            "额定转速 3000 rpm，编码器分辨率 ≥17 bit。"
        ),
        "fault_tags": [],
        "sop_tags": [],
        "risk_level": "R0",
    },
]

# --- Fault Cases ---
FAULT_DEFS = [
    {
        "fault_code": "E001_OVERHEAT",
        "name": "关节过热故障",
        "description": "关节温度超过安全阈值（65°C），可能由散热系统异常、过载运行或导热材料老化引起。",
        "category": "thermal",
        "severity": "high",
        "affected_parts": ["left_knee_joint", "right_knee_joint", "left_thigh_pitch_joint"],
        "symptoms": ["关节温度持续上升", "伺服电机降功率运行", "温度报警触发"],
        "diagnosis_steps": ["检查散热风扇", "检查导热硅脂", "测量环境温度", "检查负载曲线"],
        "solution_steps": ["清洁散热片", "更换导热硅脂", "修复或更换风扇", "调整负载参数"],
        "sop_idx": 2,
        "difficulty": "intermediate",
    },
    {
        "fault_code": "E002_BEARING_WEAR",
        "name": "轴承磨损异常",
        "description": "关节轴承磨损超标，表现为异响、振动增大或间隙超差。",
        "category": "mechanical",
        "severity": "medium",
        "affected_parts": ["left_knee_joint", "right_knee_joint"],
        "symptoms": ["关节运动时有异响", "振动幅度增大", "轴承间隙超过 0.05mm"],
        "diagnosis_steps": ["听诊异响", "测量轴承间隙", "检查润滑状态"],
        "solution_steps": ["更换轴承", "更新润滑脂", "校准关节零位"],
        "sop_idx": 0,
        "difficulty": "intermediate",
    },
    {
        "fault_code": "E003_VOLTAGE_DROP",
        "name": "供电电压骤降",
        "description": "主供电电压低于 40V（标称 48V），导致关节控制器欠压保护。",
        "category": "electrical",
        "severity": "high",
        "affected_parts": ["power_system"],
        "symptoms": ["多关节同时报欠压故障", "系统自动降功率", "电池电量骤降"],
        "diagnosis_steps": ["测量电池电压", "检查配电线路", "检查接触器"],
        "solution_steps": ["更换或充电电池", "修复松动接线", "更换老化接触器"],
        "sop_idx": 2,
        "difficulty": "advanced",
    },
    {
        "fault_code": "E004_CALIBRATION_DRIFT",
        "name": "校准偏移",
        "description": "关节编码器零位漂移超过允许范围（>0.5°），影响运动精度。",
        "category": "mechanical",
        "severity": "low",
        "affected_parts": ["right_arm_pitch_joint", "left_elbow_pitch_joint"],
        "symptoms": ["运动轨迹偏差", "重复定位精度下降"],
        "diagnosis_steps": ["读取编码器零位值", "对比上次校准记录", "检查编码器安装"],
        "solution_steps": ["重新校准零位", "紧固编码器安装螺丝"],
        "sop_idx": 1,
        "difficulty": "beginner",
    },
]

# --- Weak Steps ---
WEAK_STEPS = [
    ("student3@rmos.demo", "motor_cover_remove", "sop-knee", 5, ["wrong_tool", "sequence_error"]),
    ("student3@rmos.demo", "align_reducer", "sop-knee", 3, ["precision_low"]),
    ("student4@rmos.demo", "measure_clearance", "sop-knee", 2, ["value_out_of_range"]),
    ("student5@rmos.demo", "motor_cover_remove", "sop-knee", 2, ["wrong_tool"]),
]


# ────────────────────────────────────────────────────────
# Helper functions (get_or_create pattern)
# ────────────────────────────────────────────────────────

async def get_or_create_user(session: AsyncSession, spec: SeedUser) -> User:
    result = await session.execute(select(User).where(User.email == spec.email))
    user = result.scalar_one_or_none()
    pw_hash = hash_password(spec.password)
    if user is None:
        user = User(
            email=spec.email, password_hash=pw_hash,
            full_name=spec.full_name, role=spec.role,
            is_active=True, is_verified=True, hint_level=3,
        )
        session.add(user)
        await session.flush()
        return user
    user.password_hash = pw_hash
    user.full_name = spec.full_name
    user.role = spec.role
    user.is_active = True
    user.is_verified = True
    return user


async def get_or_create_role(session: AsyncSession, *, name: str, desc: str) -> Role:
    result = await session.execute(select(Role).where(Role.name == name))
    role = result.scalar_one_or_none()
    if role is None:
        role = Role(name=name, description=desc)
        session.add(role)
        await session.flush()
    return role


async def get_or_create_permission(
    session: AsyncSession, *, key: str, description: str,
    resource_type: str, action: str,
) -> Permission:
    result = await session.execute(select(Permission).where(Permission.key == key))
    perm = result.scalar_one_or_none()
    if perm is None:
        perm = Permission(key=key, description=description,
                          resource_type=resource_type, action=action)
        session.add(perm)
        await session.flush()
    return perm


async def ensure_role_permission(session: AsyncSession, *, role_id: int, permission_id: int):
    result = await session.execute(
        select(RolePermission).where(
            RolePermission.role_id == role_id,
            RolePermission.permission_id == permission_id,
        )
    )
    if result.scalar_one_or_none() is None:
        session.add(RolePermission(role_id=role_id, permission_id=permission_id))
        await session.flush()


async def sync_user_role(session: AsyncSession, *, user_id: int, role_id: int):
    await session.execute(
        delete(UserRole).where(UserRole.user_id == user_id, UserRole.role_id != role_id)
    )
    result = await session.execute(
        select(UserRole).where(UserRole.user_id == user_id, UserRole.role_id == role_id)
    )
    if result.scalar_one_or_none() is None:
        session.add(UserRole(user_id=user_id, role_id=role_id))
        await session.flush()


# ────────────────────────────────────────────────────────
# Tier functions
# ────────────────────────────────────────────────────────

async def tier1_users_rbac(session: AsyncSession) -> dict[str, User]:
    """Tier 1: Users + RBAC + Preferences"""
    # Roles
    roles: dict[str, Role] = {}
    for rname, rdesc in ROLE_SPECS.items():
        roles[rname] = await get_or_create_role(session, name=rname, desc=rdesc)

    # Permissions
    permissions: dict[str, Permission] = {}
    for key, (desc, res, act) in PERMISSION_SPECS.items():
        permissions[key] = await get_or_create_permission(
            session, key=key, description=desc, resource_type=res, action=act,
        )

    # Role-Permission bindings
    for rname, perm_keys in ROLE_PERMISSION_KEYS.items():
        for pkey in perm_keys:
            await ensure_role_permission(
                session, role_id=roles[rname].id, permission_id=permissions[pkey].id,
            )

    # Users
    users: dict[str, User] = {}
    for spec in DEMO_USERS:
        user = await get_or_create_user(session, spec)
        users[spec.email] = user
        await sync_user_role(session, user_id=user.id, role_id=roles[spec.role].id)

    # Set teacher_id on students
    teacher = users["teacher1@rmos.demo"]
    for spec in DEMO_USERS:
        if spec.role == "student":
            users[spec.email].teacher_id = teacher.id
    await session.flush()

    # Preferences
    for spec in DEMO_USERS:
        if spec.role == "student":
            uid = users[spec.email].id
            result = await session.execute(
                select(UserPreference).where(UserPreference.user_id == uid)
            )
            pref = result.scalar_one_or_none()
            if pref is None:
                session.add(UserPreference(
                    user_id=uid, guidance_mode=spec.guidance_mode, preferences={},
                ))
            else:
                pref.guidance_mode = spec.guidance_mode
    await session.flush()

    return users


async def tier2_robot(session: AsyncSession, teacher: User) -> RobotModel:
    """Tier 2: Robot Model + Binding + Assets"""
    result = await session.execute(
        select(RobotModel).where(RobotModel.model_name == "ATOM-01")
    )
    robot = result.scalar_one_or_none()
    if robot is None:
        robot = RobotModel(
            brand="Atom Robotics", model_name="ATOM-01", version="1.2.0",
            owner_teacher_id=teacher.id,
            visibility=RobotVisibility.SHARED, status=RobotStatus.READY,
            description="ATOM-01 人形机器人，22 自由度，适用于关节维修培训。",
        )
        session.add(robot)
        await session.flush()
    else:
        robot.visibility = RobotVisibility.SHARED
        robot.status = RobotStatus.READY
        if robot.owner_teacher_id is None:
            robot.owner_teacher_id = teacher.id
        await session.flush()

    # Owner binding
    result = await session.execute(
        select(TeacherRobotBinding).where(
            TeacherRobotBinding.teacher_id == teacher.id,
            TeacherRobotBinding.robot_model_id == robot.id,
        )
    )
    if result.scalar_one_or_none() is None:
        session.add(TeacherRobotBinding(
            teacher_id=teacher.id, robot_model_id=robot.id, binding_type="owner",
        ))
        await session.flush()

    # Register assets if directory exists
    assets_base = Path(__file__).parent.parent / "data" / "robot-assets" / str(robot.id) / "models"
    if assets_base.exists():
        existing = await session.execute(
            select(RobotAsset).where(RobotAsset.robot_model_id == robot.id)
        )
        if not existing.scalars().first():
            for glb in sorted(assets_base.glob("*.glb")):
                session.add(RobotAsset(
                    robot_model_id=robot.id,
                    asset_type=AssetType.MODEL_GLB,
                    file_path=f"models/{glb.name}",
                    file_size=glb.stat().st_size,
                ))
            # Manifest
            for mf in assets_base.glob("*.json"):
                session.add(RobotAsset(
                    robot_model_id=robot.id,
                    asset_type=AssetType.MANIFEST,
                    file_path=f"models/{mf.name}",
                    file_size=mf.stat().st_size,
                ))
            await session.flush()

    return robot


async def tier3_sops(session: AsyncSession, robot_id: int) -> list[SOP]:
    """Tier 3: SOPs + Steps"""
    sops: list[SOP] = []
    for sop_def in SOP_DEFS:
        result = await session.execute(select(SOP).where(SOP.name == sop_def["name"]))
        sop = result.scalar_one_or_none()
        if sop is None:
            sop = SOP(
                name=sop_def["name"],
                description=sop_def["description"],
                applicable_model="ATOM-01",
                category=sop_def["category"],
                difficulty_level=sop_def["difficulty_level"],
                estimated_time=sop_def["estimated_time"],
                robot_model_id=robot_id,
            )
            session.add(sop)
            await session.flush()

            for step_data in sop_def["steps"]:
                session.add(SOPStep(
                    sop_id=sop.id,
                    step_index=step_data["step_index"],
                    title=step_data["title"],
                    description=step_data["description"],
                    target_part=step_data.get("target_part"),
                    expected_action=step_data["expected_action"],
                    action_params=step_data.get("action_params"),
                    validation_rules=step_data.get("validation_rules"),
                    is_critical=step_data.get("is_critical", False),
                    severity_level=step_data.get("severity_level", "WARN"),
                    timeout_seconds=step_data.get("timeout_seconds", 300),
                    allow_skip=step_data.get("allow_skip", False),
                    hints=step_data.get("hints"),
                    tools_required=step_data.get("tools_required"),
                ))
            await session.flush()
        sops.append(sop)
    return sops


async def tier4_teaching(
    session: AsyncSession, teacher: User, students: list[User], sops: list[SOP],
) -> dict:
    """Tier 4: Teaching class + course + enrollments + assignments"""
    # Guidance Policy
    result = await session.execute(
        select(GuidancePolicy).where(GuidancePolicy.name == "标准教学模式")
    )
    policy = result.scalar_one_or_none()
    if policy is None:
        policy = GuidancePolicy(
            name="标准教学模式", base_mode="teaching",
            allow_ghost_hand=True, allow_hint_button=True,
            show_error_details=True, max_retry_count=-1,
            description="默认教学引导策略，允许全部辅助功能。",
        )
        session.add(policy)
        await session.flush()

    # Class
    result = await session.execute(
        select(TeachingClass).where(TeachingClass.name == "2026届机器人维修一班")
    )
    klass = result.scalar_one_or_none()
    if klass is None:
        klass = TeachingClass(
            name="2026届机器人维修一班", term="2026春",
            teacher_id=teacher.id, metadata_json={"seed": "demo_full"},
        )
        session.add(klass)
        await session.flush()
    else:
        klass.teacher_id = teacher.id

    # Course
    result = await session.execute(
        select(Course).where(Course.class_id == klass.id, Course.name == "人形机器人基础维保")
    )
    course = result.scalar_one_or_none()
    if course is None:
        course = Course(
            class_id=klass.id, name="人形机器人基础维保",
            description="涵盖关节检测、轴承更换、热管理维护等基础维保技能。",
            schedule={"weeks": 16}, metadata_json={"seed": "demo_full"},
        )
        session.add(course)
        await session.flush()

    # Enrollments
    for student in students:
        result = await session.execute(
            select(Enrollment).where(
                Enrollment.class_id == klass.id,
                Enrollment.student_id == student.id,
            )
        )
        if result.scalar_one_or_none() is None:
            session.add(Enrollment(
                class_id=klass.id, student_id=student.id, role="student",
            ))
        student.class_id = klass.id
    await session.flush()

    # Assignments
    now = datetime.utcnow()
    due = now + timedelta(days=30)

    assignments: list[Assignment] = []
    asn_specs = [
        ("膝关节维修实操", sops[0].id, 3),
        ("肩关节故障诊断", sops[1].id, 2),
    ]
    for title, sop_id, max_att in asn_specs:
        result = await session.execute(
            select(Assignment).where(
                Assignment.class_id == klass.id, Assignment.title == title,
            )
        )
        asn = result.scalar_one_or_none()
        if asn is None:
            asn = Assignment(
                class_id=klass.id, course_id=course.id,
                title=title, sop_id=sop_id,
                guidance_policy_id=policy.id,
                start_at=now - timedelta(days=7), due_at=due,
                max_attempts=max_att,
            )
            session.add(asn)
            await session.flush()
        assignments.append(asn)

    return {"policy": policy, "class": klass, "course": course, "assignments": assignments}


async def tier5_tasks_attempts(
    session: AsyncSession, users: dict[str, User], assignments: list[Assignment],
):
    """Tier 5: Tasks + AssignmentAttempts"""
    now = datetime.utcnow()
    for email, asn_idx, status, score in ATTEMPT_PLAN:
        student = users[email]
        asn = assignments[asn_idx]

        # Check existing
        result = await session.execute(
            select(AssignmentAttempt).where(
                AssignmentAttempt.assignment_id == asn.id,
                AssignmentAttempt.student_id == student.id,
            )
        )
        if result.scalar_one_or_none() is not None:
            continue

        # Task
        task_status_map = {
            "completed": "completed", "in_progress": "in_progress", "abandoned": "cancelled",
        }
        task = Task(
            title=f"{asn.title} - {student.full_name}",
            sop_id=asn.sop_id,
            user_id=student.id,
            assignment_id=asn.id,
            guidance_policy_id=asn.guidance_policy_id,
            status=task_status_map[status],
            current_step_index=8 if status == "completed" else 3,
            pass_score=70,
            final_score=int(score) if score else None,
            is_passed=(score >= 70) if score else None,
            started_at=now - timedelta(hours=48),
            completed_at=(now - timedelta(hours=46)) if status == "completed" else None,
        )
        session.add(task)
        await session.flush()

        # Attempt
        attempt = AssignmentAttempt(
            assignment_id=asn.id,
            student_id=student.id,
            task_id=task.id,
            status=status,
            score=score,
            graded_at=now if status == "completed" else None,
            abandoned_at=now if status == "abandoned" else None,
            attempt_index=1,
            diagnosis_code="NOMINAL" if status == "completed" and score and score >= 80 else (
                "PROC_ERROR_MINOR" if status == "completed" else None
            ),
        )
        session.add(attempt)
        await session.flush()


async def tier6_training_sessions(
    session: AsyncSession, users: dict[str, User], sops: list[SOP],
):
    """Tier 6: Training Sessions + Step Records + Submissions"""
    now = datetime.utcnow()

    for email, plans in SESSION_PLANS.items():
        student = users[email]
        for i, (status, score) in enumerate(plans):
            sid = f"demo-{student.id}-{i + 1:02d}"

            result = await session.execute(
                select(TrainingSession).where(TrainingSession.session_id == sid)
            )
            if result.scalar_one_or_none() is not None:
                continue

            sop = sops[i % len(sops)]
            num_steps = len(SOP_DEFS[i % len(SOP_DEFS)]["steps"])
            base_time = now - timedelta(days=len(plans) - i, hours=3)
            duration = 1800 + i * 300

            ts = TrainingSession(
                session_id=sid,
                project_id=str(sop.id),
                user_id=student.id,
                status=status,
                current_step=num_steps if status == "submitted" else 2,
                score=score,
                started_at=base_time,
                submitted_at=(base_time + timedelta(seconds=duration)) if status == "submitted" else None,
                total_duration=duration,
                submit_type="manual" if status == "submitted" else None,
            )
            session.add(ts)
            await session.flush()

            # Step records
            for j in range(min(num_steps, 7)):
                rec_id = f"demo-rec-{student.id}-{i + 1:02d}-{j + 1:02d}"
                if status == "submitted":
                    step_status = "pass"
                elif j < 2:
                    step_status = "pass"
                else:
                    step_status = "in_progress" if j == 2 else "pending"

                session.add(SessionStepRecord(
                    record_id=rec_id,
                    session_id=sid,
                    step_id=f"step-{j + 1}",
                    step_index=j + 1,
                    status=step_status,
                    attempt_count=1 if step_status == "pass" else 0,
                    duration_sec=(120 + j * 30) if step_status == "pass" else None,
                    started_at=base_time + timedelta(minutes=j * 5),
                    completed_at=(
                        base_time + timedelta(minutes=j * 5 + 4)
                        if step_status == "pass" else None
                    ),
                ))

            # Submission for submitted sessions
            if status == "submitted":
                sub_id = f"demo-sub-{student.id}-{i + 1:02d}"
                session.add(TrainingSubmission(
                    submission_id=sub_id,
                    session_id=sid,
                    user_id=student.id,
                    submit_type="manual",
                    submitted_at=ts.submitted_at,
                    score=score,
                    total_steps=num_steps,
                    completed_steps=num_steps,
                    failed_steps=0,
                    total_duration=duration,
                    payload={"session_id": sid, "score": score},
                ))

            await session.flush()


async def tier7_skill_profiles(session: AsyncSession, users: dict[str, User]):
    """Tier 7: Skill Profiles + Weak Steps"""
    now = datetime.utcnow()

    for email, scores in SKILL_PROFILES.items():
        student = users[email]
        result = await session.execute(
            select(StudentSkillProfile).where(StudentSkillProfile.user_id == student.id)
        )
        profile = result.scalar_one_or_none()
        if profile is None:
            profile = StudentSkillProfile(
                user_id=student.id,
                overall_level=scores["level"],
                total_sessions=scores["sessions"],
                total_duration=scores["duration"],
                last_trained_at=now - timedelta(days=1),
                score_safety=scores["safety"],
                score_procedure=scores["procedure"],
                score_precision=scores["precision"],
                score_efficiency=scores["efficiency"],
                score_tools=scores["tools"],
                cert_l1_passed=scores["level"] >= 2,
                cert_l2_passed=scores["level"] >= 3,
                cert_l3_eligible=scores["level"] >= 4,
            )
            session.add(profile)
        else:
            profile.overall_level = scores["level"]
            profile.total_sessions = scores["sessions"]
            profile.total_duration = scores["duration"]
            profile.last_trained_at = now - timedelta(days=1)
            profile.score_safety = scores["safety"]
            profile.score_procedure = scores["procedure"]
            profile.score_precision = scores["precision"]
            profile.score_efficiency = scores["efficiency"]
            profile.score_tools = scores["tools"]
            profile.cert_l1_passed = scores["level"] >= 2
            profile.cert_l2_passed = scores["level"] >= 3
            profile.cert_l3_eligible = scores["level"] >= 4
    await session.flush()

    # Weak steps
    for email, step_id, sop_tag, fail_count, fail_tags in WEAK_STEPS:
        student = users[email]
        result = await session.execute(
            select(StudentWeakStep).where(
                StudentWeakStep.user_id == student.id,
                StudentWeakStep.step_id == step_id,
            )
        )
        if result.scalar_one_or_none() is None:
            session.add(StudentWeakStep(
                user_id=student.id,
                step_id=step_id,
                sop_id=sop_tag,
                fail_count=fail_count,
                last_failed_at=now - timedelta(days=2),
                fail_tags=fail_tags,
                is_resolved=False,
            ))
    await session.flush()


async def tier8_knowledge(session: AsyncSession, robot_id: int, teacher_id: int):
    """Tier 8: Knowledge Documents (raw SQL — ORM model has extra columns not in DB)"""
    from sqlalchemy import text
    import json as _json

    now = datetime.utcnow()
    for doc_data in KNOWLEDGE_DOCS:
        result = await session.execute(
            text("SELECT id FROM knowledge_documents WHERE title = :title"),
            {"title": doc_data["title"]},
        )
        if result.scalar_one_or_none() is not None:
            continue
        await session.execute(
            text("""
                INSERT INTO knowledge_documents
                    (title, content, source, fault_tags, sop_tags, status,
                     robot_model_id, generation_status, created_at, updated_at)
                VALUES
                    (:title, :content, :source, :fault_tags, :sop_tags, :status,
                     :robot_model_id, :generation_status, :now, :now)
            """),
            {
                "title": doc_data["title"],
                "content": doc_data["content"],
                "source": doc_data["doc_type"],
                "fault_tags": _json.dumps(doc_data["fault_tags"]),
                "sop_tags": _json.dumps(doc_data["sop_tags"]),
                "status": doc_data["status"],
                "robot_model_id": robot_id,
                "generation_status": "manual",
                "now": now,
            },
        )
    await session.flush()


async def tier9_faults_scenarios(session: AsyncSession, sops: list[SOP], robot_id: int):
    """Tier 9: Fault Cases + FaultSOPMappings (Scenarios)"""
    for fdef in FAULT_DEFS:
        # FaultCase
        result = await session.execute(
            select(FaultCase).where(FaultCase.fault_code == fdef["fault_code"])
        )
        fault = result.scalar_one_or_none()
        if fault is None:
            fault = FaultCase(
                fault_code=fdef["fault_code"],
                name=fdef["name"],
                description=fdef["description"],
                category=fdef["category"],
                severity=fdef["severity"],
                affected_parts=fdef["affected_parts"],
                symptoms=fdef["symptoms"],
                diagnosis_steps=fdef["diagnosis_steps"],
                solution_steps=fdef["solution_steps"],
            )
            session.add(fault)
            await session.flush()

        # FaultSOPMapping
        sop = sops[fdef["sop_idx"]]
        result = await session.execute(
            select(FaultSOPMapping).where(
                FaultSOPMapping.fault_type == fdef["fault_code"],
                FaultSOPMapping.sop_id == sop.id,
            )
        )
        if result.scalar_one_or_none() is None:
            session.add(FaultSOPMapping(
                fault_type=fdef["fault_code"],
                sop_id=sop.id,
                difficulty=fdef["difficulty"],
                priority=1,
                robot_model_id=robot_id,
            ))
    await session.flush()


# ────────────────────────────────────────────────────────
# Reset
# ────────────────────────────────────────────────────────

async def reset_demo_data(session: AsyncSession):
    """Delete all demo data identified by @rmos.demo email domain."""
    # Find demo user IDs
    result = await session.execute(
        select(User.id).where(User.email.like(f"%{DEMO_DOMAIN}"))
    )
    demo_ids = [row[0] for row in result.all()]

    if demo_ids:
        # Training submissions (FK -> training_sessions.session_id)
        for uid in demo_ids:
            await session.execute(
                delete(TrainingSubmission).where(TrainingSubmission.user_id == uid)
            )
        # Session step records (via session_id pattern)
        await session.execute(
            delete(SessionStepRecord).where(SessionStepRecord.record_id.like("demo-rec-%"))
        )
        # Training sessions
        for uid in demo_ids:
            await session.execute(
                delete(TrainingSession).where(TrainingSession.user_id == uid)
            )
        # Assignment attempts
        for uid in demo_ids:
            await session.execute(
                delete(AssignmentAttempt).where(AssignmentAttempt.student_id == uid)
            )
        # Tasks
        for uid in demo_ids:
            await session.execute(
                delete(Task).where(Task.user_id == uid)
            )
        # Skill profiles + weak steps
        for uid in demo_ids:
            await session.execute(
                delete(StudentWeakStep).where(StudentWeakStep.user_id == uid)
            )
            await session.execute(
                delete(StudentSkillProfile).where(StudentSkillProfile.user_id == uid)
            )
        # Preferences
        for uid in demo_ids:
            await session.execute(
                delete(UserPreference).where(UserPreference.user_id == uid)
            )
        # User roles
        for uid in demo_ids:
            await session.execute(
                delete(UserRole).where(UserRole.user_id == uid)
            )
        # Enrollments
        for uid in demo_ids:
            await session.execute(
                delete(Enrollment).where(Enrollment.student_id == uid)
            )

    # Assignments by title
    for title in ("膝关节维修实操", "肩关节故障诊断"):
        await session.execute(delete(Assignment).where(Assignment.title == title))

    # Class / Course
    await session.execute(
        delete(TeachingClass).where(TeachingClass.name == "2026届机器人维修一班")
    )
    await session.execute(
        delete(GuidancePolicy).where(GuidancePolicy.name == "标准教学模式")
    )

    # Knowledge documents (raw SQL — ORM model mismatch)
    from sqlalchemy import text
    for doc in KNOWLEDGE_DOCS:
        await session.execute(
            text("DELETE FROM knowledge_documents WHERE title = :title"),
            {"title": doc["title"]},
        )

    # Fault mappings + cases
    for fdef in FAULT_DEFS:
        await session.execute(
            delete(FaultSOPMapping).where(FaultSOPMapping.fault_type == fdef["fault_code"])
        )
        await session.execute(
            delete(FaultCase).where(FaultCase.fault_code == fdef["fault_code"])
        )

    # SOP steps + SOPs
    for sop_def in SOP_DEFS:
        result = await session.execute(select(SOP.id).where(SOP.name == sop_def["name"]))
        sop_id = result.scalar_one_or_none()
        if sop_id:
            await session.execute(delete(SOPStep).where(SOPStep.sop_id == sop_id))
            await session.execute(delete(SOP).where(SOP.id == sop_id))

    # Robot bindings (for demo teacher only)
    if demo_ids:
        teacher_ids = [uid for uid in demo_ids]
        for tid in teacher_ids:
            await session.execute(
                delete(TeacherRobotBinding).where(TeacherRobotBinding.teacher_id == tid)
            )

    # Users last
    await session.execute(delete(User).where(User.email.like(f"%{DEMO_DOMAIN}")))

    await session.commit()
    print("[reset] 演示数据已清除")


# ────────────────────────────────────────────────────────
# Main
# ────────────────────────────────────────────────────────

async def main(args: argparse.Namespace):
    async with AsyncSessionLocal() as session:
        await assert_migration_contract(session)

        if args.reset:
            await reset_demo_data(session)

        print("=== R-MOS 演示数据种子脚本 ===\n")

        print("[1/9] 用户与权限...")
        users = await tier1_users_rbac(session)
        teacher = users["teacher1@rmos.demo"]
        students = [users[f"student{i}@rmos.demo"] for i in range(1, 6)]

        print("[2/9] 机器人型号与资产...")
        robot = await tier2_robot(session, teacher)

        print("[3/9] SOP 与操作步骤...")
        sops = await tier3_sops(session, robot.id)

        print("[4/9] 教学结构（班级/课程/作业）...")
        teaching = await tier4_teaching(session, teacher, students, sops)

        print("[5/9] 任务与作业批改...")
        await tier5_tasks_attempts(session, users, teaching["assignments"])

        print("[6/9] 训练会话与步骤记录...")
        await tier6_training_sessions(session, users, sops)

        print("[7/9] 学员技能画像...")
        await tier7_skill_profiles(session, users)

        print("[8/9] 知识文档...")
        await tier8_knowledge(session, robot.id, teacher.id)

        print("[9/9] 故障案例与练习场景...")
        await tier9_faults_scenarios(session, sops, robot.id)

        await session.commit()

        print("\n=== 演示数据创建完成 ===")
        print(f"\n教师账号: teacher1@rmos.demo / Teacher@123")
        for i in range(1, 6):
            s = users[f"student{i}@rmos.demo"]
            print(f"学生账号: student{i}@rmos.demo / Student@123  ({s.full_name})")
        print(f"\n机器人: ATOM-01 (id={robot.id})")
        print(f"SOP: {len(sops)} 套")
        print(f"班级: {teaching['class'].name}")
        print(f"作业: {len(teaching['assignments'])} 个")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="创建完整的 R-MOS 演示数据")
    parser.add_argument("--reset", action="store_true", help="清除所有演示数据后重建")
    asyncio.run(main(parser.parse_args()))
