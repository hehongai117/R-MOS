from __future__ import annotations

import importlib.util
from pathlib import Path


PROJECT_ROOT = Path("/Users/xuhehong/Desktop/r-mos")
SCRIPT_PATH = PROJECT_ROOT / "scripts" / "export_atom01_assembly_manifest.py"


def load_export_module():
    spec = importlib.util.spec_from_file_location("export_atom01_assembly_manifest", SCRIPT_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_exporter_reads_blueprints_and_emits_torso_screw_level_manifest():
    module = load_export_module()

    assembly_manifest = module.load_blueprint(module.ASSEMBLY_BLUEPRINT_PATH)
    explode_manifest = module.load_blueprint(module.EXPLODE_BLUEPRINT_PATH)

    assert assembly_manifest["robotId"] == "atom01"
    assert explode_manifest["robotId"] == "atom01"
    assert module.ASSEMBLY_MANIFEST == assembly_manifest
    assert module.EXPLODE_MANIFEST == explode_manifest

    torso_children = [
        node["id"]
        for node in assembly_manifest["nodes"]
        if node["parent_id"] == "torso_link"
    ]
    assert "frame_torso_chest" in torso_children
    assert "torso_motor" in torso_children
    assert "torso_pcb_main" in torso_children

    torso_fasteners = [
        instance["id"]
        for instance in assembly_manifest["fastener_instances"]
        if instance["id"].startswith("screw_torso_")
    ]
    assert len(torso_fasteners) >= 14
    assert "screw_torso_m3x10_001" in torso_fasteners
    assert "screw_torso_m3x10_008" in torso_fasteners
    assert "screw_torso_m4x12_001" in torso_fasteners
    assert "screw_torso_m4x12_006" in torso_fasteners
