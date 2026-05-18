"""
Seed script: 31 adjudication SOPs for ATOM-01
- 1  SOP: knee-bearing-replace (sopKneeBearing.ts)
- 30 SOPs: hardware SOPs (hardwareSOPScripts.ts)

Idempotent: skips SOPs that already exist by name.
Run: python -m scripts.seed_adjudication_sops
"""
import asyncio
import sys

sys.path.insert(0, ".")

from sqlalchemy import select
from app.core.database import AsyncSessionLocal
from app.models.sop import SOP, SOPStep

# ---------------------------------------------------------------------------
# Constants (mirror hardwareSOPScripts.ts)
# ---------------------------------------------------------------------------

TORSO_M3_SET = [
    "screw_torso_m3x10_001",
    "screw_torso_m3x10_002",
    "screw_torso_m3x10_003",
    "screw_torso_m3x10_004",
    "screw_torso_m3x10_005",
    "screw_torso_m3x10_006",
    "screw_torso_m3x10_007",
    "screw_torso_m3x10_008",
]

TORSO_M4_SET = [
    "screw_torso_m4x12_001",
    "screw_torso_m4x12_002",
    "screw_torso_m4x12_003",
    "screw_torso_m4x12_004",
    "screw_torso_m4x12_005",
    "screw_torso_m4x12_006",
]

LEFT_FOOT_M4_SET = [
    "screw_left_foot_m4x10_001",
    "screw_left_foot_m4x10_002",
    "screw_left_foot_m4x10_003",
    "screw_left_foot_m4x10_004",
]

RIGHT_FOOT_M4_SET = [
    "screw_right_foot_m4x10_001",
    "screw_right_foot_m4x10_002",
    "screw_right_foot_m4x10_003",
    "screw_right_foot_m4x10_004",
]

LEFT_ANKLE_M4_SET = [
    "screw_left_ankle_m4x8_001",
    "screw_left_ankle_m4x8_002",
    "screw_left_ankle_m4x8_003",
    "screw_left_ankle_m4x8_004",
]

RIGHT_ANKLE_M4_SET = [
    "screw_right_ankle_m4x8_001",
    "screw_right_ankle_m4x8_002",
    "screw_right_ankle_m4x8_003",
    "screw_right_ankle_m4x8_004",
]

TORSO_CHEST_COVER = "frame_torso_chest"

BLOCK_ON_FAILURE = {"action": "block", "message": "裁决未通过，请按提示完成当前步骤。"}

DEFAULT_FAILURE_REASONS = [
    {
        "code": "ERR_WRONG_ORDER",
        "category": "WRONG_ORDER",
        "description": "操作顺序错误",
        "severity": "major",
        "teachingResponse": {
            "showHint": True,
            "hintContent": "请严格按照 SOP 顺序执行当前步骤。",
            "allowRetry": True,
        },
        "examResponse": {"deductPoints": 5, "allowContinue": False, "recordToReport": True},
    },
    {
        "code": "ERR_WRONG_TOOL",
        "category": "WRONG_TOOL",
        "description": "工具选择错误",
        "severity": "major",
        "teachingResponse": {
            "showHint": True,
            "hintContent": "请选择步骤要求的工具后重试。",
            "allowRetry": True,
        },
        "examResponse": {"deductPoints": 4, "allowContinue": False, "recordToReport": True},
    },
    {
        "code": "ERR_INCOMPLETE",
        "category": "INCOMPLETE_ACTION",
        "description": "步骤动作未完成",
        "severity": "major",
        "teachingResponse": {
            "showHint": True,
            "hintContent": "请完成当前步骤的全部交互后再推进。",
            "allowRetry": True,
        },
        "examResponse": {"deductPoints": 3, "allowContinue": False, "recordToReport": True},
    },
]

KNEE_BEARING_DEFAULT_FAILURE_REASONS = [
    {
        "code": "ERR_CONSTRAINT",
        "category": "CONSTRAINT_VIOLATION",
        "description": "存在 ACTIVE 结构约束，禁止操作",
        "severity": "critical",
        "teachingResponse": {
            "showHint": True,
            "hintContent": "请先解除相关约束后再继续",
            "allowRetry": True,
        },
        "examResponse": {"deductPoints": 5, "allowContinue": False, "recordToReport": True},
    },
    {
        "code": "ERR_INCOMPLETE",
        "category": "INCOMPLETE_ACTION",
        "description": "操作未完成（语义/约束/几何未满足）",
        "severity": "major",
        "teachingResponse": {
            "showHint": True,
            "hintContent": "请完成当前步骤的所有动作",
            "allowRetry": True,
        },
        "examResponse": {"deductPoints": 3, "allowContinue": False, "recordToReport": True},
    },
]

# ---------------------------------------------------------------------------
# Difficulty mapping: frontend → DB
# ---------------------------------------------------------------------------
DIFFICULTY_MAP = {
    "beginner": "low",
    "intermediate": "medium",
    "advanced": "high",
}


# ---------------------------------------------------------------------------
# Step builder functions (mirror hardwareSOPScripts.ts)
# ---------------------------------------------------------------------------

def _make_tool_precondition(tool_id: str, message: str) -> dict:
    return {"type": "TOOL_EQUIPPED", "params": {"toolId": tool_id}, "errorMessage": message}


def _make_tool_validation(tool_id: str) -> dict:
    return {"type": "TOOL_MATCHED", "params": {"toolId": tool_id}, "isRequired": True}


def _make_all_screws_validation(screw_ids: list) -> dict:
    return {"type": "ALL_SCREWS_EXTRACTED", "params": {"screwIds": screw_ids}, "isRequired": True}


def focus_step(title: str, description: str, target: str) -> dict:
    return {
        "title": title,
        "description": description,
        "action": "focus_camera",
        "target_parts": [target],
        "required_tool": None,
        "preconditions": [],
        "validations": [],
    }


def tool_step(title: str, description: str, tool_id: str) -> dict:
    return {
        "title": title,
        "description": description,
        "action": "select_tool",
        "target_parts": [],
        "required_tool": tool_id,
        "preconditions": [],
        "validations": [_make_tool_validation(tool_id)],
    }


def screw_step(title: str, description: str, screw_ids: list, tool_id: str) -> dict:
    return {
        "title": title,
        "description": description,
        "action": "rotate_screw",
        "target_parts": screw_ids,
        "required_tool": tool_id,
        "preconditions": [_make_tool_precondition(tool_id, f"请先选择 {tool_id} 工具")],
        "validations": [_make_all_screws_validation(screw_ids)],
    }


def detach_step(title: str, description: str, target: str) -> dict:
    return {
        "title": title,
        "description": description,
        "action": "detach_part",
        "target_parts": [target],
        "required_tool": None,
        "preconditions": [],
        "validations": [],
    }


def remove_step(title: str, description: str, target: str) -> dict:
    return {
        "title": title,
        "description": description,
        "action": "remove_part",
        "target_parts": [target],
        "required_tool": None,
        "preconditions": [],
        "validations": [],
    }


def unplug_step(title: str, description: str, target: str) -> dict:
    return {
        "title": title,
        "description": description,
        "action": "unplug_connector",
        "target_parts": [target],
        "required_tool": None,
        "preconditions": [],
        "validations": [],
    }


def resolve_foot_cover_part_id(ankle_roll: str) -> str:
    if ankle_roll == "left_ankle_roll_link":
        return "left_foot_rubber"
    if ankle_roll == "right_ankle_roll_link":
        return "right_foot_rubber"
    return ankle_roll


# ---------------------------------------------------------------------------
# convert step drafts → SOPStep dicts
# ---------------------------------------------------------------------------

def to_sop_steps(step_drafts: list, failure_reasons: list) -> list:
    """Convert step drafts to SOPStep model dicts."""
    steps = []
    n = len(step_drafts)
    for idx, draft in enumerate(step_drafts):
        is_last = idx == n - 1
        step_id = f"step_{str(idx + 1).zfill(3)}"
        next_step_id = "end" if is_last else f"step_{str(idx + 2).zfill(3)}"
        on_success = {
            "nextStepId": next_step_id,
            "stateTransition": "VERIFICATION" if is_last else None,
        }
        steps.append({
            "step_index": idx + 1,
            "title": draft["title"],
            "description": draft["description"],
            "target_part": draft["target_parts"][0] if draft["target_parts"] else None,
            "expected_action": draft["action"],
            "action_params": {
                "action": draft["action"],
                "target_parts": draft["target_parts"],
                "stepId": step_id,
                "preconditions": draft["preconditions"],
                "onSuccess": on_success,
                "onFailure": BLOCK_ON_FAILURE,
            },
            "validation_rules": {
                "validations": draft["validations"],
                "failureReasons": failure_reasons,
            },
            "is_critical": False,
            "severity_level": "WARN",
            "timeout_seconds": 300,
            "allow_skip": False,
            "hints": [],
            "tools_required": [draft["required_tool"]] if draft["required_tool"] else [],
        })
    return steps


def create_sop(
    sop_id: str,
    title: str,
    target_module: str,
    difficulty: str,
    estimated_time_minutes: int,
    step_drafts: list,
) -> dict:
    """Build a full SOP dict (meta + steps)."""
    return {
        "name": title,
        "description": f"sopId:{sop_id}",
        "applicable_model": "ATOM-01",
        "category": "hardware",
        "difficulty_level": DIFFICULTY_MAP[difficulty],
        "estimated_time": estimated_time_minutes * 60,
        "version": "2.0.0-hw",
        "target_module": target_module,
        "robot_model_id": 1,
        "steps": to_sop_steps(step_drafts, DEFAULT_FAILURE_REASONS),
    }


# ---------------------------------------------------------------------------
# Builder functions (mirror hardwareSOPScripts.ts)
# ---------------------------------------------------------------------------

def build_l8(core: str, points: list) -> list:
    return [
        focus_step("安全确认", "确认设备断电并完成维保隔离。", core),
        focus_step("定位检查点 1", "检查第一处关键结构/连接区域。", points[0]),
        focus_step("定位检查点 2", "检查第二处关键结构/连接区域。", points[1]),
        focus_step("定位检查点 3", "检查第三处关键结构/连接区域。", points[2]),
        focus_step("定位检查点 4", "检查第四处关键结构/连接区域。", points[3]),
        focus_step("定位检查点 5", "检查第五处关键结构/连接区域。", points[4]),
        focus_step("定位检查点 6", "检查第六处关键结构/连接区域。", points[5]),
        focus_step("结束确认", "确认本轮点检无遗漏并准备提交。", core),
    ]


def build_l9(core: str, joints: list) -> list:
    return [
        focus_step("安全确认", "确认设备断电并完成维保隔离。", core),
        focus_step("起点关节定位", "定位链路起点关节。", joints[0]),
        focus_step("次级关节定位", "定位链路次级关节。", joints[1]),
        focus_step("中段关节定位", "定位链路中段关节。", joints[2]),
        focus_step("末端关节定位", "定位链路末端关节。", joints[3]),
        focus_step("末端执行段定位", "定位末端执行关节。", joints[4]),
        focus_step("中段回查", "回查中段关节状态一致性。", joints[2]),
        focus_step("起点回查", "回查起点关节状态一致性。", joints[0]),
        focus_step("结束确认", "完成点检记录并结束。", core),
    ]


def build_l10(core: str, joints: list, cover: str) -> list:
    return [
        focus_step("安全确认", "确认设备断电并完成维保隔离。", core),
        focus_step("髋关节定位", "定位髋关节并检查姿态。", joints[0]),
        focus_step("大腿滚转定位", "定位大腿滚转并检查连接。", joints[1]),
        focus_step("大腿俯仰定位", "定位大腿俯仰并检查连接。", joints[2]),
        focus_step("膝关节定位", "定位膝关节并检查配合。", joints[3]),
        focus_step("踝俯仰定位", "定位踝俯仰并检查配合。", joints[4]),
        focus_step("踝横滚定位", "定位踝横滚并检查配合。", joints[5]),
        focus_step("覆盖件定位", "检查覆盖件贴合情况。", cover),
        focus_step("膝关节回查", "回查膝关节链路稳定性。", joints[3]),
        focus_step("结束确认", "完成下肢链路点检。", core),
    ]


def build_m16_torso() -> list:
    return [
        focus_step("安全确认", "确认设备断电并固定。", "torso_link"),
        focus_step("定位躯干作业区", "定位躯干总成作业区域。", "torso_link"),
        tool_step("选择 2.5mm 工具", "准备拆卸躯干夹板螺丝。", "hex_2.5"),
        screw_step("拆卸 M3×10 螺丝组", "拆卸躯干夹板 8 颗螺丝。", TORSO_M3_SET, "hex_2.5"),
        remove_step("移除胸腔夹板", "打开躯干覆盖作业区。", TORSO_CHEST_COVER),
        focus_step("检查电机区域", "检查躯干电机周边是否异常。", "torso_link"),
        focus_step("检查主控板区域", "检查主控板区域连接与固定。", "torso_link"),
        unplug_step("检查线束连接", "检查躯干线束连接状态。", "torso_link"),
        focus_step("回装区域定位", "定位回装基准位。", "torso_link"),
        focus_step("覆盖区对齐", "确认覆盖区对齐关系。", "torso_link"),
        focus_step("紧固顺序复核", "确认紧固顺序按对角执行。", "torso_link"),
        focus_step("外观复核 1", "复核外观与间隙。", "torso_link"),
        focus_step("外观复核 2", "复核关键连接位。", "torso_link"),
        focus_step("内部区域复核", "复核内部件干涉风险。", "torso_link"),
        focus_step("结构复核", "复核结构稳定性。", "torso_link"),
        focus_step("结束确认", "完成躯干开盖检查。", "torso_link"),
    ]


def build_m18_foot(ankle_roll: str, ankle_pitch: str, knee: str, thigh_pitch: str, screw_set: list) -> list:
    cover_part_id = resolve_foot_cover_part_id(ankle_roll)
    return [
        focus_step("安全确认", "确认设备断电并固定。", ankle_roll),
        focus_step("定位脚底覆盖区", "定位脚底覆盖件作业区域。", ankle_roll),
        remove_step("移除脚底软胶覆盖件", "拆除脚底软胶覆盖件。", cover_part_id),
        tool_step("选择 3mm 工具", "准备拆卸脚底螺丝。", "hex_3"),
        screw_step("拆卸脚底 M4×10 螺丝组", "拆卸脚底 4 颗螺丝。", screw_set, "hex_3"),
        detach_step("分离脚底板", "分离脚底板并检查配合面。", ankle_roll),
        focus_step("检查踝俯仰", "检查踝俯仰连接状态。", ankle_pitch),
        focus_step("检查膝关节", "检查膝关节连接状态。", knee),
        focus_step("脚底板回装定位", "定位脚底板回装基准。", ankle_roll),
        focus_step("覆盖件回装定位", "定位覆盖件回装基准。", ankle_roll),
        focus_step("链路复核 1", "复核大腿到踝部链路。", thigh_pitch),
        focus_step("链路复核 2", "复核踝关节链路。", ankle_pitch),
        focus_step("链路复核 3", "复核脚底板链路。", ankle_roll),
        focus_step("贴合复核", "复核覆盖件贴合状态。", ankle_roll),
        focus_step("膝关节回查", "回查膝关节稳定性。", knee),
        focus_step("大腿回查", "回查大腿连接稳定性。", thigh_pitch),
        focus_step("底座回查", "回查底座支撑稳定性。", "base_link"),
        focus_step("结束确认", "完成脚底覆盖件拆装检查。", ankle_roll),
    ]


def build_m20_ankle(ankle_roll: str, ankle_pitch: str, knee: str, thigh_pitch: str, foot_screw_set: list, ankle_screw_set: list) -> list:
    cover_part_id = resolve_foot_cover_part_id(ankle_roll)
    return [
        focus_step("安全确认", "确认设备断电并固定。", ankle_roll),
        focus_step("定位脚底覆盖区", "定位脚底覆盖件作业区域。", ankle_roll),
        remove_step("移除脚底软胶覆盖件", "拆除脚底软胶覆盖件。", cover_part_id),
        tool_step("选择 3mm 工具", "准备拆卸脚底螺丝。", "hex_3"),
        screw_step("拆卸脚底 M4×10 螺丝组", "拆卸脚底 4 颗螺丝。", foot_screw_set, "hex_3"),
        detach_step("分离脚底板", "分离脚底板。", ankle_roll),
        focus_step("踝俯仰可达性检查", "确认踝俯仰可达并无遮挡。", ankle_pitch),
        screw_step("拆卸踝关节 M4×8 螺丝组", "拆卸踝关节 4 颗螺丝。", ankle_screw_set, "hex_3"),
        detach_step("分离踝俯仰件", "分离踝俯仰件。", ankle_pitch),
        focus_step("检查膝关节连接", "检查膝关节连接状态。", knee),
        focus_step("检查大腿俯仰连接", "检查大腿俯仰连接状态。", thigh_pitch),
        focus_step("踝俯仰回装定位", "定位踝俯仰回装基准。", ankle_pitch),
        focus_step("脚底板回装定位", "定位脚底板回装基准。", ankle_roll),
        focus_step("覆盖件回装定位", "定位覆盖件回装基准。", ankle_roll),
        focus_step("脚踝同轴复核", "复核脚踝同轴状态。", ankle_pitch),
        focus_step("脚底平面复核", "复核脚底平面状态。", ankle_roll),
        focus_step("膝踝链路复核", "复核膝踝链路。", knee),
        focus_step("大腿链路复核", "复核大腿链路。", thigh_pitch),
        focus_step("底座姿态复核", "复核底座姿态稳定性。", "base_link"),
        focus_step("结束确认", "完成踝总成拆检。", ankle_roll),
    ]


def build_h24_torso(primary: str) -> list:
    primary_label = "电机" if primary == "motor" else "主控板"
    return [
        focus_step("安全确认", "确认设备断电并固定。", "torso_link"),
        focus_step("主模块定位", "定位躯干主模块。", "torso_link"),
        focus_step("支撑模块定位", "定位底座支撑模块。", "base_link"),
        tool_step("选择 3mm 工具", "准备拆卸躯干主固定螺丝。", "hex_3"),
        screw_step("拆卸 M4×12 螺丝组", "拆卸躯干主固定 6 颗螺丝。", TORSO_M4_SET, "hex_3"),
        focus_step("分离作业区确认", "确认躯干外层作业区可达。", "torso_link"),
        tool_step("切换 2.5mm 工具", "准备拆卸夹板螺丝。", "hex_2.5"),
        screw_step("拆卸 M3×10 螺丝组", "拆卸夹板 8 颗螺丝。", TORSO_M3_SET, "hex_2.5"),
        remove_step("移除躯干覆盖层", "移除躯干覆盖层。", TORSO_CHEST_COVER),
        focus_step("内部件检查 1", f"检查{primary_label}区域。", "torso_link"),
        focus_step("内部件检查 2", "检查次级关键件区域。", "torso_link"),
        focus_step("主链路检查", "检查主链路是否顺畅。", "torso_link"),
        focus_step("支撑链路检查", "检查支撑链路是否稳定。", "base_link"),
        unplug_step("连接器检查", "检查并复核连接器状态。", "torso_link"),
        focus_step("内部件复核 1", f"复核{primary_label}区域状态。", "torso_link"),
        focus_step("内部件复核 2", "复核次级关键件状态。", "torso_link"),
        focus_step("覆盖层回装定位", "定位覆盖层回装基准。", "torso_link"),
        focus_step("外层回装定位", "定位外层回装基准。", "torso_link"),
        focus_step("主链路复核", "复核主链路。", "torso_link"),
        focus_step("支撑链路复核", "复核支撑链路。", "base_link"),
        focus_step("底座姿态复核", "复核底座姿态稳定性。", "base_link"),
        focus_step("躯干姿态复核", "复核躯干姿态稳定性。", "torso_link"),
        focus_step("关键点终检", f"终检{primary_label}作业区域。", "torso_link"),
        focus_step("结束确认", f"完成躯干{primary_label}维保流程。", "torso_link"),
    ]


def build_h22_ankle(ankle_roll: str, ankle_pitch: str, knee: str, thigh_pitch: str, foot_screw_set: list, ankle_screw_set: list) -> list:
    cover_part_id = resolve_foot_cover_part_id(ankle_roll)
    return [
        focus_step("安全确认", "确认设备断电并固定。", "torso_link"),
        focus_step("定位脚底模块", "定位脚底模块。", ankle_roll),
        focus_step("定位踝关节模块", "定位踝关节模块。", ankle_pitch),
        remove_step("移除脚底软胶覆盖件", "拆除脚底软胶覆盖件。", cover_part_id),
        tool_step("选择 3mm 工具", "准备拆卸脚底螺丝。", "hex_3"),
        screw_step("拆卸脚底 M4×10 螺丝组", "拆卸脚底螺丝组。", foot_screw_set, "hex_3"),
        detach_step("分离脚底板组件", "分离脚底板组件。", ankle_roll),
        focus_step("第二组件定位", "定位踝俯仰组件。", ankle_pitch),
        tool_step("保持 3mm 工具", "继续拆卸踝关节螺丝。", "hex_3"),
        screw_step("拆卸踝关节 M4×8 螺丝组", "拆卸踝关节螺丝组。", ankle_screw_set, "hex_3"),
        focus_step("覆盖区域暴露确认", "确认覆盖区域已暴露内部。", ankle_roll),
        focus_step("内部件检查 1", "检查膝关节连接区。", knee),
        focus_step("内部件检查 2", "检查大腿连接区。", thigh_pitch),
        unplug_step("连接状态检查", "检查连接状态与线束走向。", ankle_pitch),
        focus_step("目标件回装定位", "定位踝俯仰回装基准。", ankle_pitch),
        focus_step("覆盖区回装定位", "定位覆盖区回装基准。", ankle_roll),
        focus_step("脚底组件回装定位", "定位脚底组件回装基准。", ankle_roll),
        focus_step("链路复核 1", "复核踝关节链路。", ankle_pitch),
        focus_step("链路复核 2", "复核脚底模块链路。", ankle_roll),
        focus_step("结构复核", "复核底座到腿部结构链路。", "base_link"),
        focus_step("关键件复核 1", "复核膝关节关键点。", knee),
        focus_step("关键件复核 2", "复核大腿关键点。", thigh_pitch),
        focus_step("结束确认", "完成踝总成大修流程。", "torso_link"),
    ]


def build_h30_annual() -> list:
    return [
        focus_step("安全确认", "确认设备断电并固定。", "base_link"),
        focus_step("躯干定位", "定位躯干模块。", "torso_link"),
        focus_step("左臂起点定位", "定位左肩 Pitch。", "left_arm_pitch_link"),
        focus_step("左臂中段定位", "定位左肩 Roll。", "left_arm_roll_link"),
        focus_step("左臂末端定位", "定位左前臂。", "left_elbow_yaw_link"),
        focus_step("左腿髋关节定位", "定位左髋关节。", "left_thigh_yaw_link"),
        focus_step("左腿膝关节定位", "定位左膝关节。", "left_knee_link"),
        focus_step("左腿踝关节定位", "定位左踝关节。", "left_ankle_pitch_link"),
        focus_step("右腿髋关节定位", "定位右髋关节。", "right_thigh_yaw_link"),
        focus_step("右腿膝关节定位", "定位右膝关节。", "right_knee_link"),
        focus_step("右腿踝关节定位", "定位右踝关节。", "right_ankle_pitch_link"),
        focus_step("左脚覆盖区检查", "检查左脚覆盖区。", "left_ankle_roll_link"),
        focus_step("右脚覆盖区检查", "检查右脚覆盖区。", "right_ankle_roll_link"),
        remove_step("移除左脚软胶覆盖件", "拆除左脚底软胶覆盖件。", "left_foot_rubber"),
        remove_step("移除右脚软胶覆盖件", "拆除右脚底软胶覆盖件。", "right_foot_rubber"),
        tool_step("选择 3mm 工具", "准备拆卸下肢螺丝。", "hex_3"),
        screw_step("拆卸左脚底螺丝组", "拆卸左脚底 M4×10 螺丝组。", LEFT_FOOT_M4_SET, "hex_3"),
        screw_step("拆卸右脚底螺丝组", "拆卸右脚底 M4×10 螺丝组。", RIGHT_FOOT_M4_SET, "hex_3"),
        screw_step("拆卸左踝螺丝组", "拆卸左踝 M4×8 螺丝组。", LEFT_ANKLE_M4_SET, "hex_3"),
        screw_step("拆卸右踝螺丝组", "拆卸右踝 M4×8 螺丝组。", RIGHT_ANKLE_M4_SET, "hex_3"),
        tool_step("切换 2.5mm 工具", "准备拆卸躯干夹板螺丝。", "hex_2.5"),
        screw_step("拆卸躯干夹板螺丝组", "拆卸躯干 M3×10 螺丝组。", TORSO_M3_SET, "hex_2.5"),
        remove_step("移除躯干覆盖区", "移除躯干覆盖区。", TORSO_CHEST_COVER),
        focus_step("躯干电机区检查", "检查躯干电机区域。", "torso_link"),
        focus_step("主控板区检查", "检查主控板区域。", "torso_link"),
        unplug_step("躯干线束检查", "检查躯干线束连接。", "torso_link"),
        focus_step("覆盖区回装定位", "定位躯干覆盖区回装基准。", "torso_link"),
        focus_step("左腿链路复核", "复核左腿链路。", "left_ankle_roll_link"),
        focus_step("右腿链路复核", "复核右腿链路。", "right_ankle_roll_link"),
        focus_step("左臂链路复核", "复核左臂链路。", "left_elbow_pitch_link"),
        focus_step("躯干姿态复核", "复核躯干姿态。", "torso_link"),
        focus_step("结束确认", "完成年度大保养流程。", "base_link"),
    ]


def build_h21_structural() -> list:
    return [
        focus_step("安全确认", "确认设备断电并固定。", "base_link"),
        focus_step("躯干主区定位", "定位躯干主区。", "torso_link"),
        tool_step("选择 3mm 工具", "准备拆卸主固定螺丝。", "hex_3"),
        screw_step("拆卸躯干 M4×12 螺丝组", "拆卸躯干主固定螺丝。", TORSO_M4_SET, "hex_3"),
        focus_step("左脚区域定位", "定位左脚底区域。", "left_ankle_roll_link"),
        remove_step("移除左脚软胶覆盖件", "拆除左脚底软胶覆盖件。", "left_foot_rubber"),
        screw_step("拆卸左脚底 M4×10 螺丝组", "拆卸左脚底螺丝。", LEFT_FOOT_M4_SET, "hex_3"),
        focus_step("右脚区域定位", "定位右脚底区域。", "right_ankle_roll_link"),
        remove_step("移除右脚软胶覆盖件", "拆除右脚底软胶覆盖件。", "right_foot_rubber"),
        screw_step("拆卸右脚底 M4×10 螺丝组", "拆卸右脚底螺丝。", RIGHT_FOOT_M4_SET, "hex_3"),
        tool_step("切换 2.5mm 工具", "准备拆卸夹板螺丝。", "hex_2.5"),
        screw_step("拆卸躯干 M3×10 螺丝组", "拆卸躯干夹板螺丝。", TORSO_M3_SET, "hex_2.5"),
        focus_step("预紧力复核 1", "复核躯干连接位。", "torso_link"),
        focus_step("预紧力复核 2", "复核左脚连接位。", "left_ankle_roll_link"),
        focus_step("预紧力复核 3", "复核右脚连接位。", "right_ankle_roll_link"),
        focus_step("链路复核 1", "复核左腿链路。", "left_ankle_pitch_link"),
        focus_step("链路复核 2", "复核右腿链路。", "right_ankle_pitch_link"),
        focus_step("链路复核 3", "复核底座链路。", "base_link"),
        focus_step("结构复核 1", "复核躯干结构。", "torso_link"),
        focus_step("结构复核 2", "复核左腿结构。", "left_knee_link"),
        focus_step("结构复核 3", "复核右腿结构。", "right_knee_link"),
        focus_step("最终复核", "复核整体预紧一致性。", "torso_link"),
        focus_step("结束确认", "完成结构预紧力重检。", "base_link"),
    ]


def build_h22_chest_audit() -> list:
    return [
        focus_step("安全确认", "确认设备断电并固定。", "torso_link"),
        focus_step("躯干定位", "定位躯干作业区。", "torso_link"),
        tool_step("选择 2.5mm 工具", "准备拆卸夹板螺丝。", "hex_2.5"),
        screw_step("第一轮拆卸 M3×10 螺丝组", "执行第一轮夹板螺丝拆卸。", TORSO_M3_SET, "hex_2.5"),
        remove_step("第一轮移除覆盖区", "移除躯干覆盖区。", TORSO_CHEST_COVER),
        focus_step("第一轮电机区检查", "检查电机区状态。", "torso_link"),
        focus_step("第一轮主控板区检查", "检查主控板区状态。", "torso_link"),
        focus_step("第一轮回装定位", "定位第一轮回装基准。", "torso_link"),
        tool_step("再次确认 2.5mm 工具", "准备执行第二轮拆装。", "hex_2.5"),
        focus_step("第二轮拆卸路径复核", "复核第二轮夹板拆卸路径。", "torso_link"),
        focus_step("第二轮覆盖区状态确认", "确认第二轮覆盖区状态。", "torso_link"),
        focus_step("第二轮电机区检查", "复检电机区状态。", "torso_link"),
        focus_step("第二轮主控板区检查", "复检主控板区状态。", "torso_link"),
        unplug_step("线束状态核查", "核查线束连接稳定性。", "torso_link"),
        focus_step("第二轮回装定位", "定位第二轮回装基准。", "torso_link"),
        focus_step("结构复核 1", "复核夹板区域结构。", "torso_link"),
        focus_step("结构复核 2", "复核躯干主结构。", "torso_link"),
        focus_step("链路复核 1", "复核躯干到底座链路。", "base_link"),
        focus_step("链路复核 2", "复核躯干内部链路。", "torso_link"),
        focus_step("审计记录核对", "核对重复拆装记录完整性。", "torso_link"),
        focus_step("结束确认", "完成胸腔夹板拆装审计。", "torso_link"),
    ]


def build_h22_foot_audit(ankle_roll: str, ankle_pitch: str, knee: str, foot_screw_set: list) -> list:
    cover_part_id = resolve_foot_cover_part_id(ankle_roll)
    return [
        focus_step("安全确认", "确认设备断电并固定。", ankle_roll),
        focus_step("脚底区域定位", "定位脚底区域。", ankle_roll),
        remove_step("移除覆盖件", "移除脚底软胶覆盖件。", cover_part_id),
        tool_step("选择 3mm 工具", "准备拆卸脚底螺丝。", "hex_3"),
        screw_step("第一轮拆卸脚底 M4×10 螺丝组", "执行第一轮脚底螺丝拆卸。", foot_screw_set, "hex_3"),
        detach_step("第一轮分离脚底板", "分离脚底板。", ankle_roll),
        focus_step("第一轮踝关节检查", "检查踝关节状态。", ankle_pitch),
        focus_step("第一轮膝关节检查", "检查膝关节状态。", knee),
        focus_step("第一轮回装定位", "定位第一轮回装基准。", ankle_roll),
        tool_step("保持 3mm 工具", "准备执行第二轮拆装。", "hex_3"),
        focus_step("第二轮拆卸路径复核", "复核第二轮脚底螺丝拆卸路径。", ankle_roll),
        focus_step("第二轮分离路径复核", "复核第二轮脚底板分离路径。", ankle_roll),
        focus_step("第二轮踝关节检查", "复检踝关节状态。", ankle_pitch),
        focus_step("第二轮膝关节检查", "复检膝关节状态。", knee),
        focus_step("第二轮回装定位", "定位第二轮回装基准。", ankle_roll),
        focus_step("结构复核 1", "复核脚底板结构。", ankle_roll),
        focus_step("结构复核 2", "复核踝关节结构。", ankle_pitch),
        focus_step("链路复核 1", "复核膝踝链路。", knee),
        focus_step("链路复核 2", "复核底座支撑链路。", "base_link"),
        focus_step("审计记录核对", "核对重复拆装记录完整性。", ankle_roll),
        focus_step("最终复核", "复核脚底区域稳定性。", ankle_roll),
        focus_step("结束确认", "完成脚底板拆装审计。", ankle_roll),
    ]


def build_h24_baseline() -> list:
    return [
        focus_step("安全确认", "确认设备断电并固定。", "base_link"),
        focus_step("主模块定位", "定位底座主模块。", "base_link"),
        focus_step("支撑模块定位", "定位躯干支撑模块。", "torso_link"),
        remove_step("移除左脚软胶覆盖件", "拆除左脚底软胶覆盖件。", "left_foot_rubber"),
        tool_step("选择 3mm 工具", "准备拆卸脚底螺丝。", "hex_3"),
        screw_step("拆卸左脚底 M4×10 螺丝组", "拆卸左脚底螺丝。", LEFT_FOOT_M4_SET, "hex_3"),
        detach_step("分离左脚底组件", "分离左脚底组件。", "left_ankle_roll_link"),
        tool_step("切换 2.5mm 工具", "准备拆卸躯干螺丝。", "hex_2.5"),
        screw_step("拆卸躯干 M3×10 螺丝组", "拆卸躯干夹板螺丝。", TORSO_M3_SET, "hex_2.5"),
        remove_step("移除躯干覆盖区", "移除躯干覆盖区。", TORSO_CHEST_COVER),
        focus_step("内部件检查 1", "检查躯干关键区域。", "torso_link"),
        focus_step("内部件检查 2", "检查左臂关键区域。", "left_arm_pitch_link"),
        focus_step("主链路检查", "检查底座主链路。", "base_link"),
        focus_step("支撑链路检查", "检查躯干支撑链路。", "torso_link"),
        unplug_step("连接器检查", "检查躯干连接状态。", "torso_link"),
        focus_step("内部件复核 1", "复核躯干关键区域。", "torso_link"),
        focus_step("内部件复核 2", "复核左臂关键区域。", "left_arm_pitch_link"),
        focus_step("覆盖区回装定位", "定位躯干覆盖区回装基准。", "torso_link"),
        focus_step("组件回装定位", "定位左脚底组件回装基准。", "left_ankle_roll_link"),
        focus_step("主链路复核", "复核底座主链路。", "base_link"),
        focus_step("支撑链路复核", "复核躯干支撑链路。", "torso_link"),
        focus_step("底座姿态复核", "复核底座姿态。", "base_link"),
        focus_step("躯干姿态复核", "复核躯干姿态。", "torso_link"),
        focus_step("关键点终检", "终检关键点状态。", "torso_link"),
        focus_step("结束确认", "完成全身关键点基线复核。", "torso_link"),
    ]


def build_h28_master_flow() -> list:
    return [
        focus_step("安全确认", "确认设备断电并固定。", "base_link"),
        focus_step("躯干主区定位", "定位躯干主区。", "torso_link"),
        tool_step("选择 2.5mm 工具", "准备拆卸躯干螺丝。", "hex_2.5"),
        screw_step("拆卸躯干 M3×10 螺丝组", "拆卸躯干夹板螺丝。", TORSO_M3_SET, "hex_2.5"),
        remove_step("移除躯干覆盖区", "移除躯干覆盖区。", TORSO_CHEST_COVER),
        focus_step("躯干内部检查 1", "检查电机区域。", "torso_link"),
        focus_step("躯干内部检查 2", "检查主控板区域。", "torso_link"),
        unplug_step("躯干连接检查", "检查躯干连接状态。", "torso_link"),
        focus_step("躯干回装定位", "定位躯干回装基准。", "torso_link"),
        focus_step("左踝模块定位", "定位左踝模块。", "left_ankle_roll_link"),
        remove_step("移除左脚软胶覆盖件", "拆除左脚底软胶覆盖件。", "left_foot_rubber"),
        tool_step("切换 3mm 工具", "准备拆卸左脚底螺丝。", "hex_3"),
        screw_step("拆卸左脚底 M4×10 螺丝组", "拆卸左脚底螺丝。", LEFT_FOOT_M4_SET, "hex_3"),
        detach_step("分离左脚底组件", "分离左脚底组件。", "left_ankle_roll_link"),
        screw_step("拆卸左踝 M4×8 螺丝组", "拆卸左踝螺丝。", LEFT_ANKLE_M4_SET, "hex_3"),
        detach_step("分离左踝俯仰件", "分离左踝俯仰件。", "left_ankle_pitch_link"),
        focus_step("左踝链路复核", "复核左踝链路。", "left_knee_link"),
        focus_step("右踝模块定位", "定位右踝模块。", "right_ankle_roll_link"),
        remove_step("移除右脚软胶覆盖件", "拆除右脚底软胶覆盖件。", "right_foot_rubber"),
        screw_step("拆卸右脚底 M4×10 螺丝组", "拆卸右脚底螺丝。", RIGHT_FOOT_M4_SET, "hex_3"),
        detach_step("分离右脚底组件", "分离右脚底组件。", "right_ankle_roll_link"),
        screw_step("拆卸右踝 M4×8 螺丝组", "拆卸右踝螺丝。", RIGHT_ANKLE_M4_SET, "hex_3"),
        detach_step("分离右踝俯仰件", "分离右踝俯仰件。", "right_ankle_pitch_link"),
        focus_step("右踝链路复核", "复核右踝链路。", "right_knee_link"),
        focus_step("左右链路一致性复核", "复核左右链路一致性。", "base_link"),
        focus_step("左臂链路复核", "复核左臂链路。", "left_elbow_pitch_link"),
        focus_step("躯干姿态复核", "复核躯干姿态。", "torso_link"),
        focus_step("全身姿态复核", "复核全身姿态。", "base_link"),
        focus_step("记录与审计复核", "复核维保记录完整性。", "torso_link"),
        focus_step("结束确认", "完成主维保综合流程。", "base_link"),
    ]


# ---------------------------------------------------------------------------
# Knee-bearing SOP (sopKneeBearing.ts)
# ---------------------------------------------------------------------------

KNEE_BEARING_FAILURE_REASONS_JSON = KNEE_BEARING_DEFAULT_FAILURE_REASONS
KNEE_BEARING_BLOCK_ON_FAILURE = {"action": "block", "message": "裁决未通过，操作被阻断"}

def _make_knee_step(step_id: str, step_index: int, title: str, description: str, target_parts: list, next_step_id: str) -> dict:
    return {
        "step_index": step_index,
        "title": title,
        "description": description,
        "target_part": target_parts[0] if target_parts else None,
        "expected_action": "focus_camera",
        "action_params": {
            "action": "focus_camera",
            "target_parts": target_parts,
            "stepId": step_id,
            "preconditions": [],
            "onSuccess": {
                "nextStepId": next_step_id,
                "stateTransition": "VERIFICATION" if next_step_id == "COMPLETE" else None,
            },
            "onFailure": KNEE_BEARING_BLOCK_ON_FAILURE,
        },
        "validation_rules": {
            "validations": [],
            "failureReasons": KNEE_BEARING_FAILURE_REASONS_JSON,
        },
        "is_critical": False,
        "severity_level": "WARN",
        "timeout_seconds": 300,
        "allow_skip": False,
        "hints": [],
        "tools_required": [],
    }


SOP_KNEE_BEARING = {
    "name": "ATOM-01 左膝关节轴承更换",
    "description": "sopId:knee-bearing-replace",
    "applicable_model": "ATOM-01",
    "category": "hardware",
    "difficulty_level": "medium",
    "estimated_time": 45 * 60,
    "version": "1.0.0",
    "target_module": "left_knee",
    "robot_model_id": 1,
    "steps": [
        _make_knee_step("kbr-01", 1, "安全确认",
            "断电并确认维保隔离，确保机器人处于安全停机状态。确认电源指示灯熄灭，检查急停按钮已锁定。",
            ["left_knee_link"], "kbr-02"),
        _make_knee_step("kbr-02", 2, "工具准备",
            "确认 M3 内六角扳手、轴承拔取器、锂基润滑脂就位。",
            [], "kbr-03"),
        _make_knee_step("kbr-03", 3, "外壳拆卸",
            "拆卸左膝关节保护外壳，共 4 颗 M3 内六角螺丝，按对角线顺序拆卸，注意保管垫片。",
            ["left_knee_link"], "kbr-04"),
        _make_knee_step("kbr-04", 4, "轴承定位",
            "定位磨损轴承，观察并记录磨损状态（划痕、变色、异响）。检查滚珠表面是否有凹坑，记录磨损照片作为证据。",
            ["left_knee_link"], "kbr-05"),
        _make_knee_step("kbr-05", 5, "轴承更换",
            "使用拔取器取出旧轴承，安装新轴承（型号 6205-2RS），涂抹润滑脂。拔取时保持垂直用力，避免损伤轴座，新轴承安装前涂抹薄层润滑脂。",
            ["left_knee_link"], "kbr-06"),
        _make_knee_step("kbr-06", 6, "回装验证",
            "回装保护外壳，通电，执行关节活动度测试（±90° 全范围旋转）。螺丝按对角线顺序紧固，通电后先低速空载运行 5 分钟。",
            ["left_knee_link"], "COMPLETE"),
    ],
}

# ---------------------------------------------------------------------------
# All 30 hardware SOPs (hardwareSOPScripts.ts)
# ---------------------------------------------------------------------------

HARDWARE_SOP_SCRIPTS = [
    # Low difficulty (beginner) - 5
    create_sop("sop-hw-l01", "躯干外观与连接点检", "torso", "beginner", 12, build_l8("torso_link", [
        "torso_link", "left_arm_pitch_link", "right_arm_pitch_link",
        "base_link", "left_thigh_yaw_link", "right_thigh_yaw_link",
    ])),
    create_sop("sop-hw-l02", "左臂关节快速点检", "left_arm", "beginner", 14, build_l9("torso_link", [
        "left_arm_pitch_link", "left_arm_roll_link", "left_arm_yaw_link",
        "left_elbow_pitch_link", "left_elbow_yaw_link",
    ])),
    create_sop("sop-hw-l03", "左腿链路快速点检", "left_leg", "beginner", 16, build_l10("base_link", [
        "left_thigh_yaw_link", "left_thigh_roll_link", "left_thigh_pitch_link",
        "left_knee_link", "left_ankle_pitch_link", "left_ankle_roll_link",
    ], "left_ankle_roll_link")),
    create_sop("sop-hw-l04", "右腿链路快速点检", "right_leg", "beginner", 16, build_l10("base_link", [
        "right_thigh_yaw_link", "right_thigh_roll_link", "right_thigh_pitch_link",
        "right_knee_link", "right_ankle_pitch_link", "right_ankle_roll_link",
    ], "right_ankle_roll_link")),
    create_sop("sop-hw-l05", "双脚底覆盖件点检", "base", "beginner", 12, build_l8("base_link", [
        "left_ankle_roll_link", "right_ankle_roll_link", "left_ankle_pitch_link",
        "right_ankle_pitch_link", "left_knee_link", "right_knee_link",
    ])),

    # Medium difficulty (intermediate) - 10
    create_sop("sop-hw-m01", "躯干开盖检查", "torso", "intermediate", 24, build_m16_torso()),
    create_sop("sop-hw-m02", "躯干电机可达性检查", "torso", "intermediate", 28, [
        focus_step("安全确认", "确认设备断电并固定。", "torso_link"),
        focus_step("定位躯干主区", "定位躯干主区。", "torso_link"),
        tool_step("选择 3mm 工具", "准备拆卸主固定螺丝。", "hex_3"),
        screw_step("拆卸 M4×12 螺丝组", "拆卸躯干主固定螺丝。", TORSO_M4_SET, "hex_3"),
        focus_step("分离作业区确认", "确认躯干外层作业区可达。", "torso_link"),
        tool_step("切换 2.5mm 工具", "准备拆卸夹板螺丝。", "hex_2.5"),
        screw_step("拆卸 M3×10 螺丝组", "拆卸夹板螺丝。", TORSO_M3_SET, "hex_2.5"),
        remove_step("移除覆盖区", "移除躯干覆盖区。", TORSO_CHEST_COVER),
        focus_step("电机可达性检查 1", "检查电机区域可达性。", "torso_link"),
        focus_step("电机可达性检查 2", "复核电机区域可达性。", "torso_link"),
        unplug_step("线束可达性检查", "检查线束通道可达性。", "torso_link"),
        focus_step("回装定位 1", "定位覆盖区回装基准。", "torso_link"),
        focus_step("回装定位 2", "定位外层回装基准。", "torso_link"),
        focus_step("链路复核 1", "复核躯干主链路。", "torso_link"),
        focus_step("链路复核 2", "复核底座支撑链路。", "base_link"),
        focus_step("姿态复核", "复核躯干姿态。", "torso_link"),
        focus_step("关键点终检", "终检电机作业区。", "torso_link"),
        focus_step("结束确认", "完成躯干电机可达性检查。", "torso_link"),
    ]),
    create_sop("sop-hw-m03", "躯干主控板可达性检查", "torso", "intermediate", 26,
        build_m16_torso()[:8] + [
            focus_step("主控板可达性检查 1", "检查主控板区域可达性。", "torso_link"),
            focus_step("主控板可达性检查 2", "复核主控板区域可达性。", "torso_link"),
            focus_step("回装定位 1", "定位回装基准。", "torso_link"),
            focus_step("回装定位 2", "复核回装对齐。", "torso_link"),
            focus_step("链路复核 1", "复核躯干链路。", "torso_link"),
            focus_step("链路复核 2", "复核底座链路。", "base_link"),
            focus_step("姿态复核", "复核躯干姿态。", "torso_link"),
            focus_step("结束确认", "完成躯干主控板可达性检查。", "torso_link"),
        ]
    ),
    create_sop("sop-hw-m04", "躯干主固定螺丝复检", "torso", "intermediate", 22, [
        focus_step("安全确认", "确认设备断电并固定。", "torso_link"),
        focus_step("定位躯干主区", "定位躯干主区。", "torso_link"),
        tool_step("选择 3mm 工具", "准备拆卸主固定螺丝。", "hex_3"),
        screw_step("拆卸 M4×12 螺丝组", "拆卸主固定螺丝。", TORSO_M4_SET, "hex_3"),
        focus_step("螺孔检查 1", "检查第一组螺孔状态。", "torso_link"),
        focus_step("螺孔检查 2", "检查第二组螺孔状态。", "torso_link"),
        focus_step("接口检查", "检查主接口区域状态。", "torso_link"),
        focus_step("结构检查", "检查结构连接状态。", "torso_link"),
        focus_step("回装定位 1", "定位回装基准。", "torso_link"),
        focus_step("回装定位 2", "复核回装对齐。", "torso_link"),
        focus_step("预紧复核 1", "复核预紧顺序。", "torso_link"),
        focus_step("预紧复核 2", "复核预紧一致性。", "torso_link"),
        focus_step("链路复核 1", "复核躯干链路。", "torso_link"),
        focus_step("链路复核 2", "复核底座链路。", "base_link"),
        focus_step("结束确认", "完成躯干主固定螺丝复检。", "torso_link"),
    ]),
    create_sop("sop-hw-m05", "左脚底软胶拆装检查", "left_leg", "intermediate", 26,
        build_m18_foot("left_ankle_roll_link", "left_ankle_pitch_link", "left_knee_link", "left_thigh_pitch_link", LEFT_FOOT_M4_SET),
    ),
    create_sop("sop-hw-m06", "右脚底软胶拆装检查", "right_leg", "intermediate", 26,
        build_m18_foot("right_ankle_roll_link", "right_ankle_pitch_link", "right_knee_link", "right_thigh_pitch_link", RIGHT_FOOT_M4_SET),
    ),
    create_sop("sop-hw-m07", "左踝总成拆检", "left_leg", "intermediate", 30,
        build_m20_ankle("left_ankle_roll_link", "left_ankle_pitch_link", "left_knee_link", "left_thigh_pitch_link", LEFT_FOOT_M4_SET, LEFT_ANKLE_M4_SET),
    ),
    create_sop("sop-hw-m08", "右踝总成拆检", "right_leg", "intermediate", 30,
        build_m20_ankle("right_ankle_roll_link", "right_ankle_pitch_link", "right_knee_link", "right_thigh_pitch_link", RIGHT_FOOT_M4_SET, RIGHT_ANKLE_M4_SET),
    ),
    create_sop("sop-hw-m09", "双脚紧固一致性维保", "base", "intermediate", 28, [
        focus_step("安全确认", "确认设备断电并固定。", "base_link"),
        focus_step("定位左脚模块", "定位左脚模块。", "left_ankle_roll_link"),
        focus_step("定位右脚模块", "定位右脚模块。", "right_ankle_roll_link"),
        remove_step("移除左脚软胶覆盖件", "拆除左脚底软胶覆盖件。", "left_foot_rubber"),
        remove_step("移除右脚软胶覆盖件", "拆除右脚底软胶覆盖件。", "right_foot_rubber"),
        tool_step("选择 3mm 工具", "准备拆卸脚底螺丝。", "hex_3"),
        screw_step("拆卸左脚底螺丝组", "拆卸左脚底 M4×10 螺丝组。", LEFT_FOOT_M4_SET, "hex_3"),
        screw_step("拆卸右脚底螺丝组", "拆卸右脚底 M4×10 螺丝组。", RIGHT_FOOT_M4_SET, "hex_3"),
        screw_step("拆卸左踝螺丝组", "拆卸左踝 M4×8 螺丝组。", LEFT_ANKLE_M4_SET, "hex_3"),
        screw_step("拆卸右踝螺丝组", "拆卸右踝 M4×8 螺丝组。", RIGHT_ANKLE_M4_SET, "hex_3"),
        focus_step("左脚链路复核 1", "复核左脚底板链路。", "left_ankle_roll_link"),
        focus_step("右脚链路复核 1", "复核右脚底板链路。", "right_ankle_roll_link"),
        focus_step("左脚链路复核 2", "复核左踝链路。", "left_ankle_pitch_link"),
        focus_step("右脚链路复核 2", "复核右踝链路。", "right_ankle_pitch_link"),
        focus_step("左腿链路复核", "复核左腿下肢链路。", "left_knee_link"),
        focus_step("右腿链路复核", "复核右腿下肢链路。", "right_knee_link"),
        focus_step("一致性复核 1", "复核左右脚底一致性。", "base_link"),
        focus_step("一致性复核 2", "复核左右踝一致性。", "base_link"),
        focus_step("结束确认", "完成双脚紧固一致性维保。", "base_link"),
    ]),
    create_sop("sop-hw-m10", "躯干-底座连接维保", "torso", "intermediate", 22, [
        focus_step("安全确认", "确认设备断电并固定。", "base_link"),
        focus_step("定位躯干连接区", "定位躯干连接区。", "torso_link"),
        focus_step("定位底座支撑区", "定位底座支撑区。", "base_link"),
        tool_step("选择 3mm 工具", "准备拆卸躯干主固定螺丝。", "hex_3"),
        screw_step("拆卸 M4×12 螺丝组", "拆卸躯干主固定螺丝。", TORSO_M4_SET, "hex_3"),
        focus_step("分离作业区确认", "确认躯干作业区可达。", "torso_link"),
        focus_step("连接面检查 1", "检查躯干连接面。", "torso_link"),
        focus_step("连接面检查 2", "检查底座连接面。", "base_link"),
        focus_step("紧固位检查", "检查紧固位状态。", "torso_link"),
        focus_step("回装定位 1", "定位躯干回装基准。", "torso_link"),
        focus_step("回装定位 2", "定位底座回装基准。", "base_link"),
        focus_step("链路复核 1", "复核躯干链路。", "torso_link"),
        focus_step("链路复核 2", "复核底座链路。", "base_link"),
        focus_step("姿态复核", "复核躯干与底座姿态。", "base_link"),
        focus_step("结束确认", "完成躯干-底座连接维保。", "base_link"),
    ]),

    # High difficulty (advanced) - 15
    create_sop("sop-hw-h01", "躯干电机更换全流程", "torso", "advanced", 45, build_h24_torso("motor")),
    create_sop("sop-hw-h02", "躯干主控板更换全流程", "torso", "advanced", 45, build_h24_torso("pcb")),
    create_sop("sop-hw-h03", "左踝总成大修", "left_leg", "advanced", 42,
        build_h22_ankle("left_ankle_roll_link", "left_ankle_pitch_link", "left_knee_link", "left_thigh_pitch_link", LEFT_FOOT_M4_SET, LEFT_ANKLE_M4_SET),
    ),
    create_sop("sop-hw-h04", "右踝总成大修", "right_leg", "advanced", 42,
        build_h22_ankle("right_ankle_roll_link", "right_ankle_pitch_link", "right_knee_link", "right_thigh_pitch_link", RIGHT_FOOT_M4_SET, RIGHT_ANKLE_M4_SET),
    ),
    create_sop("sop-hw-h05", "双踝总成同步维保", "base", "advanced", 50,
        build_m20_ankle("left_ankle_roll_link", "left_ankle_pitch_link", "left_knee_link", "left_thigh_pitch_link", LEFT_FOOT_M4_SET, LEFT_ANKLE_M4_SET)[:13] +
        build_m20_ankle("right_ankle_roll_link", "right_ankle_pitch_link", "right_knee_link", "right_thigh_pitch_link", RIGHT_FOOT_M4_SET, RIGHT_ANKLE_M4_SET)[:13],
    ),
    create_sop("sop-hw-h06", "躯干+左踝跨模块维保", "torso", "advanced", 46,
        build_h22_ankle("left_ankle_roll_link", "left_ankle_pitch_link", "left_knee_link", "left_thigh_pitch_link", LEFT_FOOT_M4_SET, LEFT_ANKLE_M4_SET)[:10] +
        build_m16_torso()[:8] + [
            focus_step("跨模块链路复核 1", "复核躯干到左腿链路。", "torso_link"),
            focus_step("跨模块链路复核 2", "复核左踝到膝链路。", "left_knee_link"),
            focus_step("跨模块链路复核 3", "复核底座支撑链路。", "base_link"),
            focus_step("结束确认", "完成躯干+左踝跨模块维保。", "torso_link"),
        ]
    ),
    create_sop("sop-hw-h07", "躯干+右踝跨模块维保", "torso", "advanced", 46,
        build_h22_ankle("right_ankle_roll_link", "right_ankle_pitch_link", "right_knee_link", "right_thigh_pitch_link", RIGHT_FOOT_M4_SET, RIGHT_ANKLE_M4_SET)[:10] +
        build_m16_torso()[:8] + [
            focus_step("跨模块链路复核 1", "复核躯干到右腿链路。", "torso_link"),
            focus_step("跨模块链路复核 2", "复核右踝到膝链路。", "right_knee_link"),
            focus_step("跨模块链路复核 3", "复核底座支撑链路。", "base_link"),
            focus_step("结束确认", "完成躯干+右踝跨模块维保。", "torso_link"),
        ]
    ),
    create_sop("sop-hw-h08", "下肢年度大保养", "base", "advanced", 60, build_h30_annual()),
    create_sop("sop-hw-h09", "左侧链路深度维保", "left_leg", "advanced", 48,
        build_l9("torso_link", ["left_arm_pitch_link", "left_arm_roll_link", "left_arm_yaw_link", "left_elbow_pitch_link", "left_elbow_yaw_link"])[:6] +
        build_m20_ankle("left_ankle_roll_link", "left_ankle_pitch_link", "left_knee_link", "left_thigh_pitch_link", LEFT_FOOT_M4_SET, LEFT_ANKLE_M4_SET)[:10] + [
            focus_step("左侧链路复核 1", "复核左臂链路。", "left_elbow_yaw_link"),
            focus_step("左侧链路复核 2", "复核左腿链路。", "left_knee_link"),
            focus_step("左侧链路复核 3", "复核左踝链路。", "left_ankle_roll_link"),
            focus_step("左侧链路复核 4", "复核左髋链路。", "left_thigh_yaw_link"),
            focus_step("左侧链路复核 5", "复核躯干连接链路。", "torso_link"),
            focus_step("结束确认", "完成左侧链路深度维保。", "torso_link"),
        ]
    ),
    create_sop("sop-hw-h10", "右侧链路深度维保", "right_leg", "advanced", 48, [
        focus_step("安全确认", "确认设备断电并固定。", "torso_link"),
        focus_step("右腿髋定位", "定位右髋关节。", "right_thigh_yaw_link"),
        focus_step("右腿膝定位", "定位右膝关节。", "right_knee_link"),
        focus_step("右踝定位", "定位右踝关节。", "right_ankle_pitch_link"),
        remove_step("移除右脚软胶覆盖件", "拆除右脚底软胶覆盖件。", "right_foot_rubber"),
        tool_step("选择 3mm 工具", "准备拆卸右脚底螺丝。", "hex_3"),
        screw_step("拆卸右脚底 M4×10 螺丝组", "拆卸右脚底螺丝组。", RIGHT_FOOT_M4_SET, "hex_3"),
        detach_step("分离右脚底板", "分离右脚底板。", "right_ankle_roll_link"),
        screw_step("拆卸右踝 M4×8 螺丝组", "拆卸右踝螺丝组。", RIGHT_ANKLE_M4_SET, "hex_3"),
        detach_step("分离右踝俯仰件", "分离右踝俯仰件。", "right_ankle_pitch_link"),
        focus_step("躯干主区定位", "定位躯干主区。", "torso_link"),
        tool_step("切换 2.5mm 工具", "准备拆卸躯干螺丝。", "hex_2.5"),
        screw_step("拆卸躯干 M3×10 螺丝组", "拆卸躯干夹板螺丝。", TORSO_M3_SET, "hex_2.5"),
        remove_step("移除躯干覆盖区", "移除躯干覆盖区。", TORSO_CHEST_COVER),
        focus_step("右侧链路复核 1", "复核右髋链路。", "right_thigh_yaw_link"),
        focus_step("右侧链路复核 2", "复核右膝链路。", "right_knee_link"),
        focus_step("右侧链路复核 3", "复核右踝链路。", "right_ankle_roll_link"),
        focus_step("右侧链路复核 4", "复核躯干链路。", "torso_link"),
        focus_step("右侧链路复核 5", "复核底座链路。", "base_link"),
        focus_step("结构终检", "终检右侧链路结构稳定性。", "torso_link"),
        focus_step("结束确认", "完成右侧链路深度维保。", "torso_link"),
        focus_step("复核补充 1", "补充复核右腿踝区。", "right_ankle_pitch_link"),
        focus_step("复核补充 2", "补充复核躯干区。", "torso_link"),
        focus_step("最终确认", "完成最终确认。", "base_link"),
    ]),
    create_sop("sop-hw-h11", "结构预紧力重检", "base", "advanced", 44, build_h21_structural()),
    create_sop("sop-hw-h12", "胸腔夹板反复拆装审计", "torso", "advanced", 44, build_h22_chest_audit()),
    create_sop("sop-hw-h13", "双脚底板反复拆装审计", "base", "advanced", 44,
        build_h22_foot_audit("left_ankle_roll_link", "left_ankle_pitch_link", "left_knee_link", LEFT_FOOT_M4_SET)[:11] +
        build_h22_foot_audit("right_ankle_roll_link", "right_ankle_pitch_link", "right_knee_link", RIGHT_FOOT_M4_SET)[:11],
    ),
    create_sop("sop-hw-h14", "全身关键点基线复核", "base", "advanced", 46, build_h24_baseline()),
    create_sop("sop-hw-h15", "主维保流程（综合版）", "base", "advanced", 55, build_h28_master_flow()),
]

# All 31 SOPs
ALL_SOPS = [SOP_KNEE_BEARING] + HARDWARE_SOP_SCRIPTS


# ---------------------------------------------------------------------------
# Seed function
# ---------------------------------------------------------------------------

async def seed():
    async with AsyncSessionLocal() as db:
        seeded = 0
        skipped = 0
        for sop_data in ALL_SOPS:
            steps_data = sop_data.pop("steps")
            existing = await db.execute(select(SOP).where(SOP.name == sop_data["name"]))
            if existing.scalar_one_or_none():
                print(f"  Skip (exists): {sop_data['name']}")
                skipped += 1
                sop_data["steps"] = steps_data  # restore for re-runs
                continue

            sop = SOP(**sop_data)
            db.add(sop)
            await db.flush()

            for step_data in steps_data:
                step = SOPStep(sop_id=sop.id, **step_data)
                db.add(step)

            sop_data["steps"] = steps_data  # restore for re-runs
            seeded += 1
            print(f"  Seeded: {sop_data['name']} ({len(steps_data)} steps)")

        await db.commit()
        print(f"Done: {seeded} SOPs seeded, {skipped} skipped.")


if __name__ == "__main__":
    asyncio.run(seed())
