"""机器人资产完整性校验（发布闸门，T1-4）。

置 READY 前校验 assembly manifest 存在且 mesh_catalog 引用的文件齐全，
根治"发布态机器人 3D 打不开"。
"""
import json

from app.services.storage.file_storage import FileStorageBase

MANIFEST_REL_PATH = "manifests/assembly_manifest.json"


def validate_robot_assets(robot_model_id: int, storage: FileStorageBase) -> list[str]:
    """返回缺失资产的相对路径列表；空列表表示校验通过。"""
    try:
        manifest_bytes = storage.download(robot_model_id, MANIFEST_REL_PATH)
    except FileNotFoundError:
        return [MANIFEST_REL_PATH]

    try:
        manifest = json.loads(manifest_bytes)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return [f"{MANIFEST_REL_PATH} (JSON 解析失败)"]

    mesh_catalog: dict = manifest.get("mesh_catalog") or {}
    existing = set(storage.list_files(robot_model_id))
    return [rel_path for rel_path in mesh_catalog.values() if rel_path not in existing]
