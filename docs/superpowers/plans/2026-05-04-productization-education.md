# R-MOS 院校教培产品化实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 R-MOS 从技术 Demo 转为可交付院校教培产品（P0 阶段）

**Architecture:** 渐进式精简 — 不做大重构，通过配置治理、导航调整、补全关键页面、新增嵌入式 AI 助手达到可交付状态。前端按角色分层导航（基础练习/进阶工具），后端增加 AI 助手聊天端点和学生任务列表端点。

**Tech Stack:** FastAPI + SQLAlchemy 2.0 async, React 18 + TypeScript + Zustand + TailwindCSS, Docker Compose, PostgreSQL

---

## File Structure

### New Files
```
r-mos-backend/
├── app/api/v1/endpoints/ai_assistant.py    # AI 助手聊天端点
├── app/api/v1/endpoints/student_tasks.py   # 学生任务列表端点
├── app/api/v1/endpoints/scenarios.py       # 场景列表端点
├── app/services/ai_assistant_service.py    # AI 助手业务逻辑
├── .env.example                            # 环境变量模板
├── .env.production                         # 生产配置模板
├── Dockerfile                              # Backend Docker
r-mos-frontend/
├── src/components/AIAssistant/AIAssistantPanel.tsx  # AI 助手浮窗
├── src/components/AIAssistant/ChatMessage.tsx       # 聊天消息组件
├── src/api/aiAssistant.ts                           # AI 助手 API 客户端
├── src/api/studentTasks.ts                          # 学生任务 API
├── src/api/scenarios.ts                             # 场景 API
├── src/pages/DashboardPage.tsx                      # 学习进度仪表盘
├── src/store/aiAssistantStore.ts                    # AI 助手状态
├── Dockerfile                                       # Frontend Docker
docker-compose.yml                                   # 根目录部署编排
.env.example                                         # 根目录环境变量模板
```

### Modified Files
```
r-mos-backend/app/core/config.py                    # 生产配置增强
r-mos-backend/app/api/v1/__init__.py                # 注册新路由
r-mos-frontend/src/components/Layout/AppLayout.tsx  # 导航分层
r-mos-frontend/src/pages/MyTasksPage.tsx            # 补全实现
r-mos-frontend/src/pages/ScenarioPickerPage.tsx     # 补全实现
r-mos-frontend/src/App.tsx                          # 新路由 + 默认首页
```

---

### Task 1: 生产配置治理

**Files:**
- Modify: `r-mos-backend/app/core/config.py`
- Create: `r-mos-backend/.env.example`
- Create: `.env.example` (project root)

- [ ] **Step 1: 修改 config.py 增加生产安全校验**

```python
"""
配置管理 — 产品化版本
"""
from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    """应用配置"""
    # 数据库配置
    DATABASE_URL: str = "sqlite+aiosqlite:///./rmos_dev.db"

    # 服务器配置
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    DEBUG: bool = False

    # 安全配置
    SECRET_KEY: str = "dev-only-change-me"

    # CORS配置
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
    ]

    # Adapter配置
    ROBOT_MODE: str = "simulation"  # simulation / physical
    MOCK_JOINT_COUNT: int = 10
    MOCK_SIMULATION_SPEED: float = 1.0
    MOCK_BASE_TEMPERATURE: float = 40.0

    # WebSocket配置
    WEBSOCKET_HEARTBEAT_INTERVAL: int = 30
    WEBSOCKET_PUSH_FREQUENCY: int = 5  # Hz

    # 日志配置
    LOG_LEVEL: str = "INFO"

    # Agent V2 Feature Flag
    AGENT_V2_ENABLED: bool = False
    AGENT_V2_DEFAULT_BUDGET_MS: int = 300000
    AGENT_V2_IDEMPOTENCY_TTL_SECONDS: int = 3600

    # LLM Provider Config
    DEEPSEEK_API_KEY: str = ""
    DEEPSEEK_BASE_URL: str = "https://api.deepseek.com"
    MINIMAX_API_KEY: str = ""
    MINIMAX_GROUP_ID: str = ""
    LLM_PRIMARY_PROVIDER: str = "deepseek"
    LLM_FALLBACK_PROVIDER: str = "minimax"
    LLM_TIMEOUT_SECONDS: float = 10.0
    LLM_ENABLE_MOCK_FALLBACK: bool = True

    # AI Assistant
    AI_ASSISTANT_MAX_HISTORY: int = 20
    AI_ASSISTANT_SYSTEM_PROMPT: str = "你是 R-MOS 维保学习助手，帮助学生理解机器人维保操作。"

    class Config:
        env_file = ".env"
        case_sensitive = True

    def validate_production(self) -> None:
        """生产环境启动校验"""
        if not self.DEBUG:
            if self.SECRET_KEY == "dev-only-change-me":
                raise RuntimeError("SECRET_KEY must be set in production")
            if "sqlite" in self.DATABASE_URL:
                raise RuntimeError("SQLite not supported in production, use PostgreSQL")


settings = Settings()
```

- [ ] **Step 2: 创建后端 .env.example**

```bash
# r-mos-backend/.env.example
# === 必填 (生产环境) ===
DATABASE_URL=postgresql+asyncpg://postgres:password@localhost:5432/rmos
SECRET_KEY=your-random-secret-key-here

# === 可选 ===
DEBUG=false
CORS_ORIGINS=["https://your-domain.com"]
ROBOT_MODE=simulation
LOG_LEVEL=INFO

# === LLM (不填则自动降级 Mock) ===
DEEPSEEK_API_KEY=
DEEPSEEK_BASE_URL=https://api.deepseek.com
MINIMAX_API_KEY=
MINIMAX_GROUP_ID=
LLM_ENABLE_MOCK_FALLBACK=true
```

- [ ] **Step 3: 创建项目根目录 .env.example**

```bash
# .env.example — Docker Compose 使用
POSTGRES_USER=rmos
POSTGRES_PASSWORD=change-me-in-production
POSTGRES_DB=rmos
SECRET_KEY=change-me-in-production
CORS_ORIGINS=["http://localhost:3000"]
ROBOT_MODE=simulation
```

- [ ] **Step 4: 验证 config 加载**

Run: `cd /Users/xuhehong/Desktop/r-mos/r-mos-backend && python -c "from app.core.config import settings; print(settings.DEBUG, settings.ROBOT_MODE)"`

Expected: `False simulation`

- [ ] **Step 5: Commit**

```bash
git add r-mos-backend/app/core/config.py r-mos-backend/.env.example .env.example
git commit -m "feat: production config with env validation and .env templates"
```

---

### Task 2: 学生任务列表 API

**Files:**
- Create: `r-mos-backend/app/api/v1/endpoints/student_tasks.py`
- Modify: `r-mos-backend/app/api/v1/__init__.py`

- [ ] **Step 1: 创建 student_tasks.py 端点**

```python
"""学生任务列表端点 — 聚合 task_executions + training_sessions"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func, case
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

from app.core.database import get_db
from app.models.task_execution import TaskExecution
from app.models.task import Task
from app.models.sop import SOP

router = APIRouter()


class StudentTaskItem(BaseModel):
    id: int
    task_id: int
    task_name: str
    sop_name: Optional[str] = None
    fault_type: Optional[str] = None
    status: str  # in_progress / completed / abandoned
    started_at: datetime
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class StudentTaskListResponse(BaseModel):
    items: List[StudentTaskItem]
    total: int
    pending_count: int
    in_progress_count: int
    completed_count: int


@router.get("/student/tasks", response_model=StudentTaskListResponse, tags=["student"])
async def list_student_tasks(
    student_id: int = Query(..., description="学生 user ID"),
    status: Optional[str] = Query(None, description="筛选状态: in_progress/completed/abandoned"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """获取学生的任务执行列表"""
    base_query = (
        select(TaskExecution, Task.name.label("task_name"), SOP.title.label("sop_name"))
        .join(Task, TaskExecution.task_id == Task.id, isouter=True)
        .join(SOP, TaskExecution.sop_id == SOP.id, isouter=True)
        .where(TaskExecution.student_id == student_id)
        .order_by(TaskExecution.started_at.desc())
    )

    if status:
        base_query = base_query.where(TaskExecution.status == status)

    # Count query
    count_query = (
        select(
            func.count(TaskExecution.id).label("total"),
            func.sum(case((TaskExecution.status == "in_progress", 1), else_=0)).label("in_progress_count"),
            func.sum(case((TaskExecution.status == "completed", 1), else_=0)).label("completed_count"),
        )
        .where(TaskExecution.student_id == student_id)
    )
    counts = (await db.execute(count_query)).one()

    # Paginated results
    result = await db.execute(base_query.limit(limit).offset(offset))
    rows = result.all()

    items = [
        StudentTaskItem(
            id=row.TaskExecution.id,
            task_id=row.TaskExecution.task_id,
            task_name=row.task_name or f"任务 #{row.TaskExecution.task_id}",
            sop_name=row.sop_name,
            fault_type=row.TaskExecution.fault_type,
            status=row.TaskExecution.status,
            started_at=row.TaskExecution.started_at,
            completed_at=row.TaskExecution.completed_at,
        )
        for row in rows
    ]

    return StudentTaskListResponse(
        items=items,
        total=counts.total or 0,
        pending_count=0,  # No "pending" status in task_executions
        in_progress_count=counts.in_progress_count or 0,
        completed_count=counts.completed_count or 0,
    )
```

- [ ] **Step 2: 注册路由到 __init__.py**

在 `r-mos-backend/app/api/v1/__init__.py` 中添加:

```python
# import 行增加:
from app.api.v1.endpoints import student_tasks, scenarios, ai_assistant

# 注册行增加:
api_router.include_router(student_tasks.router, tags=["student"])
```

- [ ] **Step 3: 验证端点加载**

Run: `cd /Users/xuhehong/Desktop/r-mos/r-mos-backend && python -c "from app.api.v1.endpoints.student_tasks import router; print(len(router.routes))"`

Expected: `1`

- [ ] **Step 4: Commit**

```bash
git add r-mos-backend/app/api/v1/endpoints/student_tasks.py r-mos-backend/app/api/v1/__init__.py
git commit -m "feat: add student tasks list API endpoint"
```

---

### Task 3: 场景列表 API

**Files:**
- Create: `r-mos-backend/app/api/v1/endpoints/scenarios.py`
- Modify: `r-mos-backend/app/api/v1/__init__.py` (already modified in Task 2)

- [ ] **Step 1: 创建 scenarios.py 端点**

```python
"""场景列表端点 — 基于 fault_sop_mappings 提供练习场景"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from typing import Optional, List

from app.core.database import get_db
from app.models.fault_sop_mapping import FaultSOPMapping
from app.models.sop import SOP

router = APIRouter()


class ScenarioItem(BaseModel):
    id: int
    fault_type: str
    sop_id: int
    sop_title: Optional[str] = None
    difficulty: str  # beginner / intermediate / advanced
    priority: int

    class Config:
        from_attributes = True


class ScenarioListResponse(BaseModel):
    items: List[ScenarioItem]
    total: int


@router.get("/scenarios", response_model=ScenarioListResponse, tags=["scenarios"])
async def list_scenarios(
    difficulty: Optional[str] = Query(None, description="难度筛选: beginner/intermediate/advanced"),
    fault_type: Optional[str] = Query(None, description="故障类型筛选"),
    db: AsyncSession = Depends(get_db),
):
    """获取可用练习场景列表"""
    query = (
        select(FaultSOPMapping, SOP.title.label("sop_title"))
        .join(SOP, FaultSOPMapping.sop_id == SOP.id, isouter=True)
        .order_by(FaultSOPMapping.priority.desc(), FaultSOPMapping.difficulty)
    )

    if difficulty:
        query = query.where(FaultSOPMapping.difficulty == difficulty)
    if fault_type:
        query = query.where(FaultSOPMapping.fault_type == fault_type)

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

- [ ] **Step 2: 注册路由**

在 `r-mos-backend/app/api/v1/__init__.py` 中添加注册行:

```python
api_router.include_router(scenarios.router, tags=["scenarios"])
```

- [ ] **Step 3: 验证端点**

Run: `cd /Users/xuhehong/Desktop/r-mos/r-mos-backend && python -c "from app.api.v1.endpoints.scenarios import router; print(len(router.routes))"`

Expected: `1`

- [ ] **Step 4: Commit**

```bash
git add r-mos-backend/app/api/v1/endpoints/scenarios.py r-mos-backend/app/api/v1/__init__.py
git commit -m "feat: add scenarios list API endpoint"
```

---

### Task 4: AI 助手后端端点

**Files:**
- Create: `r-mos-backend/app/services/ai_assistant_service.py`
- Create: `r-mos-backend/app/api/v1/endpoints/ai_assistant.py`
- Modify: `r-mos-backend/app/api/v1/__init__.py`

- [ ] **Step 1: 创建 AI 助手服务**

```python
"""AI 助手服务 — 基于当前 SOP 步骤上下文回答学生提问"""
import logging
from typing import Optional
from dataclasses import dataclass, field

from app.core.config import settings

logger = logging.getLogger(__name__)


@dataclass
class ChatContext:
    """当前练习上下文"""
    sop_id: Optional[int] = None
    sop_title: Optional[str] = None
    current_step_index: Optional[int] = None
    current_step_description: Optional[str] = None
    fault_type: Optional[str] = None
    hint_level: int = 3  # 1=方向, 2=关键提示, 3=详细步骤


@dataclass
class ChatMessage:
    role: str  # user / assistant
    content: str


@dataclass
class ChatResponse:
    reply: str
    hint_level_used: int


class AIAssistantService:
    """嵌入式 AI 助手 — SOP 练习中为学生提供实时帮助"""

    def __init__(self):
        self._system_prompt = settings.AI_ASSISTANT_SYSTEM_PROMPT
        self._max_history = settings.AI_ASSISTANT_MAX_HISTORY

    async def chat(
        self,
        message: str,
        context: ChatContext,
        history: list[ChatMessage] | None = None,
    ) -> ChatResponse:
        """处理学生提问，根据 hint_level 控制回答深度"""
        history = (history or [])[-self._max_history:]

        system_prompt = self._build_system_prompt(context)
        messages = [{"role": "system", "content": system_prompt}]
        for msg in history:
            messages.append({"role": msg.role, "content": msg.content})
        messages.append({"role": "user", "content": message})

        reply = await self._call_llm(messages)

        return ChatResponse(reply=reply, hint_level_used=context.hint_level)

    def _build_system_prompt(self, context: ChatContext) -> str:
        """构建带上下文的 system prompt"""
        parts = [self._system_prompt]

        if context.sop_title:
            parts.append(f"\n当前 SOP: {context.sop_title}")
        if context.current_step_index is not None:
            parts.append(f"当前步骤: 第 {context.current_step_index + 1} 步")
        if context.current_step_description:
            parts.append(f"步骤内容: {context.current_step_description}")
        if context.fault_type:
            parts.append(f"故障类型: {context.fault_type}")

        hint_instructions = {
            1: "\n回答要求：只给出方向性提示，不要直接告诉答案。用反问或提示引导学生思考。",
            2: "\n回答要求：给出关键提示，指出需要注意的要点，但不给出完整步骤。",
            3: "\n回答要求：给出详细的步骤说明和操作指导。",
        }
        parts.append(hint_instructions.get(context.hint_level, hint_instructions[3]))

        return "\n".join(parts)

    async def _call_llm(self, messages: list[dict]) -> str:
        """调用 LLM — 复用现有 LLM Router 逻辑"""
        try:
            from app.services.llm.router import LLMRouter
            router = LLMRouter()
            response = await router.chat(messages)
            return response
        except Exception as e:
            logger.warning(f"LLM call failed, using fallback: {e}")
            return "抱歉，AI 助手暂时不可用。请参考 SOP 步骤说明继续操作，或联系教师获取帮助。"
```

- [ ] **Step 2: 创建 AI 助手 API 端点**

```python
"""AI 助手聊天端点"""
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from typing import Optional, List

from app.core.database import get_db
from app.services.ai_assistant_service import (
    AIAssistantService,
    ChatContext,
    ChatMessage as ServiceChatMessage,
)

router = APIRouter()

_service = AIAssistantService()


class ChatMessageInput(BaseModel):
    role: str = Field(..., pattern="^(user|assistant)$")
    content: str


class AIChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)
    sop_id: Optional[int] = None
    sop_title: Optional[str] = None
    current_step_index: Optional[int] = None
    current_step_description: Optional[str] = None
    fault_type: Optional[str] = None
    hint_level: int = Field(default=3, ge=1, le=3)
    history: List[ChatMessageInput] = Field(default_factory=list)


class AIChatResponse(BaseModel):
    reply: str
    hint_level_used: int


@router.post("/ai-assistant/chat", response_model=AIChatResponse, tags=["ai-assistant"])
async def chat_with_assistant(request: AIChatRequest):
    """与 AI 助手对话 — SOP 练习中学生提问入口"""
    context = ChatContext(
        sop_id=request.sop_id,
        sop_title=request.sop_title,
        current_step_index=request.current_step_index,
        current_step_description=request.current_step_description,
        fault_type=request.fault_type,
        hint_level=request.hint_level,
    )
    history = [
        ServiceChatMessage(role=m.role, content=m.content)
        for m in request.history
    ]
    result = await _service.chat(
        message=request.message,
        context=context,
        history=history,
    )
    return AIChatResponse(reply=result.reply, hint_level_used=result.hint_level_used)
```

- [ ] **Step 3: 注册路由**

在 `r-mos-backend/app/api/v1/__init__.py` 中添加:

```python
api_router.include_router(ai_assistant.router, tags=["ai-assistant"])
```

- [ ] **Step 4: 验证端点**

Run: `cd /Users/xuhehong/Desktop/r-mos/r-mos-backend && python -c "from app.api.v1.endpoints.ai_assistant import router; print(len(router.routes))"`

Expected: `1`

- [ ] **Step 5: Commit**

```bash
git add r-mos-backend/app/services/ai_assistant_service.py r-mos-backend/app/api/v1/endpoints/ai_assistant.py r-mos-backend/app/api/v1/__init__.py
git commit -m "feat: add embedded AI assistant chat endpoint"
```

---

### Task 5: 前端导航分层调整

**Files:**
- Modify: `r-mos-frontend/src/components/Layout/AppLayout.tsx`

- [ ] **Step 1: 重构 STUDENT_NAV 为基础/进阶分层**

将 `AppLayout.tsx` 中的 `STUDENT_NAV` 替换为:

```typescript
const STUDENT_NAV: NavGroup[] = [
  {
    label: '练习中心',
    items: [
      { label: '学习进度', to: '/dashboard', icon: BarChart3 },
      { label: '我的任务', to: '/my-tasks', icon: ClipboardList },
      { label: '自主练习', to: '/scenarios', icon: Dumbbell },
    ],
  },
  {
    label: '维保操作',
    items: [
      { label: '实时监控', to: '/monitor', icon: Activity },
      { label: '维保练习', to: '/maintenance', icon: Wrench },
    ],
  },
  {
    label: '学习成长',
    items: [
      { label: '维保报告', to: '/reports', icon: FileText },
      { label: '我的技能', to: '/student/skills', icon: BarChart3 },
      { label: '3D 展示', to: '/atom01', icon: Boxes },
    ],
  },
  {
    label: '进阶工具',
    items: [
      { label: 'AI 诊断工作台', to: '/agent/workbench', icon: Bot },
    ],
  },
]
```

- [ ] **Step 2: 验证前端编译**

Run: `cd /Users/xuhehong/Desktop/r-mos/r-mos-frontend && npx tsc --noEmit --skipLibCheck 2>&1 | head -20`

Expected: 无新错误

- [ ] **Step 3: Commit**

```bash
cd /Users/xuhehong/Desktop/r-mos && git add r-mos-frontend/src/components/Layout/AppLayout.tsx
git commit -m "feat: restructure student nav with progressive disclosure"
```

---

### Task 6: 学习进度仪表盘页面

**Files:**
- Create: `r-mos-frontend/src/pages/DashboardPage.tsx`
- Modify: `r-mos-frontend/src/App.tsx`

- [ ] **Step 1: 创建 DashboardPage**

```tsx
import { useEffect, useState } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Progress } from '@/components/ui/progress'
import { BarChart3, CheckCircle, Clock, Target } from 'lucide-react'
import { useAuthStore } from '@/store/authStore'
import { apiClient } from '@/api/client'

interface TaskStats {
  total: number
  pending_count: number
  in_progress_count: number
  completed_count: number
}

export default function DashboardPage() {
  const user = useAuthStore((s) => s.user)
  const [stats, setStats] = useState<TaskStats | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!user?.user_id) return
    apiClient
      .get('/student/tasks', { params: { student_id: user.user_id, limit: 1 } })
      .then((res) => setStats(res.data))
      .catch(() => setStats(null))
      .finally(() => setLoading(false))
  }, [user?.user_id])

  const completionRate = stats && stats.total > 0
    ? Math.round((stats.completed_count / stats.total) * 100)
    : 0

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <BarChart3 className="h-6 w-6 text-primary" />
        <h1 className="text-2xl font-semibold text-text-primary">学习进度</h1>
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium text-text-secondary">总任务数</CardTitle>
            <Target className="h-4 w-4 text-text-muted" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{loading ? '—' : stats?.total ?? 0}</div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium text-text-secondary">进行中</CardTitle>
            <Clock className="h-4 w-4 text-yellow-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-yellow-600">
              {loading ? '—' : stats?.in_progress_count ?? 0}
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
              {loading ? '—' : stats?.completed_count ?? 0}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium text-text-secondary">完成率</CardTitle>
            <BarChart3 className="h-4 w-4 text-primary" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-primary">{loading ? '—' : `${completionRate}%`}</div>
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
    </div>
  )
}
```

- [ ] **Step 2: 在 App.tsx 中添加路由并设置为学生默认首页**

在路由配置中添加:

```tsx
import DashboardPage from '@/pages/DashboardPage'

// 在 AppLayout children 路由数组中添加:
{ path: 'dashboard', element: <DashboardPage /> },

// 修改 index 重定向逻辑: 学生默认去 /dashboard
{ index: true, element: <Navigate to="/dashboard" replace /> },
```

- [ ] **Step 3: 验证编译**

Run: `cd /Users/xuhehong/Desktop/r-mos/r-mos-frontend && npx tsc --noEmit --skipLibCheck 2>&1 | head -20`

Expected: 无新错误

- [ ] **Step 4: Commit**

```bash
cd /Users/xuhehong/Desktop/r-mos && git add r-mos-frontend/src/pages/DashboardPage.tsx r-mos-frontend/src/App.tsx
git commit -m "feat: add student learning dashboard as default home page"
```

---

### Task 7: MyTasksPage 补全实现

**Files:**
- Create: `r-mos-frontend/src/api/studentTasks.ts`
- Modify: `r-mos-frontend/src/pages/MyTasksPage.tsx`

- [ ] **Step 1: 创建 API 客户端**

```typescript
// r-mos-frontend/src/api/studentTasks.ts
import { apiClient } from './client'

export interface StudentTaskItem {
  id: number
  task_id: number
  task_name: string
  sop_name: string | null
  fault_type: string | null
  status: 'in_progress' | 'completed' | 'abandoned'
  started_at: string
  completed_at: string | null
}

export interface StudentTaskListResponse {
  items: StudentTaskItem[]
  total: number
  pending_count: number
  in_progress_count: number
  completed_count: number
}

export async function fetchStudentTasks(
  studentId: number,
  status?: string,
): Promise<StudentTaskListResponse> {
  const params: Record<string, unknown> = { student_id: studentId, limit: 50 }
  if (status) params.status = status
  const res = await apiClient.get<StudentTaskListResponse>('/student/tasks', { params })
  return res.data
}
```

- [ ] **Step 2: 重写 MyTasksPage**

```tsx
import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Card, CardContent } from '@/components/ui/card'
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { ClipboardList, Clock, CheckCircle, XCircle, Play } from 'lucide-react'
import { useAuthStore } from '@/store/authStore'
import { fetchStudentTasks, type StudentTaskItem } from '@/api/studentTasks'

type TaskFilter = 'all' | 'in_progress' | 'completed'

const STATUS_CONFIG = {
  in_progress: { label: '进行中', icon: Clock, variant: 'default' as const, color: 'text-yellow-600' },
  completed: { label: '已完成', icon: CheckCircle, variant: 'success' as const, color: 'text-green-600' },
  abandoned: { label: '已放弃', icon: XCircle, variant: 'destructive' as const, color: 'text-red-600' },
}

export default function MyTasksPage() {
  const [filter, setFilter] = useState<TaskFilter>('all')
  const [tasks, setTasks] = useState<StudentTaskItem[]>([])
  const [loading, setLoading] = useState(true)
  const user = useAuthStore((s) => s.user)
  const navigate = useNavigate()

  useEffect(() => {
    if (!user?.user_id) return
    setLoading(true)
    const status = filter === 'all' ? undefined : filter
    fetchStudentTasks(user.user_id, status)
      .then((res) => setTasks(res.items))
      .catch(() => setTasks([]))
      .finally(() => setLoading(false))
  }, [user?.user_id, filter])

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <ClipboardList className="h-6 w-6 text-primary" />
        <h1 className="text-2xl font-semibold text-text-primary">我的任务</h1>
      </div>

      <Tabs value={filter} onValueChange={(v) => setFilter(v as TaskFilter)}>
        <TabsList>
          <TabsTrigger value="all">全部</TabsTrigger>
          <TabsTrigger value="in_progress">进行中</TabsTrigger>
          <TabsTrigger value="completed">已完成</TabsTrigger>
        </TabsList>
      </Tabs>

      {loading ? (
        <div className="space-y-3">
          {[1, 2, 3].map((i) => (
            <Card key={i} className="animate-pulse">
              <CardContent className="py-4">
                <div className="h-5 w-48 rounded bg-bg-elevated" />
                <div className="mt-2 h-4 w-32 rounded bg-bg-elevated" />
              </CardContent>
            </Card>
          ))}
        </div>
      ) : tasks.length === 0 ? (
        <Card>
          <CardContent className="py-8 text-center">
            <p className="text-sm text-text-muted">暂无任务记录，开始一次练习吧！</p>
            <Button className="mt-4" onClick={() => navigate('/scenarios')}>
              <Play className="mr-2 h-4 w-4" />
              去练习
            </Button>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-3">
          {tasks.map((task) => {
            const config = STATUS_CONFIG[task.status]
            const StatusIcon = config.icon
            return (
              <Card key={task.id} className="transition-colors hover:border-primary/30">
                <CardContent className="flex items-center justify-between py-4">
                  <div className="space-y-1">
                    <div className="flex items-center gap-2">
                      <span className="font-medium text-text-primary">{task.task_name}</span>
                      <Badge variant={config.variant}>{config.label}</Badge>
                    </div>
                    <div className="flex items-center gap-3 text-xs text-text-muted">
                      {task.sop_name && <span>SOP: {task.sop_name}</span>}
                      {task.fault_type && <span>故障: {task.fault_type}</span>}
                      <span>{new Date(task.started_at).toLocaleDateString()}</span>
                    </div>
                  </div>
                  <StatusIcon className={`h-5 w-5 ${config.color}`} />
                </CardContent>
              </Card>
            )
          })}
        </div>
      )}
    </div>
  )
}
```

- [ ] **Step 3: 验证编译**

Run: `cd /Users/xuhehong/Desktop/r-mos/r-mos-frontend && npx tsc --noEmit --skipLibCheck 2>&1 | head -20`

Expected: 无新错误

- [ ] **Step 4: Commit**

```bash
cd /Users/xuhehong/Desktop/r-mos && git add r-mos-frontend/src/api/studentTasks.ts r-mos-frontend/src/pages/MyTasksPage.tsx
git commit -m "feat: implement MyTasksPage with backend integration"
```

---

### Task 8: ScenarioPickerPage 补全实现

**Files:**
- Create: `r-mos-frontend/src/api/scenarios.ts`
- Modify: `r-mos-frontend/src/pages/ScenarioPickerPage.tsx`

- [ ] **Step 1: 创建 API 客户端**

```typescript
// r-mos-frontend/src/api/scenarios.ts
import { apiClient } from './client'

export interface ScenarioItem {
  id: number
  fault_type: string
  sop_id: number
  sop_title: string | null
  difficulty: 'beginner' | 'intermediate' | 'advanced'
  priority: number
}

export interface ScenarioListResponse {
  items: ScenarioItem[]
  total: number
}

export async function fetchScenarios(
  difficulty?: string,
): Promise<ScenarioListResponse> {
  const params: Record<string, string> = {}
  if (difficulty && difficulty !== 'all') params.difficulty = difficulty
  const res = await apiClient.get<ScenarioListResponse>('/scenarios', { params })
  return res.data
}
```

- [ ] **Step 2: 重写 ScenarioPickerPage**

```tsx
import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Card, CardContent } from '@/components/ui/card'
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Dumbbell, Sparkles, Play } from 'lucide-react'
import { fetchScenarios, type ScenarioItem } from '@/api/scenarios'

type Difficulty = 'all' | 'beginner' | 'intermediate' | 'advanced'

const DIFFICULTY_LABEL: Record<string, string> = {
  beginner: '入门',
  intermediate: '进阶',
  advanced: '高级',
}

const DIFFICULTY_VARIANT: Record<string, 'default' | 'success' | 'destructive'> = {
  beginner: 'default',
  intermediate: 'success',
  advanced: 'destructive',
}

export default function ScenarioPickerPage() {
  const [difficulty, setDifficulty] = useState<Difficulty>('all')
  const [scenarios, setScenarios] = useState<ScenarioItem[]>([])
  const [loading, setLoading] = useState(true)
  const navigate = useNavigate()

  useEffect(() => {
    setLoading(true)
    fetchScenarios(difficulty)
      .then((res) => setScenarios(res.items))
      .catch(() => setScenarios([]))
      .finally(() => setLoading(false))
  }, [difficulty])

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <Dumbbell className="h-6 w-6 text-primary" />
        <h1 className="text-2xl font-semibold text-text-primary">自主练习</h1>
      </div>

      <Card className="border-primary/20 bg-primary-muted/30">
        <CardContent className="flex items-center gap-3 py-4">
          <Sparkles className="h-5 w-5 text-primary" />
          <p className="text-sm text-text-secondary">
            选择一个故障场景开始练习，AI 助手会在练习过程中为你提供帮助。
          </p>
        </CardContent>
      </Card>

      <Tabs value={difficulty} onValueChange={(v) => setDifficulty(v as Difficulty)}>
        <TabsList>
          <TabsTrigger value="all">全部</TabsTrigger>
          <TabsTrigger value="beginner">入门</TabsTrigger>
          <TabsTrigger value="intermediate">进阶</TabsTrigger>
          <TabsTrigger value="advanced">高级</TabsTrigger>
        </TabsList>
      </Tabs>

      {loading ? (
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
      ) : scenarios.length === 0 ? (
        <Card>
          <CardContent className="py-8 text-center">
            <p className="text-sm text-text-muted">
              暂无可用的练习场景。教师配置故障场景后将显示在此处。
            </p>
          </CardContent>
        </Card>
      ) : (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {scenarios.map((scenario) => (
            <Card key={scenario.id} className="transition-all hover:border-primary/30 hover:shadow-sm">
              <CardContent className="space-y-3 py-5">
                <div className="flex items-center justify-between">
                  <span className="font-medium text-text-primary">
                    {scenario.sop_title || scenario.fault_type}
                  </span>
                  <Badge variant={DIFFICULTY_VARIANT[scenario.difficulty]}>
                    {DIFFICULTY_LABEL[scenario.difficulty]}
                  </Badge>
                </div>
                <p className="text-xs text-text-muted">故障类型: {scenario.fault_type}</p>
                <Button
                  size="sm"
                  className="w-full"
                  onClick={() => navigate(`/maintenance?sop_id=${scenario.sop_id}`)}
                >
                  <Play className="mr-2 h-3 w-3" />
                  开始练习
                </Button>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  )
}
```

- [ ] **Step 3: 验证编译**

Run: `cd /Users/xuhehong/Desktop/r-mos/r-mos-frontend && npx tsc --noEmit --skipLibCheck 2>&1 | head -20`

Expected: 无新错误

- [ ] **Step 4: Commit**

```bash
cd /Users/xuhehong/Desktop/r-mos && git add r-mos-frontend/src/api/scenarios.ts r-mos-frontend/src/pages/ScenarioPickerPage.tsx
git commit -m "feat: implement ScenarioPickerPage with backend integration"
```

---

### Task 9: AI 助手前端浮窗组件

**Files:**
- Create: `r-mos-frontend/src/api/aiAssistant.ts`
- Create: `r-mos-frontend/src/store/aiAssistantStore.ts`
- Create: `r-mos-frontend/src/components/AIAssistant/AIAssistantPanel.tsx`
- Create: `r-mos-frontend/src/components/AIAssistant/ChatMessage.tsx`

- [ ] **Step 1: 创建 API 客户端**

```typescript
// r-mos-frontend/src/api/aiAssistant.ts
import { apiClient } from './client'

export interface ChatMessagePayload {
  role: 'user' | 'assistant'
  content: string
}

export interface AIChatRequest {
  message: string
  sop_id?: number
  sop_title?: string
  current_step_index?: number
  current_step_description?: string
  fault_type?: string
  hint_level?: number
  history?: ChatMessagePayload[]
}

export interface AIChatResponse {
  reply: string
  hint_level_used: number
}

export async function sendAIChat(request: AIChatRequest): Promise<AIChatResponse> {
  const res = await apiClient.post<AIChatResponse>('/ai-assistant/chat', request)
  return res.data
}
```

- [ ] **Step 2: 创建 store**

```typescript
// r-mos-frontend/src/store/aiAssistantStore.ts
import { create } from 'zustand'

export interface ChatMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  timestamp: number
}

interface AIAssistantState {
  isOpen: boolean
  messages: ChatMessage[]
  isLoading: boolean
  toggle: () => void
  open: () => void
  close: () => void
  addMessage: (role: 'user' | 'assistant', content: string) => void
  setLoading: (loading: boolean) => void
  clearMessages: () => void
}

export const useAIAssistantStore = create<AIAssistantState>((set) => ({
  isOpen: false,
  messages: [],
  isLoading: false,
  toggle: () => set((s) => ({ isOpen: !s.isOpen })),
  open: () => set({ isOpen: true }),
  close: () => set({ isOpen: false }),
  addMessage: (role, content) =>
    set((s) => ({
      messages: [
        ...s.messages,
        { id: `${Date.now()}-${Math.random()}`, role, content, timestamp: Date.now() },
      ],
    })),
  setLoading: (isLoading) => set({ isLoading }),
  clearMessages: () => set({ messages: [] }),
}))
```

- [ ] **Step 3: 创建 ChatMessage 组件**

```tsx
// r-mos-frontend/src/components/AIAssistant/ChatMessage.tsx
import { Bot, User } from 'lucide-react'
import { cn } from '@/lib/utils'
import type { ChatMessage as ChatMessageType } from '@/store/aiAssistantStore'

export function ChatMessage({ message }: { message: ChatMessageType }) {
  const isUser = message.role === 'user'
  return (
    <div className={cn('flex gap-2', isUser && 'flex-row-reverse')}>
      <div
        className={cn(
          'flex h-7 w-7 shrink-0 items-center justify-center rounded-full',
          isUser ? 'bg-primary/10 text-primary' : 'bg-bg-elevated text-text-secondary',
        )}
      >
        {isUser ? <User className="h-3.5 w-3.5" /> : <Bot className="h-3.5 w-3.5" />}
      </div>
      <div
        className={cn(
          'max-w-[80%] rounded-lg px-3 py-2 text-sm',
          isUser
            ? 'bg-primary text-white'
            : 'bg-bg-elevated text-text-primary',
        )}
      >
        {message.content}
      </div>
    </div>
  )
}
```

- [ ] **Step 4: 创建 AIAssistantPanel 浮窗**

```tsx
// r-mos-frontend/src/components/AIAssistant/AIAssistantPanel.tsx
import { useRef, useState, useEffect } from 'react'
import { Bot, Send, X, Minimize2 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { ScrollArea } from '@/components/ui/scroll-area'
import { useAIAssistantStore } from '@/store/aiAssistantStore'
import { sendAIChat, type ChatMessagePayload } from '@/api/aiAssistant'
import { ChatMessage } from './ChatMessage'

interface AIAssistantPanelProps {
  sopId?: number
  sopTitle?: string
  currentStepIndex?: number
  currentStepDescription?: string
  faultType?: string
  hintLevel?: number
}

export function AIAssistantPanel({
  sopId,
  sopTitle,
  currentStepIndex,
  currentStepDescription,
  faultType,
  hintLevel = 3,
}: AIAssistantPanelProps) {
  const { isOpen, messages, isLoading, toggle, close, addMessage, setLoading } =
    useAIAssistantStore()
  const [input, setInput] = useState('')
  const scrollRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight
    }
  }, [messages])

  const handleSend = async () => {
    const trimmed = input.trim()
    if (!trimmed || isLoading) return

    addMessage('user', trimmed)
    setInput('')
    setLoading(true)

    try {
      const history: ChatMessagePayload[] = messages.map((m) => ({
        role: m.role,
        content: m.content,
      }))
      const response = await sendAIChat({
        message: trimmed,
        sop_id: sopId,
        sop_title: sopTitle,
        current_step_index: currentStepIndex,
        current_step_description: currentStepDescription,
        fault_type: faultType,
        hint_level: hintLevel,
        history,
      })
      addMessage('assistant', response.reply)
    } catch {
      addMessage('assistant', '抱歉，请求失败。请稍���重试。')
    } finally {
      setLoading(false)
    }
  }

  if (!isOpen) {
    return (
      <button
        onClick={toggle}
        className="fixed bottom-6 right-6 z-50 flex h-12 w-12 items-center justify-center rounded-full bg-primary text-white shadow-lg transition-transform hover:scale-105"
      >
        <Bot className="h-5 w-5" />
      </button>
    )
  }

  return (
    <div className="fixed bottom-6 right-6 z-50 flex h-[480px] w-[360px] flex-col rounded-xl border border-border-subtle bg-bg-surface shadow-xl">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-border-subtle px-4 py-3">
        <div className="flex items-center gap-2">
          <Bot className="h-4 w-4 text-primary" />
          <span className="text-sm font-medium text-text-primary">AI 助手</span>
        </div>
        <div className="flex items-center gap-1">
          <Button variant="ghost" size="icon" className="h-7 w-7" onClick={close}>
            <Minimize2 className="h-3.5 w-3.5" />
          </Button>
          <Button variant="ghost" size="icon" className="h-7 w-7" onClick={close}>
            <X className="h-3.5 w-3.5" />
          </Button>
        </div>
      </div>

      {/* Messages */}
      <ScrollArea className="flex-1 px-4 py-3" ref={scrollRef}>
        <div className="space-y-3">
          {messages.length === 0 && (
            <p className="py-8 text-center text-xs text-text-muted">
              有问题随时问我，我会根据当前步骤为你提供帮助。
            </p>
          )}
          {messages.map((msg) => (
            <ChatMessage key={msg.id} message={msg} />
          ))}
          {isLoading && (
            <div className="flex gap-2">
              <div className="flex h-7 w-7 items-center justify-center rounded-full bg-bg-elevated">
                <Bot className="h-3.5 w-3.5 animate-pulse text-text-secondary" />
              </div>
              <div className="rounded-lg bg-bg-elevated px-3 py-2 text-sm text-text-muted">
                思考中...
              </div>
            </div>
          )}
        </div>
      </ScrollArea>

      {/* Input */}
      <div className="border-t border-border-subtle p-3">
        <div className="flex items-center gap-2">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && !e.shiftKey && handleSend()}
            placeholder="输入问题..."
            className="flex-1 rounded-md border border-border-subtle bg-bg-base px-3 py-2 text-sm outline-none focus:border-primary"
          />
          <Button size="icon" className="h-8 w-8" onClick={handleSend} disabled={isLoading}>
            <Send className="h-3.5 w-3.5" />
          </Button>
        </div>
      </div>
    </div>
  )
}
```

- [ ] **Step 5: 验证编译**

Run: `cd /Users/xuhehong/Desktop/r-mos/r-mos-frontend && npx tsc --noEmit --skipLibCheck 2>&1 | head -20`

Expected: 无新错误

- [ ] **Step 6: Commit**

```bash
cd /Users/xuhehong/Desktop/r-mos && git add r-mos-frontend/src/api/aiAssistant.ts r-mos-frontend/src/store/aiAssistantStore.ts r-mos-frontend/src/components/AIAssistant/
git commit -m "feat: add AI assistant floating panel component"
```

---

### Task 10: 集成 AI 助手到 SOPPlayer

**Files:**
- Modify: `r-mos-frontend/src/components/Maintenance/SOPPlayerAdjudicated.tsx`

- [ ] **Step 1: 在 SOPPlayerAdjudicated 中添加 AI 助手面板**

在文件顶部添加 import:

```tsx
import { AIAssistantPanel } from '@/components/AIAssistant/AIAssistantPanel'
```

在组件 JSX return 的最外层 `<div>` 末尾、关闭标签前添加:

```tsx
<AIAssistantPanel
  sopId={sopData?.id}
  sopTitle={sopData?.title}
  currentStepIndex={currentStepIndex}
  currentStepDescription={sopData?.steps?.[currentStepIndex]?.description}
  faultType={sopData?.fault_type}
  hintLevel={3}
/>
```

- [ ] **Step 2: 验证编译**

Run: `cd /Users/xuhehong/Desktop/r-mos/r-mos-frontend && npx tsc --noEmit --skipLibCheck 2>&1 | head -20`

Expected: 无新错误

- [ ] **Step 3: Commit**

```bash
cd /Users/xuhehong/Desktop/r-mos && git add r-mos-frontend/src/components/Maintenance/SOPPlayerAdjudicated.tsx
git commit -m "feat: integrate AI assistant panel into SOP practice view"
```

---

### Task 11: Docker 部署方案

**Files:**
- Create: `r-mos-backend/Dockerfile`
- Create: `r-mos-frontend/Dockerfile`
- Create: `docker-compose.yml` (project root)
- Create: `r-mos-frontend/nginx.conf`

- [ ] **Step 1: 创建后端 Dockerfile**

```dockerfile
# r-mos-backend/Dockerfile
FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libpq-dev && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
```

- [ ] **Step 2: 创建前端 nginx.conf**

```nginx
# r-mos-frontend/nginx.conf
server {
    listen 80;
    server_name _;
    root /usr/share/nginx/html;
    index index.html;

    location / {
        try_files $uri $uri/ /index.html;
    }

    location /api/ {
        proxy_pass http://backend:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    location /ws/ {
        proxy_pass http://backend:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

- [ ] **Step 3: 创建前端 Dockerfile**

```dockerfile
# r-mos-frontend/Dockerfile
FROM node:20-alpine AS build
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
```

- [ ] **Step 4: 创建 docker-compose.yml**

```yaml
# docker-compose.yml
version: "3.8"

services:
  postgres:
    image: postgres:14-alpine
    environment:
      POSTGRES_USER: ${POSTGRES_USER:-rmos}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-changeme}
      POSTGRES_DB: ${POSTGRES_DB:-rmos}
    volumes:
      - pgdata:/var/lib/postgresql/data
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER:-rmos}"]
      interval: 5s
      timeout: 5s
      retries: 5

  backend:
    build: ./r-mos-backend
    environment:
      DATABASE_URL: postgresql+asyncpg://${POSTGRES_USER:-rmos}:${POSTGRES_PASSWORD:-changeme}@postgres:5432/${POSTGRES_DB:-rmos}
      SECRET_KEY: ${SECRET_KEY:-dev-only-change-me}
      DEBUG: "false"
      CORS_ORIGINS: '["http://localhost", "http://localhost:3000"]'
      ROBOT_MODE: ${ROBOT_MODE:-simulation}
      DEEPSEEK_API_KEY: ${DEEPSEEK_API_KEY:-}
      MINIMAX_API_KEY: ${MINIMAX_API_KEY:-}
      LLM_ENABLE_MOCK_FALLBACK: "true"
    ports:
      - "8000:8000"
    depends_on:
      postgres:
        condition: service_healthy

  frontend:
    build: ./r-mos-frontend
    ports:
      - "80:80"
    depends_on:
      - backend

volumes:
  pgdata:
```

- [ ] **Step 5: 验证 docker-compose 配置语法**

Run: `cd /Users/xuhehong/Desktop/r-mos && docker compose config --quiet 2>&1 | head -5`

Expected: 无错误输出（或 docker 未安装的友好提示）

- [ ] **Step 6: Commit**

```bash
cd /Users/xuhehong/Desktop/r-mos && git add r-mos-backend/Dockerfile r-mos-frontend/Dockerfile r-mos-frontend/nginx.conf docker-compose.yml
git commit -m "feat: add Docker Compose deployment (backend + frontend + postgres)"
```

---

### Task 12: 代码清理与统一错误格式

**Files:**
- Modify: `r-mos-backend/app/core/config.py` (已在 Task 1 改过，此处验证)
- Modify: `r-mos-backend/main.py` (添加生产校验调用)

- [ ] **Step 1: 在 main.py startup 中添加生产环境校验**

在 `main.py` 的 app startup/lifespan 逻辑中添加:

```python
from app.core.config import settings

# 在 app 创建后、startup 事件中:
if not settings.DEBUG:
    settings.validate_production()
```

- [ ] **Step 2: 确认 ROBOT_ADAPTER_TYPE 引用更新为 ROBOT_MODE**

搜索所有引用 `ROBOT_ADAPTER_TYPE` 的地方，确认是否需要更新为 `ROBOT_MODE`。如果 adapter 工厂仍用 `ROBOT_ADAPTER_TYPE`，保持兼容:

在 `config.py` 中添加兼容属性:

```python
@property
def ROBOT_ADAPTER_TYPE(self) -> str:
    """向后兼容: adapter factory 仍然用这个名字"""
    return self.ROBOT_MODE
```

- [ ] **Step 3: 验证后端启动**

Run: `cd /Users/xuhehong/Desktop/r-mos/r-mos-backend && python -c "from app.core.config import settings; print(settings.ROBOT_MODE, settings.ROBOT_ADAPTER_TYPE)"`

Expected: `simulation simulation`

- [ ] **Step 4: Commit**

```bash
cd /Users/xuhehong/Desktop/r-mos && git add r-mos-backend/main.py r-mos-backend/app/core/config.py
git commit -m "feat: add production startup validation and ROBOT_MODE compat"
```

---

### Task 13: 前端路由整合与默认首页

**Files:**
- Modify: `r-mos-frontend/src/App.tsx`

- [ ] **Step 1: 添加 DashboardPage 路由并调整默认重定向**

在 App.tsx 的路由配置中:

1. Import DashboardPage:
```tsx
import DashboardPage from '@/pages/DashboardPage'
```

2. 在 AppLayout 的 children 路由数组中添加:
```tsx
{ path: 'dashboard', element: <DashboardPage /> },
```

3. 修改 index 路由的重定向: 让学生默认跳转 `/dashboard`:
```tsx
{ index: true, element: <Navigate to="/dashboard" replace /> },
```

- [ ] **Step 2: 验证编译**

Run: `cd /Users/xuhehong/Desktop/r-mos/r-mos-frontend && npx tsc --noEmit --skipLibCheck 2>&1 | head -20`

Expected: 无新错误

- [ ] **Step 3: Commit**

```bash
cd /Users/xuhehong/Desktop/r-mos && git add r-mos-frontend/src/App.tsx
git commit -m "feat: add dashboard route and set as default student home"
```

---

### Task 14: 端到端冒烟测试

**Files:** None (验证性任务)

- [ ] **Step 1: 启动后端并验证新端点**

Run: `cd /Users/xuhehong/Desktop/r-mos/r-mos-backend && timeout 10 python -c "
import asyncio
from httpx import AsyncClient, ASGITransport
from main import app

async def test():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url='http://test') as client:
        # Health
        r = await client.get('/api/v1/health')
        assert r.status_code == 200, f'health: {r.status_code}'
        # Student tasks
        r = await client.get('/api/v1/student/tasks', params={'student_id': 1})
        assert r.status_code == 200, f'student_tasks: {r.status_code}'
        # Scenarios
        r = await client.get('/api/v1/scenarios')
        assert r.status_code == 200, f'scenarios: {r.status_code}'
        # AI assistant
        r = await client.post('/api/v1/ai-assistant/chat', json={'message': 'hello'})
        assert r.status_code == 200, f'ai_assistant: {r.status_code}'
        print('ALL ENDPOINTS OK')

asyncio.run(test())
" 2>&1`

Expected: `ALL ENDPOINTS OK`

- [ ] **Step 2: 验证前端编译无错误**

Run: `cd /Users/xuhehong/Desktop/r-mos/r-mos-frontend && npx tsc --noEmit --skipLibCheck 2>&1 | tail -5`

Expected: 无错误

- [ ] **Step 3: 验证前端 build 成功**

Run: `cd /Users/xuhehong/Desktop/r-mos/r-mos-frontend && npm run build 2>&1 | tail -10`

Expected: build 成功输出

- [ ] **Step 4: Commit (if any fixes needed)**

```bash
cd /Users/xuhehong/Desktop/r-mos && git add -A && git commit -m "fix: smoke test fixes" || echo "Nothing to commit"
```

---

## Summary

| Task | 内容 | 预期产出 |
|------|------|----------|
| 1 | 生产配置治理 | config.py + .env 模板 |
| 2 | 学生任务列表 API | GET /student/tasks |
| 3 | 场景列表 API | GET /scenarios |
| 4 | AI 助手后端 | POST /ai-assistant/chat |
| 5 | 前端导航分层 | 学生导航重构 |
| 6 | 学习进度仪表盘 | DashboardPage |
| 7 | MyTasksPage 补全 | 真实数据 + UI |
| 8 | ScenarioPickerPage 补全 | 真实数据 + UI |
| 9 | AI 助手前端组件 | 浮窗 + store + API |
| 10 | AI 助手集成 SOPPlayer | 练习时可用助手 |
| 11 | Docker 部署方案 | docker-compose 一键部署 |
| 12 | 代码清理 | 生产校验 + 兼容 |
| 13 | 路由整合 | 默认首页 → dashboard |
| 14 | 冒烟测试 | 全端点验证 |
