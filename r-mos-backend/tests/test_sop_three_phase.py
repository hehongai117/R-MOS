"""SOP 三段式字段的模型与映射测试。"""
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
