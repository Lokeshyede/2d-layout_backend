import asyncio
import os
import sys
import json

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from app.core.config import settings
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

async def update_corner_rack():
    engine = create_async_engine(settings.DATABASE_URL)
    meta = {
        "semanticType": "CORNER_RACK",
        "nativeDimensions": {
            "x": 32.52,
            "y": 84.89,
            "z": 37.21
        },
        "canonicalAxes": {
            "width": 32.52,
            "height": 84.89,
            "depth": 37.21
        },
        "cornerAnchor": {
            "x": 426.25,
            "y": -9.97,
            "z": -766.05
        },
        "cornerGeometry": {
            "wingA": {
                "name": "Wing A",
                "uprightMesh": 0,
                "direction": [-0.722, -0.692],
                "length": 25.01,
                "shelfDepth": 18.24
            },
            "wingB": {
                "name": "Wing B",
                "uprightMesh": 27,
                "direction": [-0.759, 0.652],
                "length": 23.64,
                "shelfDepth": 20.52
            },
            "cornerPillar": {
                "mesh": 19,
                "width": 1.54,
                "depth": 2.28,
                "height": 84.86
            }
        },
        "shelfMeshes": [3, 4, 11, 12, 13, 29],
        "bracketMeshes": [14, 15, 16, 28, 31, 32],
        "panelMeshes": [1, 2, 7, 10, 20, 21, 22, 23, 24, 30],
        "supportsParametricShelves": True,
        "shelfCount": 6,
        "detected_width": 32.52,
        "detected_height": 84.89,
        "detected_depth": 37.21,
        "mesh_count": 33
    }

    meta_str = json.dumps(meta)

    async with engine.begin() as conn:
        await conn.execute(text("""
            UPDATE product_3d_models
            SET product_name = 'Corner Rack 7x3',
                product_type = 'Corner Rack',
                sku = 'CR - 7 x 3',
                category = 'Corner Racks',
                width = 32.52,
                depth = 37.21,
                height = 84.89,
                shelf_count = 6,
                shelf_mode = 'AUTO_SPACING',
                shelf_thickness = 1.0,
                metadata_json = :meta_str,
                active = True
            WHERE product_id = 'RF-PRD-0008';
        """), {"meta_str": meta_str})

        print("Product RF-PRD-0008 successfully updated!")

        # Verify
        res = await conn.execute(text("""
            SELECT id, product_id, product_name, product_type, sku, category, glb_url, width, depth, height, shelf_count, metadata_json
            FROM product_3d_models
            WHERE product_id = 'RF-PRD-0008';
        """))
        row = res.fetchone()
        print(f"Verified row: {row}")

if __name__ == '__main__':
    asyncio.run(update_corner_rack())
