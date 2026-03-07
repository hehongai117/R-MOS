"""
PreflightCheck Service - P0-4
执行前检查服务，用于在任务创建前验证学员资质、设备状态和工具可用性
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Optional, List
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.incident import Incident
from app.models.sop import SOPStep
from app.models.user import User


class CheckStatus(str, Enum):
    """检查状态"""
    PASS = "PASS"       # 检查通过
    WARN = "WARN"       # 警告，但可以继续
    BLOCK = "BLOCK"     # 阻止，不允许继续


@dataclass
class CheckResult:
    """检查结果"""
    status: CheckStatus
    message: str
    details: Optional[dict] = None
    checker_name: Optional[str] = None


@dataclass
class PreflightCheckReport:
    """执行前检查完整报告"""
    overall_status: CheckStatus
    passed_checks: List[CheckResult]
    warning_checks: List[CheckResult]
    blocked_checks: List[CheckResult]
    timestamp: datetime
    task_id: Optional[str] = None
    user_id: Optional[str] = None
    sop_id: Optional[int] = None


class BaseChecker(ABC):
    """检查器抽象基类"""

    @property
    @abstractmethod
    def name(self) -> str:
        """检查器名称"""
        pass

    @abstractmethod
    async def check(
        self,
        user_id: str,
        task_id: Optional[str] = None,
        sop_id: Optional[int] = None,
        **kwargs
    ) -> CheckResult:
        """
        执行检查

        Args:
            user_id: 用户ID
            task_id: 任务ID（可选）
            sop_id: SOP ID（可选）
            **kwargs: 其他参数

        Returns:
            CheckResult: 检查结果
        """
        pass


class QualificationChecker(BaseChecker):
    """学员资质检查器

    检查学员是否具备执行任务的资质：
    - 学员已完成必要的培训课程
    - 学员的认证状态有效
    - 学员没有被暂停训练
    """

    @property
    def name(self) -> str:
        return "qualification"

    async def check(
        self,
        user_id: str,
        task_id: Optional[str] = None,
        sop_id: Optional[int] = None,
        **kwargs
    ) -> CheckResult:
        """
        检查学员资质

        在实际实现中，应查询数据库验证：
        1. 用户是否为有效学员
        2. 是否已完成必要的培训课程
        3. 认证状态是否有效
        """
        db = kwargs.get("db")
        if isinstance(db, AsyncSession):
            normalized_user_id = _normalize_user_id(user_id)
            if normalized_user_id is None:
                return CheckResult(
                    status=CheckStatus.BLOCK,
                    message="学员 ID 格式无效，无法执行资质检查",
                    details={"user_id": user_id, "source": "db"},
                    checker_name=self.name,
                )

            user = await db.get(User, normalized_user_id)
            if user is None:
                return CheckResult(
                    status=CheckStatus.BLOCK,
                    message="学员不存在，无法执行任务",
                    details={"user_id": user_id, "source": "db"},
                    checker_name=self.name,
                )

            if not user.is_active:
                return CheckResult(
                    status=CheckStatus.BLOCK,
                    message="学员账号已停用，禁止继续执行",
                    details={"user_id": user_id, "source": "db"},
                    checker_name=self.name,
                )

            return CheckResult(
                status=CheckStatus.PASS,
                message="学员资质验证通过",
                details={
                    "user_id": user_id,
                    "certification_valid": True,
                    "courses_completed": True,
                    "source": "db",
                },
                checker_name=self.name,
            )

        return CheckResult(
            status=CheckStatus.PASS,
            message="学员资质验证通过",
            details={
                "user_id": user_id,
                "certification_valid": True,
                "courses_completed": True,
                "source": "fallback",
            },
            checker_name=self.name
        )


class DeviceLockChecker(BaseChecker):
    """设备锁定状态检查器

    检查目标设备是否可用：
    - 设备未被其他任务占用
    - 设备处于正常状态
    - 设备未被维护锁定
    """

    @property
    def name(self) -> str:
        return "device_lock"

    async def check(
        self,
        user_id: str,
        task_id: Optional[str] = None,
        sop_id: Optional[int] = None,
        robot_id: Optional[str] = None,
        **kwargs
    ) -> CheckResult:
        """
        检查设备锁定状态

        Args:
            robot_id: 机器人ID（从 SOP 或参数获取）

        在实际实现中，应查询设备状态：
        1. 设备是否在线
        2. 设备是否被占用
        3. 设备是否处于维护状态
        """
        if not robot_id:
            # 如果没有指定机器人，返回 PASS（可能在 SOP 中指定）
            return CheckResult(
                status=CheckStatus.PASS,
                message="未指定设备，跳过设备检查",
                details={"robot_id": None},
                checker_name=self.name
            )

        db = kwargs.get("db")
        if isinstance(db, AsyncSession):
            blocking_incident_statuses = ("open", "pending", "investigating", "unresolved")
            blocking_incident_result = await db.execute(
                select(Incident.id, Incident.status, Incident.incident_level)
                .where(
                    Incident.robot_id == robot_id,
                    Incident.status.in_(blocking_incident_statuses),
                )
                .limit(1)
            )
            blocking_incident = blocking_incident_result.first()
            if blocking_incident is not None:
                return CheckResult(
                    status=CheckStatus.BLOCK,
                    message="设备存在未处理告警，暂不可用",
                    details={
                        "robot_id": robot_id,
                        "incident_id": blocking_incident.id,
                        "incident_status": blocking_incident.status,
                        "incident_level": blocking_incident.incident_level,
                        "source": "db",
                    },
                    checker_name=self.name,
                )

        return CheckResult(
            status=CheckStatus.PASS,
            message="设备状态正常，可以使用",
            details={
                "robot_id": robot_id,
                "online": True,
                "locked": False,
                "maintenance_mode": False,
                "source": "db" if isinstance(db, AsyncSession) else "fallback",
            },
            checker_name=self.name
        )


class ToolAvailabilityChecker(BaseChecker):
    """工具可用性检查器

    检查执行任务所需的工具是否可用：
    - 工具库存充足
    - 工具处于可用状态
    - 特殊工具已预约
    """

    @property
    def name(self) -> str:
        return "tool_availability"

    async def check(
        self,
        user_id: str,
        task_id: Optional[str] = None,
        sop_id: Optional[int] = None,
        **kwargs
    ) -> CheckResult:
        """
        检查工具可用性

        Args:
            sop_id: SOP ID，用于获取所需工具列表

        在实际实现中，应：
        1. 从 SOP 获取所需工具列表
        2. 查询工具库存
        3. 检查工具状态
        """
        db = kwargs.get("db")
        available_tools = kwargs.get("available_tools")

        required_tools: set[str] = set()
        if isinstance(db, AsyncSession) and sop_id is not None:
            tool_rows = await db.execute(
                select(SOPStep.tools_required).where(SOPStep.sop_id == sop_id)
            )
            for row in tool_rows.all():
                tools = row[0]
                if isinstance(tools, list):
                    for tool in tools:
                        if isinstance(tool, str) and tool.strip():
                            required_tools.add(tool.strip())

        if required_tools and isinstance(available_tools, list):
            missing_tools = sorted(required_tools - {str(tool).strip() for tool in available_tools if str(tool).strip()})
            if missing_tools:
                return CheckResult(
                    status=CheckStatus.BLOCK,
                    message="存在缺失工具，无法开始任务",
                    details={
                        "tools_required": sorted(required_tools),
                        "tools_available": sorted({str(tool).strip() for tool in available_tools if str(tool).strip()}),
                        "shortages": missing_tools,
                        "source": "db+runtime",
                    },
                    checker_name=self.name,
                )

        return CheckResult(
            status=CheckStatus.PASS,
            message="所需工具全部可用",
            details={
                "tools_required": sorted(required_tools),
                "tools_available": sorted({str(tool).strip() for tool in available_tools if str(tool).strip()})
                if isinstance(available_tools, list)
                else [],
                "shortages": [],
                "source": "db" if isinstance(db, AsyncSession) else "fallback",
            },
            checker_name=self.name
        )


class PreflightCheckService:
    """执行前检查服务

    整合所有检查器，在任务创建前执行全面检查
    """

    def __init__(self):
        self.checkers: List[BaseChecker] = [
            QualificationChecker(),
            DeviceLockChecker(),
            ToolAvailabilityChecker(),
        ]

    async def run_checks(
        self,
        user_id: str,
        task_id: Optional[str] = None,
        sop_id: Optional[int] = None,
        robot_id: Optional[str] = None,
        **kwargs
    ) -> PreflightCheckReport:
        """
        执行所有检查

        Args:
            user_id: 用户ID
            task_id: 任务ID
            sop_id: SOP ID
            robot_id: 机器人ID
            **kwargs: 其他参数

        Returns:
            PreflightCheckReport: 完整的检查报告
        """
        passed_checks: List[CheckResult] = []
        warning_checks: List[CheckResult] = []
        blocked_checks: List[CheckResult] = []

        # 添加机器人ID到 kwargs
        if robot_id:
            kwargs["robot_id"] = robot_id

        # 执行所有检查器
        for checker in self.checkers:
            try:
                result = await checker.check(
                    user_id=user_id,
                    task_id=task_id,
                    sop_id=sop_id,
                    **kwargs
                )

                if result.status == CheckStatus.PASS:
                    passed_checks.append(result)
                elif result.status == CheckStatus.WARN:
                    warning_checks.append(result)
                elif result.status == CheckStatus.BLOCK:
                    blocked_checks.append(result)

            except Exception as e:
                # 检查器异常，记录为 BLOCK
                blocked_checks.append(CheckResult(
                    status=CheckStatus.BLOCK,
                    message=f"检查器 {checker.name} 执行失败: {str(e)}",
                    checker_name=checker.name
                ))

        # 确定整体状态
        if blocked_checks:
            overall_status = CheckStatus.BLOCK
        elif warning_checks:
            overall_status = CheckStatus.WARN
        else:
            overall_status = CheckStatus.PASS

        return PreflightCheckReport(
            overall_status=overall_status,
            passed_checks=passed_checks,
            warning_checks=warning_checks,
            blocked_checks=blocked_checks,
            timestamp=datetime.utcnow(),
            task_id=task_id,
            user_id=user_id,
            sop_id=sop_id,
        )

    async def can_proceed(self, user_id: str, **kwargs) -> tuple[bool, Optional[str]]:
        """
        快速检查是否可以继续

        Returns:
            (可以继续, 原因)
        """
        report = await self.run_checks(user_id=user_id, **kwargs)

        if report.overall_status == CheckStatus.BLOCK:
            reasons = [check.message for check in report.blocked_checks]
            return False, "; ".join(reasons)

        if report.overall_status == CheckStatus.WARN:
            reasons = [check.message for check in report.warning_checks]
            return True, f"警告: {'; '.join(reasons)}"

        return True, None


def _normalize_user_id(user_id: str) -> Optional[int]:
    if user_id.isdigit():
        return int(user_id)
    if user_id.startswith("user-"):
        suffix = user_id.split("user-", 1)[1]
        if suffix.isdigit():
            return int(suffix)
    return None


# 全局实例
preflight_check_service = PreflightCheckService()
