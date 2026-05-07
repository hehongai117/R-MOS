"""Tests for robot CRUD API endpoints."""
import pytest


def test_robots_module_imports():
    """Verify the robots endpoint module can be imported."""
    from app.api.v1.endpoints import robots
    assert hasattr(robots, "router")
    assert hasattr(robots, "create_robot")
    assert hasattr(robots, "list_robots")
    assert hasattr(robots, "get_robot")
    assert hasattr(robots, "update_robot")
    assert hasattr(robots, "delete_robot")
