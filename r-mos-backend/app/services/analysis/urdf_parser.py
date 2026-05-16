# app/services/analysis/urdf_parser.py
"""URDF parser — extracts robot kinematic tree into standardized assembly manifest."""
import math
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class URDFLink:
    name: str
    mesh_filename: Optional[str] = None
    visual_origin_xyz: list[float] = field(default_factory=lambda: [0.0, 0.0, 0.0])
    visual_origin_rpy: list[float] = field(default_factory=lambda: [0.0, 0.0, 0.0])


@dataclass
class URDFJoint:
    name: str
    joint_type: str  # revolute, continuous, prismatic, fixed
    parent_link: str
    child_link: str
    origin_xyz: list[float] = field(default_factory=lambda: [0.0, 0.0, 0.0])
    origin_rpy: list[float] = field(default_factory=lambda: [0.0, 0.0, 0.0])
    axis: list[float] = field(default_factory=lambda: [1.0, 0.0, 0.0])
    limit_lower: Optional[float] = None
    limit_upper: Optional[float] = None


@dataclass
class URDFParseResult:
    robot_name: str
    links: list[URDFLink]
    joints: list[URDFJoint]
    root_link: str

    def to_assembly_manifest(self, robot_model_id: int) -> dict:
        """Convert parsed URDF into standardized assembly manifest JSON."""
        # Build parent map from joints
        child_to_joint: dict[str, URDFJoint] = {}
        parent_to_children: dict[str, list[str]] = {link.name: [] for link in self.links}
        for joint in self.joints:
            child_to_joint[joint.child_link] = joint
            if joint.parent_link in parent_to_children:
                parent_to_children[joint.parent_link].append(joint.child_link)

        # Build mesh catalog
        mesh_catalog: dict[str, str] = {}
        for link in self.links:
            if link.mesh_filename:
                mesh_id = f"{link.name}_mesh"
                glb_name = f"{link.name}.glb"
                mesh_catalog[mesh_id] = glb_name

        # Build nodes
        nodes = []
        for link in self.links:
            joint = child_to_joint.get(link.name)
            parent_id = joint.parent_link if joint else None
            translation = joint.origin_xyz if joint else [0.0, 0.0, 0.0]
            rpy = joint.origin_rpy if joint else [0.0, 0.0, 0.0]

            nodes.append({
                "id": link.name,
                "parent_id": parent_id,
                "children": parent_to_children.get(link.name, []),
                "mesh_id": f"{link.name}_mesh" if link.mesh_filename else None,
                "display_name": _humanize_link_name(link.name),
                "category": "link",
                "link_name": link.name,
                "transform": {
                    "translation": translation,
                    "rotation_quat": _rpy_to_quaternion(rpy),
                    "scale": [1.0, 1.0, 1.0],
                },
            })

        # Build joints list
        joints_out = []
        for joint in self.joints:
            j = {
                "name": joint.name,
                "type": joint.joint_type,
                "parent_link": joint.parent_link,
                "child_link": joint.child_link,
                "axis": joint.axis,
            }
            if joint.limit_lower is not None and joint.limit_upper is not None:
                j["limits"] = {"lower": joint.limit_lower, "upper": joint.limit_upper}
            else:
                j["limits"] = None
            joints_out.append(j)

        return {
            "version": "2026-05-16",
            "robotId": str(robot_model_id),
            "rootNodeId": self.root_link,
            "mesh_catalog": mesh_catalog,
            "nodes": nodes,
            "joints": joints_out,
        }


class URDFParser:
    """Parse URDF XML string into structured URDFParseResult."""

    def parse(self, urdf_content: str) -> URDFParseResult:
        root = ET.fromstring(urdf_content)
        robot_name = root.attrib.get("name", "unknown")

        links = self._parse_links(root)
        joints = self._parse_joints(root)
        root_link = self._find_root_link(links, joints)

        return URDFParseResult(
            robot_name=robot_name,
            links=links,
            joints=joints,
            root_link=root_link,
        )

    def _parse_links(self, root: ET.Element) -> list[URDFLink]:
        links = []
        for link_elem in root.findall("link"):
            name = link_elem.attrib.get("name", "")
            mesh_filename = None
            visual_xyz = [0.0, 0.0, 0.0]
            visual_rpy = [0.0, 0.0, 0.0]

            visual = link_elem.find("visual")
            if visual is not None:
                geom = visual.find("geometry")
                if geom is not None:
                    mesh = geom.find("mesh")
                    if mesh is not None:
                        mesh_filename = mesh.attrib.get("filename")

                origin = visual.find("origin")
                if origin is not None:
                    visual_xyz = _parse_vec3(origin.attrib.get("xyz", "0 0 0"))
                    visual_rpy = _parse_vec3(origin.attrib.get("rpy", "0 0 0"))

            links.append(URDFLink(
                name=name,
                mesh_filename=mesh_filename,
                visual_origin_xyz=visual_xyz,
                visual_origin_rpy=visual_rpy,
            ))
        return links

    def _parse_joints(self, root: ET.Element) -> list[URDFJoint]:
        joints = []
        for joint_elem in root.findall("joint"):
            name = joint_elem.attrib.get("name", "")
            joint_type = joint_elem.attrib.get("type", "fixed")

            parent = joint_elem.find("parent")
            child = joint_elem.find("child")
            parent_link = parent.attrib.get("link", "") if parent is not None else ""
            child_link = child.attrib.get("link", "") if child is not None else ""

            origin_xyz = [0.0, 0.0, 0.0]
            origin_rpy = [0.0, 0.0, 0.0]
            origin = joint_elem.find("origin")
            if origin is not None:
                origin_xyz = _parse_vec3(origin.attrib.get("xyz", "0 0 0"))
                origin_rpy = _parse_vec3(origin.attrib.get("rpy", "0 0 0"))

            axis = [1.0, 0.0, 0.0]
            axis_elem = joint_elem.find("axis")
            if axis_elem is not None:
                axis = _parse_vec3(axis_elem.attrib.get("xyz", "1 0 0"))

            limit_lower = None
            limit_upper = None
            limit_elem = joint_elem.find("limit")
            if limit_elem is not None:
                lower_str = limit_elem.attrib.get("lower")
                upper_str = limit_elem.attrib.get("upper")
                if lower_str is not None:
                    limit_lower = float(lower_str)
                if upper_str is not None:
                    limit_upper = float(upper_str)

            joints.append(URDFJoint(
                name=name,
                joint_type=joint_type,
                parent_link=parent_link,
                child_link=child_link,
                origin_xyz=origin_xyz,
                origin_rpy=origin_rpy,
                axis=axis,
                limit_lower=limit_lower,
                limit_upper=limit_upper,
            ))
        return joints

    def _find_root_link(self, links: list[URDFLink], joints: list[URDFJoint]) -> str:
        """Root link = a link that is never a child in any joint."""
        child_links = {j.child_link for j in joints}
        for link in links:
            if link.name not in child_links:
                return link.name
        return links[0].name if links else ""


def _parse_vec3(s: str) -> list[float]:
    """Parse space-separated string '0.1 0.2 0.3' into [float, float, float]."""
    parts = s.strip().split()
    return [float(x) for x in parts[:3]]


def _rpy_to_quaternion(rpy: list[float]) -> list[float]:
    """Convert roll-pitch-yaw (XYZ extrinsic) to quaternion [qx, qy, qz, qw]."""
    roll, pitch, yaw = rpy
    cr = math.cos(roll / 2)
    sr = math.sin(roll / 2)
    cp = math.cos(pitch / 2)
    sp = math.sin(pitch / 2)
    cy = math.cos(yaw / 2)
    sy = math.sin(yaw / 2)

    qw = cr * cp * cy + sr * sp * sy
    qx = sr * cp * cy - cr * sp * sy
    qy = cr * sp * cy + sr * cp * sy
    qz = cr * cp * sy - sr * sp * cy

    return [qx, qy, qz, qw]


def _humanize_link_name(name: str) -> str:
    """Convert 'left_thigh_pitch_link' → 'Left Thigh Pitch'."""
    clean = name.replace("_link", "").replace("_", " ")
    return clean.title()
