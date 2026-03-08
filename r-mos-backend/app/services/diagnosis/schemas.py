"""
Diagnosis Service Schemas - P1-2
故障诊断相关的数据结构定义
"""
from dataclasses import dataclass, field
from typing import Optional, Any
from enum import Enum


class FaultCode(str, Enum):
    """故障代码枚举"""
    E001_OVERHEAT = "E001_OVERHEAT"
    E002_STALL = "E002_STALL"
    E003_VOLTAGE_DROP = "E003_VOLTAGE_DROP"
    E004_SENSOR_FAILURE = "E004_SENSOR_FAILURE"
    E005_JOINT_LOOSE = "E005_JOINT_LOOSE"
    UNKNOWN = "UNKNOWN"


class Severity(str, Enum):
    """严重程度枚举"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class FaultHypothesis:
    """故障假设"""
    fault_code: str
    fault_name: str
    confidence: float  # 0.0 - 1.0
    affected_parts: list[str]
    possible_causes: list[str]
    evidence: dict[str, Any] = field(default_factory=dict)


@dataclass
class DiagnosisResult:
    """诊断结果"""
    success: bool
    primary_hypothesis: Optional[FaultHypothesis] = None
    alternative_hypotheses: list[FaultHypothesis] = field(default_factory=list)
    requires_supervisor: bool = False
    reasoning: str = ""
    recommended_actions: list[str] = field(default_factory=list)
    error_message: Optional[str] = None

    def to_dict(self) -> dict:
        """转换为字典格式"""
        return {
            "success": self.success,
            "primary_hypothesis": {
                "fault_code": self.primary_hypothesis.fault_code,
                "fault_name": self.primary_hypothesis.fault_name,
                "confidence": self.primary_hypothesis.confidence,
                "affected_parts": self.primary_hypothesis.affected_parts,
                "possible_causes": self.primary_hypothesis.possible_causes,
                "evidence": self.primary_hypothesis.evidence,
            } if self.primary_hypothesis else None,
            "alternative_hypotheses": [
                {
                    "fault_code": h.fault_code,
                    "fault_name": h.fault_name,
                    "confidence": h.confidence,
                    "affected_parts": h.affected_parts,
                    "possible_causes": h.possible_causes,
                    "evidence": h.evidence,
                }
                for h in self.alternative_hypotheses
            ],
            "requires_supervisor": self.requires_supervisor,
            "reasoning": self.reasoning,
            "recommended_actions": self.recommended_actions,
            "error_message": self.error_message,
        }


@dataclass
class MaintenanceAction:
    """维保动作"""
    action_id: str
    action_type: str  # CHECK, CLEAN, REPLACE, ADJUST, CALIBRATE
    target_part: str
    description: str
    estimated_duration_minutes: int
    required_tools: list[str] = field(default_factory=list)
    safety_warnings: list[str] = field(default_factory=list)


@dataclass
class MaintenancePlan:
    """维保方案"""
    success: bool
    plan_id: str
    fault_code: str
    fault_name: str
    actions: list[MaintenanceAction]
    total_duration_minutes: int
    requires_supervisor: bool
    validation_required: bool
    error_message: Optional[str] = None

    def to_dict(self) -> dict:
        """转换为字典格式"""
        return {
            "success": self.success,
            "plan_id": self.plan_id,
            "fault_code": self.fault_code,
            "fault_name": self.fault_name,
            "actions": [
                {
                    "action_id": a.action_id,
                    "action_type": a.action_type,
                    "target_part": a.target_part,
                    "description": a.description,
                    "estimated_duration_minutes": a.estimated_duration_minutes,
                    "required_tools": a.required_tools,
                    "safety_warnings": a.safety_warnings,
                }
                for a in self.actions
            ],
            "total_duration_minutes": self.total_duration_minutes,
            "requires_supervisor": self.requires_supervisor,
            "validation_required": self.validation_required,
            "error_message": self.error_message,
        }
