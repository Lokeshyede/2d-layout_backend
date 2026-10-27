from pydantic import BaseModel, ConfigDict
from typing import Optional, List, Dict, Any
from datetime import datetime


class ProductModelBase(BaseModel):
    product_name: str
    product_type: str = "Wall Rack"
    sku: Optional[str] = None
    category: Optional[str] = "Display Racks"
    width: float  # in inches
    height: float  # in inches
    depth: float  # in inches
    scaling_mode: Optional[str] = "stretch"
    shelf_count: Optional[int] = 5
    min_shelves: Optional[int] = 1
    max_shelves: Optional[int] = 10
    shelf_mode: Optional[str] = "AUTO_SPACING"
    shelf_thickness: Optional[float] = 1.0
    active: bool = True


class ProductModelCreate(ProductModelBase):
    product_id: Optional[str] = None
    glb_url: str
    storage_path: str
    thumbnail_url: Optional[str] = None
    metadata_json: Optional[str] = None


class ProductModelUpdate(BaseModel):
    product_name: Optional[str] = None
    product_type: Optional[str] = None
    sku: Optional[str] = None
    category: Optional[str] = None
    width: Optional[float] = None
    height: Optional[float] = None
    depth: Optional[float] = None
    scaling_mode: Optional[str] = None
    shelf_count: Optional[int] = None
    min_shelves: Optional[int] = None
    max_shelves: Optional[int] = None
    shelf_mode: Optional[str] = None
    shelf_thickness: Optional[float] = None
    active: Optional[bool] = None
    thumbnail_url: Optional[str] = None
    metadata_json: Optional[str] = None


class ProductModelResponse(BaseModel):
    id: int
    product_id: str
    product_name: str
    product_type: str
    sku: Optional[str] = None
    category: Optional[str] = None
    width: float
    height: float
    depth: float
    glb_url: str
    storage_path: str
    thumbnail_url: Optional[str] = None
    scaling_mode: str = "stretch"
    shelf_count: Optional[int] = 5
    min_shelves: Optional[int] = 1
    max_shelves: Optional[int] = 10
    shelf_mode: Optional[str] = "AUTO_SPACING"
    shelf_thickness: Optional[float] = 1.0
    version: int = 1
    active: bool = True
    metadata_json: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class ProductModelListResponse(BaseModel):
    items: List[ProductModelResponse]
    total: int


class ProductReferenceCheckResponse(BaseModel):
    product_id: int
    product_code: str
    product_name: str
    referenced: bool
    reference_count: int
    project_codes: List[str]
    can_delete: bool
    message: str


class DetectedDimensions(BaseModel):
    width_inches: float
    height_inches: float
    depth_inches: float
    width_mm: float
    height_mm: float
    depth_mm: float


class GLBUploadResponse(BaseModel):
    storage_path: str
    glb_url: str
    file_name: str
    file_size: int
    detected_dimensions: DetectedDimensions
    mesh_count: int
    materials: List[str]
    valid: bool
    message: str
