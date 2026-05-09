"""Fault code extractor — uses LLM to extract fault codes from documents."""
import json
import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.analysis_task import AnalysisTask
from app.models.knowledge_document import KnowledgeDocument

try:
    from app.services.llm.router import llm_router
except ImportError:  # pragma: no cover — optional dependency missing in test env
    llm_router = None  # type: ignore[assignment]

logger = logging.getLogger(__name__)

MAX_TOTAL_CONTENT = 8000
MAX_PER_DOC_CONTENT = 2000

FAULT_EXTRACTION_PROMPT = """你是一个机器人故障诊断专家。请从以下文档内容中提取所有故障码、故障类型和症状。

要求：
1. 提取所有可识别的故障码和对应症状
2. 故障码格式：E{{编号}}_{{类型}}（如 E001_OVERHEAT）
3. 每个故障码包含描述和症状列表
4. 标注故障排除难度：beginner/intermediate/advanced

请以 JSON 格式返回：
{{
  "fault_codes": [
    {{
      "fault_type": "故障码",
      "description": "故障描述",
      "symptoms": ["症状1", "症状2"],
      "difficulty": "beginner/intermediate/advanced"
    }}
  ]
}}

文档内容：
{content}
"""


class FaultExtractor:
    async def process(self, task: AnalysisTask, db: AsyncSession) -> dict:
        """从知识文档中提取故障码列表。

        1. 查询 generation_status="ai_draft" 且 robot_model_id 匹配的 KnowledgeDocument
        2. 无文档时返回 {"fault_codes_extracted": 0, "fault_codes": []}
        3. 合并内容（每篇前 2000 字，总不超过 8000）
        4. 调用 LLM 提取
        5. 解析 JSON，失败时优雅降级
        6. 返回 {"fault_codes_extracted": N, "fault_codes": [...]}
        注意：不创建 FaultSOPMapping，只提取信息（sop_id 外键不能为空，留给教师前端手动关联）
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
            logger.info(
                "task=%d robot_model_id=%d: 无 ai_draft 文档，跳过故障码提取",
                task.id, robot_model_id,
            )
            return {"fault_codes_extracted": 0, "fault_codes": []}

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
                        "content": "你是机器人故障诊断专家，输出严格 JSON。",
                    },
                    {
                        "role": "user",
                        "content": FAULT_EXTRACTION_PROMPT.format(content=combined),
                    },
                ],
                temperature=0.3,
                max_tokens=4096,
            )
        except Exception as exc:
            logger.error("task=%d LLM 调用失败: %s", task.id, exc)
            return {"fault_codes_extracted": 0, "fault_codes": [], "error": str(exc)}

        # 5. 解析 JSON
        fault_codes = self._parse_fault_codes(response.content)

        logger.info(
            "task=%d robot_model_id=%d: 提取 %d 个故障码",
            task.id, robot_model_id, len(fault_codes),
        )

        # 6. 返回结果（不写数据库，留给教师前端关联 SOP）
        return {"fault_codes_extracted": len(fault_codes), "fault_codes": fault_codes}

    def _parse_fault_codes(self, llm_content: str) -> list[dict]:
        """解析 LLM 返回的 JSON（处理 markdown code block）。失败时返回 []。"""
        text = llm_content.strip()

        # 处理 markdown code block 包裹
        if text.startswith("```"):
            lines = text.splitlines()
            inner_lines = lines[1:-1] if lines[-1].strip() == "```" else lines[1:]
            text = "\n".join(inner_lines)

        try:
            data = json.loads(text)
        except json.JSONDecodeError as exc:
            logger.warning("故障码提取 JSON 解析失败: %s", exc)
            return []

        fault_codes = data.get("fault_codes", [])
        if not isinstance(fault_codes, list):
            logger.warning("故障码提取结果格式异常: fault_codes 不是列表")
            return []

        return fault_codes
