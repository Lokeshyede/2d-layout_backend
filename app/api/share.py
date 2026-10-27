import json
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Dict, Any

from app.core.database import get_db
from app.services.share_service import (
    get_or_create_project_share,
    update_project_share,
    get_project_share_by_token,
    build_customer_presentation,
)
from app.services.pdf_service import generate_architectural_pdf
from app.services.survey_service import get_store_details_by_customer
from app.schemas.share import (
    ShareConfigResponse,
    ShareConfigUpdateRequest,
    CustomerPresentationResponse,
)

router = APIRouter(tags=["share"])

# ============================================================
# CUSTOMER PUBLIC READ-ONLY ENDPOINTS
# ============================================================

@router.get("/share/{token}", response_model=CustomerPresentationResponse)
async def get_customer_presentation(
    token: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Public read-only customer presentation endpoint.
    Returns sanitized project data without internal admin details.
    """
    share = await get_project_share_by_token(db, token)
    if not share or not share.project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project Unavailable: This customer project link is no longer active or valid."
        )

    presentation = await build_customer_presentation(db, share)
    return presentation


@router.get("/share/{token}/pdf")
async def get_customer_shared_pdf(
    token: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Direct read-only PDF download for shared customer projects.
    Uses existing architectural PDF generation without mutating CAD state.
    """
    share = await get_project_share_by_token(db, token)
    if not share or not share.project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project Unavailable: Link is inactive or invalid."
        )

    if not share.allow_pdf_download:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="PDF download is disabled for this project share."
        )

    project = share.project
    survey = project.survey
    customer = survey.customer if survey else None
    store = await get_store_details_by_customer(db, customer.id) if customer else None

    # Format entities data for PDF generator
    entities_data = []
    for ent in (project.entities or []):
        try:
            geom = json.loads(ent.geometry_json) if ent.geometry_json else {}
            props = json.loads(ent.properties_json) if ent.properties_json else {}
            entities_data.append({
                "id": ent.entity_id,
                "type": ent.entity_type,
                "geometry": geom,
                "properties": props
            })
        except Exception:
            continue

    project_dict = {
        "title": project.title,
        "revision": project.revision,
        "scale": project.scale,
        "unit": project.unit,
        "notes": project.notes,
        "entities": entities_data
    }

    survey_dict = {
        "surveyId": survey.survey_id if survey else project.project_id,
        "surveyDate": survey.survey_date if survey else "",
        "customer": {
            "customerName": customer.customer_name if customer else "Customer",
            "ownerName": customer.owner_name if customer else "",
            "mobileNumber": customer.mobile_number if customer else "",
            "city": customer.city if customer else "",
            "state": customer.state if customer else ""
        },
        "store": {
            "storeName": store.store_name if store else "Retail Store",
            "storeType": store.store_type if store else "Supermarket",
            "storeArea": store.store_area if store else ""
        },
        "survey": {
            "salesmanName": survey.salesman_name if survey else "RetailFix Surveyor",
            "siteContactPerson": survey.site_contact_person if survey else ""
        }
    }

    pdf_buffer = generate_architectural_pdf(project_dict, survey_dict)
    filename = f"RetailFix_{project.project_id}_{project.revision}.pdf"

    return StreamingResponse(
        pdf_buffer,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"'
        }
    )


# ============================================================
# ADMIN SHARING MANAGEMENT ENDPOINTS
# ============================================================

@router.get("/projects/{project_id}/share", response_model=ShareConfigResponse)
async def get_project_share_config(
    project_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Get sharing configuration for a project (Admin).
    """
    share = await get_or_create_project_share(db, project_id)
    share_url = f"/share/project/{share.share_token}"
    return ShareConfigResponse(
        shareToken=share.share_token,
        shareUrl=share_url,
        isEnabled=share.is_enabled,
        expiresAt=share.expires_at.isoformat() if share.expires_at else None,
        viewCount=share.view_count or 0,
        lastViewedAt=share.last_viewed_at.isoformat() if share.last_viewed_at else None,
        allowPdfDownload=share.allow_pdf_download,
        allowPngDownload=share.allow_png_download,
        allowVideoDownload=share.allow_video_download,
    )


@router.post("/projects/{project_id}/share", response_model=ShareConfigResponse)
async def update_project_share_config(
    project_id: str,
    update_req: ShareConfigUpdateRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Update sharing configuration (Enable/Disable, Expiration, Regenerate Token).
    """
    share = await update_project_share(db, project_id, update_req)
    share_url = f"/share/project/{share.share_token}"
    return ShareConfigResponse(
        shareToken=share.share_token,
        shareUrl=share_url,
        isEnabled=share.is_enabled,
        expiresAt=share.expires_at.isoformat() if share.expires_at else None,
        viewCount=share.view_count or 0,
        lastViewedAt=share.last_viewed_at.isoformat() if share.last_viewed_at else None,
        allowPdfDownload=share.allow_pdf_download,
        allowPngDownload=share.allow_png_download,
        allowVideoDownload=share.allow_video_download,
    )
