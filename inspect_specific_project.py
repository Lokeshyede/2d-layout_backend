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
        res = await conn.execute(text("SELECT id, project_id, title FROM projects WHERE project_id = 'RF-SUR-2026-0068';"))
        p = res.fetchone()
        if not p:
            print("Project RF-SUR-2026-0068 not found.")
            return
        print(f"Project ID {p[0]}: {p[1]} - {p[2]}")
        ent_res = await conn.execute(text(f"SELECT entity_id, entity_type, properties_json, geometry_json FROM cad_entities WHERE project_id = {p[0]};"))
        ents = ent_res.fetchall()
        print(f"Total entities: {len(ents)}")
        for e in ents:
            if e[1] == 'rack':
                prop = json.loads(e[2]) if e[2] else {}
                geom = json.loads(e[3]) if e[3] else {}
                print(f"  Rack {e[0]}: type={prop.get('rackType')}, pModelId={prop.get('productModelId')}, pName={prop.get('productName')}, geom={geom}")

if __name__ == '__main__':
    asyncio.run(check())
