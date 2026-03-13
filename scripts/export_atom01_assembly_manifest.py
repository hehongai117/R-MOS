#!/usr/bin/env python3
"""Write the current ATOM01 static assembly/explode manifests to the public model directory."""

from __future__ import annotations

import json
from pathlib import Path


PROJECT_ROOT = Path("/Users/xuhehong/Desktop/r-mos")
ATOM01_DIR = PROJECT_ROOT / "r-mos-frontend" / "public" / "models" / "robots" / "atom01"
ASSEMBLY_PATH = ATOM01_DIR / "assembly_manifest.json"
EXPLODE_PATH = ATOM01_DIR / "explode_manifest.json"


ASSEMBLY_MANIFEST = {
    "version": "2026-03-13",
    "robotId": "atom01",
    "rootNodeId": "base_link",
    "mesh_catalog": {
        "base_link_mesh": "/models/robots/atom01/base_link.glb",
        "torso_link_mesh": "/models/robots/atom01/torso_link.glb",
        "left_arm_pitch_link_mesh": "/models/robots/atom01/left_arm_pitch_link.glb",
        "right_arm_pitch_link_mesh": "/models/robots/atom01/right_arm_pitch_link.glb",
        "left_knee_link_mesh": "/models/robots/atom01/left_knee_link.glb",
        "right_knee_link_mesh": "/models/robots/atom01/right_knee_link.glb",
        "torso_shell_front_mesh": "/models/parts/frames/胸腔胸部.glb",
        "torso_shell_rear_mesh": "/models/parts/frames/胸腔夹板后.glb",
        "torso_bracket_mesh": "/models/parts/frames/胸腔前后夹板.glb",
        "left_arm_pitch_shell_mesh": "/models/parts/frames/肩膀.glb",
        "left_arm_pitch_bracket_mesh": "/models/parts/frames/肩部固定件数量2.glb",
        "right_arm_pitch_shell_mesh": "/models/parts/frames/肩膀_2.glb",
        "right_arm_pitch_bracket_mesh": "/models/parts/frames/肩部固定件数量2_2.glb",
        "left_knee_frame_mesh": "/models/parts/frames/小腿.glb",
        "left_knee_calibration_mesh": "/models/parts/calibration/膝盖标定数量2.glb",
        "right_knee_frame_mesh": "/models/parts/frames/小腿_1.glb",
        "right_knee_calibration_mesh": "/models/parts/calibration/膝盖标定数量2_1.glb",
        "fastener_m4x12_mesh": "/models/parts/screws/内六角圆柱头螺钉M4x12.glb",
        "fastener_m4x8_mesh": "/models/parts/screws/内六角圆柱头螺钉M4x8.glb",
        "fastener_m5x10_mesh": "/models/parts/screws/内六角圆柱头螺钉M5x10.glb",
    },
    "nodes": [
        {
            "id": "base_link",
            "parent_id": None,
            "children": ["torso_link", "left_knee_link", "right_knee_link"],
            "mesh_id": "base_link_mesh",
            "display_name": "底座总成",
            "category": "link",
            "link_name": "base_link",
            "transform": {
                "translation": [0, 0, 0],
                "rotation_quat": [0, 0, 0, 1],
                "scale": [1, 1, 1],
            },
        },
        {
            "id": "torso_link",
            "parent_id": "base_link",
            "children": ["torso_shell_front", "torso_shell_rear", "torso_bracket", "left_arm_pitch_link", "right_arm_pitch_link"],
            "mesh_id": "torso_link_mesh",
            "display_name": "躯干总成",
            "category": "link",
            "link_name": "torso_link",
            "transform": {
                "translation": [-0.028, 0, 0.067],
                "rotation_quat": [0, 0, 0, 1],
                "scale": [1, 1, 1],
            },
        },
        {
            "id": "torso_shell_front",
            "parent_id": "torso_link",
            "children": [],
            "mesh_id": "torso_shell_front_mesh",
            "display_name": "躯干前盖",
            "category": "frame",
            "link_name": "torso_link",
            "transform": {
                "translation": [0.008, 0, 0.014],
                "rotation_quat": [0, 0, 0, 1],
                "scale": [1, 1, 1],
            },
        },
        {
            "id": "torso_shell_rear",
            "parent_id": "torso_link",
            "children": [],
            "mesh_id": "torso_shell_rear_mesh",
            "display_name": "躯干后盖",
            "category": "frame",
            "link_name": "torso_link",
            "transform": {
                "translation": [-0.01, 0, -0.012],
                "rotation_quat": [0, 0, 0, 1],
                "scale": [1, 1, 1],
            },
        },
        {
            "id": "torso_bracket",
            "parent_id": "torso_link",
            "children": [],
            "mesh_id": "torso_bracket_mesh",
            "display_name": "躯干连接夹板",
            "category": "frame",
            "link_name": "torso_link",
            "transform": {
                "translation": [0, 0, 0.004],
                "rotation_quat": [0, 0, 0, 1],
                "scale": [1, 1, 1],
            },
        },
        {
            "id": "left_arm_pitch_link",
            "parent_id": "torso_link",
            "children": ["left_arm_pitch_shell", "left_arm_pitch_bracket"],
            "mesh_id": "left_arm_pitch_link_mesh",
            "display_name": "左肩俯仰总成",
            "category": "link",
            "link_name": "left_arm_pitch_link",
            "transform": {
                "translation": [0, 0.122, 0.206],
                "rotation_quat": [0, 0, 0, 1],
                "scale": [1, 1, 1],
            },
        },
        {
            "id": "left_arm_pitch_shell",
            "parent_id": "left_arm_pitch_link",
            "children": [],
            "mesh_id": "left_arm_pitch_shell_mesh",
            "display_name": "左肩壳体",
            "category": "frame",
            "link_name": "left_arm_pitch_link",
            "transform": {
                "translation": [0.012, 0.008, 0],
                "rotation_quat": [0, 0, 0, 1],
                "scale": [1, 1, 1],
            },
        },
        {
            "id": "left_arm_pitch_bracket",
            "parent_id": "left_arm_pitch_link",
            "children": [],
            "mesh_id": "left_arm_pitch_bracket_mesh",
            "display_name": "左肩固定件",
            "category": "frame",
            "link_name": "left_arm_pitch_link",
            "transform": {
                "translation": [0.016, 0.024, -0.004],
                "rotation_quat": [0, 0, 0, 1],
                "scale": [1, 1, 1],
            },
        },
        {
            "id": "right_arm_pitch_link",
            "parent_id": "torso_link",
            "children": ["right_arm_pitch_shell", "right_arm_pitch_bracket"],
            "mesh_id": "right_arm_pitch_link_mesh",
            "display_name": "右肩俯仰总成",
            "category": "link",
            "link_name": "right_arm_pitch_link",
            "transform": {
                "translation": [0, -0.122, 0.206],
                "rotation_quat": [0, 0, 0, 1],
                "scale": [1, 1, 1],
            },
        },
        {
            "id": "right_arm_pitch_shell",
            "parent_id": "right_arm_pitch_link",
            "children": [],
            "mesh_id": "right_arm_pitch_shell_mesh",
            "display_name": "右肩壳体",
            "category": "frame",
            "link_name": "right_arm_pitch_link",
            "transform": {
                "translation": [0.012, -0.008, 0],
                "rotation_quat": [0, 0, 0, 1],
                "scale": [1, 1, 1],
            },
        },
        {
            "id": "right_arm_pitch_bracket",
            "parent_id": "right_arm_pitch_link",
            "children": [],
            "mesh_id": "right_arm_pitch_bracket_mesh",
            "display_name": "右肩固定件",
            "category": "frame",
            "link_name": "right_arm_pitch_link",
            "transform": {
                "translation": [0.016, -0.024, -0.004],
                "rotation_quat": [0, 0, 0, 1],
                "scale": [1, 1, 1],
            },
        },
        {
            "id": "left_knee_link",
            "parent_id": "base_link",
            "children": ["left_knee_frame", "left_knee_calibration"],
            "mesh_id": "left_knee_link_mesh",
            "display_name": "左膝总成",
            "category": "link",
            "link_name": "left_knee_link",
            "transform": {
                "translation": [-0.089, 0.0725, -0.33],
                "rotation_quat": [0, 0, 0, 1],
                "scale": [1, 1, 1],
            },
        },
        {
            "id": "left_knee_frame",
            "parent_id": "left_knee_link",
            "children": [],
            "mesh_id": "left_knee_frame_mesh",
            "display_name": "左膝小腿结构件",
            "category": "frame",
            "link_name": "left_knee_link",
            "transform": {
                "translation": [0, 0.01, -0.034],
                "rotation_quat": [0, 0, 0, 1],
                "scale": [1, 1, 1],
            },
        },
        {
            "id": "left_knee_calibration",
            "parent_id": "left_knee_link",
            "children": [],
            "mesh_id": "left_knee_calibration_mesh",
            "display_name": "左膝标定件",
            "category": "calibration",
            "link_name": "left_knee_link",
            "transform": {
                "translation": [0.006, -0.012, 0.014],
                "rotation_quat": [0, 0, 0, 1],
                "scale": [1, 1, 1],
            },
        },
        {
            "id": "right_knee_link",
            "parent_id": "base_link",
            "children": ["right_knee_frame", "right_knee_calibration"],
            "mesh_id": "right_knee_link_mesh",
            "display_name": "右膝总成",
            "category": "link",
            "link_name": "right_knee_link",
            "transform": {
                "translation": [-0.089, -0.0725, -0.33],
                "rotation_quat": [0, 0, 0, 1],
                "scale": [1, 1, 1],
            },
        },
        {
            "id": "right_knee_frame",
            "parent_id": "right_knee_link",
            "children": [],
            "mesh_id": "right_knee_frame_mesh",
            "display_name": "右膝小腿结构件",
            "category": "frame",
            "link_name": "right_knee_link",
            "transform": {
                "translation": [0, -0.01, -0.034],
                "rotation_quat": [0, 0, 0, 1],
                "scale": [1, 1, 1],
            },
        },
        {
            "id": "right_knee_calibration",
            "parent_id": "right_knee_link",
            "children": [],
            "mesh_id": "right_knee_calibration_mesh",
            "display_name": "右膝标定件",
            "category": "calibration",
            "link_name": "right_knee_link",
            "transform": {
                "translation": [0.006, 0.012, 0.014],
                "rotation_quat": [0, 0, 0, 1],
                "scale": [1, 1, 1],
            },
        },
    ],
    "fastener_instances": [
        {
            "id": "torso_shell_front_m4x12_01",
            "type": "M4x12",
            "parent_id": "torso_shell_front",
            "mesh_id": "fastener_m4x12_mesh",
            "transform": {
                "translation": [0.032, 0.046, 0.02],
                "rotation_quat": [0, 0, 0, 1],
                "scale": [1, 1, 1],
            },
            "tool": "hex_3",
            "torque_nm": 1.2,
        },
        {
            "id": "torso_shell_rear_m4x12_01",
            "type": "M4x12",
            "parent_id": "torso_shell_rear",
            "mesh_id": "fastener_m4x12_mesh",
            "transform": {
                "translation": [-0.028, -0.042, -0.02],
                "rotation_quat": [0, 0, 0, 1],
                "scale": [1, 1, 1],
            },
            "tool": "hex_3",
            "torque_nm": 1.2,
        },
        {
            "id": "left_arm_pitch_shell_m4x8_01",
            "type": "M4x8",
            "parent_id": "left_arm_pitch_shell",
            "mesh_id": "fastener_m4x8_mesh",
            "transform": {
                "translation": [0.018, 0.016, 0.008],
                "rotation_quat": [0, 0, 0, 1],
                "scale": [1, 1, 1],
            },
            "tool": "hex_3",
            "torque_nm": 1.2,
        },
        {
            "id": "right_arm_pitch_shell_m4x8_01",
            "type": "M4x8",
            "parent_id": "right_arm_pitch_shell",
            "mesh_id": "fastener_m4x8_mesh",
            "transform": {
                "translation": [0.018, -0.016, 0.008],
                "rotation_quat": [0, 0, 0, 1],
                "scale": [1, 1, 1],
            },
            "tool": "hex_3",
            "torque_nm": 1.2,
        },
        {
            "id": "left_knee_frame_m5x10_01",
            "type": "M5x10",
            "parent_id": "left_knee_frame",
            "mesh_id": "fastener_m5x10_mesh",
            "transform": {
                "translation": [0.014, 0.012, -0.008],
                "rotation_quat": [0, 0, 0, 1],
                "scale": [1, 1, 1],
            },
            "tool": "hex_4",
            "torque_nm": 2.5,
        },
        {
            "id": "right_knee_frame_m5x10_01",
            "type": "M5x10",
            "parent_id": "right_knee_frame",
            "mesh_id": "fastener_m5x10_mesh",
            "transform": {
                "translation": [0.014, -0.012, -0.008],
                "rotation_quat": [0, 0, 0, 1],
                "scale": [1, 1, 1],
            },
            "tool": "hex_4",
            "torque_nm": 2.5,
        },
    ],
}

EXPLODE_MANIFEST = {
    "version": "2026-03-13",
    "robotId": "atom01",
    "views": [
        {
            "id": "torso_service_view",
            "focus_node_id": "torso_link",
            "camera": {
                "projection": "orthographic",
                "position": [1.15, 0.58, 0.72],
                "target": [0.04, 0, 0.28],
            },
        },
        {
            "id": "left_knee_service_view",
            "focus_node_id": "left_knee_link",
            "camera": {
                "projection": "orthographic",
                "position": [0.84, 0.62, -0.22],
                "target": [-0.08, 0.08, -0.32],
            },
        },
    ],
    "sequences": [
        {
            "id": "torso_cover_removal",
            "step_index": 1,
            "node_ids": ["torso_shell_front", "torso_shell_rear"],
            "direction": [0, 0, 1],
            "distance": 0.18,
            "anchor_node_id": "torso_link",
        },
        {
            "id": "torso_bracket_release",
            "step_index": 2,
            "node_ids": ["torso_bracket"],
            "direction": [0, 0.2, 1],
            "distance": 0.14,
            "anchor_node_id": "torso_link",
        },
        {
            "id": "left_arm_pitch_exposure",
            "step_index": 3,
            "node_ids": ["left_arm_pitch_shell", "left_arm_pitch_bracket"],
            "direction": [0, 1, 0.2],
            "distance": 0.12,
            "anchor_node_id": "left_arm_pitch_link",
        },
        {
            "id": "left_knee_cover_release",
            "step_index": 4,
            "node_ids": ["left_knee_frame", "left_knee_calibration"],
            "direction": [0.1, 1, 0],
            "distance": 0.11,
            "anchor_node_id": "left_knee_link",
        },
        {
            "id": "right_knee_cover_release",
            "step_index": 5,
            "node_ids": ["right_knee_frame", "right_knee_calibration"],
            "direction": [0.1, -1, 0],
            "distance": 0.11,
            "anchor_node_id": "right_knee_link",
        },
    ],
}


def write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    ATOM01_DIR.mkdir(parents=True, exist_ok=True)
    write_json(ASSEMBLY_PATH, ASSEMBLY_MANIFEST)
    write_json(EXPLODE_PATH, EXPLODE_MANIFEST)
    print(f"wrote {ASSEMBLY_PATH}")
    print(f"wrote {EXPLODE_PATH}")


if __name__ == "__main__":
    main()
