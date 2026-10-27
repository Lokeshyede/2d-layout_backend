from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional
from datetime import datetime
from app.schemas.cad import CADEntitySchema

class ShareConfigResponse(BaseModel):
    shareToken: str
    shareUrl: str
    isEnabled: bool
    expiresAt: Optional[str] = None
    viewCount: int = 0
    lastViewedAt: Optional[str] = None
    allowPdfDownload: bool = True
    allowPngDownload: bool = True
    allowVideoDownload: bool = True

class ShareConfigUpdateRequest(BaseModel):
    isEnabled: Optional[bool] = None
    expiresAt: Optional[datetime] = None
    regenerateToken: Optional[bool] = False
    allowPdfDownload: Optional[bool] = None
    allowPngDownload: Optional[bool] = None
    allowVideoDownload: Optional[bool] = None

class RackBreakdownItem(BaseModel):
    name: str
    rackType: str
    dimensions: str
    count: int

class CustomerProjectSummary(BaseModel):
    totalRacks: int = 0
    wallRacks: int = 0
    centerRacks: int = 0
    endcaps: int = 0
    cornerRacks: int = 0
    columns: int = 0
    doors: int = 0
    windows: int = 0
    roomSize: Optional[str] = None

class CustomerPresentationResponse(BaseModel):
    storeName: str
    customerName: str
    storeType: Optional[str] = None
    location: Optional[str] = None
    projectTitle: str
    revision: str
    status: str = "Layout Proposal"
    unit: str = "Feet + Inches"
    scale: str = '1/4" = 1\'-0"'
    viewport: Dict[str, Any] = {}
    entities: List[CADEntitySchema] = []
    summary: CustomerProjectSummary
    rackBreakdown: List[RackBreakdownItem] = []
    products: List[Dict[str, Any]] = []
    allowPdfDownload: bool = True
    allowPngDownload: bool = True
    allowVideoDownload: bool = True
