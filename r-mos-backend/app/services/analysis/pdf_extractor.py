"""PDF document extractor — splits PDF into knowledge document chunks."""
import logging
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

try:
    import fitz  # PyMuPDF
except ImportError:
    fitz = None

from app.models.analysis_task import AnalysisTask
from app.models.robot_asset import RobotAsset, AssetType
from app.models.knowledge_document import KnowledgeDocument
from app.services.storage.file_storage import LocalFileStorage

logger = logging.getLogger(__name__)

MIN_CHUNK_LENGTH = 30
MAX_CHUNK_LENGTH = 4000


class PdfExtractor:
    def __init__(self):
        self.storage = LocalFileStorage()

    async def process(self, task: AnalysisTask, db: AsyncSession) -> dict:
        """提取机器人所有 PDF 资产的文本，按页面切片存入 KnowledgeDocument。

        Returns:
            dict with keys: documents_created (int), files_processed (int)
        """
        # 1. 查询该机器人的所有 UPLOAD_ORIGINAL 资产
        result = await db.execute(
            select(RobotAsset).where(
                RobotAsset.robot_model_id == task.robot_model_id,
                RobotAsset.asset_type == AssetType.UPLOAD_ORIGINAL,
            )
        )
        assets = result.scalars().all()

        # 2. 过滤出 .pdf 文件
        pdf_assets = [a for a in assets if a.file_path.lower().endswith(".pdf")]

        documents_created = 0
        files_processed = 0

        # 3. 对每个 PDF：提取切片并创建 KnowledgeDocument
        for asset in pdf_assets:
            try:
                # file_path 格式为 "10/uploads/manual.pdf"，去掉第一段再调用 get_full_path
                rel = asset.file_path.split("/", 1)[-1]
                full_path = self.storage.get_full_path(asset.robot_model_id, rel)
            except (ValueError, Exception) as exc:
                logger.warning("跳过资产 %s，路径解析失败：%s", asset.file_path, exc)
                continue

            try:
                chunks = self._extract_text_from_pdf(full_path)
            except Exception as exc:
                logger.warning("PDF 提取失败 %s：%s", full_path, exc)
                continue

            files_processed += 1

            # 4. 每个切片创建 KnowledgeDocument
            for chunk in chunks:
                doc = KnowledgeDocument(
                    title=chunk["title"],
                    content=chunk["content"],
                    doc_type="manual",
                    generation_status="ai_draft",
                    robot_model_id=task.robot_model_id,
                    status="PENDING",
                )
                db.add(doc)
                documents_created += 1

        # 5. flush 使插入生效（不提交事务，由调用方决定）
        await db.flush()

        logger.info(
            "PdfExtractor: robot_model_id=%s，处理 %d 个文件，创建 %d 个文档",
            task.robot_model_id,
            files_processed,
            documents_created,
        )

        # 6. 返回统计
        return {"documents_created": documents_created, "files_processed": files_processed}

    def _extract_text_from_pdf(self, pdf_path: str) -> list[dict]:
        """从 PDF 文件按页面提取文本切片。

        Args:
            pdf_path: PDF 文件的绝对路径

        Returns:
            list of dicts with keys: title, content

        Raises:
            RuntimeError: 如果 PyMuPDF 未安装
        """
        if fitz is None:
            raise RuntimeError(
                "PyMuPDF 未安装，请执行 pip install PyMuPDF"
            )

        chunks = []

        with fitz.open(pdf_path) as doc:
            # doc_title 优先使用元数据 title，否则用文件名
            raw_title = doc.metadata.get("title", "").strip() if doc.metadata else ""
            doc_title = raw_title if raw_title else Path(pdf_path).stem

            for page_num, page in enumerate(doc, start=1):
                text = page.get_text().strip()

                # 跳过长度不足的页面（空白页 / 纯图片页）
                if len(text) < MIN_CHUNK_LENGTH:
                    continue

                # 截断超长内容
                if len(text) > MAX_CHUNK_LENGTH:
                    text = text[:MAX_CHUNK_LENGTH]

                chunks.append(
                    {
                        "title": f"{doc_title} — 第 {page_num} 页",
                        "content": text,
                    }
                )

        return chunks
