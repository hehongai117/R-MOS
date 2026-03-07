from __future__ import annotations

import ast
from pathlib import Path


def _parse_locustfile() -> ast.Module:
    locustfile_path = Path(__file__).with_name("locustfile.py")
    return ast.parse(locustfile_path.read_text(encoding="utf-8"))


def test_locustfile_syntax_and_user_classes_exist() -> None:
    tree = _parse_locustfile()
    class_names = {node.name for node in tree.body if isinstance(node, ast.ClassDef)}
    assert "RMOSUser" in class_names
    assert "APIPerformanceUser" in class_names


def test_rmos_user_declares_expected_tasks() -> None:
    tree = _parse_locustfile()
    rmos_user = next(
        node
        for node in tree.body
        if isinstance(node, ast.ClassDef) and node.name == "RMOSUser"
    )

    for method_name in (
        "health_check",
        "list_sops",
        "get_task",
        "create_task",
        "agent_execute",
    ):
        method = next(
            node
            for node in rmos_user.body
            if isinstance(node, ast.FunctionDef) and node.name == method_name
        )
        decorator_names = [
            decorator.func.id if isinstance(decorator, ast.Call) and isinstance(decorator.func, ast.Name)
            else decorator.id if isinstance(decorator, ast.Name)
            else ""
            for decorator in method.decorator_list
        ]
        assert "task" in decorator_names, f"{method_name} 缺少 @task 装饰器"
