from __future__ import annotations

from app.services.knowledge.file_classifier import FileClassification, classify_file


def test_classify_file_uses_frozen_format_support_matrix() -> None:
    assert classify_file("robot/assembly.SLDASM").kind == FileClassification.ASSEMBLY
    assert classify_file("robot/part.SLDPRT").kind == FileClassification.PART_MODEL
    assert classify_file("robot/preview.glb").kind == FileClassification.VIEWER_ASSET
    assert classify_file("robot/scene.urdf").kind == FileClassification.STRUCTURE
    assert classify_file("robot/manual.pdf").kind == FileClassification.DOCUMENT
    assert classify_file("robot/runtime/demo.py").kind == FileClassification.DEFERRED
    assert classify_file("robot/video/install.mp4").kind == FileClassification.DEFERRED
