"""Mock LLM provider with pre-written responses for demo."""
import asyncio
import re
from dataclasses import dataclass
from typing import Optional


@dataclass
class MockLLMResponse:
    text: str
    diagnosis: Optional[dict] = None
    citations: Optional[list] = None
    sop_recommendation: Optional[dict] = None


# --- Pre-written response templates ---

DIAGNOSIS_RESPONSE = MockLLMResponse(
    text=(
        "## 故障诊断报告\n\n"
        "**故障类型：** 左膝关节轴承磨损\n\n"
        "**严重程度：** 中高风险 (需尽快维保)\n\n"
        "**置信度：** 92%\n\n"
        "### 分析过程\n\n"
        "通过对传感器数据的多维度关联分析，我发现以下异常模式：\n\n"
        "1. **温度异常** — 左膝关节温度从正常基线 35°C 持续升高至 65°C，"
        "升温速率约 1°C/s，符合轴承摩擦过热的典型特征\n"
        "2. **扭矩波动** — 同期扭矩数据出现 ±2.1Nm 的周期性波动，"
        "表明关节内部存在不规则机械阻力\n"
        "3. **电流上升** — 驱动电流从 2.0A 上升至 2.8A，"
        "与温度升高呈正相关，说明电机在补偿额外摩擦负荷\n\n"
        "### 根因判定\n\n"
        "综合以上证据，判定根因为**左膝关节主轴承磨损**，导致滚珠与滚道之间"
        "间隙增大，运转时产生异常摩擦热。若不及时处理，可能导致轴承卡死或"
        "关节结构损伤。\n\n"
        "### 建议\n\n"
        "建议立即执行 **SOP: ATOM-01 左膝关节轴承更换**，预计耗时约 45 分钟。"
    ),
    diagnosis={
        "fault_type": "bearing_wear",
        "joint": "KNEE_LEFT",
        "severity": "high",
        "confidence": 0.92,
        "primary_hypothesis": {
            "name": "左膝关节轴承磨损",
            "confidence": 0.92,
            "affected_parts": ["left_knee_bearing", "left_knee_joint"],
            "evidence": [
                {"type": "temperature", "desc": "温度异常升高 35→65°C"},
                {"type": "torque", "desc": "扭矩周期性波动 ±2.1Nm"},
                {"type": "current", "desc": "驱动电流上升 2.0→2.8A"},
            ],
        },
        "alternative_hypotheses": [
            {
                "name": "润滑油不足",
                "confidence": 0.15,
                "affected_parts": ["left_knee_joint"],
            }
        ],
        "reasoning": "温度-扭矩-电流三维关联指向轴承机械磨损，排除润滑不足（润滑不足通常不会导致如此快速的温升）",
        "recommended_actions": [
            "立即停机，防止轴承卡死",
            "执行左膝关节轴承更换 SOP",
            "更换后进行 30 分钟空载磨合测试",
        ],
    },
    citations=[
        {"type": "sensor", "desc": "左膝温度 35→65°C（30s 内）", "source": "KNEE_LEFT.temperature"},
        {"type": "sensor", "desc": "左膝扭矩波动 ±2.1Nm", "source": "KNEE_LEFT.torque"},
        {"type": "sensor", "desc": "左膝电流 2.0→2.8A", "source": "KNEE_LEFT.current"},
        {"type": "history", "desc": "上次维保距今 180 天，超出建议周期", "source": "maintenance_log"},
    ],
    sop_recommendation={
        "sop_id": "knee-bearing-replace",
        "sop_name": "ATOM-01 左膝关节轴承更换",
        "estimated_time": "45 分钟",
        "steps_count": 6,
    },
)

SOP_GENERATION_RESPONSE = MockLLMResponse(
    text=(
        "## 维保方案已生成\n\n"
        "根据诊断结果，我已为您生成针对性维保方案：\n\n"
        "**SOP: ATOM-01 左膝关节轴承更换** (6 步)\n\n"
        "| 步骤 | 操作 | 预计时间 |\n"
        "|------|------|----------|\n"
        "| 01 | 安全确认 — 断电并确认维保隔离 | 3 分钟 |\n"
        "| 02 | 工具准备 — 确认扳手、轴承拔取器、润滑剂就位 | 5 分钟 |\n"
        "| 03 | 外壳拆卸 — 拆卸左膝关节保护外壳 (4 颗 M3 螺丝) | 8 分钟 |\n"
        "| 04 | 轴承定位 — 定位磨损轴承，记录磨损状态 | 5 分钟 |\n"
        "| 05 | 轴承更换 — 拔取旧轴承，安装新轴承，涂润滑剂 | 15 分钟 |\n"
        "| 06 | 回装验证 — 回装外壳，通电，关节活动度测试 | 9 分钟 |\n\n"
        "点击下方 **开始维保** 按钮，进入 3D 引导式维保工作台。"
    ),
    sop_recommendation={
        "sop_id": "knee-bearing-replace",
        "sop_name": "ATOM-01 左膝关节轴承更换",
        "estimated_time": "45 分钟",
        "steps_count": 6,
    },
)

EXPLANATION_RESPONSE = MockLLMResponse(
    text=(
        "## 故障机理详解\n\n"
        "### 轴承磨损的物理过程\n\n"
        "人形机器人膝关节使用深沟球轴承（型号 6205-2RS），"
        "在持续行走训练中承受周期性径向和轴向载荷。\n\n"
        "当轴承滚珠与滚道之间的润滑膜破裂后，金属直接接触产生摩擦热，"
        "导致温度快速升高。同时，磨损产生的金属微粒进入滚道间隙，"
        "形成 **磨粒磨损** 的恶性循环。\n\n"
        "### 数据关联分析\n\n"
        "- **温度↑ + 扭矩波动↑**：摩擦增大 → 热量增加 + 阻力不均\n"
        "- **电流↑**：电机 PID 控制器补偿额外阻力，增大输出电流\n"
        "- **三者正相关性 > 0.85**：排除传感器故障（传感器故障表现为随机噪声，无相关性）\n\n"
        "### 不处理的后果\n\n"
        "1. 轴承完全卡死 → 膝关节锁定 → 机器人摔倒风险\n"
        "2. 过热可能损伤周围线束和密封件\n"
        "3. 磨损碎屑扩散到相邻关节"
    ),
)

DEFAULT_RESPONSE = MockLLMResponse(
    text=(
        "我是 R-MOS 维保智能体，可以帮您完成以下任务：\n\n"
        "- 输入 **诊断** 或 **故障分析** 来分析当前设备异常\n"
        "- 输入 **维保方案** 或 **怎么修** 来生成维保 SOP\n"
        "- 输入 **为什么** 或 **解释** 来了解故障机理\n\n"
        "请告诉我您需要什么帮助。"
    ),
)


def match_intent(message: str) -> MockLLMResponse:
    """Match user message to a pre-written response based on keywords."""
    msg = message.lower().strip()

    diagnosis_kw = r"诊断|故障|什么问题|分析|检测|异常|温度.*高|过热"
    sop_kw = r"维保方案|怎么修|修复|sop|生成.*方案|开始.*维保|更换"
    explain_kw = r"为什么|解释|原因|机理|详解|怎么.*回事"

    if re.search(diagnosis_kw, msg):
        return DIAGNOSIS_RESPONSE
    if re.search(sop_kw, msg):
        return SOP_GENERATION_RESPONSE
    if re.search(explain_kw, msg):
        return EXPLANATION_RESPONSE
    return DEFAULT_RESPONSE


async def stream_text(text: str, chunk_size: int = 3, delay: float = 0.03):
    """Yield text in small chunks to simulate LLM streaming."""
    for i in range(0, len(text), chunk_size):
        yield text[i:i + chunk_size]
        await asyncio.sleep(delay)
