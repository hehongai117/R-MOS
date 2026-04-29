"""Seed 5 knowledge documents for 3 fault cases."""
import asyncio
import sys
sys.path.insert(0, ".")

from datetime import datetime
from sqlalchemy import select
from app.core.database import AsyncSessionLocal
from app.models.knowledge_document import KnowledgeDocument


DOCUMENTS = [
    {
        "title": "关节过热维修手册",
        "doc_type": "manual",
        "fault_tags": ["E001_OVERHEAT"],
        "sop_tags": ["sop-e001-overheat"],
        "content": """# 关节过热维修手册

## 1. 过热原因分析

ATOM-01 关节过热的常见原因：
- 散热风扇堵塞或故障（占比45%）
- 关节长时间高负载运行（占比30%）
- 环境温度过高（占比15%）
- 轴承磨损导致摩擦增大（占比10%）

## 2. 温度阈值标准

| 状态 | 温度范围 | 处理方式 |
|------|----------|----------|
| 正常 | < 55°C | 继续运行 |
| 预警 | 55-70°C | 降低负载 |
| 告警 | 70-80°C | 立即停机 |
| 危险 | > 80°C | 紧急断电 |

## 3. 降温操作步骤

1. 确认安全后按下急停按钮
2. 等待自然降温（不可使用液体冷却）
3. 使用红外测温仪确认温度降至50°C以下
4. 检查散热通道是否通畅

## 4. 传感器校准

温度传感器每6个月需要校准一次：
- 标准环境温度下偏差不超过±2°C
- 使用标准热源进行三点校准（25°C, 50°C, 75°C）
""",
    },
    {
        "title": "关节松动维修手册",
        "doc_type": "manual",
        "fault_tags": ["E005_LOOSE"],
        "sop_tags": ["sop-e005-loose"],
        "content": """# 关节松动维修手册

## 1. 松动检测方法

### 位置偏差检测
- 正常偏差范围: < 0.05 rad
- 预警阈值: 0.05 - 0.10 rad
- 告警阈值: > 0.10 rad

### 物理检测
- 手动摇晃关节，感受是否有明显间隙
- 使用塞尺测量轴承间隙（标准: 0.02-0.05mm）

## 2. 扭矩标准

ATOM-01 各关节紧固扭矩：
| 关节 | 螺栓规格 | 标准扭矩 |
|------|----------|----------|
| 肩关节 | M4 | 5 Nm |
| 肘关节 | M3 | 3 Nm |
| 腕关节 | M2.5 | 2 Nm |
| 髋关节 | M5 | 8 Nm |
| 膝关节 | M5 | 8 Nm |
| 踝关节 | M4 | 5 Nm |

## 3. 紧固流程

1. 按对角线顺序预紧（50%扭矩）
2. 再按对角线顺序终紧（100%扭矩）
3. 等待5分钟后复检（热膨胀稳定后）
""",
    },
    {
        "title": "电压系统维修手册",
        "doc_type": "manual",
        "fault_tags": ["E003_VOLTAGE_DROP", "E001_OVERHEAT"],
        "sop_tags": ["sop-e003-e001-compound"],
        "content": """# 电压系统维修手册

## 1. 电压跌落排查流程

### 症状识别
- 主路电压低于20V（正常24V±2V）
- 多关节同时出现过热（电流补偿效应）
- 逻辑系统不稳定

### 因果关系
电压跌落 → 电机PID补偿 → 电流增大 → 发热增加 → 过热告警

**关键判断**: 如果多个关节同时过热，且伴随电压异常，根因是电压而非过热本身。

## 2. 安全断电流程

⚠️ 电压异常时的断电顺序：
1. 停止所有关节运动命令
2. 等待2秒（惯性停止）
3. 切断伺服电源（48V）
4. 切断主电源（24V）
5. 确认全部指示灯熄灭

**禁止**: 直接拔总电源（可能损坏控制板）

## 3. 电压测量要求

| 电路 | 正常范围 | 测量点 |
|------|----------|--------|
| 主路 | 23-25V | PSU输出端 |
| 逻辑 | 4.9-5.1V | 控制板输入 |
| 伺服 | 46-50V | 驱动器输入 |
""",
    },
    {
        "title": "安全操作通用规范",
        "doc_type": "guide",
        "fault_tags": ["*"],
        "sop_tags": [],
        "content": """# 安全操作通用规范

## 1. 通电/断电标准

### 上电流程
1. 确认周围无人员（安全距离 > 1.5m）
2. 目视检查机器人外观无异常
3. 接通主电源
4. 等待系统自检完成（约15秒）
5. 确认所有状态灯正常（绿色常亮）

### 断电流程
1. 发送停止命令
2. 等待所有关节停止运动
3. 切断伺服电源
4. 切断主电源
5. 确认指示灯全部熄灭

## 2. 防护装备要求

| 操作类型 | 必需装备 |
|----------|----------|
| 日常巡检 | 工作服、防护眼镜 |
| 关节维修 | 工作服、防护眼镜、绝缘手套 |
| 电气维修 | 工作服、防护眼镜、绝缘手套、绝缘鞋 |

## 3. 应急处理

### 急停情况
- 机器人异常运动
- 人员进入安全区域
- 冒烟、异味、火花

### 急停后操作
1. 不要立即上电
2. 排查异常原因
3. 确认安全后方可重启
""",
    },
    {
        "title": "ATOM-01 结构参数手册",
        "doc_type": "spec",
        "fault_tags": ["*"],
        "sop_tags": [],
        "content": """# ATOM-01 结构参数手册

## 1. 关节参数

| 关节 | 自由度 | 额定扭矩 | 最大温度 | 额定电压 |
|------|--------|----------|----------|----------|
| 腰部(waist) | 1 DOF | 50 Nm | 80°C | 24V |
| 肩部(shoulder) | 2 DOF | 30 Nm | 75°C | 24V |
| 肘部(elbow) | 1 DOF | 20 Nm | 70°C | 24V |
| 髋部(hip) | 2 DOF | 60 Nm | 80°C | 24V |
| 膝部(knee) | 1 DOF | 50 Nm | 80°C | 24V |
| 踝部(ankle) | 2 DOF | 25 Nm | 70°C | 24V |

## 2. 额定值范围

### 温度
- 环境温度: 0-40°C
- 关节正常工作温度: 30-55°C
- 散热器工作温度: 40-65°C

### 电气
- 主电源: 24V DC (±10%)
- 伺服电源: 48V DC (±5%)
- 逻辑电源: 5V DC (±2%)
- 单关节最大电流: 5A

## 3. 零件编号

| 部件 | 编号 | 供应商 |
|------|------|--------|
| 腰关节电机 | MOT-W-001 | 内部 |
| 肘关节减速器 | GBX-E-002 | 哈默纳科 |
| 膝关节轴承 | BRG-K-003 | NSK |
| 散热风扇 | FAN-001 | 台达 |
| 电源模块 | PSU-24V-300W | 明纬 |
""",
    },
]


async def seed():
    async with AsyncSessionLocal() as db:
        for doc_data in DOCUMENTS:
            existing = await db.execute(
                select(KnowledgeDocument).where(KnowledgeDocument.title == doc_data["title"])
            )
            if existing.scalar_one_or_none():
                print(f"  Skip (exists): {doc_data['title']}")
                continue

            doc = KnowledgeDocument(
                **doc_data,
                status="APPROVED",
                approved_at=datetime.utcnow(),
            )
            db.add(doc)
            print(f"  Seeded: {doc_data['title']}")

        await db.commit()
        print("Done: 5 knowledge documents seeded.")


if __name__ == "__main__":
    asyncio.run(seed())
