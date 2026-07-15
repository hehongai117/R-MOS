"""存量发布态机器人资产审计（P0-4 闸门的存量闭环）。

闸门只拦截新的置位动作；本脚本审计已处于 READY 的存量机器人。
用法：
    python scripts/audit_published_assets.py            # 只读报告
    python scripts/audit_published_assets.py --unpublish --yes  # 资产不全者置回 DRAFT
"""
import argparse
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select  # noqa: E402
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine  # noqa: E402

from app.core.config import settings  # noqa: E402
from app.models.robot_model import RobotModel, RobotStatus  # noqa: E402
from app.services.robot_asset_validator import validate_robot_assets  # noqa: E402
from app.services.storage import get_storage  # noqa: E402


async def main(unpublish: bool) -> int:
    engine = create_async_engine(settings.DATABASE_URL)
    storage = get_storage()
    incomplete = []
    robots = []  # 防御性初始化：避免 select 前异常导致 finally 外 NameError
    try:
        async with async_sessionmaker(engine)() as session:
            result = await session.execute(
                select(RobotModel).where(RobotModel.status == RobotStatus.READY)
            )
            robots = list(result.scalars().all())
            print(f"== 审计 {len(robots)} 个 READY 机器人 ==")
            for robot in robots:
                missing = validate_robot_assets(robot.id, storage)
                if missing:
                    incomplete.append((robot, missing))
                    shown = "、".join(missing[:5])
                    more = f" 等共 {len(missing)} 项" if len(missing) > 5 else ""
                    print(f"  [缺资产] id={robot.id} {robot.brand}/{robot.model_name}: {shown}{more}")
                else:
                    print(f"  [完整]   id={robot.id} {robot.brand}/{robot.model_name}")

            if incomplete and unpublish:
                for robot, _ in incomplete:
                    robot.status = RobotStatus.DRAFT
                await session.commit()
                print(f"== 已将 {len(incomplete)} 个资产不全的机器人置回 DRAFT ==")
    finally:
        await engine.dispose()

    print(f"== 结果: {len(incomplete)} 个不完整 / {len(robots)} 个已发布 ==")
    return 1 if (incomplete and not unpublish) else 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--unpublish", action="store_true", help="资产不全者置回 DRAFT")
    parser.add_argument("--yes", action="store_true", help="确认执行写操作")
    args = parser.parse_args()
    if args.unpublish and not args.yes:
        print("写操作需同时传 --yes 确认", file=sys.stderr)
        raise SystemExit(2)
    raise SystemExit(asyncio.run(main(args.unpublish and args.yes)))
