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


def test_list_tasks_endpoint_enforces_actor_scoping():
    """学生只能看自己的任务报告，不能越权看到他人记录。

    回归用例：列表接口若不带 actor 依赖、仅靠前端传 user_id 过滤，
    任何登录用户都能拉到全部任务（实测学生端看到了 22 条，含其他学生的记录）。
    """
    import inspect

    from app.api.v1.endpoints import tasks

    source = inspect.getsource(tasks.list_tasks)
    assert "ActorContext" in source, "列表接口必须解析调用者身份"
    assert "get_current_actor" in source, "列表接口必须要求认证"
    # 必须按角色收敛可见范围，而不是直接采信入参 user_id
    assert "roles" in source, "必须按角色决定可见范围"


@pytest.mark.asyncio
async def test_list_tasks_scopes_students_to_their_own_tasks(test_db):
    """service 层按 user_id 过滤的能力是权限收敛的基础。"""
    from app.services.task_service import TaskService

    test_db.add(Task(title="学生A的任务", user_id=19, status=TaskStatus.COMPLETED))
    test_db.add(Task(title="学生B的任务", user_id=20, status=TaskStatus.COMPLETED))
    test_db.add(Task(title="无主任务", user_id=None, status=TaskStatus.PENDING))
    await test_db.commit()

    service = TaskService(test_db)
    items, total = await service.list_tasks(user_id=19)

    assert total == 1
    assert items[0].title == "学生A的任务"
