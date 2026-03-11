from __future__ import annotations

from dataclasses import dataclass

from app.models.robot_project import RobotProject
from app.services.knowledge.file_classifier import ClassifiedFile, FileClassification


@dataclass(frozen=True)
class ChunkDraft:
    source_id: str
    content: str
    metadata: dict


class DocumentChunker:
    def chunk(
        self,
        *,
        project: RobotProject,
        relative_path: str,
        classified: ClassifiedFile,
        content: bytes,
    ) -> list[ChunkDraft]:
        base_metadata = {
            "robot_project_id": project.id,
            "robot_key": project.robot_key,
            "brand": project.brand,
            "model": project.model,
            "file_kind": classified.kind.value,
            "source_path": relative_path,
            "citability": classified.kind in {FileClassification.DOCUMENT, FileClassification.STRUCTURE},
        }

        if classified.kind is FileClassification.DOCUMENT:
            text = self._decode_text(content)
            return [
                ChunkDraft(
                    source_id=relative_path,
                    content=text[:4000],
                    metadata=base_metadata,
                )
            ]

        if classified.kind in {FileClassification.ASSEMBLY, FileClassification.PART_MODEL, FileClassification.STRUCTURE, FileClassification.VIEWER_ASSET}:
            summary = f"{classified.kind.value}: {relative_path}"
            return [
                ChunkDraft(
                    source_id=relative_path,
                    content=summary,
                    metadata=base_metadata,
                )
            ]

        return []

    def _decode_text(self, content: bytes) -> str:
        for encoding in ("utf-8", "utf-8-sig", "gb18030", "latin-1"):
            try:
                return content.decode(encoding)
            except UnicodeDecodeError:
                continue
        return ""
