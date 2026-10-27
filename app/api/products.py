import json
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.api.auth import get_current_admin
from app.models import Admin, Product3DModel
from app.schemas.product import (
    ProductModelCreate,
    ProductModelUpdate,
    ProductModelResponse,
    ProductModelListResponse,
    ProductReferenceCheckResponse,
    GLBUploadResponse,
    DetectedDimensions,
)
from app.services.product_service import (
    validate_and_parse_glb,
    save_glb_file,
    get_all_products,
    get_active_products,
    get_product_by_id,
    check_product_references,
    create_product,
    update_product,
    replace_product_glb,
    toggle_product_active,
    archive_product,
    safe_delete_product,
)

router = APIRouter(tags=["products"])


# -------------------------------------------------------------
# Public / CAD Endpoints
# -------------------------------------------------------------

@router.get("/products", response_model=ProductModelListResponse)
@router.get("/product-models/active", response_model=ProductModelListResponse)
async def list_products(
    search: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    include_inactive: bool = Query(False),
    db: AsyncSession = Depends(get_db)
):
    """
    List products available for CAD and 3D rendering.
    By default returns only active products unless include_inactive=True.
    """
    products = await get_all_products(
        db=db,
        search=search,
        category=category,
        active_only=not include_inactive
    )
    return ProductModelListResponse(
        items=[ProductModelResponse.model_validate(p) for p in products],
        total=len(products)
    )


@router.get("/products/{id_or_code}", response_model=ProductModelResponse)
async def get_product(
    id_or_code: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Get a single product model by its numeric ID or product code (e.g. RF-PRD-0001).
    """
    product = await get_product_by_id(db, id_or_code)
    if not product:
        raise HTTPException(status_code=404, detail="Product model not found")
    return ProductModelResponse.model_validate(product)


# -------------------------------------------------------------
# Admin Management Endpoints (Secured)
# -------------------------------------------------------------

@router.get("/admin/products", response_model=ProductModelListResponse)
@router.get("/admin/product-models", response_model=ProductModelListResponse)
async def admin_list_products(
    search: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    include_inactive: bool = Query(True),
    admin: Admin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Admin: List all product models including active/inactive status.
    """
    products = await get_all_products(
        db=db,
        search=search,
        category=category,
        active_only=not include_inactive
    )
    return ProductModelListResponse(
        items=[ProductModelResponse.model_validate(p) for p in products],
        total=len(products)
    )


@router.get("/admin/products/{product_id}", response_model=ProductModelResponse)
@router.get("/admin/product-models/{product_id}", response_model=ProductModelResponse)
async def admin_get_product(
    product_id: int,
    admin: Admin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Admin: Get full details of a product model for View mode.
    """
    product = await get_product_by_id(db, str(product_id))
    if not product:
        raise HTTPException(status_code=404, detail="Product model not found")
    return ProductModelResponse.model_validate(product)


@router.get("/admin/products/{product_id}/reference-check", response_model=ProductReferenceCheckResponse)
async def get_product_reference_check(
    product_id: int,
    admin: Admin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Admin: Check if a product model is referenced by existing CAD projects.
    Returns whether it can be permanently deleted or must be archived.
    """
    try:
        result = await check_product_references(db, product_id)
        return ProductReferenceCheckResponse(**result)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to check product references: {str(e)}")


@router.post("/admin/products/upload-glb", response_model=GLBUploadResponse)
async def upload_glb_file(
    file: UploadFile = File(...),
    admin: Admin = Depends(get_current_admin)
):
    """
    Admin: Upload and validate a new .glb 3D model.
    Validates glTF binary structure, mesh presence, and computes detected dimensions.
    """
    filename_lower = file.filename.lower()
    if not (filename_lower.endswith(".glb") or filename_lower.endswith(".gltf")):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only .glb and .gltf files are accepted."
        )

    file_bytes = await file.read()
    if len(file_bytes) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty."
        )

    try:
        val_result = validate_and_parse_glb(file_bytes, file.filename)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"GLB validation failed: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unexpected error validating GLB: {str(e)}"
        )

    storage_path, glb_url = save_glb_file(file_bytes, file.filename)

    return GLBUploadResponse(
        storage_path=storage_path,
        glb_url=glb_url,
        file_name=file.filename,
        file_size=len(file_bytes),
        detected_dimensions=val_result["detected_dimensions"],
        mesh_count=val_result["mesh_count"],
        materials=val_result["materials"],
        valid=True,
        message="GLB file validated and uploaded successfully."
    )


@router.post("/admin/products", response_model=ProductModelResponse)
@router.post("/admin/product-models", response_model=ProductModelResponse)
async def create_new_product(
    payload: ProductModelCreate,
    admin: Admin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Admin: Register a new 3D product model in the library.
    Validates SKU uniqueness, dimension constraints, and logs audit record.
    """
    try:
        product = await create_product(db, payload, admin_user=admin.username)
        return ProductModelResponse.model_validate(product)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create product: {str(e)}")


@router.put("/admin/products/{product_id}", response_model=ProductModelResponse)
@router.patch("/admin/products/{product_id}", response_model=ProductModelResponse)
@router.patch("/admin/product-models/{product_id}", response_model=ProductModelResponse)
async def update_existing_product(
    product_id: int,
    payload: ProductModelUpdate,
    admin: Admin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Admin: Update product metadata (name, sku, category, dimensions, shelf settings).
    Validates unique SKU and dimension bounds.
    """
    try:
        updated = await update_product(db, product_id, payload, admin_user=admin.username)
        if not updated:
            raise HTTPException(status_code=404, detail="Product model not found")
        return ProductModelResponse.model_validate(updated)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update product: {str(e)}")


@router.post("/admin/products/{product_id}/replace-glb", response_model=ProductModelResponse)
async def replace_glb(
    product_id: int,
    file: UploadFile = File(...),
    admin: Admin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Admin: Replace GLB model for an existing product. Preserves product_id and increments version.
    Does NOT alter existing saved CAD entity geometry.
    """
    filename_lower = file.filename.lower()
    if not (filename_lower.endswith(".glb") or filename_lower.endswith(".gltf")):
        raise HTTPException(status_code=400, detail="Only .glb and .gltf files are accepted.")

    file_bytes = await file.read()
    try:
        val_result = validate_and_parse_glb(file_bytes, file.filename)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=f"GLB validation failed: {str(e)}")

    storage_path, glb_url = save_glb_file(file_bytes, file.filename)

    meta_str = json.dumps({
        "detected_width": val_result["detected_dimensions"].width_inches,
        "detected_height": val_result["detected_dimensions"].height_inches,
        "detected_depth": val_result["detected_dimensions"].depth_inches,
        "mesh_count": val_result["mesh_count"],
        "materials": val_result["materials"],
        "replaced_filename": file.filename
    })

    updated = await replace_product_glb(db, product_id, storage_path, glb_url, meta_str, admin_user=admin.username)
    if not updated:
        raise HTTPException(status_code=404, detail="Product model not found")

    return ProductModelResponse.model_validate(updated)


@router.patch("/admin/products/{product_id}/toggle-active", response_model=ProductModelResponse)
async def toggle_active(
    product_id: int,
    admin: Admin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Admin: Toggle active status of product model.
    Active products appear in CAD Add Rack; inactive products disappear from new placements.
    """
    updated = await toggle_product_active(db, product_id, admin_user=admin.username)
    if not updated:
        raise HTTPException(status_code=404, detail="Product model not found")
    return ProductModelResponse.model_validate(updated)


@router.patch("/admin/products/{product_id}/archive", response_model=ProductModelResponse)
async def archive_product_endpoint(
    product_id: int,
    admin: Admin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Admin: Explicitly archive a product model.
    """
    success, message, product = await archive_product(db, product_id, admin_user=admin.username)
    if not success or not product:
        raise HTTPException(status_code=404, detail=message)
    return ProductModelResponse.model_validate(product)


@router.delete("/admin/products/{product_id}")
@router.delete("/admin/product-models/{product_id}")
async def delete_product(
    product_id: int,
    force_delete: bool = Query(False),
    admin: Admin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Admin: Safely delete or archive a product model.
    If referenced by existing CAD projects, blocks permanent deletion and archives instead.
    """
    success, message, was_archived = await safe_delete_product(db, product_id, admin_user=admin.username)
    if not success:
        raise HTTPException(status_code=404, detail=message)
    return {
        "success": True,
        "message": message,
        "archived": was_archived,
        "permanent": not was_archived
    }
