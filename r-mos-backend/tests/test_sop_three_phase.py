"""SOP 三段式字段的模型与映射测试。"""
import json
from pathlib import Path

from app.models.sop import SOP, SOPStep
from app.services.sop_service import SOPService


def _make_step(**overrides):
    defaults = dict(
        id=1,
        sop_id=1,
        step_index=1,
        title="齐套确认",
        description="确认工具与备件齐套",
        expected_action="confirm_kit",
        is_critical=False,
    )
    defaults.update(overrides)
    return SOPStep(**defaults)


def test_sop_step_phase_defaults_to_execute():
    """老数据不带 phase 时必须落在 execute 段，保证 30 个存量 SOP 不受影响。"""
    step = _make_step()
    assert step.phase is None or step.phase == "execute"


def test_sop_step_accepts_three_phase_columns():
    step = _make_step(
        phase="prep",
        group_path="knee/sub_a",
        step_view={
            "camera": {
                "position": [1.0, 0.5, 1.2],
                "target": [0, 0.4, 0],
                "fov": 45,
            },
            "highlight": ["left_knee_link"],
            "explode": 0.4,
        },
        required_parts=[
            {
                "bom_code": "6205-2RS",
                "name": "深沟球轴承",
                "qty": 1,
                "note": "更换件",
            }
        ],
    )
    assert step.phase == "prep"
    assert step.group_path == "knee/sub_a"
    assert step.step_view["explode"] == 0.4
    assert step.required_parts[0]["bom_code"] == "6205-2RS"


def test_adjudication_mapper_emits_three_phase_fields():
    """映射器必须把 4 个新字段透传到裁决格式，缺省时给安全默认值。"""
    sop = SOP(
        id=7,
        name="测试 SOP",
        applicable_model="ATOM-01",
        version="1.0",
        target_module="knee",
        difficulty_level="medium",
        estimated_time=600,
    )
    sop.steps = [
        _make_step(
            id=11,
            phase="prep",
            group_path="knee/sub_a",
            step_view={"explode": 0.4},
            required_parts=[{"bom_code": "6205-2RS", "name": "轴承", "qty": 1}],
        ),
        _make_step(id=12, step_index=2, title="老步骤", phase=None),
    ]
    result = SOPService.__new__(SOPService)._sop_to_adjudication(sop)
    assert result.steps[0].phase == "prep"
    assert result.steps[0].groupPath == "knee/sub_a"
    assert result.steps[0].stepView == {"explode": 0.4}
    assert result.steps[0].requiredParts[0]["bom_code"] == "6205-2RS"
    # 存量步骤：phase 缺省回落 execute，其余为空
    assert result.steps[1].phase == "execute"
    assert result.steps[1].groupPath is None
    assert result.steps[1].stepView is None
    assert result.steps[1].requiredParts == []


def test_knee_bearing_sop_is_three_phase_22_steps():
    """膝关节标杆 SOP 必须严格匹配计划规定的 22 步结构。"""
    from scripts.seed_adjudication_sops import SOP_KNEE_BEARING

    steps = SOP_KNEE_BEARING["steps"]
    assert len(steps) == 22
    assert [step["phase"] for step in steps] == (
        ["prep"] * 4 + ["execute"] * 14 + ["verify"] * 4
    )
    assert [step["title"] for step in steps] == [
        "故障确认",
        "断电隔离确认",
        "工具齐套",
        "备件齐套",
        "定位膝关节作业区",
        "选择 3mm 内六角",
        "拆膝部覆盖件螺丝组（4 颗 M4×8）",
        "移除膝部覆盖件",
        "选择拔取器",
        "拆轴承座固定螺丝（4 颗 M4×8）",
        "分离轴承座",
        "拔取旧轴承",
        "清洁轴座配合面",
        "新轴承涂抹润滑脂",
        "压入新轴承 6205-2RS",
        "装回轴承座",
        "对角拧紧轴承座 4 颗螺丝",
        "装回膝部覆盖件",
        "外观间隙复核",
        "紧固扭矩复核",
        "通电",
        "±90° 全行程活动度测试",
    ]
    assert [step["expected_action"] for step in steps] == [
        "focus_camera",
        "verify_check",
        "confirm_kit",
        "confirm_kit",
        "focus_camera",
        "select_tool",
        "verify_check",
        "focus_camera",
        "select_tool",
        "verify_check",
        "focus_camera",
        "focus_camera",
        "focus_camera",
        "focus_camera",
        "focus_camera",
        "focus_camera",
        "verify_check",
        "focus_camera",
        "verify_check",
        "verify_check",
        "verify_check",
        "verify_check",
    ]


def test_knee_bearing_sop_part_and_screw_ids_exist_in_assembly_manifest():
    """标杆 SOP 引用的零件和螺丝必须能被真实装配清单解析。"""
    from scripts.seed_adjudication_sops import SOP_KNEE_BEARING

    manifest_path = (
        Path(__file__).parents[1]
        / "data/robot-assets/1/manifests/assembly_manifest.json"
    )
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    resolvable_ids = {
        item["id"]
        for registry_name in ("parts_registry", "screw_instances")
        for item in manifest[registry_name]
    }

    referenced_ids = set()
    for step in SOP_KNEE_BEARING["steps"]:
        referenced_ids.update(step["action_params"]["target_parts"])
        view = step["step_view"]
        for field in ("visibleLinks", "highlight", "screwFocus"):
            referenced_ids.update(view.get(field, []))
        for validation in step["validation_rules"]["validations"]:
            params = validation["params"]
            referenced_ids.update(params.get("screwIds", []))
            referenced_ids.update(params.get("expectedOrder", []))

    missing_ids = sorted(referenced_ids - resolvable_ids)
    assert missing_ids == [], f"SOP 引用了装配清单中不存在的 ID：{missing_ids}"


def test_knee_bearing_sop_has_required_validations_and_content():
    from scripts.seed_adjudication_sops import SOP_KNEE_BEARING

    steps = SOP_KNEE_BEARING["steps"]
    validation_types = [
        [item["type"] for item in step["validation_rules"]["validations"]]
        for step in steps
    ]
    assert validation_types == [
        [],
        ["checklist_confirmed"],
        ["kit_confirmed"],
        ["kit_confirmed"],
        [],
        [],
        ["checklist_confirmed"],
        [],
        [],
        ["checklist_confirmed"],
        [],
        [],
        [],
        [],
        [],
        [],
        ["checklist_confirmed"],
        [],
        ["checklist_confirmed"],
        ["checklist_confirmed"],
        ["checklist_confirmed"],
        ["checklist_confirmed"],
    ]

    assert [step["group_path"] for step in steps[:4]] == ["knee/prep"] * 4
    assert steps[2]["validation_rules"]["validations"][0]["params"]["requiredItems"] == [
        "hex_2.5", "hex_3", "bearing_puller", "torque_wrench",
    ]
    assert steps[3]["required_parts"] == [
        {"bom_code": "6205-2RS", "name": "轴承", "qty": 1},
        {"bom_code": "grease", "name": "润滑脂", "qty": 1},
        {"bom_code": "threadlocker", "name": "螺纹胶", "qty": 1},
    ]
    assert steps[11]["is_critical"] is True

    screw_order_check = steps[16]["validation_rules"]["validations"][0]["params"]
    assert screw_order_check["requiredItems"] == ["diagonal_order_confirmed"]
    assert screw_order_check["items"] == [{
        "key": "diagonal_order_confirmed",
        "label": "已按 1→3→2→4 对角顺序紧固",
    }]

    verify_expectations = [
        step["validation_rules"]["validations"][0]["params"]["items"][0]["expected"]
        for step in steps[18:21]
    ]
    assert verify_expectations == [
        "间隙 ≤ 0.5mm",
        "2.5 N·m",
        "低速空载 5 分钟无异响",
    ]


def test_other_30_sop_step_counts_are_unchanged():
    """膝关节编排不能改变另外 30 个 SOP 的步骤数。"""
    from scripts.seed_adjudication_sops import HARDWARE_SOP_SCRIPTS

    expected_counts = [
        8, 9, 10, 10, 8, 16, 18, 16, 15, 18,
        18, 20, 20, 19, 15, 24, 24, 23, 23, 26,
        22, 22, 32, 22, 24, 23, 21, 22, 25, 30,
    ]
    assert len(HARDWARE_SOP_SCRIPTS) == 30
    assert [len(sop["steps"]) for sop in HARDWARE_SOP_SCRIPTS] == expected_counts


def test_make_knee_step_defaults_preserve_old_behavior():
    """新增参数必须有默认值，旧调用仍生成原有 focus_camera 步骤。"""
    from scripts.seed_adjudication_sops import _make_knee_step

    step = _make_knee_step("legacy", 1, "旧步骤", "旧描述", ["left_knee_link"], "COMPLETE")
    assert step["expected_action"] == "focus_camera"
    assert step["action_params"]["action"] == "focus_camera"
    assert step["validation_rules"]["validations"] == []
    assert step["is_critical"] is False


def test_knee_bearing_steps_have_step_view():
    """22 步必须全部带 step_view，否则 3D 展示会退回启发式猜测。"""
    from scripts.seed_adjudication_sops import SOP_KNEE_BEARING

    steps = SOP_KNEE_BEARING["steps"]
    missing = [step["title"] for step in steps if not step.get("step_view")]
    assert missing == [], f"以下步骤缺 step_view：{missing}"


def test_knee_bearing_step_view_shape_is_valid():
    from scripts.seed_adjudication_sops import SOP_KNEE_BEARING

    for step in SOP_KNEE_BEARING["steps"]:
        view = step["step_view"]
        camera = view["camera"]
        assert len(camera["position"]) == 3
        assert len(camera["target"]) == 3
        assert 20 <= camera["fov"] <= 90
        if "explode" in view:
            assert 0 <= view["explode"] <= 1


def test_knee_bearing_required_parts_only_mark_material_steps():
    from scripts.seed_adjudication_sops import SOP_KNEE_BEARING

    steps = SOP_KNEE_BEARING["steps"]
    populated = {
        step["step_index"]: step["required_parts"]
        for step in steps
        if step["required_parts"]
    }
    assert populated == {
        4: [
            {"bom_code": "6205-2RS", "name": "轴承", "qty": 1},
            {"bom_code": "grease", "name": "润滑脂", "qty": 1},
            {"bom_code": "threadlocker", "name": "螺纹胶", "qty": 1},
        ],
        14: [{"bom_code": "grease", "name": "润滑脂", "qty": 1}],
        15: [{"bom_code": "6205-2RS", "name": "轴承", "qty": 1}],
        17: [{"bom_code": "threadlocker", "name": "螺纹胶", "qty": 1}],
    }


def test_other_30_sops_keep_step_view_and_required_parts_empty():
    """存量 SOP 必须继续依赖 T3.4 回落逻辑，不得被标杆内容污染。"""
    from scripts.seed_adjudication_sops import HARDWARE_SOP_SCRIPTS

    steps = [step for sop in HARDWARE_SOP_SCRIPTS for step in sop["steps"]]
    assert all(step.get("step_view") is None for step in steps)
    assert all(step.get("required_parts") is None for step in steps)
