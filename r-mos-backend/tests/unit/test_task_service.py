"""
TaskService单元测试
"""
import pytest
from app.services.task_service import TaskService
from app.schemas.task import TaskCreate, StepExecutionRequest


@pytest.mark.asyncio
async def test_create_task(db_session, sample_sop):
    """测试创建Task"""
    service = TaskService(db_session)
    
    request = TaskCreate(
        title="测试任务",
        sop_id=sample_sop.id,
        user_id=1,
        pass_score=70
    )
    
    task = await service.create_task(request)
    await db_session.commit()
    
    assert task.id is not None
    assert task.title == "测试任务"
    assert task.status == "pending"


@pytest.mark.asyncio
async def test_execute_step_success(db_session, sample_task):
    """测试执行步骤成功"""
    service = TaskService(db_session)
    
    # 先开始Task
    await service.start_task(sample_task.id)
    
    # 执行第1步
    request = StepExecutionRequest(
        step_index=1,
        action="execute",
        parameters={"target": "knee_right"}
    )
    
    response = await service.execute_step(sample_task.id, request)
    
    assert response.task_id == sample_task.id
    assert response.step_index == 1
    assert response.status == "success"
    assert response.snapshot_id is not None


@pytest.mark.asyncio
async def test_execute_step_skip(db_session, sample_task_with_skippable_step):
    """测试跳过步骤"""
    service = TaskService(db_session)
    
    await service.start_task(sample_task_with_skippable_step.id)
    
    # 直接执行第2步（跳过第1步）
    request = StepExecutionRequest(
        step_index=2,
        action="execute",
        parameters={}
    )
    
    response = await service.execute_step(sample_task_with_skippable_step.id, request)
    
    assert response.status == "success"
    assert "已跳过" in response.message
