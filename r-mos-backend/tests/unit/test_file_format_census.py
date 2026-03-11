from __future__ import annotations

from pathlib import Path

from app.services.knowledge.format_support_matrix import (
    FormatStrategy,
    get_format_strategy,
)


def test_format_support_matrix_covers_primary_robot_package_formats() -> None:
    assert get_format_strategy(".sldasm") is FormatStrategy.METADATA_ONLY
    assert get_format_strategy(".sldprt") is FormatStrategy.METADATA_ONLY
    assert get_format_strategy(".step") is FormatStrategy.METADATA_ONLY
    assert get_format_strategy(".stp") is FormatStrategy.METADATA_ONLY
    assert get_format_strategy(".stl") is FormatStrategy.METADATA_ONLY
    assert get_format_strategy(".obj") is FormatStrategy.METADATA_ONLY
    assert get_format_strategy(".dae") is FormatStrategy.METADATA_ONLY
    assert get_format_strategy(".glb") is FormatStrategy.VIEWER_READY
    assert get_format_strategy(".urdf") is FormatStrategy.STRUCTURE_SOURCE
    assert get_format_strategy(".xml") is FormatStrategy.STRUCTURE_SOURCE

    assert get_format_strategy(".pdf") is FormatStrategy.TEXT_EXTRACT
    assert get_format_strategy(".md") is FormatStrategy.TEXT_EXTRACT
    assert get_format_strategy(".txt") is FormatStrategy.TEXT_EXTRACT

    assert get_format_strategy(".mp4") is FormatStrategy.DEFERRED
    assert get_format_strategy(".pt") is FormatStrategy.DEFERRED
    assert get_format_strategy(".py") is FormatStrategy.DEFERRED
    assert get_format_strategy(".so") is FormatStrategy.DEFERRED


def test_format_census_document_exists_and_mentions_primary_families() -> None:
    repo_root = Path(__file__).resolve().parents[3]
    census_doc = repo_root / "docs" / "development" / "2026-03-09-robot-project-format-census.md"
    assert census_doc.exists()

    content = census_doc.read_text(encoding="utf-8")
    assert "SLDASM" in content
    assert "SLDPRT" in content
    assert "URDF" in content
    assert "GLB" in content
    assert "MP4" in content
