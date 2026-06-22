"""
MaintenancePlanGenerator - P1-2
维保方案生成器 - 基于诊断结果生成维保计划
"""
import json
import uuid
import logging
from typing import Optional, Any

from app.services.diagnosis.schemas import (
    DiagnosisResult,
    MaintenancePlan,
    MaintenanceAction,
)
from app.services.diagnosis.fault_diagnosis_engine import FaultDiagnosisEngine
from app.services.llm.prompts import PROMPT_MAINTENANCE_PLAN

logger = logging.getLogger(__name__)


class MaintenancePlanGenerator:
    """
    维保方案生成器

    功能：
    1. 基于诊断结果生成维保方案
    2. 从知识库检索相关 SOP
    3. 生成具体的维保动作
    4. 评估是否需要监督

    维保动作类型：
    - CHECK: 检查
    - CLEAN: 清洁
    - REPLACE: 更换
    - ADJUST: 调整
    - CALIBRATE: 校准
    """

    # 故障代码到维保动作模板的映射
    MAINTENANCE_TEMPLATES = {
        "E001_OVERHEAT": [
            {
                "action_type": "CHECK",
                "description": "检查散热系统是否正常工作",
                "estimated_duration_minutes": 5,
                "required_tools": ["红外测温仪"],
                "safety_warnings": ["小心烫伤"],
            },
            {
                "action_type": "CHECK",
                "description": "检查风扇和散热片是否堵塞",
                "estimated_duration_minutes": 10,
                "required_tools": ["螺丝刀", "吹风机"],
                "safety_warnings": ["断电后操作"],
            },
            {
                "action_type": "CLEAN",
                "description": "清洁散热片和风扇叶片",
                "estimated_duration_minutes": 15,
                "required_tools": ["清洁刷", "酒精"],
                "safety_warnings": ["断电后操作", "避免酒精接触电路"],
            },
            {
                "action_type": "ADJUST",
                "description": "调整散热风扇转速参数",
                "estimated_duration_minutes": 5,
                "required_tools": ["诊断电脑"],
                "safety_warnings": [],
            },
        ],
        "E002_STALL": [
            {
                "action_type": "CHECK",
                "description": "检查关节是否有机械卡滞",
                "estimated_duration_minutes": 10,
                "required_tools": ["手动工具"],
                "safety_warnings": ["确保断电"],
            },
            {
                "action_type": "CHECK",
                "description": "检查电机驱动器状态",
                "estimated_duration_minutes": 5,
                "required_tools": ["诊断电脑"],
                "safety_warnings": [],
            },
            {
                "action_type": "CHECK",
                "description": "检查传动机构是否损坏",
                "estimated_duration_minutes": 15,
                "required_tools": ["扳手", "螺丝刀"],
                "safety_warnings": ["确保断电"],
            },
            {
                "action_type": "CALIBRATE",
                "description": "校准位置传感器",
                "estimated_duration_minutes": 20,
                "required_tools": ["诊断电脑", "校准工具"],
                "safety_warnings": ["按照 SOP 执行"],
            },
        ],
        "E003_VOLTAGE_DROP": [
            {
                "action_type": "CHECK",
                "description": "检查电池电量",
                "estimated_duration_minutes": 2,
                "required_tools": [],
                "safety_warnings": [],
            },
            {
                "action_type": "CHECK",
                "description": "检查电源模块连接",
                "estimated_duration_minutes": 5,
                "required_tools": ["螺丝刀"],
                "safety_warnings": ["断电后操作"],
            },
            {
                "action_type": "CHECK",
                "description": "检查线路接触是否良好",
                "estimated_duration_minutes": 10,
                "required_tools": ["万用表"],
                "safety_warnings": ["断电后操作"],
            },
            {
                "action_type": "REPLACE",
                "description": "更换老化电池（如需要）",
                "estimated_duration_minutes": 30,
                "required_tools": ["螺丝刀", "新电池"],
                "safety_warnings": ["使用原装电池", "注意极性"],
            },
        ],
        "E004_SENSOR_FAILURE": [
            {
                "action_type": "CHECK",
                "description": "检查传感器连接线",
                "estimated_duration_minutes": 5,
                "required_tools": [],
                "safety_warnings": ["断电后操作"],
            },
            {
                "action_type": "CALIBRATE",
                "description": "重新校准传感器",
                "estimated_duration_minutes": 15,
                "required_tools": ["诊断电脑", "校准工具"],
                "safety_warnings": ["按照 SOP 执行"],
            },
            {
                "action_type": "REPLACE",
                "description": "更换故障传感器（如需要）",
                "estimated_duration_minutes": 20,
                "required_tools": ["螺丝刀", "新传感器"],
                "safety_warnings": ["使用原装传感器"],
            },
        ],
        "E005_JOINT_LOOSE": [
            {
                "action_type": "CHECK",
                "description": "检查关节固定螺丝",
                "estimated_duration_minutes": 5,
                "required_tools": ["螺丝刀", "扳手"],
                "safety_warnings": ["确保断电"],
            },
            {
                "action_type": "ADJUST",
                "description": "紧固松动的螺丝",
                "estimated_duration_minutes": 10,
                "required_tools": ["扳手", "螺丝刀"],
                "safety_warnings": ["使用正确扭矩"],
            },
            {
                "action_type": "CHECK",
                "description": "检查关节轴承状态",
                "estimated_duration_minutes": 15,
                "required_tools": ["润滑油", "清洁工具"],
                "safety_warnings": ["使用合适润滑油"],
            },
            {
                "action_type": "CALIBRATE",
                "description": "校准关节位置",
                "estimated_duration_minutes": 20,
                "required_tools": ["诊断电脑", "校准工具"],
                "safety_warnings": ["按照 SOP 执行"],
            },
        ],
    }

    # 需要监督的动作
    SUPERVISOR_REQUIRED_ACTIONS = {"REPLACE", "CALIBRATE"}

    # 需要验证的动作
    VALIDATION_REQUIRED_ACTIONS = {"REPLACE", "CALIBRATE", "ADJUST"}

    def __init__(
        self,
        knowledge_hub: Optional[Any] = None,
        llm_router: Optional[Any] = None,
    ):
        """
        初始化维保方案生成器

        Args:
            knowledge_hub: 知识中枢（用于检索 SOP）
            llm_router: LLM 路由器（用于生成定制化方案）
        """
        self.knowledge_hub = knowledge_hub
        self.llm_router = llm_router

    async def generate(
        self,
        diagnosis_result: DiagnosisResult,
        use_llm: bool = False,
    ) -> MaintenancePlan:
        """
        生成维保方案

        Args:
            diagnosis_result: 诊断结果
            use_llm: 是否使用 LLM 生成定制化方案

        Returns:
            MaintenancePlan: 维保方案
        """
        # 1. 检查诊断是否成功
        if not diagnosis_result.success:
            return MaintenancePlan(
                success=False,
                plan_id=str(uuid.uuid4()),
                fault_code="UNKNOWN",
                fault_name="未知",
                actions=[],
                total_duration_minutes=0,
                requires_supervisor=False,
                validation_required=False,
                error_message=diagnosis_result.error_message or "诊断失败",
            )

        # 2. 获取主假设
        primary = diagnosis_result.primary_hypothesis
        if not primary:
            return MaintenancePlan(
                success=False,
                plan_id=str(uuid.uuid4()),
                fault_code="UNKNOWN",
                fault_name="未知",
                actions=[],
                total_duration_minutes=0,
                requires_supervisor=False,
                validation_required=False,
                error_message="无有效诊断结果",
            )

        fault_code = primary.fault_code
        fault_name = primary.fault_name

        # 3. 获取动作模板
        template = self.MAINTENANCE_TEMPLATES.get(fault_code, [])

        if not template:
            return MaintenancePlan(
                success=False,
                plan_id=str(uuid.uuid4()),
                fault_code=fault_code,
                fault_name=fault_name,
                actions=[],
                total_duration_minutes=0,
                requires_supervisor=False,
                validation_required=False,
                error_message=f"未知故障类型: {fault_code}",
            )

        # 4. 构建维保动作
        actions = []
        for i, action_template in enumerate(template):
            action = MaintenanceAction(
                action_id=f"{fault_code}-A{i+1}",
                action_type=action_template["action_type"],
                target_part=", ".join(primary.affected_parts) if primary.affected_parts else "通用",
                description=action_template["description"],
                estimated_duration_minutes=action_template["estimated_duration_minutes"],
                required_tools=action_template["required_tools"],
                safety_warnings=action_template["safety_warnings"],
            )
            actions.append(action)

        # 5. 计算总时长
        total_duration = sum(a.estimated_duration_minutes for a in actions)

        # 6. 检查是否需要监督
        requires_supervisor = self._check_requires_supervisor(
            diagnosis_result,
            actions,
        )

        # 7. 检查是否需要验证
        validation_required = any(
            a.action_type in self.VALIDATION_REQUIRED_ACTIONS
            for a in actions
        )

        # 8. 如果使用 LLM，尝试优化方案
        if use_llm and self.llm_router and self.knowledge_hub:
            try:
                optimized = await self._optimize_with_llm(
                    diagnosis_result,
                    actions,
                )
                if optimized:
                    return optimized
            except Exception as e:
                logger.warning(f"LLM optimization failed: {e}")

        # 9. 返回方案
        return MaintenancePlan(
            success=True,
            plan_id=str(uuid.uuid4()),
            fault_code=fault_code,
            fault_name=fault_name,
            actions=actions,
            total_duration_minutes=total_duration,
            requires_supervisor=requires_supervisor,
            validation_required=validation_required,
        )

    def _check_requires_supervisor(
        self,
        diagnosis_result: DiagnosisResult,
        actions: list[MaintenanceAction],
    ) -> bool:
        """
        检查是否需要监督

        需要监督的情况：
        1. 诊断置信度低于阈值
        2. 存在高风险动作
        3. 诊断结果明确要求监督
        """
        # 1. 诊断结果要求监督
        if diagnosis_result.requires_supervisor:
            return True

        # 2. 主假设置信度低
        primary = diagnosis_result.primary_hypothesis
        if primary and primary.confidence < 0.7:
            return True

        # 3. 包含高风险动作
        high_risk_actions = {"REPLACE", "CALIBRATE"}
        for action in actions:
            if action.action_type in high_risk_actions:
                # 检查是否有安全警告
                if action.safety_warnings:
                    return True

        return False

    async def _optimize_with_llm(
        self,
        diagnosis_result: DiagnosisResult,
        actions: list[MaintenanceAction],
    ) -> Optional[MaintenancePlan]:
        """
        使用 LLM 优化维保方案

        根据具体情况进行定制化
        """
        from app.services.llm.router import LLMProvider
        from app.core.config import settings

        primary = diagnosis_result.primary_hypothesis

        # 构建提示词
        prompt = f"""你是一个专业的维保方案规划专家。请根据以下诊断结果，优化维保方案。

诊断结果：
- 故障类型: {primary.fault_name}
- 置信度: {primary.confidence}
- 受影响部件: {", ".join(primary.affected_parts)}
- 可能原因: {", ".join(primary.possible_causes[:3])}

当前方案包含 {len(actions)} 个步骤。

请返回优化后的方案，格式如下：
{{
    "optimized": true/false,
    "reason": "优化原因...",
    "modified_actions": [
        {{
            "action_type": "CHECK",
            "description": "优化后的描述",
            "estimated_duration_minutes": 数字,
            "required_tools": ["工具列表"],
            "safety_warnings": ["警告列表"]
        }}
    ]
}}

如果没有更好的优化方案，请返回原始方案。
"""

        try:
            response = await self.llm_router.chat(
                messages=[
                    {"role": "system", "content": PROMPT_MAINTENANCE_PLAN},
                    {"role": "user", "content": prompt}
                ],
                provider=LLMProvider.DEEPSEEK,
                model=settings.LLM_MODEL_ADVANCED,
                temperature=0.3,
                max_tokens=800,
            )

            # 尝试解析响应
            try:
                data = json.loads(response.content)
                if data.get("optimized"):
                    # 应用优化
                    modified = data.get("modified_actions", [])
                    if modified and len(modified) > 0:
                        new_actions = []
                        for i, ma in enumerate(modified):
                            action = MaintenanceAction(
                                action_id=f"{primary.fault_code}-OPT{i+1}",
                                action_type=ma.get("action_type", "CHECK"),
                                target_part=", ".join(primary.affected_parts) if primary.affected_parts else "通用",
                                description=ma.get("description", ""),
                                estimated_duration_minutes=ma.get("estimated_duration_minutes", 10),
                                required_tools=ma.get("required_tools", []),
                                safety_warnings=ma.get("safety_warnings", []),
                            )
                            new_actions.append(action)

                        if new_actions:
                            total_duration = sum(a.estimated_duration_minutes for a in new_actions)
                            requires_supervisor = self._check_requires_supervisor(diagnosis_result, new_actions)
                            validation_required = any(
                                a.action_type in self.VALIDATION_REQUIRED_ACTIONS
                                for a in new_actions
                            )

                            return MaintenancePlan(
                                success=True,
                                plan_id=str(uuid.uuid4()),
                                fault_code=primary.fault_code,
                                fault_name=primary.fault_name,
                                actions=new_actions,
                                total_duration_minutes=total_duration,
                                requires_supervisor=requires_supervisor,
                                validation_required=validation_required,
                            )

            except (json.JSONDecodeError, KeyError):
                logger.warning("Failed to parse LLM optimization response")

        except Exception as e:
            logger.warning(f"LLM optimization error: {e}")

        return None


# 全局实例
maintenance_plan_generator = MaintenancePlanGenerator()
