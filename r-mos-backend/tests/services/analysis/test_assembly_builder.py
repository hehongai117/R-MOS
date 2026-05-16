# tests/services/analysis/test_assembly_builder.py
import pytest
from app.services.analysis.assembly_builder import AssemblyBuilder


@pytest.fixture
def builder():
    return AssemblyBuilder()


def test_find_urdf_in_uploads(builder, tmp_path):
    """Should locate .urdf files in robot's upload directory."""
    upload_dir = tmp_path / "uploads"
    upload_dir.mkdir()
    urdf_file = upload_dir / "robot.urdf"
    urdf_file.write_text('<?xml version="1.0"?><robot name="test"></robot>')
    (upload_dir / "part.stl").write_bytes(b"dummy")

    found = builder._find_urdf_files(str(tmp_path))
    assert len(found) == 1
    assert found[0].endswith("robot.urdf")


def test_resolve_mesh_paths(builder, tmp_path):
    """Should resolve URDF mesh references to actual files."""
    uploads_dir = tmp_path / "uploads"
    uploads_dir.mkdir()
    (uploads_dir / "base_link.STL").write_bytes(b"stl data")
    (uploads_dir / "arm_link.STL").write_bytes(b"stl data")

    mesh_refs = ["../meshes/base_link.STL", "../meshes/arm_link.STL"]
    resolved = builder._resolve_mesh_files(mesh_refs, str(tmp_path))

    assert "base_link.STL" in resolved
    assert "arm_link.STL" in resolved
    assert resolved["base_link.STL"].endswith("base_link.STL")
