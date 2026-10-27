import asyncio
from app.core.database import AsyncSessionLocal
from app.models import CADEntity
from sqlalchemy import select, func

async def main():
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(CADEntity.project_id, CADEntity.entity_type, func.count(CADEntity.id))
            .group_by(CADEntity.project_id, CADEntity.entity_type)
        )
        data = {}
        for pid, etype, count in result.all():
            if pid not in data:
                data[pid] = {}
            data[pid][etype] = count
        for pid, types in list(data.items())[:10]:
            print(f"Project {pid}: {types}")

if __name__ == '__main__':
    asyncio.run(main())
