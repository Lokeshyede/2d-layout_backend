import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.core.database import engine, Base

@pytest.mark.asyncio
async def test_share_system_comprehensive():
    """
    Comprehensive Phase 5 Verification:
    - Share link generation
    - Cryptographic security
    - Read-only data presentation
    - Rack breakdown counts
    - Revocation & re-enabling
    - Direct PDF streaming
    - CAD state immutability (integrity test)
    - Multi-project isolation
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # Step 1: Create Project A
        survey_payload_a = {
            "customer": {
                "customerName": "Customer A Retail",
                "mobileNumber": "+91 9111111111",
                "city": "Mumbai",
                "state": "Maharashtra"
            },
            "store": {
                "storeName": "Store A General",
                "storeType": "Supermarket",
                "approxWidth": "10'-0\"",
                "approxHeight": "20'-0\"",
                "unit": "Feet + Inches"
            },
            "survey": {
                "surveyDate": "2026-09-30"
            }
        }
        res_a = await ac.post("/api/surveys", json=survey_payload_a)
        assert res_a.status_code == 200, res_a.text
        proj_a_id = res_a.json()["projectId"]
        token_a = res_a.json()["secureToken"]

        # Step 2: Save 10x20 CAD Layout with Wall Racks, Columns, and Doors in Project A
        cad_payload_a = {
            "title": "Store A Layout",
            "scale": "1/4\" = 1'-0\"",
            "unit": "Feet + Inches",
            "entities": [
                # 4 Walls (10' x 20' = 120" x 240")
                {"id": "w1", "type": "wall", "geometry": {"x1": 0, "y1": 0, "x2": 120, "y2": 0}, "properties": {"thickness": 6}},
                {"id": "w2", "type": "wall", "geometry": {"x1": 120, "y1": 0, "x2": 120, "y2": 240}, "properties": {"thickness": 6}},
                {"id": "w3", "type": "wall", "geometry": {"x1": 120, "y1": 240, "x2": 0, "y2": 240}, "properties": {"thickness": 6}},
                {"id": "w4", "type": "wall", "geometry": {"x1": 0, "y1": 240, "x2": 0, "y2": 0}, "properties": {"thickness": 6}},
                # 1 Column
                {"id": "c1", "type": "column", "geometry": {"x": 60, "y": 120, "width": 12, "length": 12}, "properties": {}},
                # 1 Door
                {"id": "d1", "type": "door", "geometry": {"x": 30, "y": 0, "width": 36}, "properties": {}},
                # 3 Wall Racks 7x3
                {"id": "r1", "type": "rack", "geometry": {"x": 10, "y": 50, "width": 36, "height": 84, "length": 18}, "properties": {"rackType": "wall_rack_7x3", "productName": "Wall Rack 7×3"}},
                {"id": "r2", "type": "rack", "geometry": {"x": 10, "y": 90, "width": 36, "height": 84, "length": 18}, "properties": {"rackType": "wall_rack_7x3", "productName": "Wall Rack 7×3"}},
                {"id": "r3", "type": "rack", "geometry": {"x": 10, "y": 130, "width": 36, "height": 84, "length": 18}, "properties": {"rackType": "wall_rack_7x3", "productName": "Wall Rack 7×3"}},
                # 1 Center Rack 5x3
                {"id": "r4", "type": "rack", "geometry": {"x": 60, "y": 60, "width": 36, "height": 60, "length": 36}, "properties": {"rackType": "center_rack_5x3", "productName": "Center Rack 5×3"}}
            ]
        }
        put_a = await ac.put(f"/api/projects/{proj_a_id}?token={token_a}", json=cad_payload_a)
        assert put_a.status_code == 200, put_a.text
        initial_entity_count = len(cad_payload_a["entities"])
        assert initial_entity_count == 10

        # Step 3: Admin generates/gets Share Link for Project A
        share_res_a = await ac.get(f"/api/projects/{proj_a_id}/share")
        assert share_res_a.status_code == 200, share_res_a.text
        share_data_a = share_res_a.json()
        share_token_a = share_data_a["shareToken"]
        
        # Verify Token Security: long, URL-safe, non-sequential, not based on ID
        assert len(share_token_a) >= 32
        assert proj_a_id not in share_token_a
        assert share_data_a["isEnabled"] is True

        # Step 4: Customer views project via GET /api/share/{token}
        cust_res = await ac.get(f"/api/share/{share_token_a}")
        assert cust_res.status_code == 200, cust_res.text
        presentation = cust_res.json()

        # Check accurate project & summary fields
        assert presentation["storeName"] == "Store A General"
        assert presentation["customerName"] == "Customer A Retail"
        assert presentation["status"] == "Layout Proposal"
        assert presentation["summary"]["totalRacks"] == 4
        assert presentation["summary"]["wallRacks"] == 3
        assert presentation["summary"]["centerRacks"] == 1
        assert presentation["summary"]["columns"] == 1
        assert presentation["summary"]["doors"] == 1
        assert presentation["summary"]["windows"] == 0

        # Check rack breakdown counts
        breakdown = presentation["rackBreakdown"]
        wall_item = next((b for b in breakdown if "Wall Rack" in b["name"]), None)
        center_item = next((b for b in breakdown if "Center Rack" in b["name"]), None)
        assert wall_item is not None and wall_item["count"] == 3
        assert center_item is not None and center_item["count"] == 1

        # Check data minimization (NO internal admin details or DB passwords)
        assert "hashed_password" not in cust_res.text
        assert "audit_logs" not in cust_res.text

        # Step 5: Customer downloads PDF
        pdf_res = await ac.get(f"/api/share/{share_token_a}/pdf")
        assert pdf_res.status_code == 200
        assert pdf_res.headers["content-type"] == "application/pdf"
        assert len(pdf_res.content) > 1000

        # Step 6: Token Revocation Test
        # Admin disables sharing
        disable_res = await ac.post(f"/api/projects/{proj_a_id}/share", json={"isEnabled": False})
        assert disable_res.status_code == 200
        assert disable_res.json()["isEnabled"] is False

        # Customer tries to access revoked link -> returns 404
        revoked_res = await ac.get(f"/api/share/{share_token_a}")
        assert revoked_res.status_code == 404
        assert "Project Unavailable" in revoked_res.json()["detail"]

        # Admin re-enables sharing
        re_enable_res = await ac.post(f"/api/projects/{proj_a_id}/share", json={"isEnabled": True})
        assert re_enable_res.status_code == 200
        assert re_enable_res.json()["isEnabled"] is True

        # Customer access restored
        restored_res = await ac.get(f"/api/share/{share_token_a}")
        assert restored_res.status_code == 200

        # Step 7: CAD Integrity Test (Verify entity count remains exactly unchanged)
        verify_cad = await ac.get(f"/api/projects/{proj_a_id}")
        assert verify_cad.status_code == 200
        assert len(verify_cad.json()["entities"]) == initial_entity_count

        # Step 8: Multi-Project Isolation Test
        # Create Project B
        survey_payload_b = {
            "customer": {"customerName": "Customer B Mart", "mobileNumber": "+91 9222222222"},
            "store": {"storeName": "Store B Express", "storeType": "Convenience"},
            "survey": {"surveyDate": "2026-09-30"}
        }
        res_b = await ac.post("/api/surveys", json=survey_payload_b)
        proj_b_id = res_b.json()["projectId"]
        
        share_res_b = await ac.get(f"/api/projects/{proj_b_id}/share")
        share_token_b = share_res_b.json()["shareToken"]
        
        # Share tokens must be different and distinct
        assert share_token_a != share_token_b

        # Link A sees Store A; Link B sees Store B
        cust_a_view = (await ac.get(f"/api/share/{share_token_a}")).json()
        cust_b_view = (await ac.get(f"/api/share/{share_token_b}")).json()
        assert cust_a_view["storeName"] == "Store A General"
        assert cust_b_view["storeName"] == "Store B Express"
        assert cust_a_view["customerName"] == "Customer A Retail"
        assert cust_b_view["customerName"] == "Customer B Mart"
