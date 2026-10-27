import asyncio
from app.core.database import AsyncSessionLocal
from app.models import Project, CADEntity
from sqlalchemy import select
import json

async def main():
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Project))
        projects = result.scalars().all()
        for p in projects:
            walls = [e for e in (p.entities or []) if e.entity_type == 'wall']
            racks = [e for e in (p.entities or []) if e.entity_type == 'rack']
            if len(walls) >= 4:
                xs = []
                ys = []
                for w in walls:
                    g = json.loads(w.geometry_json)
                    xs.extend([g.get('x1', 0), g.get('x2', 0)])
                    ys.extend([g.get('y1', 0), g.get('y2', 0)])
                if xs and ys:
                    w_ft = (max(xs) - min(xs)) / 12
                    h_ft = (max(ys) - min(ys)) / 12
                    print(f"Project ID: {p.project_id}, Title: {p.title}, Size: {w_ft:.1f}' x {h_ft:.1f}', Racks: {len(racks)}, Walls: {len(walls)}")

if __name__ == '__main__':
    asyncio.run(main())
