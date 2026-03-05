"""
UF-03: TrainingIntentRouter tests.
"""
from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.services.intent.engine import IntentScene
from app.services.intent.training_intent_router import TrainingIntentRouter, TrainingIntentType


@pytest.mark.asyncio
async def test_training_intent_router_routes_new_training(monkeypatch, test_db, test_user):
    router = TrainingIntentRouter(test_db)

    async def fake_recognize(_text: str):
        return SimpleNamespace(scene=IntentScene.TRAINING_NEW)

    monkeypatch.setattr(router.intent_engine, "recognize", fake_recognize)

    result = await router.route("我要开始一个新的ABB训练", user_id=test_user.id)
    assert result.can_proceed is True
    assert result.routing_target == "project_generator"
    assert result.intent.intent_type == TrainingIntentType.NEW


@pytest.mark.asyncio
async def test_training_intent_router_non_training_scene(test_db, test_user):
    router = TrainingIntentRouter(test_db)

    async def fake_recognize(_text: str):
        return SimpleNamespace(scene=IntentScene.GENERAL_CHAT)

    router.intent_engine.recognize = fake_recognize

    result = await router.route("今天天气怎么样", user_id=test_user.id)
    assert result.can_proceed is False
    assert result.routing_target == "general"
