from __future__ import annotations

from collections import defaultdict
from pathlib import Path, PurePosixPath
from xml.etree import ElementTree

from app.models.robot_project import RobotProject
from app.models.robot_project_file import RobotProjectFile

RUNTIME_ASSET_EXTENSIONS = {
    ".glb": "gltf",
    ".gltf": "gltf",
    ".stl": "stl",
    ".obj": "obj",
    ".dae": "dae",
    ".wrl": "wrl",
}


def _append_unique(values: list[str], value: str | None) -> None:
    if value and value not in values:
        values.append(value)


def _sort_unique(values: list[str]) -> list[str]:
    return list(dict.fromkeys(values))


class RobotManifestBuilder:
    def build(self, project: RobotProject, files: list[RobotProjectFile]) -> dict:
        mapping: dict[str, dict[str, list[str]]] = defaultdict(
            lambda: {
                "source_paths": [],
                "file_kinds": [],
                "runtime_asset_paths": [],
            }
        )
        parent_by_node: dict[str, str | None] = {}
        children_by_node: dict[str, list[str]] = defaultdict(list)
        viewer_assets: dict[str, dict] = {}
        structures: list[dict] = []

        files_by_path = {self._normalize_path(file.relative_path): file for file in files}

        for file in files:
            if file.file_kind == "structure":
                continue
            node_id = Path(file.filename).stem
            self._register_source_path(mapping[node_id], file.relative_path)
            _append_unique(mapping[node_id]["file_kinds"], file.file_kind)
            parent_by_node.setdefault(node_id, None)
            if self._is_runtime_asset(file.relative_path):
                self._register_runtime_asset(
                    viewer_assets,
                    mapping[node_id],
                    node_id=node_id,
                    display_name=node_id,
                    path=file.relative_path,
                )

        for file in files:
            if file.file_kind != "structure":
                continue
            parsed = self._parse_structure_file(file, files_by_path)
            if parsed is None:
                continue
            structures.append(parsed["structure"])
            for node_id, node_payload in parsed["nodes"].items():
                node = mapping[node_id]
                self._register_source_path(node, file.relative_path)
                _append_unique(node["file_kinds"], file.file_kind)
                parent = node_payload["parent_id"]
                if node_id not in parent_by_node:
                    parent_by_node[node_id] = parent
                elif parent_by_node[node_id] is None and parent is not None:
                    parent_by_node[node_id] = parent
                if parent is not None and node_id not in children_by_node[parent]:
                    children_by_node[parent].append(node_id)
                for mesh_path in node_payload["mesh_paths"]:
                    self._register_source_path(node, mesh_path)
                    source_file = files_by_path.get(self._normalize_path(mesh_path))
                    if source_file is not None:
                        _append_unique(node["file_kinds"], source_file.file_kind)
                    if self._is_runtime_asset(mesh_path):
                        self._register_runtime_asset(
                            viewer_assets,
                            node,
                            node_id=node_id,
                            display_name=node_id,
                            path=mesh_path,
                        )

        tree_nodes: list[dict] = []
        needs_review_nodes: list[str] = []
        for node_id in sorted(mapping):
            node = mapping[node_id]
            source_paths = _sort_unique(node["source_paths"])
            file_kinds = _sort_unique(node["file_kinds"])
            runtime_asset_paths = self._sorted_runtime_assets(node["runtime_asset_paths"])
            for runtime_asset_path in runtime_asset_paths:
                if runtime_asset_path in viewer_assets:
                    viewer_assets[runtime_asset_path]["source_paths"] = source_paths
            child_ids = sorted(children_by_node.get(node_id, []))
            tree_nodes.append(
                {
                    "id": node_id,
                    "display_name": node_id,
                    "parent_id": parent_by_node.get(node_id),
                    "children": child_ids,
                    "source_paths": source_paths,
                    "file_kinds": file_kinds,
                    "runtime_asset_paths": runtime_asset_paths,
                }
            )
            if not runtime_asset_paths or "structure" not in file_kinds:
                needs_review_nodes.append(node_id)

        root_nodes = sorted(
            node["id"]
            for node in tree_nodes
            if node["parent_id"] is None
        )
        assets = sorted(viewer_assets.values(), key=lambda item: item["path"])
        parts = [asset["path"] for asset in assets]
        viewer_manifest = {
            "robotId": project.robot_key,
            "label": f"{project.brand} {project.model}".strip(),
            "parts": parts,
            "assets": assets,
            "structures": structures,
            "needs_review_nodes": sorted(needs_review_nodes),
        }

        return {
            "tree": {
                "robot_key": project.robot_key,
                "root_nodes": root_nodes,
                "nodes": tree_nodes,
            },
            "mapping": {
                node_id: {
                    "source_paths": _sort_unique(node["source_paths"]),
                    "file_kinds": _sort_unique(node["file_kinds"]),
                    "runtime_asset_paths": self._sorted_runtime_assets(node["runtime_asset_paths"]),
                }
                for node_id, node in sorted(mapping.items())
            },
            "viewer_manifest": viewer_manifest,
            "needs_review_nodes": sorted(needs_review_nodes),
        }

    def _parse_structure_file(
        self,
        file: RobotProjectFile,
        files_by_path: dict[str, RobotProjectFile],
    ) -> dict | None:
        extension = Path(file.relative_path).suffix.lower()
        if extension != ".urdf":
            return None

        content = self._read_file_text(file.storage_path)
        root = ElementTree.fromstring(content)
        base_dir = PurePosixPath(file.relative_path).parent
        nodes: dict[str, dict[str, list[str] | str | None]] = {}
        parent_by_child: dict[str, str | None] = {}

        for link in root.findall("link"):
            node_id = link.attrib.get("name")
            if not node_id:
                continue
            mesh_paths: list[str] = []
            for mesh in link.findall("./visual/geometry/mesh"):
                raw_filename = mesh.attrib.get("filename")
                resolved = self._resolve_structure_reference(base_dir, raw_filename, files_by_path)
                if resolved:
                    _append_unique(mesh_paths, resolved)
            nodes[node_id] = {
                "mesh_paths": mesh_paths,
                "parent_id": None,
            }

        for joint in root.findall("joint"):
            parent = joint.find("parent")
            child = joint.find("child")
            parent_id = parent.attrib.get("link") if parent is not None else None
            child_id = child.attrib.get("link") if child is not None else None
            if not child_id:
                continue
            nodes.setdefault(child_id, {"mesh_paths": [], "parent_id": None})
            nodes[child_id]["parent_id"] = parent_id
            parent_by_child[child_id] = parent_id
            if parent_id:
                nodes.setdefault(parent_id, {"mesh_paths": [], "parent_id": None})

        root_nodes = sorted(node_id for node_id in nodes if parent_by_child.get(node_id) is None)
        return {
            "structure": {
                "path": file.relative_path,
                "structure_type": "urdf",
                "root_nodes": root_nodes,
            },
            "nodes": nodes,
        }

    def _resolve_structure_reference(
        self,
        base_dir: PurePosixPath,
        raw_filename: str | None,
        files_by_path: dict[str, RobotProjectFile],
    ) -> str | None:
        if not raw_filename:
            return None
        normalized = self._normalize_path(str((base_dir / raw_filename).as_posix()))
        if normalized in files_by_path:
            return files_by_path[normalized].relative_path

        target_name = Path(raw_filename).name.lower()
        matches = [
            path
            for path in files_by_path
            if Path(path).name.lower() == target_name
        ]
        if matches:
            return files_by_path[matches[0]].relative_path
        return str((base_dir / raw_filename).as_posix()).replace("\\", "/")

    def _register_source_path(self, node: dict[str, list[str]], path: str) -> None:
        _append_unique(node["source_paths"], path)

    def _register_runtime_asset(
        self,
        viewer_assets: dict[str, dict],
        node: dict[str, list[str]],
        *,
        node_id: str,
        display_name: str,
        path: str,
    ) -> None:
        asset_type = self._asset_type_for_path(path)
        if asset_type is None:
            return
        _append_unique(node["runtime_asset_paths"], path)
        viewer_assets[path] = {
            "asset_id": f"{node_id}::{path}",
            "asset_type": asset_type,
            "display_name": display_name,
            "node_id": node_id,
            "path": path,
            "source_paths": [],
        }

    def _sorted_runtime_assets(self, runtime_asset_paths: list[str]) -> list[str]:
        return sorted(
            dict.fromkeys(runtime_asset_paths),
            key=lambda path: (self._runtime_asset_priority(path), path.lower()),
        )

    def _runtime_asset_priority(self, path: str) -> int:
        asset_type = self._asset_type_for_path(path)
        order = {"gltf": 0, "stl": 1, "obj": 2, "dae": 3, "wrl": 4}
        return order.get(asset_type or "", 99)

    def _asset_type_for_path(self, path: str) -> str | None:
        return RUNTIME_ASSET_EXTENSIONS.get(Path(path).suffix.lower())

    def _is_runtime_asset(self, path: str) -> bool:
        return self._asset_type_for_path(path) is not None

    def _normalize_path(self, path: str) -> str:
        return path.replace("\\", "/").lower()

    def _read_file_text(self, storage_path: str) -> str:
        if "::" in storage_path:
            archive_path_str, member_name = storage_path.split("::", 1)
            import zipfile

            with zipfile.ZipFile(archive_path_str) as archive:
                return archive.read(member_name).decode("utf-8", errors="ignore")
        return Path(storage_path).read_text(encoding="utf-8", errors="ignore")
