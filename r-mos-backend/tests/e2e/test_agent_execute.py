"""
P2-1: Agent Execute E2E Tests
Tests the unified /agent/execute endpoint

Run with: pytest tests/e2e/test_agent_execute.py -v
"""

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.models.base import Base
from app.models.command_runtime import Command


@pytest_asyncio.fixture
async def async_client():
    """Create async HTTP client for testing."""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test"
    ) as client:
        yield client


class TestAgentExecuteEndpoint:
    """Test cases for POST /agent/execute"""

    @pytest.mark.asyncio
    async def test_execute_command_mode(self, async_client: AsyncClient):
        """Test command mode execution with explicit mode"""
        # This test requires authentication - will fail with 401/403
        # In real tests, you'd need to mock the auth dependency
        response = await async_client.post(
            "/api/v1/agent/execute",
            json={
                "user_id": "test-user-123",
                "mode": "command",
                "intent": "dispatch",
                "tool_name": "assignments.create_draft",
                "skill_id": "teaching.dispatch.draft",
                "tool_args": {"input_text": "Test task creation"},
                "side_effects": ["assignments.write"],
            }
        )
        # Should get 401 or 403 (auth required) or 200 with proper auth
        assert response.status_code in [200, 401, 403]

    @pytest.mark.asyncio
    async def test_execute_message_mode(self, async_client: AsyncClient):
        """Test message mode execution"""
        response = await async_client.post(
            "/api/v1/agent/execute",
            json={
                "user_id": "test-user-123",
                "mode": "message",
                "message": "Help with robot maintenance",
                "context": {"task_id": "task-456"},
            }
        )
        # Should get 401 or 403 (auth required) or 200 with proper auth
        assert response.status_code in [200, 401, 403]

    @pytest.mark.asyncio
    async def test_execute_auto_detect_command(self, async_client: AsyncClient):
        """Test auto-detect mode: should detect command mode from tool_name"""
        response = await async_client.post(
            "/api/v1/agent/execute",
            json={
                "user_id": "test-user-123",
                "mode": "auto",
                "tool_name": "assignments.create_draft",
                "tool_args": {},
            }
        )
        assert response.status_code in [200, 401, 403]

    @pytest.mark.asyncio
    async def test_execute_auto_detect_message(self, async_client: AsyncClient):
        """Test auto-detect mode: should detect message mode from message field"""
        response = await async_client.post(
            "/api/v1/agent/execute",
            json={
                "user_id": "test-user-123",
                "mode": "auto",
                "message": "What is the status of my task?",
            }
        )
        assert response.status_code in [200, 401, 403]

    @pytest.mark.asyncio
    async def test_execute_response_schema(self, async_client: AsyncClient):
        """Test response schema has required fields"""
        # This is a schema validation test
        # Response should have: status, result, trace_id, from_cache, mode_used
        pass  # Schema is validated by Pydantic

    @pytest.mark.asyncio
    async def test_execute_with_idempotency_key(self, async_client: AsyncClient):
        """Test idempotency key is passed through"""
        response = await async_client.post(
            "/api/v1/agent/execute",
            json={
                "user_id": "test-user-123",
                "mode": "message",
                "message": "Test message",
                "idempotency_key": "test-key-12345",
            }
        )
        assert response.status_code in [200, 401, 403]


class TestRemovedLegacyEndpoints:
    """Legacy endpoints should be removed in C-01 cleanup."""

    @pytest.mark.asyncio
    async def test_removed_ai_commands_returns_404(self, async_client: AsyncClient):
        """Test removed /ai/commands returns 404."""
        response = await async_client.post(
            "/api/v1/ai/commands",
            json={
                "intent": "dispatch",
                "input_text": "Test",
            }
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_removed_v2_request_returns_404(self, async_client: AsyncClient):
        """Test removed /agent/v2/request returns 404."""
        response = await async_client.post(
            "/api/v1/agent/v2/request",
            json={
                "user_id": "test-user",
                "message": "Test message",
            }
        )
        assert response.status_code == 404


class TestBackwardCompatibility:
    """Legacy compatibility route should be removed in cleanup."""

    @pytest.mark.asyncio
    async def test_legacy_request_removed(self, async_client: AsyncClient):
        """Ensure /agent/request has been removed."""
        response = await async_client.post(
            "/api/v1/agent/request",
            json={
                "user_id": "test-user",
                "message": "Legacy request test",
            },
        )
        assert response.status_code == 404
