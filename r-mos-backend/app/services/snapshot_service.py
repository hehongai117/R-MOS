"""
Snapshot服务（V2.3完整版）
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional
from datetime import datetime, timezone
import logging

from app.models.snapshot import Snapshot
from app.adapters.factory import AdapterFactory
from app.core.exceptions import AdapterConnectionError

logger = logging.getLogger(__name__)


class SnapshotService:
    """Snapshot服务
    
    职责：
    - 创建机器人状态快照
    - 从Adapter采集数据
    - 处理Snapshot失败降级（符合骨架§5.4）
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def create_snapshot(
        self,
        task_id: int,
        step_index: int,
        trigger: str = "step_execution"
    ) -> Optional[Snapshot]:
        """创建Snapshot（V2.4 故障惩罚支持）
        
        ⚠️ MVP策略（骨架§5.4）：
        - Snapshot创建失败不阻断Task执行
        - 记录警告日志，返回None
        - 调用方继续后续流程
        
        V2.4 新增：
        - 检测 active_faults 是否非空
        - 如果存在活动故障，标记 is_anomaly=True
        
        Args:
            task_id: 任务ID
            step_index: 步骤索引
            trigger: 触发原因
            
        Returns:
            Snapshot对象，失败时返回None
        """
        try:
            # 1. 获取Adapter
            adapter = await AdapterFactory.get_adapter()
            
            if not await adapter.is_connected():
                raise AdapterConnectionError("Adapter未连接")
            
            # 2. 采集机器人状态数据
            joint_states = await adapter.get_joint_states()
            sensor_data = await adapter.get_sensor_data()
            active_faults = await adapter.get_active_faults()
            
            # 3. 序列化为JSON（Pydantic自动序列化）
            joint_states_json = [js.model_dump() for js in joint_states]
            sensor_data_json = sensor_data.model_dump()
            
            # V2.4 新增：检测是否存在活动故障
            is_anomaly = len(active_faults) > 0 if active_faults else False
            if is_anomaly:
                logger.warning(f"Snapshot检测到活动故障: task_id={task_id}, faults={active_faults}")
            
            # 4. 创建Snapshot记录
            snapshot = Snapshot(
                task_id=task_id,
                step_index=step_index,
                timestamp=datetime.now(timezone.utc),
                trigger=trigger,
                joint_states=joint_states_json,
                sensor_data=sensor_data_json,
                active_faults=active_faults,
                adapter_type=adapter.__class__.__name__,
                is_anomaly=is_anomaly  # V2.4 新增
            )
            
            self.db.add(snapshot)
            await self.db.flush()  # 获取ID但不提交
            
            logger.info(f"Snapshot创建成功: task_id={task_id}, step_index={step_index}, snapshot_id={snapshot.id}, is_anomaly={is_anomaly}")
            return snapshot
            
        except AdapterConnectionError as e:
            # 降级策略：Adapter未连接，不阻断Task流程
            logger.warning(f"Snapshot创建失败（Adapter未连接）: {e}")
            return None
        except ConnectionError as e:
            # 降级策略：Adapter连接失败，不阻断Task流程
            logger.warning(f"Snapshot创建失败（连接失败）: {e}")
            return None
        except NotImplementedError as e:
            # 降级策略：Adapter类型未实现，不阻断Task流程
            logger.warning(f"Snapshot创建失败（Adapter未实现）: {e}")
            return None
        except Exception as e:
            # 降级策略：未知错误，记录但不阻断
            logger.error(f"Snapshot创建失败（未知错误）: {e}")
            return None
    
    async def get_snapshot(self, snapshot_id: int) -> Optional[Snapshot]:
        """查询Snapshot"""
        result = await self.db.execute(
            select(Snapshot).where(Snapshot.id == snapshot_id)
        )
        return result.scalar_one_or_none()
    
    async def get_task_snapshots(self, task_id: int) -> list[Snapshot]:
        """查询Task的所有Snapshot"""
        result = await self.db.execute(
            select(Snapshot).where(Snapshot.task_id == task_id).order_by(Snapshot.step_index)
        )
        return result.scalars().all()
