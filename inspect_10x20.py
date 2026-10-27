import asyncio
import json
from app.core.database import AsyncSessionLocal
from app.models import Project
from sqlalchemy import select

async def main():
    async with AsyncSessionLocal() as session:
        res = await session.execute(select(Project).where(Project.project_id == 'RF-SUR-2026-0056'))
        p = res.scalar_one_or_none()
        if not p:
            print("Project not found")
            return
        walls = []
        racks = []
        for e in p.entities:
            geom = json.loads(e.geometry_json) if e.geometry_json else {}
            if e.entity_type == 'wall':
                walls.append(geom)
            elif e.entity_type == 'rack':
                racks.append(geom)
        print("WALLS (count =", len(walls), "):")
        for w in walls:
            print(f"  ({w.get('x1')}, {w.get('y1')}) -> ({w.get('x2')}, {w.get('y2')})")
        print("RACKS (count =", len(racks), "):")
        for r in racks[:5]:
            print(f"  pos: ({r.get('x')}, {r.get('y')}), size: {r.get('width')}x{r.get('depth')}x{r.get('height')}, rot: {r.get('rotation')}")

if __name__ == '__main__':
    asyncio.run(main())
