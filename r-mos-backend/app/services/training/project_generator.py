"""
UF-04: Training Project Generator
训练项目生成器

职责：
- 双路融合检索（知识库 + 个人记忆）
- LLM 项目生成
- 项目合规检查
- SSE 流式响应
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Optional, Any, AsyncGenerator
from enum import Enum

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.llm import llm_router, LLMProvider
from app.services.knowledge.hub import KnowledgeHub

logger = logging.getLogger(__name__)


class ProjectStatus(str, Enum):
    """项目生成状态"""
    RETRIEVING_KNOWLEDGE = "retrieving_knowledge"
    ANALYZING_HISTORY = "analyzing_history"
    GENERATING_PROJECT = "generating_project"
    COMPLETED = "completed"
    ERROR = "error"


@dataclass
class StepConfig:
    """步骤配置"""
    step_id: str
    title: str
    description: str
    model_highlight: list[str] = field(default_factory=list)
    required_tools: list[str] = field(default_factory=list)
    ref_ids: list[str] = field(default_factory=list)
    required_level: int = 1


@dataclass
class ToolConfig:
    """工具配置"""
    tool_id: str
    name: str
    spec: str
    is_critical: bool = False


@dataclass
class VerdictConfig:
    """裁决配置"""
    mode: str = "normal"  # strict / normal / guided
    time_limit: int = 60  # 分钟
    max_attempts: int = 3


@dataclass
class RobotConfig:
    """机器人配置"""
    asset_id: str
    brand: str
    model: str


@dataclass
class TrainingProject:
    """训练项目"""
    project_id: str
    title: str
    description: str
    steps: list[StepConfig] = field(default_factory=list)
    tools_checklist: list[ToolConfig] = field(default_factory=list)
    verdict_config: VerdictConfig = field(default_factory=VerdictConfig)
    robot: Optional[RobotConfig] = None
    estimated_time: int = 60  # 分钟
    difficulty_cap: int = 5
    emphasize_steps: list[str] = field(default_factory=list)


class ProjectGenerator:
    """训练项目生成器 - UF-04"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.knowledge_hub = KnowledgeHub()

    async def generate(
        self,
        intent: Any,
        user_id: int,
    ) -> AsyncGenerator[dict, None]:
        """UF-04-d-2: 生成训练项目（SSE 流式响应）

        Args:
            intent: TrainingIntent 意图参数
            user_id: 用户ID

        Yields:
            dict: 阶段性状态
        """
        # Stage 1: 检索知识库
        yield {"status": ProjectStatus.RETRIEVING_KNOWLEDGE, "message": "检索知识库中..."}

        knowledge_results = await self._retrieve_knowledge(intent)

        if not knowledge_results or len(knowledge_results) < 5:
            yield {
                "status": ProjectStatus.ERROR,
                "error": "knowledge_missing",
                "hint": f"请先在知识库上传 {intent.brand or ''} {intent.model or ''} 的技术手册",
            }
            return

        # Stage 2: 分析历史记录
        yield {"status": ProjectStatus.ANALYZING_HISTORY, "message": "分析历史记录..."}

        history_context = await self._analyze_history(user_id, intent)

        # Stage 3: 生成项目
        yield {"status": ProjectStatus.GENERATING_PROJECT, "message": "生成训练步骤..."}

        project = await self._generate_project(intent, knowledge_results, history_context)

        # Stage 4: 完成
        yield {"status": ProjectStatus.COMPLETED, "message": "完成", "project": project}

    async def _retrieve_knowledge(self, intent: Any) -> list[dict]:
        """UF-04-a-2: 知识库检索"""
        # 构建查询
        query = f"{intent.category or ''} {intent.brand or ''} {intent.model or ''}"

        try:
            results = await self.knowledge_hub.search(
                db=self.db,
                query=query,
                top_k=10,
                filters={"brand": intent.brand, "model": intent.model},
                allow_degraded=True,
            )
            normalized: list[dict] = []
            for item in results:
                if isinstance(item, dict):
                    normalized.append(item)
                    continue
                normalized.append(
                    {
                        "title": getattr(item, "title", "Unknown"),
                        "content": getattr(item, "content", ""),
                        "score": getattr(item, "score", 0),
                    }
                )
            return normalized
        except Exception as e:
            logger.warning(f"[UF-04] Knowledge retrieval failed: {e}")
            return []

    async def _analyze_history(self, user_id: int, intent: Any) -> dict:
        """UF-04-a-3: 个人记忆分析

        获取 skill_level / weak_steps / completed_tasks / avg_duration
        """
        # TODO: 实际从 MemoryHub 获取
        return {
            "skill_level": 2,
            "weak_steps": ["step_002", "step_005"],
            "completed_tasks": [],
            "avg_duration": 45,
        }

    async def _generate_project(
        self,
        intent: Any,
        knowledge_results: list[dict],
        history_context: dict,
    ) -> TrainingProject:
        """UF-04-b: LLM 项目生成"""

        # 构建生成 prompt
        prompt = self._build_generation_prompt(intent, knowledge_results, history_context)

        # 调用 LLM
        try:
            response = await llm_router.chat(
                messages=[{"role": "user", "content": prompt}],
                provider=LLMProvider.OPENAI,
                model="gpt-4",
                temperature=0.3,
                max_tokens=4000,
            )

            # 解析响应
            project = self._parse_llm_response(response.content, intent)

            # UF-04-c: 项目合规检查
            project = self._validate_project(project)

            return project

        except Exception as e:
            logger.error(f"[UF-04] Project generation failed: {e}")
            # 降级策略：从知识库加载评分最高的 SOP
            return await self._fallback_project(intent, knowledge_results)

    def _build_generation_prompt(
        self,
        intent: Any,
        knowledge_results: list[dict],
        history_context: dict,
    ) -> str:
        """UF-04-b-1: 构建项目生成 prompt"""

        # 格式化知识库结果
        knowledge_context = "\n\n".join([
            f"【{r.get('title', 'Unknown')}】\n{r.get('content', '')}"
            for r in knowledge_results[:5]
        ])

        # 格式化历史上下文
        history_context_str = f"""
学员技能等级: L{history_context.get('skill_level', 1)}
薄弱步骤: {', '.join(history_context.get('weak_steps', [])[:3])}
已完成任务数: {len(history_context.get('completed_tasks', []))}
平均用时: {history_context.get('avg_duration', 0)}分钟
"""

        prompt = f"""你是一位维保培训专家。请根据以下信息生成一个训练项目。

## 学员背景
{history_context_str}

## 知识库参考
{knowledge_context}

## 训练需求
- 类型: {intent.intent_type.value if hasattr(intent, 'intent_type') else 'new'}
- 品牌: {getattr(intent, 'brand', '未指定')}
- 型号: {getattr(intent, 'model', '未指定')}
- 类别: {getattr(intent, 'category', '未指定')}

## 生成要求
1. 最多 {min(20, 5 + history_context.get('skill_level', 1) * 3)} 个步骤
2. 难度上限: L{history_context.get('skill_level', 1) + 1}
3. 重点强化步骤: {', '.join(history_context.get('weak_steps', [])[:3])}
4. 避免重复: 不要生成学员已完成的任务
5. 估计时长: 60分钟

## 输出格式 (JSON)
请直接输出 JSON，不要包含其他内容：
{{
    "project_id": "训练项目ID",
    "title": "项目标题",
    "description": "项目描述",
    "steps": [
        {{
            "step_id": "步骤ID",
            "title": "步骤标题",
            "description": "步骤描述",
            "model_highlight": ["部件名称"],
            "required_tools": ["工具名称"],
            "ref_ids": ["引用ID"],
            "required_level": 1
        }}
    ],
    "tools_checklist": [
        {{
            "tool_id": "工具ID",
            "name": "工具名称",
            "spec": "规格",
            "is_critical": true/false
        }}
    ],
    "verdict_config": {{
        "mode": "strict/normal/guided",
        "time_limit": 60,
        "max_attempts": 3
    }},
    "robot": {{
        "asset_id": "机器人ID",
        "brand": "品牌",
        "model": "型号"
    }},
    "estimated_time": 60,
    "difficulty_cap": 3
}}
"""
        return prompt

    def _parse_llm_response(self, content: str, intent: Any) -> TrainingProject:
        """UF-04-b-3: 解析 LLM 响应"""
        import json

        try:
            data = json.loads(content)

            # 验证必填字段
            if not data.get("steps"):
                raise ValueError("Steps cannot be empty")
            if not data.get("robot"):
                raise ValueError("Robot config required")

            # 构建项目对象
            project = TrainingProject(
                project_id=data.get("project_id", f"proj_{id(intent)}"),
                title=data.get("title", "训练项目"),
                description=data.get("description", ""),
                estimated_time=data.get("estimated_time", 60),
                difficulty_cap=data.get("difficulty_cap", 5),
                steps=[StepConfig(**s) for s in data.get("steps", [])],
                tools_checklist=[ToolConfig(**t) for t in data.get("tools_checklist", [])],
                verdict_config=VerdictConfig(**data.get("verdict_config", {})),
                robot=RobotConfig(**data.get("robot", {})),
            )

            return project

        except json.JSONDecodeError as e:
            logger.error(f"[UF-04] JSON parse failed: {e}")
            raise ValueError("LLM response is not valid JSON")

    def _validate_project(self, project: TrainingProject) -> TrainingProject:
        """UF-04-c: 项目合规检查"""

        # UF-04-c-1: 步骤引用检查
        for step in project.steps:
            if not step.ref_ids:
                step.description = "⚠ 依据待补充 - " + step.description

        # UF-04-c-2: 安全步骤自动补全
        if not any("安全" in s.title for s in project.steps[:2]):
            # 在第一步之前插入安全检查步骤
            safety_step = StepConfig(
                step_id="step_001_safety",
                title="安全确认",
                description="确认工作区域安全，检查防护设备",
                required_tools=[],
                required_level=1,
            )
            project.steps.insert(0, safety_step)

        # UF-04-c-3: verdict_config 生成规则
        # TODO: 根据 intent 类型设置 mode

        return project

    async def _fallback_project(
        self,
        intent: Any,
        knowledge_results: list[dict],
    ) -> TrainingProject:
        """UF-04-b-4: 降级策略"""

        # 从知识库加载评分最高的 SOP
        # 简化版：返回基础项目
        return TrainingProject(
            project_id=f"fallback_{id(intent)}",
            title="标准训练项目",
            description="已为您选取最相近的标准训练方案",
            steps=[
                StepConfig(
                    step_id="step_001",
                    title="基础操作",
                    description="请按照标准流程执行",
                    required_level=1,
                )
            ],
            verdict_config=VerdictConfig(mode="normal"),
        )
