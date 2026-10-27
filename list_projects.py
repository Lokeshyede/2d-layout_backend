import asyncio
from app.core.database import AsyncSessionLocal
from app.models import Project
from sqlalchemy import select

async def main():
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Project.id, Project.project_id, Project.title))
        projects = result.all()
        for p in projects:
            print(f"ID: {p[0]}, Project ID: {p[1]}, Title: {p[2]}")

if __name__ == '__main__':
    asyncio.run(main())
