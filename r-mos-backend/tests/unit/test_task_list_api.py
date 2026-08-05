"""任务列表接口测试。

维保报告菜单指向 /reports，但前端只有详情页（依赖 taskId），
没有列表页可用 —— 根因之一是后端缺少任务列表接口。
"""
import pytest

from app.models.task import Task, TaskStatus


def test_tasks_module_exposes_list_endpoint():
    from app.api.v1.endpoints import tasks

    assert hasattr(tasks, "list_tasks"), "应提供任务列表接口 list_tasks"


@pytest.mark.asyncio
async def test_list_tasks_returns_items_and_total(test_db):
    from app.services.task_service import TaskService

    for i in range(3):
        test_db.add(
            Task(
                title=f"维保任务 {i}",
                user_id=101,
                status=TaskStatus.COMPLETED,
                final_score=80 + i,
                is_passed=True,
            )
        )
    test_db.add(
        Task(title="他人的任务", user_id=999, status=TaskStatus.PENDING)
    )
    await test_db.commit()

    service = TaskService(test_db)
    items, total = await service.list_tasks(user_id=101)

    assert total == 3
    assert len(items) == 3
    assert all(t.user_id == 101 for t in items)


@pytest.mark.asyncio
async def test_list_tasks_filters_by_status_and_paginates(test_db):
    from app.services.task_service import TaskService

    for i in range(5):
        test_db.add(
            Task(
                title=f"已完成 {i}",
                user_id=202,
                status=TaskStatus.COMPLETED,
                final_score=70,
            )
        )
    test_db.add(Task(title="进行中", user_id=202, status=TaskStatus.IN_PROGRESS))
    await test_db.commit()

    service = TaskService(test_db)

    completed, total = await service.list_tasks(
        user_id=202, status=TaskStatus.COMPLETED
    )
    assert total == 5
    assert all(t.status == TaskStatus.COMPLETED for t in completed)

    page, total_again = await service.list_tasks(
        user_id=202, status=TaskStatus.COMPLETED, limit=2, offset=0
    )
    assert total_again == 5
    assert len(page) == 2


@pytest.mark.asyncio
async def test_list_tasks_orders_newest_first(test_db):
    from app.services.task_service import TaskService

    for i in range(3):
        test_db.add(Task(title=f"任务 {i}", user_id=303, status=TaskStatus.PENDING))
    await test_db.commit()

    service = TaskService(test_db)
    items, _ = await service.list_tasks(user_id=303)

    ids = [t.id for t in items]
    assert ids == sorted(ids, reverse=True), "列表应按最新在前排序"
