from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

from app.services.knowledge.format_support_matrix import FormatStrategy, get_format_strategy


class FileClassification(StrEnum):
    ARCHIVE = "archive"
    ASSEMBLY = "assembly"
    PART_MODEL = "part_model"
    DOCUMENT = "document"
    STRUCTURE = "structure"
    VIEWER_ASSET = "viewer_asset"
    DEFERRED = "deferred"


@dataclass(frozen=True)
class ClassifiedFile:
    filename: str
    extension: str
    strategy: FormatStrategy
    kind: FileClassification


def classify_file(filename: str) -> ClassifiedFile:
    extension = Path(filename).suffix.lower()

    if extension == ".zip":
        return ClassifiedFile(
            filename=filename,
            extension=extension,
            strategy=FormatStrategy.DEFERRED,
            kind=FileClassification.ARCHIVE,
        )

    strategy = get_format_strategy(extension)

    if extension == ".sldasm":
        kind = FileClassification.ASSEMBLY
    elif extension in {".sldprt", ".step", ".stp", ".stl", ".obj", ".dae", ".wrl", ".usda", ".mtl"}:
        kind = FileClassification.PART_MODEL
    elif strategy is FormatStrategy.TEXT_EXTRACT:
        kind = FileClassification.DOCUMENT
    elif strategy is FormatStrategy.STRUCTURE_SOURCE:
        kind = FileClassification.STRUCTURE
    elif strategy is FormatStrategy.VIEWER_READY:
        kind = FileClassification.VIEWER_ASSET
    else:
        kind = FileClassification.DEFERRED

    return ClassifiedFile(
        filename=filename,
        extension=extension,
        strategy=strategy,
        kind=kind,
    )
