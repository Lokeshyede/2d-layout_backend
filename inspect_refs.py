import asyncio
from app.core.database import AsyncSessionLocal
from sqlalchemy import text

async def main():
    async with AsyncSessionLocal() as session:
        result = await session.execute(text("""
            SELECT ce.id, p.project_id, ce.properties_json
            FROM cad_entities ce
            JOIN projects p ON ce.project_id = p.id
            WHERE ce.entity_type = 'rack'
            LIMIT 5
        """))
        for row in result.fetchall():
            print(f"ID: {row[0]}, Proj: {row[1]}, Props: {row[2][:120]}...")

if __name__ == "__main__":
    asyncio.run(main())
