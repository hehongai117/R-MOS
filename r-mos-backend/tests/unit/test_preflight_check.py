"""
P0-4-4: PreflightCheck 单元测试
测试三个检查器的正常/WARN/BLOCK 场景
"""
from datetime import datetime

import pytest
from app.models.incident import Incident
from app.models.sop import SOP, SOPStep
from app.models.user import User
from app.services.preflight_check import (
    PreflightCheckService,
    QualificationChecker,
    DeviceLockChecker,
    ToolAvailabilityChecker,
    CheckStatus,
    CheckResult,
    PreflightCheckReport,
)


# ============ QualificationChecker 测试 ============

@pytest.mark.asyncio
async def test_qualification_checker_pass():
    """测试资质检查器通过场景"""
    checker = QualificationChecker()
    result = await checker.check(user_id="user-001")

    assert result.status == CheckStatus.PASS
    assert result.checker_name == "qualification"
    assert result.details["certification_valid"] is True


# ============ DeviceLockChecker 测试 ============

@pytest.mark.asyncio
async def test_device_lock_checker_pass():
    """测试设备锁定检查器通过场景"""
    checker = DeviceLockChecker()
    result = await checker.check(user_id="user-001", robot_id="robot-01")

    assert result.status == CheckStatus.PASS
    assert result.checker_name == "device_lock"
    assert result.details["locked"] is False


@pytest.mark.asyncio
async def test_device_lock_checker_no_robot():
    """测试设备锁定检查器 - 未指定机器人"""
    checker = DeviceLockChecker()
    result = await checker.check(user_id="user-001")

    assert result.status == CheckStatus.PASS
    assert "跳过设备检查" in result.message


# ============ ToolAvailabilityChecker 测试 ============

@pytest.mark.asyncio
async def test_tool_availability_checker_pass():
    """测试工具可用性检查器通过场景"""
    checker = ToolAvailabilityChecker()
    result = await checker.check(user_id="user-001", sop_id=1)

    assert result.status == CheckStatus.PASS
    assert result.checker_name == "tool_availability"


# ============ PreflightCheckService 测试 ============

@pytest.mark.asyncio
async def test_preflight_service_all_pass():
    """测试完整检查服务 - 全部通过"""
    service = PreflightCheckService()
    report = await service.run_checks(user_id="user-001", robot_id="robot-01")

    assert report.overall_status == CheckStatus.PASS
    assert len(report.passed_checks) == 3  # 3 个检查器
    assert len(report.warning_checks) == 0
    assert len(report.blocked_checks) == 0


@pytest.mark.asyncio
async def test_preflight_service_can_proceed():
    """测试快速检查方法"""
    service = PreflightCheckService()
    can_proceed, reason = await service.can_proceed(user_id="user-001")

    assert can_proceed is True
    assert reason is None


@pytest.mark.asyncio
async def test_preflight_service_with_sop_id():
    """测试带 SOP ID 的检查"""
    service = PreflightCheckService()
    report = await service.run_checks(
        user_id="user-001",
        sop_id=1,
        robot_id="robot-01"
    )

    assert report.sop_id == 1
    assert report.user_id == "user-001"
    assert report.overall_status in [CheckStatus.PASS, CheckStatus.WARN, CheckStatus.BLOCK]


# ============ CheckStatus 枚举测试 ============

def test_check_status_enum_values():
    """测试 CheckStatus 枚举值"""
    assert CheckStatus.PASS.value == "PASS"
    assert CheckStatus.WARN.value == "WARN"
    assert CheckStatus.BLOCK.value == "BLOCK"


# ============ CheckResult 数据类测试 ============

def test_check_result_creation():
    """测试 CheckResult 创建"""
    result = CheckResult(
        status=CheckStatus.PASS,
        message="测试通过",
        details={"key": "value"},
        checker_name="test_checker"
    )

    assert result.status == CheckStatus.PASS
    assert result.message == "测试通过"
    assert result.details["key"] == "value"
    assert result.checker_name == "test_checker"


# ============ PreflightCheckReport 数据类测试 ============

def test_preflight_check_report_creation():
    """测试 PreflightCheckReport 创建"""
    from datetime import datetime

    result = CheckResult(status=CheckStatus.PASS, message="OK", checker_name="test")
    report = PreflightCheckReport(
        overall_status=CheckStatus.PASS,
        passed_checks=[result],
        warning_checks=[],
        blocked_checks=[],
        timestamp=datetime.utcnow(),
        user_id="user-001",
        sop_id=1
    )

    assert report.overall_status == CheckStatus.PASS
    assert len(report.passed_checks) == 1
    assert report.user_id == "user-001"
    assert report.sop_id == 1


@pytest.mark.asyncio
async def test_preflight_service_three_block_scenarios():
    service = PreflightCheckService()

    class _BlockerOne:
        name = "blocker_one"

        async def check(self, **_kwargs):
            return CheckResult(status=CheckStatus.BLOCK, message="资质不满足", checker_name=self.name)

    class _BlockerTwo:
        name = "blocker_two"

        async def check(self, **_kwargs):
            return CheckResult(status=CheckStatus.BLOCK, message="设备锁定", checker_name=self.name)

    class _BlockerThree:
        name = "blocker_three"

        async def check(self, **_kwargs):
            return CheckResult(status=CheckStatus.BLOCK, message="工具缺失", checker_name=self.name)

    service.checkers = [_BlockerOne(), _BlockerTwo(), _BlockerThree()]
    report = await service.run_checks(user_id="user-001")

    assert report.overall_status == CheckStatus.BLOCK
    assert len(report.blocked_checks) == 3


@pytest.mark.asyncio
async def test_preflight_service_checker_exception_becomes_block():
    service = PreflightCheckService()

    class _ErrorChecker:
        name = "error_checker"

        async def check(self, **_kwargs):
            raise RuntimeError("boom")

    service.checkers = [_ErrorChecker()]
    report = await service.run_checks(user_id="user-001")

    assert report.overall_status == CheckStatus.BLOCK
    assert len(report.blocked_checks) == 1
    assert "执行失败" in report.blocked_checks[0].message


@pytest.mark.asyncio
async def test_preflight_can_proceed_returns_false_on_block():
    service = PreflightCheckService()

    class _AlwaysBlock:
        name = "always_block"

        async def check(self, **_kwargs):
            return CheckResult(status=CheckStatus.BLOCK, message="禁止执行", checker_name=self.name)

    service.checkers = [_AlwaysBlock()]
    can_proceed, reason = await service.can_proceed(user_id="user-001")

    assert can_proceed is False
    assert "禁止执行" in reason


@pytest.mark.asyncio
async def test_qualification_checker_blocks_inactive_user_with_db(test_db):
    checker = QualificationChecker()
    user = User(
        email="inactive_user@example.com",
        password_hash="pbkdf2_sha256$fixture",
        full_name="Inactive User",
        role="student",
        is_active=False,
    )
    test_db.add(user)
    await test_db.commit()
    await test_db.refresh(user)

    result = await checker.check(user_id=str(user.id), db=test_db)

    assert result.status == CheckStatus.BLOCK
    assert "停用" in result.message


@pytest.mark.asyncio
async def test_device_lock_checker_blocks_open_incident_with_db(test_db):
    checker = DeviceLockChecker()
    incident = Incident(
        id="incident-001",
        robot_id="robot-01",
        incident_type="fault",
        incident_level="high",
        status="open",
        event_time_start=datetime.utcnow(),
    )
    test_db.add(incident)
    await test_db.commit()

    result = await checker.check(user_id="1", robot_id="robot-01", db=test_db)

    assert result.status == CheckStatus.BLOCK
    assert result.details["incident_id"] == "incident-001"


@pytest.mark.asyncio
async def test_tool_availability_checker_blocks_when_missing_tools_with_db(test_db):
    checker = ToolAvailabilityChecker()

    sop = SOP(
        name="Tool Check SOP",
        description="SOP for tool checker test",
        applicable_model="ABB-IRB120",
    )
    test_db.add(sop)
    await test_db.flush()

    step = SOPStep(
        sop_id=sop.id,
        step_index=1,
        title="Use tools",
        description="Need two tools",
        expected_action="inspect",
        tools_required=["wrench", "gauge"],
    )
    test_db.add(step)
    await test_db.commit()

    result = await checker.check(
        user_id="1",
        sop_id=sop.id,
        available_tools=["wrench"],
        db=test_db,
    )

    assert result.status == CheckStatus.BLOCK
    assert result.details["shortages"] == ["gauge"]
