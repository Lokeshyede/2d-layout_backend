import asyncio
import os
import sys
import json

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from app.core.config import settings
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

async def update_center_rack():
    engine = create_async_engine(settings.DATABASE_URL)
    meta = {
        "detected_width": 38.22,
        "detected_height": 85.04,
        "detected_depth": 21.23,
        "mesh_count": 41,
        "localWidthAxis": "Z",
        "localHeightAxis": "Y",
        "localDepthAxis": "X",
        "correctionRotation": {"x": 0, "y": 90, "z": 0},
        "supportsParametricShelves": True,
        "shelfCount": 5,
        "shelfThickness": 1.0,
        "shelfSpacing": "auto",
        "materials": [
            "[Color M00]",
            "[Color C05]",
            "<auto>",
            "[0077_DarkGreen]",
            "[0134_DimGray]",
            "[0010_Snow]",
            "[0128_White]"
        ]
    }

    meta_str = json.dumps(meta)

    async with engine.begin() as conn:
        await conn.execute(text("""
            UPDATE product_3d_models
            SET glb_url = '/uploads/models/updated_rack_b02b4896.glb',
                storage_path = 'models/updated_rack_b02b4896.glb',
                width = 36.0,
                depth = 24.0,
                height = 60.0,
                shelf_count = 5,
                shelf_mode = 'AUTO_SPACING',
                shelf_thickness = 1.0,
                metadata_json = :meta_str,
                active = True
            WHERE id = 8;
        """), {"meta_str": meta_str})

        print("Product ID 8 successfully updated to authentic RetailFix model!")

        # Verify
        res = await conn.execute(text("""
            SELECT id, product_id, product_name, sku, category, glb_url, width, depth, height, shelf_count, metadata_json
            FROM product_3d_models
            WHERE id = 8;
        """))
        row = res.fetchone()
        print(f"Verified row: {row}")

if __name__ == '__main__':
    asyncio.run(update_center_rack())
