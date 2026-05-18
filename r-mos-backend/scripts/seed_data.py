"""
种子数据导入脚本
数据来源：data/config/seed_base.yaml
"""
import asyncio
import sys
import os
import yaml

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.realpath(os.path.join(os.path.dirname(__file__), '..')))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.models.sop import SOP, SOPStep
from app.models.fault import FaultCase
from app.core.config import settings

# 数据库连接（从 settings 读取）
engine = create_async_engine(settings.DATABASE_URL, echo=True)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

# 加载 YAML 种子数据
_CONFIG_PATH = os.path.realpath(
    os.path.join(os.path.dirname(__file__), '..', 'data', 'config', 'seed_base.yaml')
)

with open(_CONFIG_PATH, 'r', encoding='utf-8') as _f:
    _seed_config = yaml.safe_load(_f)

SEED_SOPS = _seed_config['sops']
SEED_FAULT_CASES = _seed_config['fault_cases']


async def seed_database():
    """导入种子数据"""
    async with AsyncSessionLocal() as session:
        # 导入SOP
        for sop_data in SEED_SOPS:
            # 深拷贝避免修改原始数据（pop 会改变列表中的 dict）
            sop_data = dict(sop_data)
            steps_data = sop_data.pop("steps")

            sop = SOP(**sop_data)
            session.add(sop)
            await session.flush()

            for step_data in steps_data:
                step = SOPStep(sop_id=sop.id, **step_data)
                session.add(step)

            print(f"✅ Imported SOP: {sop.name}")

        # 导入故障案例
        for fault_data in SEED_FAULT_CASES:
            fault = FaultCase(**fault_data)
            session.add(fault)
            print(f"✅ Imported Fault Case: {fault.fault_code}")

        await session.commit()
        print("\n🎉 Seed data imported successfully!")


if __name__ == "__main__":
    asyncio.run(seed_database())
