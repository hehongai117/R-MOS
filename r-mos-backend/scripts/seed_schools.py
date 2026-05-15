"""导入学校白名单数据到 schools 表。

Usage:
    cd r-mos-backend
    source venv/bin/activate
    python scripts/seed_schools.py [--file data/schools.json]
"""
import argparse
import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select, func
from app.core.database import AsyncSessionLocal
from app.models.school import School


async def seed_schools(json_path: str) -> None:
    data = json.loads(Path(json_path).read_text(encoding="utf-8"))
    print(f"读取 {len(data)} 条学校记录")

    async with AsyncSessionLocal() as db:
        existing_count = (await db.execute(select(func.count(School.id)))).scalar() or 0
        print(f"数据库中已有 {existing_count} 条记录")

        inserted = 0
        for item in data:
            name = item["name"].strip()
            province = item.get("province", "").strip() or None
            exists = (
                await db.execute(select(School.id).where(School.name == name))
            ).scalar_one_or_none()
            if exists:
                continue
            db.add(School(name=name, province=province))
            inserted += 1

        await db.commit()
        print(f"新增 {inserted} 条，跳过 {len(data) - inserted} 条重复记录")


def main():
    parser = argparse.ArgumentParser(description="导入学校白名单")
    parser.add_argument(
        "--file",
        default="data/schools.json",
        help="学校 JSON 文件路径 (默认: data/schools.json)",
    )
    args = parser.parse_args()
    asyncio.run(seed_schools(args.file))


if __name__ == "__main__":
    main()
