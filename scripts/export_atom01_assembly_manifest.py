#!/usr/bin/env python3
"""Export ATOM01 assembly/explode manifests from validated blueprint files."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ATOM01_DIR = PROJECT_ROOT / "r-mos-frontend" / "public" / "models" / "robots" / "atom01"
DATA_DIR = PROJECT_ROOT / "scripts" / "data" / "atom01"

ASSEMBLY_BLUEPRINT_PATH = DATA_DIR / "assembly_blueprint.json"
EXPLODE_BLUEPRINT_PATH = DATA_DIR / "explode_blueprint.json"
ASSEMBLY_PATH = ATOM01_DIR / "assembly_manifest.json"
EXPLODE_PATH = ATOM01_DIR / "explode_manifest.json"


def load_blueprint(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def expect(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def expect_transform(transform: Any, label: str) -> None:
    expect(isinstance(transform, dict), f"{label} transform must be an object")
    for field, size in (("translation", 3), ("rotation_quat", 4), ("scale", 3)):
        value = transform.get(field)
        expect(isinstance(value, list) and len(value) == size, f"{label} transform.{field} must be length {size}")
        expect(all(isinstance(entry, (int, float)) for entry in value), f"{label} transform.{field} must be numeric")


def validate_assembly_manifest(manifest: dict[str, Any]) -> None:
    expect(isinstance(manifest.get("robotId"), str), "assembly robotId must be a string")
    expect(isinstance(manifest.get("rootNodeId"), str), "assembly rootNodeId must be a string")
    mesh_catalog = manifest.get("mesh_catalog")
    expect(isinstance(mesh_catalog, dict) and mesh_catalog, "assembly mesh_catalog must be a non-empty object")

    nodes = manifest.get("nodes")
    expect(isinstance(nodes, list) and nodes, "assembly nodes must be a non-empty array")
    node_ids = {node.get("id") for node in nodes if isinstance(node, dict)}
    expect(manifest["rootNodeId"] in node_ids, "assembly rootNodeId must exist in nodes")

    for node in nodes:
        expect(isinstance(node, dict), "assembly node must be an object")
        node_id = node.get("id")
        expect(isinstance(node_id, str) and node_id, "assembly node id must be a non-empty string")
        parent_id = node.get("parent_id")
        expect(parent_id is None or parent_id in node_ids, f"assembly node {node_id} parent_id must reference a node")
        mesh_id = node.get("mesh_id")
        expect(mesh_id is None or mesh_id in mesh_catalog, f"assembly node {node_id} mesh_id must exist in mesh_catalog")
        children = node.get("children", [])
        expect(isinstance(children, list), f"assembly node {node_id} children must be an array")
        expect(all(isinstance(child, str) and child in node_ids for child in children), f"assembly node {node_id} children must reference nodes")
        expect_transform(node.get("transform"), f"assembly node {node_id}")

    fasteners = manifest.get("fastener_instances")
    expect(isinstance(fasteners, list), "assembly fastener_instances must be an array")
    for fastener in fasteners:
        expect(isinstance(fastener, dict), "assembly fastener must be an object")
        fastener_id = fastener.get("id")
        expect(isinstance(fastener_id, str) and fastener_id, "assembly fastener id must be a non-empty string")
        expect(fastener.get("parent_id") in node_ids, f"assembly fastener {fastener_id} parent_id must reference a node")
        expect(fastener.get("mesh_id") in mesh_catalog, f"assembly fastener {fastener_id} mesh_id must exist in mesh_catalog")
        expect_transform(fastener.get("transform"), f"assembly fastener {fastener_id}")

    torso_fasteners = [item for item in fasteners if isinstance(item, dict) and str(item.get("id", "")).startswith("screw_torso_")]
    expect(len(torso_fasteners) >= 14, "assembly manifest must include at least 14 torso screw instances")

    for mesh_id, mesh_path in mesh_catalog.items():
        expect(isinstance(mesh_path, str) and mesh_path.startswith("/models/"), f"mesh_catalog.{mesh_id} must be a public /models path")
        relative_path = mesh_path.removeprefix("/")
        expect((PROJECT_ROOT / "r-mos-frontend" / "public" / relative_path).exists(), f"mesh asset missing for {mesh_id}: {mesh_path}")


def validate_explode_manifest(manifest: dict[str, Any], assembly_manifest: dict[str, Any]) -> None:
    expect(isinstance(manifest.get("robotId"), str), "explode robotId must be a string")
    node_ids = {
        node["id"]
        for node in assembly_manifest.get("nodes", [])
        if isinstance(node, dict) and isinstance(node.get("id"), str)
    }

    views = manifest.get("views")
    expect(isinstance(views, list) and views, "explode views must be a non-empty array")
    for view in views:
        expect(isinstance(view, dict), "explode view must be an object")
        view_id = view.get("id")
        expect(isinstance(view_id, str) and view_id, "explode view id must be a non-empty string")
        expect(view.get("focus_node_id") in node_ids, f"explode view {view_id} focus_node_id must reference a node")
        camera = view.get("camera")
        expect(isinstance(camera, dict), f"explode view {view_id} camera must be an object")
        expect(camera.get("projection") in {"orthographic", "perspective"}, f"explode view {view_id} projection is invalid")
        for field in ("position", "target"):
            value = camera.get(field)
            expect(isinstance(value, list) and len(value) == 3, f"explode view {view_id} camera.{field} must be length 3")
            expect(all(isinstance(entry, (int, float)) for entry in value), f"explode view {view_id} camera.{field} must be numeric")

    sequences = manifest.get("sequences")
    expect(isinstance(sequences, list) and sequences, "explode sequences must be a non-empty array")
    for sequence in sequences:
        expect(isinstance(sequence, dict), "explode sequence must be an object")
        sequence_id = sequence.get("id")
        expect(isinstance(sequence_id, str) and sequence_id, "explode sequence id must be a non-empty string")
        expect(isinstance(sequence.get("step_index"), int), f"explode sequence {sequence_id} step_index must be an int")
        node_refs = sequence.get("node_ids")
        expect(isinstance(node_refs, list) and node_refs, f"explode sequence {sequence_id} node_ids must be a non-empty array")
        expect(all(isinstance(node_id, str) and node_id in node_ids for node_id in node_refs), f"explode sequence {sequence_id} node_ids must reference nodes")
        expect(sequence.get("anchor_node_id") in node_ids, f"explode sequence {sequence_id} anchor_node_id must reference a node")
        direction = sequence.get("direction")
        expect(isinstance(direction, list) and len(direction) == 3, f"explode sequence {sequence_id} direction must be length 3")
        expect(all(isinstance(entry, (int, float)) for entry in direction), f"explode sequence {sequence_id} direction must be numeric")
        expect(isinstance(sequence.get("distance"), (int, float)), f"explode sequence {sequence_id} distance must be numeric")


ASSEMBLY_MANIFEST = load_blueprint(ASSEMBLY_BLUEPRINT_PATH)
EXPLODE_MANIFEST = load_blueprint(EXPLODE_BLUEPRINT_PATH)


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    validate_assembly_manifest(ASSEMBLY_MANIFEST)
    validate_explode_manifest(EXPLODE_MANIFEST, ASSEMBLY_MANIFEST)
    ATOM01_DIR.mkdir(parents=True, exist_ok=True)
    write_json(ASSEMBLY_PATH, ASSEMBLY_MANIFEST)
    write_json(EXPLODE_PATH, EXPLODE_MANIFEST)
    print(f"wrote {ASSEMBLY_PATH}")
    print(f"wrote {EXPLODE_PATH}")


if __name__ == "__main__":
    main()
