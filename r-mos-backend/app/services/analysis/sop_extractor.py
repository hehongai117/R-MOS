"""SOP extractor — uses LLM to extract maintenance procedures from documents."""
import json
import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.analysis_task import AnalysisTask
from app.models.knowledge_document import KnowledgeDocument
from app.models.sop import SOP, SOPStep

try:
    from app.services.llm.router import llm_router
except ImportError:  # pragma: no cover — optional dependency (openai) missing in test env
    llm_router = None  # type: ignore[assignment]

logger = logging.getLogger(__name__)

MAX_TOTAL_CONTENT = 8000
MAX_PER_DOC_CONTENT = 2000

SOP_EXTRACTION_PROMPT = """你是一个机器人维保手册分析专家。请从以下文档内容中提取标准操作流程（SOP）。

要求：
1. 提取所有可识别的维保操作流程
2. 每个 SOP 包含名称、描述、分类、难度、预估时间
3. 每个 SOP 包含详细步骤，每个步骤包含标题、描述、期望操作类型
4. 期望操作类型：verify（验证）、remove（拆卸）、install（安装）、adjust（调整）、inspect（检查）、connect（连接）、test（测试）
5. 标记关键安全步骤（is_critical=true）

请以 JSON 格式返回：
{{
  "sops": [
    {{
      "name": "流程名称",
      "description": "流程描述",
      "category": "分类（维修/检查/保养/安装）",
      "difficulty_level": "low/medium/high",
      "estimated_time": 秒数,
      "steps": [
        {{
          "title": "步骤标题",
          "description": "步骤详细描述",
          "expected_action": "操作类型",
          "is_critical": true/false
        }}
      ]
    }}
  ]
}}

文档内容：
{content}
"""


class SopExtractor:
    async def process(self, task: AnalysisTask, db: AsyncSession) -> dict:
        """从知识文档中提取 SOP 草稿。

        1. 查询 generation_status="ai_draft" 且 robot_model_id=task.robot_model_id 的文档
        2. 无文档时返回空结果
        3. 合并文档内容，总长度限制 8000 字符
        4. 调用 LLM 提取 SOP
        5. 解析并持久化 SOP/SOPStep
        """
        robot_model_id = task.robot_model_id

        # 1. 查询关联文档
        stmt = select(KnowledgeDocument).where(
            KnowledgeDocument.robot_model_id == robot_model_id,
            KnowledgeDocument.generation_status == "ai_draft",
        )
        result = await db.execute(stmt)
        documents = result.scalars().all()

        # 2. 无文档时返回空结果
        if not documents:
            logger.info("task=%d robot_model_id=%d: 无 ai_draft 文档，跳过 SOP 提取", task.id, robot_model_id)
            return {"sops_created": 0, "steps_created": 0}

        # 3. 合并文档内容，总长度不超过 8000 字符
        parts = [doc.content[:MAX_PER_DOC_CONTENT] for doc in documents]
        combined = "\n\n---\n\n".join(parts)
        if len(combined) > MAX_TOTAL_CONTENT:
            combined = combined[:MAX_TOTAL_CONTENT]

        # 4. 调用 LLM
        try:
            response = await llm_router.chat_with_fallback(
                messages=[
                    {
                        "role": "system",
                        "content": "你是机器人维保手册分析专家，输出严格 JSON。",
                    },
                    {
                        "role": "user",
                        "content": SOP_EXTRACTION_PROMPT.format(content=combined),
                    },
                ],
                temperature=0.3,
                max_tokens=4096,
            )
        except Exception as exc:
            logger.error("task=%d LLM 调用失败: %s", task.id, exc)
            return {"sops_created": 0, "steps_created": 0, "error": str(exc)}

        # 5. 解析并保存
        return self._parse_and_save(response.content, robot_model_id, db)

    def _parse_and_save(self, llm_content: str, robot_model_id: int, db) -> dict:
        """解析 LLM 返回的 JSON 并创建 SOP/SOPStep 对象。"""
        # 处理 markdown code block 包裹
        text = llm_content.strip()
        if text.startswith("```"):
            lines = text.splitlines()
            # 去除首行（```json 或 ```）和末行（```）
            inner_lines = lines[1:-1] if lines[-1].strip() == "```" else lines[1:]
            text = "\n".join(inner_lines)

        try:
            data = json.loads(text)
        except json.JSONDecodeError as exc:
            logger.warning("SOP 提取 JSON 解析失败: %s", exc)
            return {"sops_created": 0, "steps_created": 0, "parse_error": True}

        sops_list = data.get("sops", [])
        total_sops = 0
        total_steps = 0

        for sop_data in sops_list:
            sop = SOP(
                name=sop_data.get("name", "未命名 SOP"),
                description=sop_data.get("description"),
                applicable_model="",  # 必填字段，传空字符串
                category=sop_data.get("category"),
                difficulty_level=sop_data.get("difficulty_level", "medium"),
                estimated_time=sop_data.get("estimated_time"),
                robot_model_id=robot_model_id,
            )

            steps_data = sop_data.get("steps", [])
            for idx, step_data in enumerate(steps_data):
                step = SOPStep(
                    sop=sop,
                    step_index=idx,
                    title=step_data.get("title", f"步骤 {idx + 1}"),
                    description=step_data.get("description", ""),
                    expected_action=step_data.get("expected_action", "inspect"),
                    is_critical=step_data.get("is_critical", False),
                )
                sop.steps.append(step)
                total_steps += 1

            db.add(sop)
            total_sops += 1

        logger.info(
            "robot_model_id=%d: 提取 %d 个 SOP，共 %d 个步骤",
            robot_model_id, total_sops, total_steps,
        )
        return {"sops_created": total_sops, "steps_created": total_steps}
