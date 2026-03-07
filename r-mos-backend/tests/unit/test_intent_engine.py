"""
P1-3-5: IntentEngine 单元测试
"""
import pytest
from app.services.intent.engine import (
    IntentEngine,
    IntentScene,
    EntityType,
    IntentEntity,
    IntentResult,
)


# ============ IntentScene 测试 ============

def test_intent_scene_enum():
    """测试意图场景枚举"""
    assert IntentScene.TASK_EXECUTION.value == "task_execution"
    assert IntentScene.DIAGNOSIS.value == "diagnosis"
    assert IntentScene.KNOWLEDGE_QUERY.value == "knowledge_query"
    assert IntentScene.TEACHING_GUIDE.value == "teaching_guide"


def test_entity_type_enum():
    """测试实体类型枚举"""
    assert EntityType.SOP.value == "sop"
    assert EntityType.TASK.value == "task"
    assert EntityType.ROBOT.value == "robot"


# ============ IntentResult 测试 ============

def test_intent_result_creation():
    """测试意图结果创建"""
    result = IntentResult(
        scene=IntentScene.TASK_EXECUTION,
        action="create_task",
        entities=[],
        confidence=0.85,
        raw_text="帮我开始一个维保任务"
    )

    assert result.scene == IntentScene.TASK_EXECUTION
    assert result.action == "create_task"
    assert result.confidence == 0.85


def test_intent_result_with_entities():
    """测试带实体的意图结果"""
    entities = [
        IntentEntity(type=EntityType.SOP, value="sop-001", confidence=0.9),
        IntentEntity(type=EntityType.ROBOT, value="robot-01", confidence=0.85)
    ]

    result = IntentResult(
        scene=IntentScene.TEACHING_GUIDE,
        action="guide_step",
        entities=entities,
        confidence=0.9,
        raw_text="指导我完成 SOP-001"
    )

    assert len(result.entities) == 2
    assert result.entities[0].type == EntityType.SOP


def test_intent_result_with_clarification():
    """测试带澄清请求的意图结果"""
    result = IntentResult(
        scene=IntentScene.GENERAL_CHAT,
        action="chat",
        entities=[],
        confidence=0.4,  # 低置信度
        raw_text="那个",
        clarification_request="请更详细地描述您的需求"
    )

    assert result.clarification_request is not None


# ============ IntentEngine 测试 ============

def test_intent_engine_init():
    """测试引擎初始化"""
    engine = IntentEngine()

    assert engine.llm is not None
    assert engine._confidence_threshold == 0.6


def test_set_confidence_threshold():
    """测试设置置信度阈值"""
    engine = IntentEngine()

    engine.set_confidence_threshold(0.7)
    assert engine._confidence_threshold == 0.7


@pytest.mark.asyncio
async def test_rule_based_recognize_task_execution():
    """测试规则识别 - 任务执行"""
    engine = IntentEngine()

    result = await engine.recognize(
        "帮我开始一个维保任务",
        use_llm=False  # 使用规则模式
    )

    assert result.scene == IntentScene.TASK_EXECUTION
    assert result.confidence > 0


@pytest.mark.asyncio
async def test_rule_based_recognize_diagnosis():
    """测试规则识别 - 故障诊断"""
    engine = IntentEngine()

    result = await engine.recognize(
        "机器人无法移动，请诊断问题",
        use_llm=False
    )

    assert result.scene == IntentScene.DIAGNOSIS


@pytest.mark.asyncio
async def test_rule_based_recognize_knowledge():
    """测试规则识别 - 知识查询"""
    engine = IntentEngine()

    result = await engine.recognize(
        "搜索电机维护相关知识",
        use_llm=False
    )

    assert result.scene == IntentScene.KNOWLEDGE_QUERY


@pytest.mark.asyncio
async def test_rule_based_recognize_teaching():
    """测试规则识别 - 教学指导"""
    engine = IntentEngine()

    result = await engine.recognize(
        "请指导我完成这个步骤",
        use_llm=False
    )

    assert result.scene == IntentScene.TEACHING_GUIDE


@pytest.mark.asyncio
async def test_rule_based_recognize_general():
    """测试规则识别 - 通用对话"""
    engine = IntentEngine()

    result = await engine.recognize(
        "今天天气不错",
        use_llm=False
    )

    assert result.scene == IntentScene.GENERAL_CHAT


def test_intent_engine_singleton():
    """测试全局单例"""
    from app.services.intent import intent_engine

    result = IntentEngine()
    assert isinstance(result, IntentEngine)
