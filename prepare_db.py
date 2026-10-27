import asyncio
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.core.config import settings
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

async def prepare_db():
    engine = create_async_engine(settings.DATABASE_URL)
    async with engine.begin() as conn:
        print("Finding and renaming all indexes on legacy_customers...")
        res = await conn.execute(text("""
            SELECT indexname 
            FROM pg_indexes 
            WHERE tablename = 'legacy_customers';
        """))
        for row in res:
            idx = row[0]
            if not idx.startswith('legacy_'):
                print(f"Renaming {idx} to legacy_{idx}")
                try:
                    await conn.execute(text(f"ALTER INDEX {idx} RENAME TO legacy_{idx};"))
                except Exception as e:
                    print(f"Failed to rename {idx}: {e}")

asyncio.run(prepare_db())
