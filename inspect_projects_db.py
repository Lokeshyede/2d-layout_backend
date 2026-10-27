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
        res = await conn.execute(text("SELECT id, title, project_id FROM projects ORDER BY id;"))
        projects = res.fetchall()
        print(f"Total Projects: {len(projects)}")
        for p in projects:
            print(f"Project ID {p[0]}: {p[1]}")
            ent_res = await conn.execute(text(f"SELECT id, entity_type, properties_json, geometry_json FROM cad_entities WHERE project_id = {p[0]};"))
            ents = ent_res.fetchall()
            racks = [e for e in ents if e[1] == 'rack']
            print(f"  Total Entities: {len(ents)}, Racks: {len(racks)}")
            for r in racks:
                prop = json.loads(r[2]) if r[2] else {}
                geom = json.loads(r[3]) if r[3] else {}
                print(f"    Rack ID {r[0]}: type={prop.get('rackType')}, pId={prop.get('productModelId')}, geom={geom}")

if __name__ == '__main__':
    asyncio.run(check())
