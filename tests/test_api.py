import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.core.database import engine, Base

@pytest.mark.asyncio
async def test_health():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/api/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"

@pytest.mark.asyncio
async def test_survey_creation_and_cad_flow():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # 1. Create survey
        survey_payload = {
            "customer": {
                "customerName": "Metro Supermarket",
                "ownerName": "Rajesh Kumar",
                "mobileNumber": "+91 9876543210",
                "whatsAppNumber": "+91 9876543210",
                "email": "rajesh@metrosuper.com",
                "storeAddress": "123 Commercial Street",
                "city": "Bengaluru",
                "state": "Karnataka",
                "pincode": "560001"
            },
            "store": {
                "storeName": "Metro Supermarket Flagship",
                "storeType": "Supermarket",
                "storeArea": "2500 sq ft",
                "approxWidth": "50'-0\"",
                "approxHeight": "50'-0\"",
                "unit": "Feet + Inches"
            },
            "survey": {
                "surveyDate": "2026-08-23",
                "salesmanName": "Suresh Surveyor",
                "siteContactPerson": "Rajesh Kumar",
                "remarks": "Corner property with 2 entry shutters",
                "specialRequirements": "Include central gondola racks with 4ft aisles"
            }
        }
        
        create_res = await ac.post("/api/surveys", json=survey_payload)
        assert create_res.status_code == 200, create_res.text
        survey_data = create_res.json()
        assert "RF-SUR-" in survey_data["surveyId"]
        assert survey_data["secureToken"] is not None
        survey_id = survey_data["surveyId"]

        # 2. Get project CAD state
        proj_res = await ac.get(f"/api/projects/{survey_id}")
        assert proj_res.status_code == 200
        proj_data = proj_res.json()
        assert proj_data["projectId"] == survey_id
        assert proj_data["customerName"] == "Metro Supermarket"

        # 3. Save CAD entities (Wall + Column + Door + Rack)
        save_payload = {
            "title": "Metro Supermarket Flagship - 2D CAD Store Layout",
            "scale": '1/4" = 1\'-0"',
            "unit": "Feet + Inches",
            "viewport": {"zoom": 1.2, "panX": 100, "panY": 50},
            "entities": [
                {
                    "id": "w1",
                    "type": "wall",
                    "geometry": {"x1": 0, "y1": 0, "x2": 600, "y2": 0},
                    "properties": {"thickness": 9}
                },
                {
                    "id": "w2",
                    "type": "wall",
                    "geometry": {"x1": 600, "y1": 0, "x2": 600, "y2": 600},
                    "properties": {"thickness": 9}
                },
                {
                    "id": "col1",
                    "type": "column",
                    "geometry": {"x": 300, "y": 0, "width": 24, "height": 24},
                    "properties": {"columnType": "wall", "inwardProjection": 24}
                },
                {
                    "id": "door1",
                    "type": "door",
                    "geometry": {"x": 150, "y": 0, "width": 36, "height": 9},
                    "properties": {"doorType": "single", "swing": "inward"}
                },
                {
                    "id": "rack1",
                    "type": "rack",
                    "geometry": {"x": 300, "y": 300, "width": 84, "depth": 36},
                    "properties": {"rackType": "Center Gondola", "modules": 2}
                }
            ],
            "createRevision": True,
            "revisionName": "REV 2"
        }
        
        save_res = await ac.put(f"/api/projects/{survey_id}", json=save_payload)
        assert save_res.status_code == 200
        saved_data = save_res.json()
        assert len(saved_data["entities"]) == 5
        assert saved_data["revision"] == "REV 2"

        # 4. Generate ReportLab PDF Drawing Sheet
        pdf_res = await ac.get(f"/api/projects/{survey_id}/export/pdf")
        assert pdf_res.status_code == 200
        assert pdf_res.headers["content-type"] == "application/pdf"
        assert len(pdf_res.content) > 1000

        # 5. Admin Login & Dashboard
        login_res = await ac.post("/api/admin/login", json={"username": "admin", "password": "retailfix@2026"})
        assert login_res.status_code == 200
        token = login_res.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        dash_res = await ac.get("/api/admin/dashboard", headers=headers)
        assert dash_res.status_code == 200
        dash_data = dash_res.json()
        assert dash_data["totalSurveys"] >= 1

        # 6. Admin Search
        search_res = await ac.get("/api/admin/surveys?search=Metro", headers=headers)
        assert search_res.status_code == 200
        assert len(search_res.json()["items"]) >= 1
