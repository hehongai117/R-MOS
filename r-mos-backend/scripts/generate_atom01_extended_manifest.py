#!/usr/bin/env python3
"""
Generate extended assembly_manifest.json for ATOM-01.

Reads existing manifest and adds: parts_registry, display_names,
camera_presets, overview_config, tools, screw_instances, constraints,
explode_offsets.

Usage:
    python scripts/generate_atom01_extended_manifest.py <robot_id>
    python scripts/generate_atom01_extended_manifest.py 1
"""

import json
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Static data migrated from frontend TypeScript files
# ---------------------------------------------------------------------------

DISPLAY_NAMES = {
    "base_link": "髋部底座",
    "torso_link": "躯干总成",
    "torso_shell_front": "躯干前盖",
    "torso_shell_rear": "躯干后盖",
    "torso_shell_lower": "躯干下盖",
    "torso_shell_back_lower": "躯干后下盖",
    "frame_torso_chest": "胸腔框架",
    "torso_motor": "躯干电机",
    "torso_pcb_main": "主控电路板",
    "left_arm_pitch_link": "左肩俯仰",
    "left_arm_roll_link": "左肩横滚",
    "left_arm_yaw_link": "左肩偏航",
    "left_elbow_pitch_link": "左肘俯仰",
    "left_elbow_yaw_link": "左肘偏航",
    "right_arm_pitch_link": "右肩俯仰",
    "right_arm_roll_link": "右肩横滚",
    "right_arm_yaw_link": "右肩偏航",
    "right_elbow_pitch_link": "右肘俯仰",
    "right_elbow_yaw_link": "右肘偏航",
    "left_thigh_yaw_link": "左大腿偏航",
    "left_thigh_roll_link": "左大腿横滚",
    "left_thigh_pitch_link": "左大腿俯仰",
    "left_knee_link": "左膝关节",
    "left_ankle_pitch_link": "左踝俯仰",
    "left_ankle_roll_link": "左踝横滚",
    "right_thigh_yaw_link": "右大腿偏航",
    "right_thigh_roll_link": "右大腿横滚",
    "right_thigh_pitch_link": "右大腿俯仰",
    "right_knee_link": "右膝关节",
    "right_ankle_pitch_link": "右踝俯仰",
    "right_ankle_roll_link": "右踝横滚",
}

# Camera presets from useCameraFocus.ts PART_FOCUS_POSITIONS
CAMERA_PRESETS = {
    "L0_overview": {"position": [1.5, 1.0, 1.5], "target": [0.0, 0.3, 0.0], "fov": 45},
    "base_link": {"position": [0.6, 0.2, 0.6], "target": [0.0, 0.1, 0.0], "fov": 40},
    "torso_link": {"position": [0.6, 0.6, 0.6], "target": [0.0, 0.5, 0.0], "fov": 40},
    "left_arm_pitch_link": {"position": [0.5, 0.6, 0.3], "target": [0.15, 0.55, 0.0], "fov": 40},
    "left_arm_yaw_link": {"position": [0.5, 0.6, 0.3], "target": [0.2, 0.55, 0.0], "fov": 40},
    "right_arm_pitch_link": {"position": [-0.5, 0.6, 0.3], "target": [-0.15, 0.55, 0.0], "fov": 40},
    "right_arm_yaw_link": {"position": [-0.5, 0.6, 0.3], "target": [-0.2, 0.55, 0.0], "fov": 40},
    "left_knee_link": {"position": [0.4, -0.3, 0.4], "target": [0.1, -0.45, 0.0], "fov": 40},
    "right_knee_link": {"position": [-0.4, -0.3, 0.4], "target": [-0.1, -0.45, 0.0], "fov": 40},
    "left_ankle_roll_link": {"position": [0.3, -0.6, 0.3], "target": [0.1, -0.75, 0.0], "fov": 40},
    "right_ankle_roll_link": {"position": [-0.3, -0.6, 0.3], "target": [-0.1, -0.75, 0.0], "fov": 40},
}

# Overview config from assemblyTree.ts ASSEMBLY_GROUPS + partsManifest.ts
OVERVIEW_CONFIG = {
    "overview_nodes": [
        "base_link", "torso_link",
        "left_arm_yaw_link", "left_elbow_yaw_link",
        "right_arm_yaw_link", "right_elbow_yaw_link",
        "left_thigh_pitch_link", "left_knee_link", "left_ankle_roll_link",
        "right_thigh_pitch_link", "right_knee_link", "right_ankle_roll_link",
    ],
    "reference_set": ["base_link", "torso_link"],
    "assembly_groups": {
        "base_link": {
            "display_name": "髋部底座",
            "child_links": ["base_link"],
            "explode_dir": [0, 0, -1],
        },
        "torso_link": {
            "display_name": "躯干",
            "child_links": ["torso_link"],
            "explode_dir": [0, 0, 1],
        },
        "left_arm_yaw_link": {
            "display_name": "左上臂",
            "child_links": ["left_arm_pitch_link", "left_arm_roll_link", "left_arm_yaw_link"],
            "explode_dir": [0, 1, 0],
        },
        "left_elbow_yaw_link": {
            "display_name": "左前臂",
            "child_links": ["left_elbow_pitch_link", "left_elbow_yaw_link"],
            "explode_dir": [0, 1, -1],
        },
        "right_arm_yaw_link": {
            "display_name": "右上臂",
            "child_links": ["right_arm_pitch_link", "right_arm_roll_link", "right_arm_yaw_link"],
            "explode_dir": [0, -1, 0],
        },
        "right_elbow_yaw_link": {
            "display_name": "右前臂",
            "child_links": ["right_elbow_pitch_link", "right_elbow_yaw_link"],
            "explode_dir": [0, -1, -1],
        },
        "left_thigh_pitch_link": {
            "display_name": "左大腿",
            "child_links": ["left_thigh_yaw_link", "left_thigh_roll_link", "left_thigh_pitch_link"],
            "explode_dir": [0, 1, -1],
        },
        "left_knee_link": {
            "display_name": "左小腿",
            "child_links": ["left_knee_link", "left_ankle_pitch_link"],
            "explode_dir": [0, 1, -1],
        },
        "left_ankle_roll_link": {
            "display_name": "左脚",
            "child_links": ["left_ankle_roll_link"],
            "explode_dir": [0, 1, -1],
        },
        "right_thigh_pitch_link": {
            "display_name": "右大腿",
            "child_links": ["right_thigh_yaw_link", "right_thigh_roll_link", "right_thigh_pitch_link"],
            "explode_dir": [0, -1, -1],
        },
        "right_knee_link": {
            "display_name": "右小腿",
            "child_links": ["right_knee_link", "right_ankle_pitch_link"],
            "explode_dir": [0, -1, -1],
        },
        "right_ankle_roll_link": {
            "display_name": "右脚",
            "child_links": ["right_ankle_roll_link"],
            "explode_dir": [0, -1, -1],
        },
    },
}

# Tools from toolData.ts TOOLS
TOOLS = [
    {"id": "hex_2.5", "name": "2.5mm 内六角扳手", "type": "hex_key", "size": "2.5mm", "description": "用于 M3 螺丝"},
    {"id": "hex_3", "name": "3mm 内六角扳手", "type": "hex_key", "size": "3mm", "description": "用于 M4 螺丝"},
    {"id": "hex_4", "name": "4mm 内六角扳手", "type": "hex_key", "size": "4mm", "description": "用于 M5 螺丝"},
    {"id": "hex_5", "name": "5mm 内六角扳手", "type": "hex_key", "size": "5mm", "description": "用于 M6 螺丝"},
    {"id": "torque_wrench", "name": "扭矩扳手", "type": "torque_wrench", "size": "1-10Nm", "description": "精确扭矩控制"},
    {"id": "pliers", "name": "尖嘴钳", "type": "pliers", "size": "通用", "description": "夹持和取出零件"},
]

# ---------------------------------------------------------------------------
# Group assignment for parts_registry
# ---------------------------------------------------------------------------

GROUP_MAP = {
    "base_link": "base",
    "torso_link": "torso",
    "torso_shell_front": "torso",
    "torso_shell_rear": "torso",
    "torso_shell_lower": "torso",
    "torso_shell_back_lower": "torso",
    "frame_torso_chest": "torso",
    "torso_motor": "torso",
    "torso_pcb_main": "torso",
    "left_arm_pitch_link": "left_arm",
    "left_arm_roll_link": "left_arm",
    "left_arm_yaw_link": "left_arm",
    "left_elbow_pitch_link": "left_arm",
    "left_elbow_yaw_link": "left_arm",
    "right_arm_pitch_link": "right_arm",
    "right_arm_roll_link": "right_arm",
    "right_arm_yaw_link": "right_arm",
    "right_elbow_pitch_link": "right_arm",
    "right_elbow_yaw_link": "right_arm",
    "left_thigh_yaw_link": "left_leg",
    "left_thigh_roll_link": "left_leg",
    "left_thigh_pitch_link": "left_leg",
    "left_knee_link": "left_leg",
    "left_ankle_pitch_link": "left_leg",
    "left_ankle_roll_link": "left_leg",
    "right_thigh_yaw_link": "right_leg",
    "right_thigh_roll_link": "right_leg",
    "right_thigh_pitch_link": "right_leg",
    "right_knee_link": "right_leg",
    "right_ankle_pitch_link": "right_leg",
    "right_ankle_roll_link": "right_leg",
}

# Map node category values to BOM category names
CATEGORY_MAP = {
    "link": "frame",
    "frame": "frame",
    "shell": "cover",
    "actuator": "motor",
    "electronics": "pcb",
}


# ---------------------------------------------------------------------------
# Core logic
# ---------------------------------------------------------------------------

def build_parts_registry_from_nodes(nodes: list) -> list:
    """Generate parts_registry from existing manifest nodes."""
    parts = []
    for node in nodes:
        nid = node["id"]
        raw_cat = node.get("category", "link")
        cat = CATEGORY_MAP.get(raw_cat, "frame")
        group = GROUP_MAP.get(nid)
        t = node.get("transform", {})
        pos = t.get("translation", [0, 0, 0])
        display_name = DISPLAY_NAMES.get(nid, node.get("display_name", nid))

        parts.append({
            "id": nid,
            "category": cat,
            "bom_code": f"ATOM-01-{nid.upper().replace('_', '-')}",
            "display_name": display_name,
            "parent_id": node.get("parent_id"),
            "mesh_id": node.get("mesh_id"),
            "local_position": pos,
            "local_rotation": [0, 0, 0],
            "group": group,
        })
    return parts


def extend_manifest(robot_id: str) -> None:
    base_dir = Path(__file__).parent.parent  # r-mos-backend/
    manifest_path = base_dir / "data" / "robot-assets" / robot_id / "manifests" / "assembly_manifest.json"

    if not manifest_path.exists():
        print(f"[ERROR] Manifest not found: {manifest_path}")
        sys.exit(1)

    print(f"[INFO] Reading manifest: {manifest_path}")
    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    nodes = manifest.get("nodes", [])
    print(f"[INFO] Found {len(nodes)} nodes in existing manifest")

    # Only add fields that don't already exist (idempotent)
    if "parts_registry" not in manifest:
        manifest["parts_registry"] = build_parts_registry_from_nodes(nodes)
        print(f"[INFO] Built parts_registry with {len(manifest['parts_registry'])} entries")
    else:
        print(f"[SKIP] parts_registry already present ({len(manifest['parts_registry'])} entries)")

    if "display_names" not in manifest:
        manifest["display_names"] = DISPLAY_NAMES
        print(f"[INFO] Added display_names ({len(DISPLAY_NAMES)} entries)")
    else:
        print(f"[SKIP] display_names already present")

    if "camera_presets" not in manifest:
        manifest["camera_presets"] = CAMERA_PRESETS
        print(f"[INFO] Added camera_presets ({len(CAMERA_PRESETS)} entries)")
    else:
        print(f"[SKIP] camera_presets already present")

    if "overview_config" not in manifest:
        manifest["overview_config"] = OVERVIEW_CONFIG
        print("[INFO] Added overview_config")
    else:
        print("[SKIP] overview_config already present")

    if "tools" not in manifest:
        manifest["tools"] = TOOLS
        print(f"[INFO] Added tools ({len(TOOLS)} entries)")
    else:
        print(f"[SKIP] tools already present")

    for placeholder in ("screw_instances", "constraints", "explode_offsets"):
        if placeholder not in manifest:
            manifest[placeholder] = []
            print(f"[INFO] Added {placeholder} (empty placeholder)")
        else:
            print(f"[SKIP] {placeholder} already present")

    # Write back
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)

    print(f"[OK] Extended manifest written to {manifest_path}")

    # Quick summary
    print()
    print("=== Summary ===")
    print(f"  parts_registry : {len(manifest.get('parts_registry', []))}")
    print(f"  display_names  : {len(manifest.get('display_names', {}))}")
    print(f"  camera_presets : {len(manifest.get('camera_presets', {}))}")
    print(f"  tools          : {len(manifest.get('tools', []))}")
    print(f"  overview_nodes : {len(manifest.get('overview_config', {}).get('overview_nodes', []))}")


def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/generate_atom01_extended_manifest.py <robot_id>")
        print("Example: python scripts/generate_atom01_extended_manifest.py 1")
        sys.exit(1)

    robot_id = sys.argv[1]
    extend_manifest(robot_id)


if __name__ == "__main__":
    main()
