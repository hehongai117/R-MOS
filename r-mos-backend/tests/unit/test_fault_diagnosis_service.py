"""Fault diagnosis pipeline service tests."""
from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from app.services.pipeline.fault_diagnosis_service import FaultDiagnosisService


@pytest.mark.asyncio
async def test_diagnose_e001_overheat():
    """Diagnose E001 from telemetry with high temperature."""
    telemetry = {
        "joints": [
            {"joint_id": "waist", "temperature": 78, "velocity": 0.1, "torque": 1.2, "error_code": None},
        ],
        "sensors": {"voltage": {"main": 24}},
    }

    service = FaultDiagnosisService()
    result = await service.diagnose(telemetry)

    assert result["success"] is True
    assert result["fault_type"] == "E001_OVERHEAT"
    assert result["confidence"] >= 0.8
    assert "waist" in result["affected_joints"]
    assert result["recommended_sop"] is not None


@pytest.mark.asyncio
async def test_diagnose_e003_compound():
    """Diagnose E003 compound fault: voltage drop + temperature."""
    telemetry = {
        "joints": [
            {"joint_id": "shoulder", "temperature": 72, "velocity": 0.05, "torque": 2.0, "error_code": None},
            {"joint_id": "elbow", "temperature": 70, "velocity": 0.08, "torque": 1.8, "error_code": None},
        ],
        "sensors": {"voltage": {"main": 19}},
    }

    service = FaultDiagnosisService()
    result = await service.diagnose(telemetry)

    assert result["success"] is True
    assert result["fault_type"] == "E003_VOLTAGE_DROP"
    assert result["is_compound"] is True


@pytest.mark.asyncio
async def test_diagnose_no_fault():
    """Normal telemetry returns no fault."""
    telemetry = {
        "joints": [
            {"joint_id": "waist", "temperature": 42, "velocity": 1.0, "torque": 0.5, "error_code": None},
        ],
        "sensors": {"voltage": {"main": 24}},
    }

    service = FaultDiagnosisService()
    result = await service.diagnose(telemetry)

    assert result["success"] is True
    assert result["fault_type"] is None
