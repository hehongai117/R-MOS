# Phase 4: 学生前端（机器人选择 + 上下文切换）实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 学生登录后看到教师名下已发布的机器人列表，选择后全局上下文切换——SOP、故障场景、AI 助手均按当前机器人过滤。

**Architecture:** 后端新增学生机器人列表 API（通过 User.teacher_id → TeacherRobotBinding → RobotModel 查询）；前端新建 robotContextStore（Zustand + localStorage 持久化）驱动全局上下文；SOP 和场景 API 追加 robot_model_id 过滤参数。

**Tech Stack:** FastAPI, SQLAlchemy AsyncSession, React 18, Zustand, TypeScript, Tailwind CSS, shadcn/ui, lucide-react

---

## 文件结构总览

| 操作 | 文件路径 | 职责 |
|------|---------|------|
| 新建 | `r-mos-backend/tests/test_api_student_robots.py` | 学生机器人列表 API 测试 |
| 修改 | `r-mos-backend/app/api/v1/endpoints/robots.py` | 新增 `GET /students/{student_id}/robots` |
| 修改 | `r-mos-backend/app/api/v1/endpoints/sops.py` | 追加 `robot_model_id` 过滤参数 |
| 修改 | `r-mos-backend/app/services/sop_service.py` | `list_sops` 支持 robot_model_id 过滤 |
| 修改 | `r-mos-backend/app/api/v1/endpoints/scenarios.py` | 追加 `robot_model_id` 过滤参数 |
| 新建 | `r-mos-frontend/src/store/robotContextStore.ts` | 学生全局机器人上下文 Store |
| 新建 | `r-mos-frontend/src/components/RobotCards.tsx` | 机器人选择卡片组件 |
| 修改 | `r-mos-frontend/src/api/robots.ts` | 新增 `listStudentRobots` 函数 |
| 修改 | `r-mos-frontend/src/api/sop.ts` | `listSOPs` 增加 `robot_model_id` 参数 |
| 修改 | `r-mos-frontend/src/api/scenarios.ts` | `fetchScenarios` 增加 `robot_model_id` 参数 |
| 修改 | `r-mos-frontend/src/pages/DashboardPage.tsx` | 集成机器人选择卡片 |
| 修改 | `r-mos-frontend/src/pages/SOPListPage.tsx` | 按当前机器人过滤 SOP |
| 修改 | `r-mos-frontend/src/pages/ScenarioPickerPage.tsx` | 按当前机器人过滤场景 |
| 修改 | `r-mos-frontend/src/components/Layout/AppLayout.tsx` | 顶部导航显示当前机器人+切换 |

---

### Task 4.1: 学生机器人列表 API

**Files:**
- Create: `r-mos-backend/tests/test_api_student_robots.py`
- Modify: `r-mos-backend/app/api/v1/endpoints/robots.py`

**查询逻辑:** Student (user.teacher_id) → TeacherRobotBinding (teacher_id) → RobotModel (status=READY)

- [ ] **Step 1: 编写测试文件**

```python
# r-mos-backend/tests/test_api_student_robots.py
"""学生机器人列表 API 测试"""
import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.models.robot_model import RobotModel, RobotStatus, RobotVisibility, TeacherRobotBinding


@pytest.fixture
async def teacher_with_robots(db_session: AsyncSession):
    """创建教师 + 2 个 READY 机器人 + 1 个 DRAFT 机器人"""
    teacher = User(
        email="teacher_robot@test.com",
        password_hash="hashed",
        role="teacher",
        full_name="Robot Teacher",
    )
    db_session.add(teacher)
    await db_session.flush()

    robot_ready_1 = RobotModel(
        brand="FANUC", model_name="M-20iA", version="1.0",
        owner_teacher_id=teacher.id, status=RobotStatus.READY,
        visibility=RobotVisibility.PRIVATE,
    )
    robot_ready_2 = RobotModel(
        brand="ABB", model_name="IRB 1200", version="2.0",
        owner_teacher_id=teacher.id, status=RobotStatus.READY,
        visibility=RobotVisibility.SHARED,
    )
    robot_draft = RobotModel(
        brand="KUKA", model_name="KR 10", version="1.0",
        owner_teacher_id=teacher.id, status=RobotStatus.DRAFT,
        visibility=RobotVisibility.PRIVATE,
    )
    db_session.add_all([robot_ready_1, robot_ready_2, robot_draft])
    await db_session.flush()

    for robot in [robot_ready_1, robot_ready_2, robot_draft]:
        db_session.add(TeacherRobotBinding(
            teacher_id=teacher.id, robot_model_id=robot.id, binding_type="owner",
        ))
    await db_session.commit()
    await db_session.refresh(teacher)
    return teacher, [robot_ready_1, robot_ready_2], robot_draft


@pytest.fixture
async def student_of_teacher(db_session: AsyncSession, teacher_with_robots):
    """创建绑定到上述教师的学生"""
    teacher, _, _ = teacher_with_robots
    student = User(
        email="student_robot@test.com",
        password_hash="hashed",
        role="student",
        full_name="Robot Student",
        teacher_id=teacher.id,
    )
    db_session.add(student)
    await db_session.commit()
    await db_session.refresh(student)
    return student


@pytest.mark.asyncio
async def test_student_robots_returns_only_ready(
    async_client: AsyncClient,
    student_of_teacher,
    teacher_with_robots,
):
    """学生只能看到绑定教师名下 status=READY 的机器人"""
    student = student_of_teacher
    _, ready_robots, _ = teacher_with_robots

    response = await async_client.get(
        f"/api/v1/students/{student.id}/robots",
        headers={"X-User-Id": str(student.id), "X-User-Role": "student"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 2
    ids = {item["id"] for item in data["items"]}
    assert ids == {r.id for r in ready_robots}


@pytest.mark.asyncio
async def test_student_robots_no_teacher_returns_empty(
    async_client: AsyncClient,
    db_session: AsyncSession,
):
    """没有绑定教师的学生返回空列表"""
    orphan = User(
        email="orphan_student@test.com",
        password_hash="hashed",
        role="student",
        full_name="Orphan",
        teacher_id=None,
    )
    db_session.add(orphan)
    await db_session.commit()
    await db_session.refresh(orphan)

    response = await async_client.get(
        f"/api/v1/students/{orphan.id}/robots",
        headers={"X-User-Id": str(orphan.id), "X-User-Role": "student"},
    )
    assert response.status_code == 200
    assert response.json()["total"] == 0


@pytest.mark.asyncio
async def test_student_robots_forbidden_for_other_student(
    async_client: AsyncClient,
    student_of_teacher,
    db_session: AsyncSession,
):
    """学生不能查看其他学生的机器人列表"""
    other = User(
        email="other_student@test.com",
        password_hash="hashed",
        role="student",
        full_name="Other",
        teacher_id=None,
    )
    db_session.add(other)
    await db_session.commit()
    await db_session.refresh(other)

    response = await async_client.get(
        f"/api/v1/students/{student_of_teacher.id}/robots",
        headers={"X-User-Id": str(other.id), "X-User-Role": "student"},
    )
    assert response.status_code == 403
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd r-mos-backend && python -m pytest tests/test_api_student_robots.py -v`
Expected: FAIL — endpoint 404 (路由不存在)

- [ ] **Step 3: 实现学生机器人列表端点**

在 `r-mos-backend/app/api/v1/endpoints/robots.py` 文件末尾追加：

```python
@router.get("/students/{student_id}/robots", response_model=RobotModelListResponse)
async def list_student_robots(
    student_id: int,
    db: AsyncSession = Depends(get_db),
    actor: ActorContext = Depends(get_current_actor),
):
    """学生查看绑定教师名下已发布(READY)的机器人列表。"""
    # 权限检查：只能查自己的，或者教师/管理员可查任意学生
    if "admin" not in actor.roles and "teacher" not in actor.roles:
        if actor.user_id != student_id:
            raise HTTPException(status_code=403, detail="只能查看自己的机器人列表")

    # 查询学生的 teacher_id
    from app.models.user import User
    student_result = await db.execute(select(User).where(User.id == student_id))
    student = student_result.scalar_one_or_none()
    if not student:
        raise HTTPException(status_code=404, detail="学生不存在")
    if not student.teacher_id:
        return RobotModelListResponse(items=[], total=0)

    # 查询教师名下 READY 的机器人
    stmt = (
        select(RobotModel)
        .join(TeacherRobotBinding, TeacherRobotBinding.robot_model_id == RobotModel.id)
        .where(
            TeacherRobotBinding.teacher_id == student.teacher_id,
            RobotModel.status == RobotStatus.READY,
        )
    )
    result = await db.execute(stmt)
    items = list(result.scalars().all())
    return RobotModelListResponse(items=items, total=len(items))
```

注意：由于 router 前缀是 `/robots`，实际注册路径是 `/robots/students/{student_id}/robots`，不符合 RESTful 设计。需要将此端点注册到独立路由或调整路径。

**更好的方案：** 将 prefix 改为在 main router 上直接注册 `/students/{id}/robots`。但为最小化变动，在 `robots.py` 中不使用 router prefix，而是直接在 API v1 路由注册处新增一个独立 router。

实际实现：在 `robots.py` 中新增一个 `students_router`：

```python
# 在文件顶部 router 定义之后新增
students_router = APIRouter(prefix="/students", tags=["students"])
```

然后端点改为：

```python
@students_router.get("/{student_id}/robots", response_model=RobotModelListResponse)
async def list_student_robots(
    student_id: int,
    db: AsyncSession = Depends(get_db),
    actor: ActorContext = Depends(get_current_actor),
):
    """学生查看绑定教师名下已发布(READY)的机器人列表。"""
    if "admin" not in actor.roles and "teacher" not in actor.roles:
        if actor.user_id != student_id:
            raise HTTPException(status_code=403, detail="只能查看自己的机器人列表")

    from app.models.user import User
    student_result = await db.execute(select(User).where(User.id == student_id))
    student = student_result.scalar_one_or_none()
    if not student:
        raise HTTPException(status_code=404, detail="学生不存在")
    if not student.teacher_id:
        return RobotModelListResponse(items=[], total=0)

    stmt = (
        select(RobotModel)
        .join(TeacherRobotBinding, TeacherRobotBinding.robot_model_id == RobotModel.id)
        .where(
            TeacherRobotBinding.teacher_id == student.teacher_id,
            RobotModel.status == RobotStatus.READY,
        )
    )
    result = await db.execute(stmt)
    items = list(result.scalars().all())
    return RobotModelListResponse(items=items, total=len(items))
```

然后在 API router 注册文件中引入 `students_router`。

- [ ] **Step 4: 注册 students_router 到 API v1**

修改 `r-mos-backend/app/api/v1/__init__.py`，在 import 区域的 `robots` 后确认可导入 `students_router`：

```python
from app.api.v1.endpoints.robots import students_router
```

在 `api_router.include_router(robots.router, tags=["robots"])` 之后追加：

```python
api_router.include_router(students_router, tags=["students"])
```

- [ ] **Step 5: 运行测试确认通过**

Run: `cd r-mos-backend && python -m pytest tests/test_api_student_robots.py -v`
Expected: 3 passed

- [ ] **Step 6: Commit**

```bash
git add r-mos-backend/tests/test_api_student_robots.py r-mos-backend/app/api/v1/endpoints/robots.py r-mos-backend/app/api/v1/router.py
git commit -m "feat(api): add student robot list endpoint (Phase 4, Task 4.1)"
```

---

### Task 4.2: 机器人上下文 Store

**Files:**
- Create: `r-mos-frontend/src/store/robotContextStore.ts`
- Modify: `r-mos-frontend/src/api/robots.ts`

- [ ] **Step 1: 在 API 客户端中新增 `listStudentRobots` 函数**

在 `r-mos-frontend/src/api/robots.ts` 文件末尾追加：

```typescript
/** 学生查看可用机器人列表 */
export async function listStudentRobots(studentId: number): Promise<RobotModelListResponse> {
  const response = await apiClient.get<RobotModelListResponse>(`/students/${studentId}/robots`)
  return response.data
}
```

- [ ] **Step 2: 创建 robotContextStore**

```typescript
// r-mos-frontend/src/store/robotContextStore.ts
import { create } from 'zustand'

import { listStudentRobots } from '@/api/robots'
import type { RobotModel } from '@/types/robotModel'

const STORAGE_KEY = 'rmos_current_robot_id'

interface RobotContextState {
  currentRobotId: number | null
  currentRobot: RobotModel | null
  availableRobots: RobotModel[]
  isLoading: boolean

  /** 加载学生可用机器人列表 */
  fetchAvailableRobots: (studentId: number) => Promise<void>
  /** 设置当前机器人 */
  setCurrentRobot: (robot: RobotModel) => void
  /** 清除上下文（登出时） */
  clearContext: () => void
}

function getStoredRobotId(): number | null {
  const stored = localStorage.getItem(STORAGE_KEY)
  if (!stored) return null
  const parsed = parseInt(stored, 10)
  return isNaN(parsed) ? null : parsed
}

export const useRobotContextStore = create<RobotContextState>((set, get) => ({
  currentRobotId: getStoredRobotId(),
  currentRobot: null,
  availableRobots: [],
  isLoading: false,

  async fetchAvailableRobots(studentId: number) {
    set({ isLoading: true })
    try {
      const res = await listStudentRobots(studentId)
      const robots = res.items

      // 恢复之前选中的机器人，或自动选中唯一一台
      const storedId = getStoredRobotId()
      let current: RobotModel | null = null
      if (storedId) {
        current = robots.find((r) => r.id === storedId) ?? null
      }
      if (!current && robots.length === 1) {
        current = robots[0]
      }

      set({
        availableRobots: robots,
        currentRobot: current,
        currentRobotId: current?.id ?? null,
      })

      if (current) {
        localStorage.setItem(STORAGE_KEY, String(current.id))
      }
    } catch {
      set({ availableRobots: [] })
    } finally {
      set({ isLoading: false })
    }
  },

  setCurrentRobot(robot: RobotModel) {
    localStorage.setItem(STORAGE_KEY, String(robot.id))
    set({ currentRobotId: robot.id, currentRobot: robot })
  },

  clearContext() {
    localStorage.removeItem(STORAGE_KEY)
    set({ currentRobotId: null, currentRobot: null, availableRobots: [] })
  },
}))

/** Hook: 获取当前选中的机器人 ID（便于组件消费） */
export function useCurrentRobotId(): number | null {
  return useRobotContextStore((s) => s.currentRobotId)
}
```

- [ ] **Step 3: 确认编译通过**

Run: `cd r-mos-frontend && npx tsc --noEmit`
Expected: 无错误

- [ ] **Step 4: Commit**

```bash
git add r-mos-frontend/src/store/robotContextStore.ts r-mos-frontend/src/api/robots.ts
git commit -m "feat(frontend): add robot context store with localStorage persistence (Phase 4, Task 4.2)"
```

---

### Task 4.3: 机器人选择卡片组件

**Files:**
- Create: `r-mos-frontend/src/components/RobotCards.tsx`

- [ ] **Step 1: 创建 RobotCards 组件**

```tsx
// r-mos-frontend/src/components/RobotCards.tsx
import { Card, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Bot, CheckCircle2 } from 'lucide-react'
import { cn } from '@/lib/utils'
import type { RobotModel } from '@/types/robotModel'

interface RobotCardsProps {
  robots: RobotModel[]
  selectedId: number | null
  onSelect: (robot: RobotModel) => void
  loading?: boolean
}

export default function RobotCards({ robots, selectedId, onSelect, loading }: RobotCardsProps) {
  if (loading) {
    return (
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {[1, 2, 3].map((i) => (
          <Card key={i} className="animate-pulse">
            <CardContent className="py-6">
              <div className="h-5 w-32 rounded bg-bg-elevated" />
              <div className="mt-3 h-4 w-24 rounded bg-bg-elevated" />
            </CardContent>
          </Card>
        ))}
      </div>
    )
  }

  if (robots.length === 0) {
    return (
      <Card>
        <CardContent className="py-8 text-center">
          <Bot className="mx-auto h-10 w-10 text-text-muted" />
          <p className="mt-3 text-sm text-text-muted">
            暂无可用机器人。请联系教师配置并发布机器人。
          </p>
        </CardContent>
      </Card>
    )
  }

  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
      {robots.map((robot) => {
        const isSelected = robot.id === selectedId
        return (
          <Card
            key={robot.id}
            className={cn(
              'cursor-pointer transition-all hover:shadow-sm',
              isSelected
                ? 'border-primary bg-primary-muted/30 shadow-sm'
                : 'hover:border-primary/30',
            )}
            onClick={() => onSelect(robot)}
          >
            <CardContent className="flex items-start gap-3 py-5">
              <div className={cn(
                'flex h-10 w-10 shrink-0 items-center justify-center rounded-lg',
                isSelected ? 'bg-primary text-white' : 'bg-bg-elevated text-text-muted',
              )}>
                <Bot className="h-5 w-5" />
              </div>
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-2">
                  <span className="truncate font-medium text-text-primary">
                    {robot.model_name}
                  </span>
                  {isSelected && (
                    <CheckCircle2 className="h-4 w-4 shrink-0 text-primary" />
                  )}
                </div>
                <p className="mt-1 text-xs text-text-secondary">{robot.brand}</p>
                {robot.description && (
                  <p className="mt-1 line-clamp-2 text-xs text-text-muted">{robot.description}</p>
                )}
              </div>
              <Badge variant="default" className="shrink-0 text-[10px]">
                v{robot.version}
              </Badge>
            </CardContent>
          </Card>
        )
      })}
    </div>
  )
}
```

- [ ] **Step 2: 确认编译通过**

Run: `cd r-mos-frontend && npx tsc --noEmit`
Expected: 无错误

- [ ] **Step 3: Commit**

```bash
git add r-mos-frontend/src/components/RobotCards.tsx
git commit -m "feat(frontend): add RobotCards selection component (Phase 4, Task 4.3)"
```

---

### Task 4.4: Dashboard 页面改造

**Files:**
- Modify: `r-mos-frontend/src/pages/DashboardPage.tsx`

- [ ] **Step 1: 改造 DashboardPage 集成机器人选择**

将 `DashboardPage.tsx` 完整重写为：

```tsx
// r-mos-frontend/src/pages/DashboardPage.tsx
import { useEffect, useState } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Progress } from '@/components/ui/progress'
import { BarChart3, Bot, CheckCircle, Clock, Target } from 'lucide-react'
import { useAuthStore } from '@/store/authStore'
import { useRobotContextStore } from '@/store/robotContextStore'
import RobotCards from '@/components/RobotCards'
import { apiClient } from '@/api/client'

interface TaskStats {
  total: number
  pending_count: number
  in_progress_count: number
  completed_count: number
}

export default function DashboardPage() {
  const user = useAuthStore((s) => s.user)
  const {
    availableRobots,
    currentRobotId,
    currentRobot,
    isLoading: robotsLoading,
    fetchAvailableRobots,
    setCurrentRobot,
  } = useRobotContextStore()

  const [stats, setStats] = useState<TaskStats | null>(null)
  const [statsLoading, setStatsLoading] = useState(true)

  // 加载可用机器人列表
  useEffect(() => {
    if (user?.user_id) {
      fetchAvailableRobots(user.user_id)
    }
  }, [user?.user_id, fetchAvailableRobots])

  // 加载任务统计
  useEffect(() => {
    if (!user?.user_id) return
    apiClient
      .get('/student/tasks', { params: { student_id: user.user_id, limit: 1 } })
      .then((res) => setStats(res.data))
      .catch(() => setStats(null))
      .finally(() => setStatsLoading(false))
  }, [user?.user_id])

  const completionRate = stats && stats.total > 0
    ? Math.round((stats.completed_count / stats.total) * 100)
    : 0

  // 如果有多台机器人且未选中，优先显示机器人选择界面
  const showRobotPicker = availableRobots.length > 1 && !currentRobot

  return (
    <div className="space-y-6">
      {/* 机器人选择区域（多机器人时始终显示） */}
      {availableRobots.length > 1 && (
        <section className="space-y-3">
          <div className="flex items-center gap-3">
            <Bot className="h-6 w-6 text-primary" />
            <h1 className="text-2xl font-semibold text-text-primary">选择机器人</h1>
          </div>
          <RobotCards
            robots={availableRobots}
            selectedId={currentRobotId}
            onSelect={setCurrentRobot}
            loading={robotsLoading}
          />
        </section>
      )}

      {/* 单台机器人或已选中时显示学习进度 */}
      {!showRobotPicker && (
        <>
          <div className="flex items-center gap-3">
            <BarChart3 className="h-6 w-6 text-primary" />
            <h1 className="text-2xl font-semibold text-text-primary">学习进度</h1>
            {currentRobot && (
              <span className="text-sm text-text-secondary">
                — {currentRobot.brand} {currentRobot.model_name}
              </span>
            )}
          </div>

          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <Card>
              <CardHeader className="flex flex-row items-center justify-between pb-2">
                <CardTitle className="text-sm font-medium text-text-secondary">总任务数</CardTitle>
                <Target className="h-4 w-4 text-text-muted" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{statsLoading ? '—' : stats?.total ?? 0}</div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="flex flex-row items-center justify-between pb-2">
                <CardTitle className="text-sm font-medium text-text-secondary">进行中</CardTitle>
                <Clock className="h-4 w-4 text-yellow-500" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold text-yellow-600">
                  {statsLoading ? '—' : stats?.in_progress_count ?? 0}
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="flex flex-row items-center justify-between pb-2">
                <CardTitle className="text-sm font-medium text-text-secondary">已完成</CardTitle>
                <CheckCircle className="h-4 w-4 text-green-500" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold text-green-600">
                  {statsLoading ? '—' : stats?.completed_count ?? 0}
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="flex flex-row items-center justify-between pb-2">
                <CardTitle className="text-sm font-medium text-text-secondary">完成率</CardTitle>
                <BarChart3 className="h-4 w-4 text-primary" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold text-primary">{statsLoading ? '—' : `${completionRate}%`}</div>
                <Progress value={completionRate} className="mt-2" />
              </CardContent>
            </Card>
          </div>

          <Card>
            <CardHeader>
              <CardTitle className="text-base">技能雷达</CardTitle>
            </CardHeader>
            <CardContent className="flex items-center justify-center py-8">
              <p className="text-sm text-text-muted">
                完成更多练习任务后，技能雷达图将在此显示你的五维能力分布。
              </p>
            </CardContent>
          </Card>
        </>
      )}
    </div>
  )
}
```

- [ ] **Step 2: 确认编译通过**

Run: `cd r-mos-frontend && npx tsc --noEmit`
Expected: 无错误

- [ ] **Step 3: Commit**

```bash
git add r-mos-frontend/src/pages/DashboardPage.tsx
git commit -m "feat(frontend): integrate robot selection into DashboardPage (Phase 4, Task 4.4)"
```

---

### Task 4.5: SOP/故障场景按 robot_model_id 过滤

**Files:**
- Modify: `r-mos-backend/app/api/v1/endpoints/sops.py`
- Modify: `r-mos-backend/app/services/sop_service.py`
- Modify: `r-mos-backend/app/api/v1/endpoints/scenarios.py`
- Modify: `r-mos-frontend/src/api/sop.ts`
- Modify: `r-mos-frontend/src/api/scenarios.ts`
- Modify: `r-mos-frontend/src/pages/SOPListPage.tsx`
- Modify: `r-mos-frontend/src/pages/ScenarioPickerPage.tsx`

- [ ] **Step 1: 后端 — SOP list_sops 增加 robot_model_id 过滤**

在 `r-mos-backend/app/services/sop_service.py` 的 `list_sops` 方法中增加参数：

```python
async def list_sops(
    self,
    applicable_model: Optional[str] = None,
    category: Optional[str] = None,
    robot_model_id: Optional[int] = None,
    skip: int = 0,
    limit: int = 100
) -> List[SOP]:
    """查询SOP列表"""
    query = select(SOP)

    if applicable_model:
        query = query.where(SOP.applicable_model == applicable_model)

    if category:
        query = query.where(SOP.category == category)

    if robot_model_id is not None:
        query = query.where(SOP.robot_model_id == robot_model_id)

    query = query.offset(skip).limit(limit)
    result = await self.db.execute(query)
    return list(result.scalars().all())
```

- [ ] **Step 2: 后端 — sops.py 端点增加 robot_model_id 查询参数**

在 `r-mos-backend/app/api/v1/endpoints/sops.py` 的 `list_sops` 端点增加参数：

```python
@router.get("/sops", response_model=List[SOPResponse], tags=["SOPs"])
async def list_sops(
    applicable_model: Optional[str] = Query(None, description="过滤：机器人型号"),
    category: Optional[str] = Query(None, description="过滤：分类"),
    robot_model_id: Optional[int] = Query(None, description="过滤：机器人型号ID"),
    skip: int = Query(0, ge=0, description="跳过数量"),
    limit: int = Query(100, ge=1, le=500, description="返回数量"),
    db: AsyncSession = Depends(get_db)
):
    """查询SOP列表"""
    try:
        service = SOPService(db)
        sops = await service.list_sops(
            applicable_model=applicable_model,
            category=category,
            robot_model_id=robot_model_id,
            skip=skip,
            limit=limit
        )
        return sops
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

- [ ] **Step 3: 后端 — scenarios.py 增加 robot_model_id 过滤**

在 `r-mos-backend/app/api/v1/endpoints/scenarios.py` 的 `list_scenarios` 端点中增加：

```python
@router.get("/scenarios", response_model=ScenarioListResponse, tags=["scenarios"])
async def list_scenarios(
    difficulty: Optional[str] = Query(None, description="难度筛选: beginner/intermediate/advanced"),
    fault_type: Optional[str] = Query(None, description="故障类型筛选"),
    robot_model_id: Optional[int] = Query(None, description="机器人型号ID筛选"),
    db: AsyncSession = Depends(get_db),
):
    """获取可用练习场景列表"""
    query = (
        select(FaultSOPMapping, SOP.name.label("sop_title"))
        .join(SOP, FaultSOPMapping.sop_id == SOP.id, isouter=True)
        .order_by(FaultSOPMapping.priority.desc(), FaultSOPMapping.difficulty)
    )

    if difficulty:
        query = query.where(FaultSOPMapping.difficulty == difficulty)
    if fault_type:
        query = query.where(FaultSOPMapping.fault_type == fault_type)
    if robot_model_id is not None:
        query = query.where(FaultSOPMapping.robot_model_id == robot_model_id)

    result = await db.execute(query)
    rows = result.all()

    items = [
        ScenarioItem(
            id=row.FaultSOPMapping.id,
            fault_type=row.FaultSOPMapping.fault_type,
            sop_id=row.FaultSOPMapping.sop_id,
            sop_title=row.sop_title,
            difficulty=row.FaultSOPMapping.difficulty,
            priority=row.FaultSOPMapping.priority,
        )
        for row in rows
    ]

    return ScenarioListResponse(items=items, total=len(items))
```

- [ ] **Step 4: 前端 — sop.ts 增加 robot_model_id 参数**

修改 `r-mos-frontend/src/api/sop.ts`：

```typescript
export interface ListSOPsParams {
    skip?: number
    limit?: number
    category?: string
    applicable_model?: string
    robot_model_id?: number
}

export async function listSOPs(params: ListSOPsParams = {}): Promise<SOPListResponse> {
    const { skip = 0, limit = 20, category, applicable_model, robot_model_id } = params
    const response = await apiClient.get<SOP[]>('/sops', {
        params: { skip, limit, category, applicable_model, robot_model_id },
    })
    const items = response.data
    return {
        items: items.map(sop => ({
            id: sop.id,
            name: sop.name,
            category: sop.category,
            difficulty_level: sop.difficulty_level,
            step_count: sop.steps?.length ?? 0,
            estimated_time: sop.estimated_time,
            created_at: sop.created_at,
        })),
        total: items.length,
    }
}
```

- [ ] **Step 5: 前端 — scenarios.ts 增加 robot_model_id 参数**

修改 `r-mos-frontend/src/api/scenarios.ts`：

```typescript
export async function fetchScenarios(
  difficulty?: string,
  robotModelId?: number,
): Promise<ScenarioListResponse> {
  const params: Record<string, string | number> = {}
  if (difficulty && difficulty !== 'all') params.difficulty = difficulty
  if (robotModelId) params.robot_model_id = robotModelId
  const res = await apiClient.get<ScenarioListResponse>('/scenarios', { params })
  return res.data
}
```

- [ ] **Step 6: 前端 — SOPListPage 使用当前机器人过滤**

修改 `r-mos-frontend/src/pages/SOPListPage.tsx`，在 import 区域新增：

```typescript
import { useRobotContextStore } from '@/store/robotContextStore'
```

在组件内部获取当前机器人 ID：

```typescript
const currentRobotId = useRobotContextStore((s) => s.currentRobotId)
```

修改 `fetchSOPs` 中的 API 调用：

```typescript
const response = await listSOPs({
    skip: (page - 1) * pageSize,
    limit: pageSize,
    robot_model_id: currentRobotId ?? undefined,
});
```

将 `currentRobotId` 加入 `useEffect` 的依赖数组：

```typescript
useEffect(() => {
    fetchSOPs();
}, [page, pageSize, currentRobotId]);
```

- [ ] **Step 7: 前端 — ScenarioPickerPage 使用当前机器人过滤**

修改 `r-mos-frontend/src/pages/ScenarioPickerPage.tsx`，在 import 区域新增：

```typescript
import { useRobotContextStore } from '@/store/robotContextStore'
```

在组件内部获取当前机器人 ID：

```typescript
const currentRobotId = useRobotContextStore((s) => s.currentRobotId)
```

修改 `useEffect` 中的 API 调用：

```typescript
useEffect(() => {
    setLoading(true)
    fetchScenarios(difficulty, currentRobotId ?? undefined)
      .then((res) => setScenarios(res.items))
      .catch(() => setScenarios([]))
      .finally(() => setLoading(false))
}, [difficulty, currentRobotId])
```

- [ ] **Step 8: 确认前后端编译通过**

Run: `cd r-mos-backend && python -c "from app.api.v1.endpoints.sops import list_sops; print('OK')"`
Run: `cd r-mos-frontend && npx tsc --noEmit`
Expected: 均无错误

- [ ] **Step 9: Commit**

```bash
git add r-mos-backend/app/api/v1/endpoints/sops.py r-mos-backend/app/services/sop_service.py r-mos-backend/app/api/v1/endpoints/scenarios.py r-mos-frontend/src/api/sop.ts r-mos-frontend/src/api/scenarios.ts r-mos-frontend/src/pages/SOPListPage.tsx r-mos-frontend/src/pages/ScenarioPickerPage.tsx
git commit -m "feat: add robot_model_id filtering to SOP and scenario APIs (Phase 4, Task 4.5)"
```

---

### Task 4.6: 上下文切换导航

**Files:**
- Modify: `r-mos-frontend/src/components/Layout/AppLayout.tsx`

- [ ] **Step 1: 在 AppLayout 顶部 Header 区域添加当前机器人显示 + 切换**

在 `AppLayout.tsx` 中增加机器人上下文切换功能。修改 `RoleLayoutShell` 组件的 `<main>` 区域，在内容顶部加一个 topbar。

在文件顶部增加 import：

```typescript
import { useRobotContextStore } from '@/store/robotContextStore'
```

注意：`Bot` 已在 lucide-react import 列表中。

在 `RoleLayoutShell` 内部（`return` 之前）增加对 store 的访问：

```typescript
const { currentRobot, availableRobots, setCurrentRobot } = useRobotContextStore()
```

将 `<main>` 区域改为（使用已有的 DropdownMenu 组件替代不存在的 Select）：

```tsx
<main className="ml-[220px] flex-1 overflow-auto">
  {/* 学生角色且有多台机器人时显示顶部机器人切换栏 */}
  {role === 'student' && availableRobots.length > 1 && (
    <div className="sticky top-0 z-10 flex items-center gap-3 border-b border-border-subtle bg-bg-surface/95 px-6 py-2 backdrop-blur">
      <Bot className="h-4 w-4 text-text-muted" />
      <span className="text-xs text-text-secondary">当前机器人:</span>
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <button className="flex items-center gap-2 rounded-md border border-border-subtle px-3 py-1 text-xs transition-colors hover:bg-bg-elevated">
            <span>{currentRobot ? `${currentRobot.brand} ${currentRobot.model_name}` : '请选择机器人'}</span>
          </button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="start">
          {availableRobots.map((r) => (
            <DropdownMenuItem
              key={r.id}
              onClick={() => setCurrentRobot(r)}
              className={cn(r.id === currentRobot?.id && 'bg-primary-muted text-primary')}
            >
              {r.brand} {r.model_name}
            </DropdownMenuItem>
          ))}
        </DropdownMenuContent>
      </DropdownMenu>
    </div>
  )}
  <div className="mx-auto min-h-[calc(100vh-3rem)] max-w-[1600px] p-6">
    <Outlet />
  </div>
</main>
```

注：`DropdownMenu`、`DropdownMenuContent`、`DropdownMenuItem`、`DropdownMenuTrigger` 以及 `cn` 已在文件中导入。

- [ ] **Step 2: 确认编译通过**

Run: `cd r-mos-frontend && npx tsc --noEmit`
Expected: 无错误

- [ ] **Step 3: Commit**

```bash
git add r-mos-frontend/src/components/Layout/AppLayout.tsx
git commit -m "feat(frontend): add robot context switcher in top navigation (Phase 4, Task 4.6)"
```

---

## 验收检查清单

完成全部 Task 后，执行以下验收：

1. **后端测试:** `cd r-mos-backend && python -m pytest tests/test_api_student_robots.py -v` — 3 passed
2. **前端编译:** `cd r-mos-frontend && npx tsc --noEmit` — 无错误
3. **功能验证:**
   - 学生登录 → Dashboard 显示可用机器人卡片
   - 选择机器人后 → SOP 列表按 robot_model_id 过滤
   - 切换机器人 → 故障场景列表更新
   - 刷新页面 → localStorage 恢复之前选中的机器人
   - 顶部导航 → 显示当前机器人名称并可切换
4. **更新文档:** 完成后更新 CLAUDE.md Phase 4 状态 + 总控计划 + 记忆文件
