"""Robot project package format support matrix.

Task 0 output:
- freeze which file families are supported in phase 1
- give the classifier a deterministic strategy lookup
- prevent later ingest code from assuming every discovered format is parseable
"""
from __future__ import annotations

from enum import StrEnum


class FormatStrategy(StrEnum):
    TEXT_EXTRACT = "text_extract"
    STRUCTURE_SOURCE = "structure_source"
    VIEWER_READY = "viewer_ready"
    METADATA_ONLY = "metadata_only"
    DEFERRED = "deferred"


FORMAT_SUPPORT_MATRIX: dict[str, FormatStrategy] = {
    # Text/document sources
    ".md": FormatStrategy.TEXT_EXTRACT,
    ".txt": FormatStrategy.TEXT_EXTRACT,
    ".pdf": FormatStrategy.TEXT_EXTRACT,
    ".html": FormatStrategy.TEXT_EXTRACT,
    ".json": FormatStrategy.TEXT_EXTRACT,
    ".yaml": FormatStrategy.TEXT_EXTRACT,
    ".yml": FormatStrategy.TEXT_EXTRACT,

    # Structured robot description sources
    ".urdf": FormatStrategy.STRUCTURE_SOURCE,
    ".xml": FormatStrategy.STRUCTURE_SOURCE,

    # Viewer-ready assets already compatible with current frontend
    ".glb": FormatStrategy.VIEWER_READY,

    # CAD / mesh inputs that phase 1 only indexes via metadata and file graph
    ".sldasm": FormatStrategy.METADATA_ONLY,
    ".sldprt": FormatStrategy.METADATA_ONLY,
    ".slddrw": FormatStrategy.METADATA_ONLY,
    ".step": FormatStrategy.METADATA_ONLY,
    ".stp": FormatStrategy.METADATA_ONLY,
    ".stl": FormatStrategy.METADATA_ONLY,
    ".obj": FormatStrategy.METADATA_ONLY,
    ".dae": FormatStrategy.METADATA_ONLY,
    ".wrl": FormatStrategy.METADATA_ONLY,
    ".usda": FormatStrategy.METADATA_ONLY,
    ".mtl": FormatStrategy.METADATA_ONLY,
    ".png": FormatStrategy.METADATA_ONLY,
    ".jpg": FormatStrategy.METADATA_ONLY,
    ".jpeg": FormatStrategy.METADATA_ONLY,
    ".hdr": FormatStrategy.METADATA_ONLY,

    # Explicitly out of phase 1 scope
    ".mp4": FormatStrategy.DEFERRED,
    ".pt": FormatStrategy.DEFERRED,
    ".py": FormatStrategy.DEFERRED,
    ".so": FormatStrategy.DEFERRED,
    ".sample": FormatStrategy.DEFERRED,
    ".pyc": FormatStrategy.DEFERRED,
    ".tmp": FormatStrategy.DEFERRED,
    ".p2m": FormatStrategy.DEFERRED,
    ".p2s": FormatStrategy.DEFERRED,
    ".cwr": FormatStrategy.DEFERRED,
}


def get_format_strategy(extension: str) -> FormatStrategy:
    normalized = extension.strip().lower()
    if not normalized:
        return FormatStrategy.DEFERRED
    if not normalized.startswith("."):
        normalized = f".{normalized}"
    return FORMAT_SUPPORT_MATRIX.get(normalized, FormatStrategy.DEFERRED)
