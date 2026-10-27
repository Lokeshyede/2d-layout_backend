import hashlib
import json
import secrets
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from app.models import Project, CADEntity, Survey, Customer, StoreDetails, ProjectShare, Product3DModel
from app.schemas.share import (
    ShareConfigResponse,
    ShareConfigUpdateRequest,
    CustomerPresentationResponse,
    CustomerProjectSummary,
    RackBreakdownItem,
)
from app.schemas.cad import CADEntitySchema

def utcnow():
    return datetime.now(timezone.utc)

def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()

def generate_secure_share_token() -> str:
    # 256-bit cryptographically secure, URL-safe random string
    return secrets.token_urlsafe(32)

async def get_or_create_project_share(db: AsyncSession, project_id: str) -> ProjectShare:
    query = (
        select(Project)
        .where(Project.project_id == project_id)
        .options(selectinload(Project.shares))
    )
    result = await db.execute(query)
    project = result.scalar_one_or_none()
    if not project:
        raise ValueError(f"Project '{project_id}' not found")

    # Find existing share
    if project.shares:
        share = project.shares[0]
        return share

    # Create new share
    raw_token = generate_secure_share_token()
    token_hash = hash_token(raw_token)
    share = ProjectShare(
        project_id=project.id,
        share_token=raw_token,
        share_token_hash=token_hash,
        is_enabled=True,
        allow_pdf_download=True,
        allow_png_download=True,
        allow_video_download=True,
        view_count=0,
    )
    db.add(share)
    await db.commit()
    await db.refresh(share)
    return share

async def update_project_share(
    db: AsyncSession,
    project_id: str,
    update_req: ShareConfigUpdateRequest
) -> ProjectShare:
    share = await get_or_create_project_share(db, project_id)

    if update_req.regenerateToken:
        new_token = generate_secure_share_token()
        share.share_token = new_token
        share.share_token_hash = hash_token(new_token)

    if update_req.isEnabled is not None:
        share.is_enabled = update_req.isEnabled

    if update_req.expiresAt is not None:
        share.expires_at = update_req.expiresAt

    if update_req.allowPdfDownload is not None:
        share.allow_pdf_download = update_req.allowPdfDownload

    if update_req.allowPngDownload is not None:
        share.allow_png_download = update_req.allowPngDownload

    if update_req.allowVideoDownload is not None:
        share.allow_video_download = update_req.allowVideoDownload

    share.updated_at = utcnow()
    await db.commit()
    await db.refresh(share)
    return share

async def get_project_share_by_token(db: AsyncSession, token: str) -> Optional[ProjectShare]:
    # Match on share_token
    query = (
        select(ProjectShare)
        .where(ProjectShare.share_token == token)
        .options(
            selectinload(ProjectShare.project).selectinload(Project.entities),
            selectinload(ProjectShare.project).selectinload(Project.survey).selectinload(Survey.customer),
        )
    )
    result = await db.execute(query)
    share = result.scalar_one_or_none()
    
    if not share:
        return None

    # Check enabled status
    if not share.is_enabled:
        return None

    # Check expiration if set
    if share.expires_at and share.expires_at < utcnow():
        return None

    # Update analytics safely
    share.view_count = (share.view_count or 0) + 1
    share.last_viewed_at = utcnow()
    await db.commit()

    return share

def parse_rack_display_name(rack_type: str, geom: Dict[str, Any], props: Dict[str, Any]) -> tuple[str, str, str]:
    """
    Returns (displayName, rackCategory, dimensionStr)
    e.g. ("Wall Rack 7×3", "Wall Rack", "7'×3'")
    """
    product_name = props.get("productName")
    rt = (rack_type or props.get("rackType") or "rack").lower()
    
    # Dimensions in feet/inches
    width_in = geom.get("width", 36)
    height_in = geom.get("height", 84)
    depth_in = geom.get("length", geom.get("depth", 18))
    
    # Convert height and width to feet for standard labels (e.g. 7x3)
    h_ft = round(height_in / 12) if height_in else 7
    w_ft = round(width_in / 12) if width_in else 3
    dim_str = f"{h_ft}×{w_ft}"

    if "wall" in rt or props.get("attachedWallId"):
        category = "Wall Rack"
        name = product_name or f"Wall Rack {dim_str}"
    elif "endcap" in rt or "end_cap" in rt or "end cap" in rt:
        category = "Endcap"
        name = product_name or f"Endcap {dim_str}"
    elif "corner" in rt:
        category = "Corner Rack"
        c_w = round(width_in / 12) if width_in else 2
        c_d = round(depth_in / 12) if depth_in else 2
        dim_str = f"{c_w}×{c_d}"
        name = product_name or f"Corner Rack {dim_str}"
    else:
        category = "Center Rack"
        name = product_name or f"Center Rack {dim_str}"

    return name, category, f"{dim_str}"

async def build_customer_presentation(db: AsyncSession, share: ProjectShare) -> CustomerPresentationResponse:
    project = share.project
    survey = project.survey
    customer = survey.customer if survey else None

    # Store details
    store_name = "Retail Store"
    store_type = "Supermarket"
    location = None
    room_size = None

    if customer:
        store_query = select(StoreDetails).where(StoreDetails.customer_id == customer.id)
        store_res = await db.execute(store_query)
        store = store_res.scalars().first()
        if store:
            store_name = store.store_name or store_name
            store_type = store.store_type or store_type
            if store.approx_width and store.approx_height:
                room_size = f"{store.approx_width}' × {store.approx_height}'"
            elif store.store_area:
                room_size = f"{store.store_area} sq ft"

        loc_parts = [p for p in [customer.city, customer.state] if p]
        if loc_parts:
            location = ", ".join(loc_parts)

    # Process CAD Entities (Read-Only)
    entities_list: List[CADEntitySchema] = []
    total_racks = 0
    wall_racks = 0
    center_racks = 0
    endcaps = 0
    corner_racks = 0
    columns = 0
    doors = 0
    windows = 0

    rack_groups: Dict[str, Dict[str, Any]] = {}

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

            etype = ent.entity_type.lower()
            if etype == "rack":
                total_racks += 1
                rt = props.get("rackType", "")
                display_name, category, dim_str = parse_rack_display_name(rt, geom, props)
                
                if category == "Wall Rack":
                    wall_racks += 1
                elif category == "Endcap":
                    endcaps += 1
                elif category == "Corner Rack":
                    corner_racks += 1
                else:
                    center_racks += 1

                # Group rack item
                group_key = f"{category}_{dim_str}_{display_name}"
                if group_key not in rack_groups:
                    rack_groups[group_key] = {
                        "name": display_name,
                        "rackType": category,
                        "dimensions": dim_str,
                        "count": 0
                    }
                rack_groups[group_key]["count"] += 1

            elif etype == "column":
                columns += 1
            elif etype == "door":
                doors += 1
            elif etype == "window":
                windows += 1
        except Exception:
            continue

    rack_breakdown = [
        RackBreakdownItem(
            name=item["name"],
            rackType=item["rackType"],
            dimensions=item["dimensions"],
            count=item["count"]
        )
        for item in rack_groups.values()
    ]
    # Sort breakdown by category then count descending
    rack_breakdown.sort(key=lambda x: (x.rackType, -x.count))

    # Active 3D product models for GLB rendering
    products_query = select(Product3DModel).where(Product3DModel.active == True)
    prod_res = await db.execute(products_query)
    prod_models = prod_res.scalars().all()
    products_data = [
        {
            "id": p.id,
            "productId": p.product_id,
            "productName": p.product_name,
            "productType": p.product_type,
            "sku": p.sku,
            "category": p.category,
            "width": p.width,
            "height": p.height,
            "depth": p.depth,
            "glbUrl": p.glb_url,
            "thumbnailUrl": p.thumbnail_url,
            "scalingMode": p.scaling_mode,
            "shelfCount": p.shelf_count,
            "shelfMode": p.shelf_mode,
        }
        for p in prod_models
    ]

    viewport_dict = {"zoom": 1.0, "panX": 0.0, "panY": 0.0}
    if project.viewport_data:
        try:
            viewport_dict = json.loads(project.viewport_data)
        except Exception:
            pass

    # Status mapping from survey
    status_label = "Layout Proposal"
    if survey and survey.status:
        s_map = {
            "draft": "Draft",
            "survey_completed": "Survey Completed",
            "layout_in_progress": "Layout Ready",
            "layout_completed": "Layout Proposal",
            "approved": "Approved"
        }
        status_label = s_map.get(survey.status, "Layout Proposal")

    summary = CustomerProjectSummary(
        totalRacks=total_racks,
        wallRacks=wall_racks,
        centerRacks=center_racks,
        endcaps=endcaps,
        cornerRacks=corner_racks,
        columns=columns,
        doors=doors,
        windows=windows,
        roomSize=room_size
    )

    return CustomerPresentationResponse(
        storeName=store_name,
        customerName=customer.customer_name if customer else "Valued Client",
        storeType=store_type,
        location=location,
        projectTitle=project.title,
        revision=project.revision,
        status=status_label,
        unit=project.unit or "Feet + Inches",
        scale=project.scale or '1/4" = 1\'-0"',
        viewport=viewport_dict,
        entities=entities_list,
        summary=summary,
        rackBreakdown=rack_breakdown,
        products=products_data,
        allowPdfDownload=share.allow_pdf_download,
        allowPngDownload=share.allow_png_download,
        allowVideoDownload=share.allow_video_download,
    )
