"""
Mock Adapter 单元测试
"""
import pytest
from app.adapters.mock import MockRobotAdapter


@pytest.mark.asyncio
async def test_mock_adapter_connect():
    """测试Mock Adapter连接"""
    adapter = MockRobotAdapter()
    result = await adapter.connect()
    assert result is True
    assert await adapter.is_connected() is True


@pytest.mark.asyncio
async def test_mock_adapter_get_joint_states():
    """测试获取关节状态"""
    adapter = MockRobotAdapter(config={"joint_count": 5})
    await adapter.connect()
    
    joint_states = await adapter.get_joint_states()
    assert len(joint_states) == 5
    assert all(state.joint_id for state in joint_states)


@pytest.mark.asyncio
async def test_mock_adapter_inject_fault():
    """测试故障注入"""
    adapter = MockRobotAdapter()
    await adapter.connect()
    
    result = await adapter.inject_fault(
        fault_code="E001_OVERHEAT",
        target_part="knee_right",
        severity="high"
    )
    
    assert result.success is True
    assert result.fault_code == "E001_OVERHEAT"
    
    active_faults = await adapter.get_active_faults()
    assert "E001_OVERHEAT" in active_faults


@pytest.mark.asyncio
async def test_mock_adapter_apply_maintenance_action_clears_faults():
    adapter = MockRobotAdapter()
    await adapter.connect()

    await adapter.inject_fault(
        fault_code="E002_STALL",
        target_part="knee_right",
        severity="high",
    )

    success = await adapter.apply_maintenance_action("clear_fault")

    assert success is True
    assert await adapter.get_active_faults() == []
