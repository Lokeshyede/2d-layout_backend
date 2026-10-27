import os
import re
import uuid
import struct
import json
import shutil
from typing import Optional, List, Dict, Any, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import desc, or_

from app.core.config import settings
from app.models import Product3DModel, CADEntity, AuditLog, Project, utcnow
from app.schemas.product import ProductModelCreate, ProductModelUpdate, DetectedDimensions

MODELS_DIR = os.path.join(settings.UPLOAD_DIR, "models")
os.makedirs(MODELS_DIR, exist_ok=True)


def validate_and_parse_glb(file_bytes: bytes, original_filename: str) -> Dict[str, Any]:
    """
    Validates a GLB file:
    - Verifies extension
    - Checks 12-byte GLB header (magic b'glTF', version 2)
    - Parses JSON chunk (chunk 0)
    - Verifies presence of meshes/geometry
    - Computes bounding box and detected dimensions
    """
    if not original_filename.lower().endswith(".glb"):
        raise ValueError("Invalid file extension. Only .glb files are accepted.")

    if len(file_bytes) < 20:
        raise ValueError("File is too small or corrupted to be a valid GLB.")

    # GLB header: 4 bytes magic, 4 bytes version, 4 bytes length
    magic, version, total_length = struct.unpack("<4sII", file_bytes[:12])
    if magic != b"glTF":
        raise ValueError("Invalid GLB header. Missing glTF magic identifier.")
    if version not in (1, 2):
        raise ValueError(f"Unsupported glTF version: {version}. Version 2 is required.")

    # Read chunk 0 (JSON chunk)
    chunk_len, chunk_type = struct.unpack("<II", file_bytes[12:20])
    if chunk_type != 0x4E4F534A:  # ASCII for 'JSON'
        raise ValueError("Malformed GLB chunk. First chunk must be JSON.")

    json_bytes = file_bytes[20:20 + chunk_len]
    try:
        gltf = json.loads(json_bytes.decode("utf-8"))
    except Exception as e:
        raise ValueError(f"Failed to parse GLTF JSON payload: {str(e)}")

    meshes = gltf.get("meshes", [])
    if not meshes:
        raise ValueError("GLB file contains no renderable meshes.")

    # Check for primitives
    total_primitives = sum(len(m.get("primitives", [])) for m in meshes)
    if total_primitives == 0:
        raise ValueError("GLB file meshes contain no renderable geometry primitives.")

    # Collect material names
    materials = []
    for mat in gltf.get("materials", []):
        mat_name = mat.get("name")
        if mat_name:
            materials.append(mat_name)

    # Compute bounding box from accessors and node transforms
    accessors = gltf.get("accessors", [])
    nodes = gltf.get("nodes", [])

    def _mat4_identity() -> List[float]:
        return [
            1.0, 0.0, 0.0, 0.0,
            0.0, 1.0, 0.0, 0.0,
            0.0, 0.0, 1.0, 0.0,
            0.0, 0.0, 0.0, 1.0,
        ]

    def _mat4_multiply(a: List[float], b: List[float]) -> List[float]:
        out = [0.0] * 16
        for col in range(4):
            for row in range(4):
                val = 0.0
                for k in range(4):
                    val += a[k * 4 + row] * b[col * 4 + k]
                out[col * 4 + row] = val
        return out

    def _mat4_transform_point(m: List[float], p: List[float]) -> List[float]:
        x, y, z = p
        w = m[3] * x + m[7] * y + m[11] * z + m[15]
        if abs(w) < 1e-9:
            w = 1.0
        return [
            (m[0] * x + m[4] * y + m[8] * z + m[12]) / w,
            (m[1] * x + m[5] * y + m[9] * z + m[13]) / w,
            (m[2] * x + m[6] * y + m[10] * z + m[14]) / w,
        ]

    def _get_node_matrix(n: Dict[str, Any]) -> List[float]:
        if "matrix" in n and len(n["matrix"]) == 16:
            return [float(v) for v in n["matrix"]]
        m = _mat4_identity()
        if "translation" in n and len(n["translation"]) == 3:
            t = n["translation"]
            m[12], m[13], m[14] = float(t[0]), float(t[1]), float(t[2])
        if "rotation" in n and len(n["rotation"]) == 4:
            x, y, z, w = [float(v) for v in n["rotation"]]
            rot = [
                1.0 - 2.0 * (y * y + z * z), 2.0 * (x * y + z * w), 2.0 * (x * z - y * w), 0.0,
                2.0 * (x * y - z * w), 1.0 - 2.0 * (x * x + z * z), 2.0 * (y * z + x * w), 0.0,
                2.0 * (x * z + y * w), 2.0 * (y * z - x * w), 1.0 - 2.0 * (x * x + y * y), 0.0,
                0.0, 0.0, 0.0, 1.0,
            ]
            m = _mat4_multiply(m, rot)
        if "scale" in n and len(n["scale"]) == 3:
            s = [float(v) for v in n["scale"]]
            scale_mat = [
                s[0], 0.0, 0.0, 0.0,
                0.0, s[1], 0.0, 0.0,
                0.0, 0.0, s[2], 0.0,
                0.0, 0.0, 0.0, 1.0,
            ]
            m = _mat4_multiply(m, scale_mat)
        return m

    mesh_boxes: Dict[int, List[List[float]]] = {}

    def traverse(node_idx: int, parent_mat: List[float]):
        if node_idx >= len(nodes):
            return
        n = nodes[node_idx]
        mat = _mat4_multiply(parent_mat, _get_node_matrix(n))
        mesh_idx = n.get("mesh")
        if mesh_idx is not None and mesh_idx < len(meshes):
            m = meshes[mesh_idx]
            for p in m.get("primitives", []):
                pos_idx = p.get("attributes", {}).get("POSITION")
                if pos_idx is not None and pos_idx < len(accessors):
                    acc = accessors[pos_idx]
                    if "min" in acc and "max" in acc:
                        pmin = acc["min"]
                        pmax = acc["max"]
                        corners = [
                            [pmin[0], pmin[1], pmin[2]],
                            [pmin[0], pmin[1], pmax[2]],
                            [pmin[0], pmax[1], pmin[2]],
                            [pmin[0], pmax[1], pmax[2]],
                            [pmax[0], pmin[1], pmin[2]],
                            [pmax[0], pmin[1], pmax[2]],
                            [pmax[0], pmax[1], pmin[2]],
                            [pmax[0], pmax[1], pmax[2]],
                        ]
                        for c in corners:
                            w = _mat4_transform_point(mat, c)
                            mesh_boxes.setdefault(mesh_idx, []).append(w)
        for c in n.get("children", []):
            traverse(c, mat)

    scenes = gltf.get("scenes", [])
    scene_idx = gltf.get("scene", 0)
    root_nodes = scenes[scene_idx].get("nodes", []) if scene_idx < len(scenes) else []
    if not root_nodes and nodes:
        root_nodes = [0]

    for r in root_nodes:
        traverse(r, _mat4_identity())

    # Filter out architectural environment / room shell meshes:
    # Any mesh with extent > 6.0 meters (20 feet) is an environment room, not product rack
    product_pts: List[List[float]] = []
    product_mesh_indices: List[int] = []

    for m_idx, pts in mesh_boxes.items():
        xs = [pt[0] for pt in pts]
        ys = [pt[1] for pt in pts]
        zs = [pt[2] for pt in pts]
        size = [max(xs) - min(xs), max(ys) - min(ys), max(zs) - min(zs)]
        if max(size) <= 6.0:  # <= 6 meters
            product_pts.extend(pts)
            product_mesh_indices.append(m_idx)

    if not product_pts:
        # If all meshes were large or single mesh, use all
        for m_idx, pts in mesh_boxes.items():
            product_pts.extend(pts)
            product_mesh_indices.append(m_idx)

    if product_pts:
        px = [pt[0] for pt in product_pts]
        py = [pt[1] for pt in product_pts]
        pz = [pt[2] for pt in product_pts]
        raw_dx = max(px) - min(px)
        raw_dy = max(py) - min(py)
        raw_dz = max(pz) - min(pz)
    else:
        raw_dx, raw_dy, raw_dz = 0.54, 2.16, 0.97

    # Determine native unit scale:
    max_dim = max(raw_dx, raw_dy, raw_dz)
    if max_dim <= 10.0:
        # Meters (standard glTF)
        scale_to_inches = 39.37007874
        scale_to_mm = 1000.0
    elif max_dim > 150.0:
        # mm
        scale_to_inches = 1.0 / 25.4
        scale_to_mm = 1.0
    else:
        # inches
        scale_to_inches = 1.0
        scale_to_mm = 25.4

    # Standard product orientation:
    # UP is vertical Y
    h_raw = raw_dy
    # Between horizontal axes X and Z: larger dimension is Width, smaller is Depth
    w_raw = max(raw_dx, raw_dz)
    d_raw = min(raw_dx, raw_dz)

    width_in = round(w_raw * scale_to_inches, 2)
    height_in = round(h_raw * scale_to_inches, 2)
    depth_in = round(d_raw * scale_to_inches, 2)

    width_mm = round(w_raw * scale_to_mm, 1)
    height_mm = round(h_raw * scale_to_mm, 1)
    depth_mm = round(d_raw * scale_to_mm, 1)

    detected = DetectedDimensions(
        width_inches=width_in,
        height_inches=height_in,
        depth_inches=depth_in,
        width_mm=width_mm,
        height_mm=height_mm,
        depth_mm=depth_mm
    )

    return {
        "valid": True,
        "detected_dimensions": detected,
        "mesh_count": len(product_mesh_indices),
        "materials": materials[:10],
        "file_size": len(file_bytes)
    }


def save_glb_file(file_bytes: bytes, original_filename: str) -> Tuple[str, str]:
    """
    Saves GLB file in backend/uploads/models/ with a sanitized unique name.
    Returns (storage_path, glb_url).
    """
    clean_base = re.sub(r'[^a-zA-Z0-9_\-]', '_', os.path.splitext(original_filename)[0])
    safe_name = f"{clean_base}_{uuid.uuid4().hex[:8]}.glb"
    dest_path = os.path.join(MODELS_DIR, safe_name)

    with open(dest_path, "wb") as f:
        f.write(file_bytes)

    relative_storage_path = f"models/{safe_name}"
    glb_url = f"/uploads/models/{safe_name}"
    return relative_storage_path, glb_url


async def get_active_products(db: AsyncSession) -> List[Product3DModel]:
    query = (
        select(Product3DModel)
        .where(Product3DModel.active == True)
        .order_by(Product3DModel.product_name)
    )
    result = await db.execute(query)
    return list(result.scalars().all())


async def get_all_products(
    db: AsyncSession,
    search: Optional[str] = None,
    category: Optional[str] = None,
    active_only: bool = False
) -> List[Product3DModel]:
    query = select(Product3DModel)
    if active_only:
        query = query.where(Product3DModel.active == True)
    if category and category != "All":
        query = query.where(Product3DModel.category == category)
    if search:
        s = f"%{search.lower()}%"
        query = query.where(
            or_(
                Product3DModel.product_name.ilike(s),
                Product3DModel.sku.ilike(s),
                Product3DModel.product_type.ilike(s),
                Product3DModel.category.ilike(s)
            )
        )
    query = query.order_by(desc(Product3DModel.created_at))
    result = await db.execute(query)
    return list(result.scalars().all())


async def get_product_by_id(db: AsyncSession, id_or_code: str) -> Optional[Product3DModel]:
    # Check by integer ID if numeric, else product_id
    if id_or_code.isdigit():
        query = select(Product3DModel).where(Product3DModel.id == int(id_or_code))
    else:
        query = select(Product3DModel).where(Product3DModel.product_id == id_or_code)
    result = await db.execute(query)
    return result.scalar_one_or_none()


async def record_audit_log(
    db: AsyncSession,
    event_type: str,
    product_id: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
    admin_user: str = "admin"
):
    """
    Records an entry in audit_logs for product management events.
    """
    try:
        log_payload = {
            "admin": admin_user,
            "action": event_type,
            "timestamp": utcnow().isoformat(),
            **(details or {})
        }
        entry = AuditLog(
            event_type=event_type,
            survey_id=None,
            project_id=product_id,
            user_type="admin",
            details=json.dumps(log_payload),
            created_at=utcnow()
        )
        db.add(entry)
    except Exception as e:
        print(f"[RETAILFIX] Audit logging warning: {e}")


async def validate_product_data(
    db: AsyncSession,
    name: str,
    sku: Optional[str],
    width: float,
    depth: float,
    height: float,
    shelf_count: Optional[int] = None,
    exclude_id: Optional[int] = None
):
    """
    Validates product fields:
    - Name: required
    - SKU: required and must be unique
    - Width > 0, Depth > 0, Height > 0
    - Shelf count >= 0
    """
    if not name or not name.strip():
        raise ValueError("Product Name is required.")

    if not sku or not sku.strip():
        raise ValueError("SKU is required.")

    clean_sku = sku.strip()
    sku_q = select(Product3DModel).where(Product3DModel.sku.ilike(clean_sku))
    if exclude_id is not None:
        sku_q = sku_q.where(Product3DModel.id != exclude_id)
    sku_res = await db.execute(sku_q)
    existing_with_sku = sku_res.scalars().first()
    if existing_with_sku:
        raise ValueError(
            f"SKU '{clean_sku}' is already in use by '{existing_with_sku.product_name}' "
            f"({existing_with_sku.product_id}). SKU must be unique."
        )

    if width <= 0:
        raise ValueError("Base Width must be greater than zero.")
    if depth <= 0:
        raise ValueError("Base Depth must be greater than zero.")
    if height <= 0:
        raise ValueError("Base Height must be greater than zero.")

    if shelf_count is not None and shelf_count < 0:
        raise ValueError("Shelf count must be 0 or greater.")


async def check_product_references(db: AsyncSession, product_id: int) -> Dict[str, Any]:
    """
    Checks if any existing saved CAD projects reference this product model.
    Checks by product_id code (e.g. RF-PRD-0001, PRD-WR-7X3), numeric id, and SKU.
    """
    query = select(Product3DModel).where(Product3DModel.id == product_id)
    result = await db.execute(query)
    product = result.scalar_one_or_none()
    if not product:
        raise ValueError("Product not found")

    filters = [
        CADEntity.properties_json.like(f"%{product.product_id}%"),
        CADEntity.properties_json.like(f"%\"productModelId\": \"{product.id}\"%"),
        CADEntity.properties_json.like(f"%\"productModelId\":\"{product.id}\"%"),
    ]
    if product.sku:
        filters.append(CADEntity.properties_json.like(f"%{product.sku}%"))

    cad_q = (
        select(CADEntity, Project)
        .join(Project, CADEntity.project_id == Project.id, isouter=True)
        .where(or_(*filters))
    )
    cad_res = await db.execute(cad_q)
    rows = cad_res.all()

    project_codes = sorted(list({p.project_id for ce, p in rows if p and p.project_id}))
    ref_count = len(rows)
    referenced = ref_count > 0

    return {
        "product_id": product.id,
        "product_code": product.product_id,
        "product_name": product.product_name,
        "referenced": referenced,
        "reference_count": ref_count,
        "project_codes": project_codes,
        "can_delete": not referenced,
        "message": (
            f"This rack is used by existing projects ({', '.join(project_codes[:3]) if project_codes else f'{ref_count} entity(ies)'}) "
            "and cannot be permanently deleted. It will be archived instead."
            if referenced else
            f"This rack is not used in any CAD projects and can be permanently deleted."
        )
    }


async def create_product(
    db: AsyncSession,
    data: ProductModelCreate,
    admin_user: str = "admin"
) -> Product3DModel:
    await validate_product_data(
        db=db,
        name=data.product_name,
        sku=data.sku,
        width=data.width,
        depth=data.depth,
        height=data.height,
        shelf_count=data.shelf_count
    )

    if not data.product_id:
        count_q = select(Product3DModel.id)
        count_res = await db.execute(count_q)
        total_count = len(count_res.scalars().all())
        data.product_id = f"RF-PRD-{total_count + 1:04d}"

    product = Product3DModel(
        product_id=data.product_id,
        product_name=data.product_name.strip(),
        product_type=data.product_type or "Wall Rack",
        sku=data.sku.strip() if data.sku else None,
        category=data.category or "Display Racks",
        width=float(data.width),
        height=float(data.height),
        depth=float(data.depth),
        glb_url=data.glb_url,
        storage_path=data.storage_path,
        thumbnail_url=data.thumbnail_url,
        version=1,
        scaling_mode=data.scaling_mode or "stretch",
        shelf_count=data.shelf_count if data.shelf_count is not None else 5,
        min_shelves=data.min_shelves if data.min_shelves is not None else 1,
        max_shelves=data.max_shelves if data.max_shelves is not None else 10,
        shelf_mode=data.shelf_mode or "AUTO_SPACING",
        shelf_thickness=data.shelf_thickness if data.shelf_thickness is not None else 1.0,
        active=data.active,
        metadata_json=data.metadata_json
    )
    db.add(product)

    await record_audit_log(
        db=db,
        event_type="CREATE_PRODUCT",
        product_id=product.product_id,
        details={
            "product_name": product.product_name,
            "sku": product.sku,
            "category": product.category,
            "dimensions": f"{product.width}x{product.height}x{product.depth}",
            "scaling_mode": product.scaling_mode,
            "shelf_count": product.shelf_count,
            "shelf_mode": product.shelf_mode,
            "active": product.active
        },
        admin_user=admin_user
    )

    await db.commit()
    await db.refresh(product)
    return product


async def update_product(
    db: AsyncSession,
    product_id: int,
    data: ProductModelUpdate,
    admin_user: str = "admin"
) -> Optional[Product3DModel]:
    query = select(Product3DModel).where(Product3DModel.id == product_id)
    result = await db.execute(query)
    product = result.scalar_one_or_none()
    if not product:
        return None

    update_dict = data.model_dump(exclude_unset=True)

    # Validate updated values
    check_name = update_dict.get("product_name", product.product_name)
    check_sku = update_dict.get("sku", product.sku)
    check_w = update_dict.get("width", product.width)
    check_d = update_dict.get("depth", product.depth)
    check_h = update_dict.get("height", product.height)
    check_shelves = update_dict.get("shelf_count", product.shelf_count)

    await validate_product_data(
        db=db,
        name=check_name,
        sku=check_sku,
        width=check_w,
        depth=check_d,
        height=check_h,
        shelf_count=check_shelves,
        exclude_id=product_id
    )

    for k, v in update_dict.items():
        if k in ("product_name", "sku", "category") and isinstance(v, str):
            v = v.strip()
        setattr(product, k, v)

    await record_audit_log(
        db=db,
        event_type="UPDATE_PRODUCT",
        product_id=product.product_id,
        details={
            "product_id": product.id,
            "updated_fields": list(update_dict.keys()),
            "product_name": product.product_name,
            "sku": product.sku,
            "active": product.active
        },
        admin_user=admin_user
    )

    await db.commit()
    await db.refresh(product)
    return product


async def replace_product_glb(
    db: AsyncSession,
    product_id: int,
    storage_path: str,
    glb_url: str,
    metadata: Optional[str] = None,
    admin_user: str = "admin"
) -> Optional[Product3DModel]:
    query = select(Product3DModel).where(Product3DModel.id == product_id)
    result = await db.execute(query)
    product = result.scalar_one_or_none()
    if not product:
        return None

    old_url = product.glb_url
    product.storage_path = storage_path
    product.glb_url = glb_url
    product.version += 1
    if metadata:
        product.metadata_json = metadata

    await record_audit_log(
        db=db,
        event_type="REPLACE_GLB",
        product_id=product.product_id,
        details={
            "old_glb_url": old_url,
            "new_glb_url": glb_url,
            "new_version": product.version
        },
        admin_user=admin_user
    )

    await db.commit()
    await db.refresh(product)
    return product


async def toggle_product_active(
    db: AsyncSession,
    product_id: int,
    admin_user: str = "admin"
) -> Optional[Product3DModel]:
    query = select(Product3DModel).where(Product3DModel.id == product_id)
    result = await db.execute(query)
    product = result.scalar_one_or_none()
    if not product:
        return None

    product.active = not product.active
    action = "ACTIVATE_PRODUCT" if product.active else "DEACTIVATE_PRODUCT"

    await record_audit_log(
        db=db,
        event_type=action,
        product_id=product.product_id,
        details={
            "active": product.active,
            "product_name": product.product_name,
            "sku": product.sku
        },
        admin_user=admin_user
    )

    await db.commit()
    await db.refresh(product)
    return product


async def archive_product(
    db: AsyncSession,
    product_id: int,
    admin_user: str = "admin"
) -> Tuple[bool, str, Optional[Product3DModel]]:
    query = select(Product3DModel).where(Product3DModel.id == product_id)
    result = await db.execute(query)
    product = result.scalar_one_or_none()
    if not product:
        return False, "Product not found", None

    product.active = False
    await record_audit_log(
        db=db,
        event_type="ARCHIVE_PRODUCT",
        product_id=product.product_id,
        details={
            "product_name": product.product_name,
            "sku": product.sku,
            "active": False
        },
        admin_user=admin_user
    )

    await db.commit()
    await db.refresh(product)
    return True, f"Rack '{product.product_name}' was successfully archived.", product


async def safe_delete_product(
    db: AsyncSession,
    product_id: int,
    admin_user: str = "admin"
) -> Tuple[bool, str, bool]:
    """
    Safely deletes or archives a product model.
    Returns (success: bool, message: str, was_archived: bool).
    If referenced by CAD entities, blocks permanent deletion and archives instead.
    """
    ref_check = await check_product_references(db, product_id)

    query = select(Product3DModel).where(Product3DModel.id == product_id)
    result = await db.execute(query)
    product = result.scalar_one_or_none()
    if not product:
        return False, "Product not found", False

    if ref_check["referenced"]:
        product.active = False
        await record_audit_log(
            db=db,
            event_type="ARCHIVE_PRODUCT",
            product_id=product.product_id,
            details={
                "reason": "Safe delete triggered for referenced product",
                "references": ref_check["reference_count"],
                "project_codes": ref_check["project_codes"]
            },
            admin_user=admin_user
        )
        await db.commit()
        return True, ref_check["message"], True

    # Permanently delete if unreferenced
    prod_code = product.product_id
    prod_name = product.product_name
    await db.delete(product)

    await record_audit_log(
        db=db,
        event_type="DELETE_PRODUCT",
        product_id=prod_code,
        details={
            "product_name": prod_name,
            "permanent": True
        },
        admin_user=admin_user
    )

    await db.commit()
    return True, f"Rack '{prod_name}' ({prod_code}) was permanently deleted.", False
