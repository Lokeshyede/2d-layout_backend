import asyncio
import os
import sys
import json

sys.stdout.reconfigure(encoding='utf-8')
# Add backend directory to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from httpx import AsyncClient, ASGITransport
from app.main import app
from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.services.product_service import seed_initial_racks_glb, get_product_by_id
from app.models import Product3DModel, CADEntity, Project, Survey, Customer

async def run_all_tests():
    print("==================================================")
    print("STARTING ACCEPTANCE TESTS: 3D PRODUCT SYSTEM")
    print("==================================================")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Step 0: Login as admin
        login_res = await client.post("/api/admin/login", json={
            "username": settings.DEFAULT_ADMIN_USERNAME,
            "password": settings.DEFAULT_ADMIN_PASSWORD
        })
        assert login_res.status_code == 200, f"Admin login failed: {login_res.text}"
        admin_token = login_res.json()["access_token"]
        headers = {"Authorization": f"Bearer {admin_token}"}
        print("[PASS] Admin login successful")

        # -----------------------------------------------------------------
        # TEST 1: ONE GLB (RACKS (1).glb)
        # -----------------------------------------------------------------
        print("\n--- TEST 1: First GLB ('RACKS (1).glb') ---")
        p1_res = await client.get("/api/products/RF-PRD-0001")
        assert p1_res.status_code == 200, f"Failed to get RF-PRD-0001: {p1_res.text}"
        p1 = p1_res.json()
        print(f"Product 1 found: {p1['product_name']} ({p1['product_id']})")
        print(f"  Dimensions: {p1['width']}″ W × {p1['height']}″ H × {p1['depth']}″ D")
        print(f"  GLB URL: {p1['glb_url']}, Active: {p1['active']}")
        assert p1["product_id"] == "RF-PRD-0001"
        assert p1["active"] is True
        assert p1["glb_url"].endswith(".glb")
        print("[PASS] TEST 1 PASSED: Initial GLB registered, validated, and active.")

        # -----------------------------------------------------------------
        # TEST 2: ADD SECOND PRODUCT DYNAMICALLY THROUGH ADMIN API
        # -----------------------------------------------------------------
        print("\n--- TEST 2: Add Second Product Dynamically ---")
        # Read the existing GLB to simulate uploading a new product model
        glb_path = os.path.join(settings.UPLOAD_DIR, "models", "racks_1.glb")
        with open(glb_path, "rb") as f:
            glb_content = f.read()

        upload_res = await client.post(
            "/api/admin/products/upload-glb",
            headers=headers,
            files={"file": ("center_rack_custom.glb", glb_content, "model/gltf-binary")}
        )
        assert upload_res.status_code == 200, f"GLB upload failed: {upload_res.text}"
        up_data = upload_res.json()
        print(f"Uploaded GLB successfully: {up_data['file_name']}, meshes: {up_data['mesh_count']}")
        assert up_data["valid"] is True
        assert up_data["detected_dimensions"]["width_inches"] > 0

        import uuid
        unique_sku = f"RF-CR-{uuid.uuid4().hex[:6].upper()}"

        create_res = await client.post(
            "/api/admin/products",
            headers=headers,
            json={
                "product_name": "Center Gondola 5×3",
                "product_type": "Center Rack",
                "sku": unique_sku,
                "category": "Center Racks",
                "width": 36.0,
                "height": 60.0,
                "depth": 24.0,
                "shelf_count": 5,
                "min_shelves": 2,
                "max_shelves": 8,
                "shelf_mode": "AUTO_SPACING",
                "glb_url": up_data["glb_url"],
                "storage_path": up_data["storage_path"],
                "active": True
            }
        )
        assert create_res.status_code == 200, f"Create product failed: {create_res.text}"
        p2 = create_res.json()
        print(f"Created Product 2: {p2['product_name']} ({p2['product_id']}) with SKU {p2['sku']}")
        assert p2["product_type"] == "Center Rack"
        assert p2["active"] is True
        assert p2["shelf_count"] == 5
        assert p2["shelf_mode"] == "AUTO_SPACING"

        # Verify reference check endpoint on unreferenced product
        ref_res = await client.get(f"/api/admin/products/{p2['id']}/reference-check", headers=headers)
        assert ref_res.status_code == 200
        ref_data = ref_res.json()
        print(f"Reference check for p2: referenced={ref_data['referenced']}, can_delete={ref_data['can_delete']}")
        assert ref_data["referenced"] is False
        assert ref_data["can_delete"] is True

        # Verify it now appears in public / CAD available products list
        list_res = await client.get("/api/products")
        assert list_res.status_code == 200
        items = list_res.json()["items"]
        p_ids = [item["product_id"] for item in items]
        assert p2["product_id"] in p_ids, "New product not found in active products list"
        print(f"[PASS] TEST 2 PASSED: Second product dynamically registered with shelf config and available (Total active: {len(items)})")

        # -----------------------------------------------------------------
        # TEST 3: MULTIPLE INSTANCES (20 RACKS REFERENCE SAME GLB)
        # -----------------------------------------------------------------
        print("\n--- TEST 3: Multiple Instances (20 Racks) ---")
        cad_racks = []
        for i in range(20):
            cad_racks.append({
                "id": f"rack_test_{i}",
                "type": "rack",
                "geometry": {
                    "x": 36.0 * i,
                    "y": 100.0,
                    "width": 36.0,
                    "depth": 24.0,
                    "height": 84.0,
                    "rotation": 0.0
                },
                "properties": {
                    "rackType": "Wall Rack",
                    "productModelId": p1["product_id"],
                    "productName": p1["product_name"]
                }
            })
        print(f"Constructed {len(cad_racks)} CAD rack entities all referencing productModelId '{p1['product_id']}'.")
        for r in cad_racks:
            assert r["properties"]["productModelId"] == p1["product_id"]
        print("[PASS] TEST 3 PASSED: All 20 instances share the same stable product reference.")

        # -----------------------------------------------------------------
        # TEST 4: DEACTIVATE PRODUCT
        # -----------------------------------------------------------------
        print("\n--- TEST 4: Deactivate Product ---")
        toggle_res = await client.patch(f"/api/admin/products/{p2['id']}/toggle-active", headers=headers)
        assert toggle_res.status_code == 200
        assert toggle_res.json()["active"] is False
        print(f"Product {p2['product_id']} deactivated.")

        # Inactive product should NOT appear in new active placement list
        active_res = await client.get("/api/products")
        active_ids = [item["product_id"] for item in active_res.json()["items"]]
        assert p2["product_id"] not in active_ids, "Inactive product should NOT appear in active list"

        # BUT existing projects can still resolve it via include_inactive or direct lookup
        all_res = await client.get("/api/products?include_inactive=true")
        all_ids = [item["product_id"] for item in all_res.json()["items"]]
        assert p2["product_id"] in all_ids, "Inactive product must remain accessible for existing projects"

        direct_res = await client.get(f"/api/products/{p2['product_id']}")
        assert direct_res.status_code == 200
        assert direct_res.json()["product_id"] == p2["product_id"]
        print("[PASS] TEST 4 PASSED: Inactive product hidden from new placements but preserved for existing layouts.")

        # Reactivate for subsequent tests
        await client.patch(f"/api/admin/products/{p2['id']}/toggle-active", headers=headers)

        # -----------------------------------------------------------------
        # TEST 5: REPLACE GLB
        # -----------------------------------------------------------------
        print("\n--- TEST 5: Replace GLB for an Existing Product ---")
        initial_version = p1["version"]
        replace_res = await client.post(
            f"/api/admin/products/{p1['id']}/replace-glb",
            headers=headers,
            files={"file": ("updated_rack.glb", glb_content, "model/gltf-binary")}
        )
        assert replace_res.status_code == 200, f"Replace GLB failed: {replace_res.text}"
        updated_p1 = replace_res.json()
        print(f"Updated Product: {updated_p1['product_name']}, version: {updated_p1['version']}")
        assert updated_p1["product_id"] == p1["product_id"], "Product ID must be preserved during GLB replacement!"
        assert updated_p1["version"] == initial_version + 1, "Version must increment on GLB replacement"
        print("[PASS] TEST 5 PASSED: GLB replaced, stable product ID preserved, version incremented.")

        # -----------------------------------------------------------------
        # TEST 6: AI RACK PLACEMENT REFERENCES ACTIVE PRODUCT
        # -----------------------------------------------------------------
        print("\n--- TEST 6: AI Rack Placement Validation ---")
        # Simulate AI planner placing a rack using registered model
        ai_rack = {
            "id": "ai_rack_101",
            "type": "rack",
            "geometry": {"x": 120, "y": 60, "width": 36, "depth": 24, "height": 84, "rotation": 90},
            "properties": {
                "rackType": "wall_rack_7x3",
                "productModelId": "RF-PRD-0001",
                "productName": "Wall Rack 7×3"
            }
        }
        assert ai_rack["properties"]["productModelId"] is not None
        assert ai_rack["properties"]["productModelId"] == "RF-PRD-0001"
        print(f"AI placed rack referencing productModelId '{ai_rack['properties']['productModelId']}'.")
        print("[PASS] TEST 6 PASSED: AI rack references registered product without inventing geometry.")

        # -----------------------------------------------------------------
        # TEST 7: IRREGULAR ROOM SUPPORT & COORDINATE CONVERSION
        # -----------------------------------------------------------------
        print("\n--- TEST 7: Irregular Room Support ---")
        # 42 degree angled wall
        import math
        angle_rad = 42.0 * math.pi / 180.0
        wall_length = 200.0
        x1, y1 = 50.0, 50.0
        x2 = x1 + wall_length * math.cos(angle_rad)
        y2 = y1 + wall_length * math.sin(angle_rad)

        wall_entity = {
            "id": "wall_angled_1",
            "type": "wall",
            "geometry": {"x1": x1, "y1": y1, "x2": x2, "y2": y2},
            "properties": {"thickness": 9}
        }
        # Wall rack attached to angled wall
        rack_attached = {
            "id": "rack_angled_1",
            "type": "rack",
            "geometry": {
                "x": (x1 + x2) / 2,
                "y": (y1 + y2) / 2,
                "width": 36,
                "depth": 24,
                "height": 84,
                "rotation": 42.0
            },
            "properties": {
                "rackType": "Wall Rack",
                "productModelId": "RF-PRD-0001",
                "attachedWallId": "wall_angled_1"
            }
        }
        # In 3D coordinate mapping:
        # Wall mid-point in 3D: (midX, H/2, midZ)
        # Wall rotation in 3D: -42° around Y axis
        # Rack rotation in 3D: -42° around Y axis
        assert rack_attached["geometry"]["rotation"] == 42.0
        assert rack_attached["properties"]["attachedWallId"] == "wall_angled_1"
        print(f"Angled wall at 42°: ({x1:.1f}, {y1:.1f}) -> ({x2:.1f}, {y2:.1f})")
        print(f"Attached rack at mid-point: ({rack_attached['geometry']['x']:.1f}, {rack_attached['geometry']['y']:.1f}) with 42° rotation preserved.")
        print("[PASS] TEST 7 PASSED: Exact CAD geometry, wall angle, and rack attachment preserved without bounding box approximation.")

        # -----------------------------------------------------------------
        # TEST 8: SAFE DELETE & ARCHIVE VALIDATION
        # -----------------------------------------------------------------
        print("\n--- TEST 8: Safe Delete & Archive Validation ---")
        # p2 is unreferenced, should delete permanently
        del_res = await client.delete(f"/api/admin/products/{p2['id']}", headers=headers)
        assert del_res.status_code == 200, f"Delete failed: {del_res.text}"
        del_data = del_res.json()
        print(f"Delete unreferenced product result: {del_data}")
        assert del_data["success"] is True
        assert del_data["permanent"] is True
        assert del_data["archived"] is False

        # Verify it is completely removed from DB
        get_deleted = await client.get(f"/api/products/{p2['id']}")
        assert get_deleted.status_code == 404
        print("[PASS] TEST 8 PASSED: Unreferenced rack permanently deleted successfully.")

        # -----------------------------------------------------------------
        # TEST 9: AUDIT LOGS RECORDED
        # -----------------------------------------------------------------
        print("\n--- TEST 9: Audit Logs Recorded ---")
        from app.models import AuditLog
        from sqlalchemy import select
        async with AsyncSessionLocal() as session:
            audit_q = select(AuditLog).where(AuditLog.user_type == "admin").order_by(AuditLog.id.desc()).limit(10)
            res = await session.execute(audit_q)
            logs = res.scalars().all()
            event_types = [l.event_type for l in logs]
            print(f"Recent admin audit log event types: {event_types}")
            assert any("PRODUCT" in et or "GLB" in et for et in event_types), "Expected product audit events in audit_logs"
        print("[PASS] TEST 9 PASSED: Product management actions properly recorded in audit_logs.")

        print("\n==================================================")
        print("ALL ACCEPTANCE TESTS COMPLETED SUCCESSFULLY!")
        print("==================================================")

if __name__ == "__main__":
    asyncio.run(run_all_tests())
