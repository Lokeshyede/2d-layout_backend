import asyncio
import os
import sys
import json

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from app.core.config import settings
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

async def check():
    engine = create_async_engine(settings.DATABASE_URL)
    async with engine.connect() as conn:
        res = await conn.execute(text("""
            SELECT id, product_id, product_name, product_type, sku, category, active,
                   width, depth, height, shelf_count, shelf_mode, glb_url, metadata_json
            FROM product_3d_models
            ORDER BY id;
        """))
        rows = res.fetchall()
        for r in rows:
            print(f"ID {r[0]} | Code: {r[1]} | Name: {r[2]} | Type: {r[3]} | SKU: {r[4]} | Cat: {r[5]} | Active: {r[6]}")
            print(f"       Dims: {r[7]}x{r[8]}x{r[9]} | Shelves: {r[10]} ({r[11]})")
            print(f"       GLB: {r[12]}")
            print(f"       Metadata: {r[13]}")
            print("-" * 60)

if __name__ == '__main__':
    asyncio.run(check())
