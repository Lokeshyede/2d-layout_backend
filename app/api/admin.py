from datetime import datetime, date, timezone
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from sqlalchemy import func, desc, or_, delete
from typing import Optional, List
from app.core.database import get_db
from app.api.auth import get_current_admin
from app.models import Admin, Survey, Customer, StoreDetails, Project, CADEntity, SurveyPhoto
from app.services.survey_service import get_store_details_by_customer
from app.schemas.survey import SurveyListItem, SurveyResponse, CustomerInfoSchema, StoreInfoSchema, SurveyInfoSchema, SurveyPhotoResponse
from app.schemas.admin import DashboardStats

router = APIRouter(prefix="/admin", tags=["admin"])

@router.get("/dashboard", response_model=DashboardStats)
async def get_admin_dashboard_stats(
    admin: Admin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    total_q = select(func.count(Survey.id))
    total_res = await db.execute(total_q)
    total_surveys = total_res.scalar() or 0

    today_date = datetime.now(timezone.utc).date()
    today_q = select(func.count(Survey.id)).where(func.date(Survey.created_at) == today_date)
    today_res = await db.execute(today_q)
    today_surveys = today_res.scalar() or 0

    comp_q = select(func.count(Survey.id)).where(Survey.status.in_(["layout_completed", "survey_completed"]))
    comp_res = await db.execute(comp_q)
    completed_layouts = comp_res.scalar() or 0
    draft_layouts = max(0, total_surveys - completed_layouts)

    dist_q = select(StoreDetails.store_type, func.count(StoreDetails.id)).group_by(StoreDetails.store_type)
    dist_res = await db.execute(dist_q)
    store_types = {r[0]: r[1] for r in dist_res.all()}

    recent_q = (
        select(Survey)
        .options(
            selectinload(Survey.customer),
            selectinload(Survey.project).selectinload(Project.entities)
        )
        .order_by(desc(Survey.created_at))
        .limit(10)
    )
    recent_res = await db.execute(recent_q)
    recent_items = []
    for s in recent_res.scalars().all():
        store = await get_store_details_by_customer(db, s.customer_id)
        recent_items.append({
            "id": s.id,
            "surveyId": s.survey_id,
            "projectId": s.project.project_id if s.project else s.survey_id,
            "customerName": s.customer.customer_name if s.customer else "Unknown",
            "storeName": store.store_name if store else "Retail Store",
            "mobileNumber": s.customer.mobile_number if s.customer else "-",
            "city": s.customer.city if s.customer else "-",
            "storeType": store.store_type if store else "Supermarket",
            "surveyDate": s.survey_date,
            "status": s.status,
            "revision": s.project.revision if s.project else "REV 1",
            "entityCount": len(s.project.entities) if (s.project and s.project.entities) else 0,
            "createdAt": s.created_at.isoformat()
        })

    return DashboardStats(
        totalSurveys=total_surveys,
        todaySurveys=today_surveys,
        completedLayouts=completed_layouts,
        draftLayouts=draft_layouts,
        storeTypeDistribution=store_types,
        recentSurveys=recent_items
    )

@router.get("/surveys")
async def list_surveys_for_admin(
    search: Optional[str] = Query(None),
    store_type: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    surveyor: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    admin: Admin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    query = (
        select(Survey)
        .options(
            selectinload(Survey.customer),
            selectinload(Survey.project).selectinload(Project.entities)
        )
    )

    if status:
        query = query.where(Survey.status == status)
    if surveyor:
        query = query.where(Survey.salesman_name.ilike(f"%{surveyor}%"))

    query = query.order_by(desc(Survey.created_at))
    result = await db.execute(query)
    all_surveys = result.scalars().all()

    filtered = []
    for s in all_surveys:
        store = await get_store_details_by_customer(db, s.customer_id)
        s_type = store.store_type if store else ""
        s_name = store.store_name if store else ""
        c_name = s.customer.customer_name if s.customer else ""
        c_mobile = s.customer.mobile_number if s.customer else ""
        c_city = s.customer.city if s.customer else ""

        if store_type and store_type != "All" and s_type.lower() != store_type.lower():
            continue

        if search:
            s_low = search.lower()
            match = (
                s_low in s.survey_id.lower() or
                s_low in c_name.lower() or
                s_low in s_name.lower() or
                s_low in c_mobile.lower() or
                (c_city and s_low in c_city.lower())
            )
            if not match:
                continue

        filtered.append({
            "id": s.id,
            "surveyId": s.survey_id,
            "projectId": s.project.project_id if s.project else s.survey_id,
            "customerName": c_name,
            "ownerName": s.customer.owner_name if s.customer else "",
            "storeName": s_name,
            "mobileNumber": c_mobile,
            "city": c_city,
            "storeType": s_type or "Supermarket",
            "surveyDate": s.survey_date,
            "status": s.status,
            "revision": s.project.revision if s.project else "REV 1",
            "entityCount": len(s.project.entities) if (s.project and s.project.entities) else 0,
            "createdAt": s.created_at.isoformat()
        })

    total = len(filtered)
    start = (page - 1) * limit
    paged_items = filtered[start:start + limit]

    return {
        "items": paged_items,
        "total": total,
        "page": page,
        "limit": limit,
        "totalPages": (total + limit - 1) // limit if limit > 0 else 1
    }

@router.delete("/surveys/{survey_id}")
async def delete_survey_admin(
    survey_id: str,
    admin: Admin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    query = select(Survey).where(Survey.survey_id == survey_id).options(selectinload(Survey.customer))
    result = await db.execute(query)
    survey = result.scalar_one_or_none()
    if not survey:
        raise HTTPException(status_code=404, detail="Survey not found")

    await db.delete(survey)
    await db.commit()
    return {"message": f"Survey {survey_id} deleted successfully"}
