import json
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List
from app.core.database import get_db
from app.services.cad_service import get_project_by_id, save_project_state
from app.services.survey_service import get_store_details_by_customer
from app.schemas.cad import ProjectSaveRequest, ProjectResponse, CADEntitySchema

router = APIRouter(prefix="/projects", tags=["projects"])

@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: str,
    token: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    project = await get_project_by_id(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Serialize entities
    entities_list = []
    for ent in (project.entities or []):
        try:
            geom = json.loads(ent.geometry_json) if ent.geometry_json else {}
            props = json.loads(ent.properties_json) if ent.properties_json else {}
            entities_list.append(CADEntitySchema(
                id=ent.entity_id,
                type=ent.entity_type,
                geometry=geom,
                properties=props,
                layer=ent.layer,
                zIndex=ent.z_index
            ))
        except Exception:
            continue

    # Versions list
    versions_list = []
    for v in (project.versions or []):
        versions_list.append({
            "id": v.id,
            "revisionName": v.revision_name,
            "createdBy": v.created_by,
            "createdAt": v.created_at.isoformat()
        })

    # Customer and Store details
    cust_name = None
    store_name = None
    store_type = None
    approx_w = None
    approx_h = None
    survey_date = None

    if project.survey:
        survey_date = project.survey.survey_date
        if project.survey.customer:
            cust_name = project.survey.customer.customer_name
            store = await get_store_details_by_customer(db, project.survey.customer.id)
            if store:
                store_name = store.store_name
                store_type = store.store_type
                approx_w = store.approx_width
                approx_h = store.approx_height

    viewport_dict = {"zoom": 1.0, "panX": 0.0, "panY": 0.0}
    if project.viewport_data:
        try:
            viewport_dict = json.loads(project.viewport_data)
        except Exception:
            pass

    return ProjectResponse(
        projectId=project.project_id,
        surveyId=project.survey.survey_id if project.survey else project.project_id,
        title=project.title,
        revision=project.revision,
        viewport=viewport_dict,
        scale=project.scale,
        unit=project.unit,
        notes=project.notes,
        entities=entities_list,
        versions=versions_list,
        customerName=cust_name,
        storeName=store_name,
        storeType=store_type,
        approxWidth=approx_w,
        approxHeight=approx_h,
        surveyDate=survey_date,
        updatedAt=project.updated_at.isoformat() if project.updated_at else None
    )

@router.put("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: str,
    save_req: ProjectSaveRequest,
    token: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    try:
        project = await save_project_state(db, project_id, save_req, user_type="customer")
        return await get_project(project_id, token, db)
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to save project: {str(e)}")
