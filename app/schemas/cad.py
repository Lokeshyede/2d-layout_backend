from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional
from datetime import datetime

class CADEntitySchema(BaseModel):
    id: str
    type: str
    geometry: Dict[str, Any]
    properties: Optional[Dict[str, Any]] = None
    layer: Optional[str] = "default"
    zIndex: Optional[int] = 0

class ViewportSchema(BaseModel):
    zoom: float = 1.0
    panX: float = 0.0
    panY: float = 0.0

class ProjectSaveRequest(BaseModel):
    title: Optional[str] = None
    revision: Optional[str] = None
    viewport: Optional[ViewportSchema] = None
    scale: Optional[str] = None
    unit: Optional[str] = "Feet + Inches"
    notes: Optional[str] = None
    entities: List[CADEntitySchema] = []
    createRevision: Optional[bool] = False
    revisionName: Optional[str] = None

class ProjectResponse(BaseModel):
    projectId: str
    surveyId: str
    title: str
    revision: str
    viewport: Dict[str, Any]
    scale: str
    unit: str
    notes: Optional[str] = None
    entities: List[CADEntitySchema] = []
    versions: List[Dict[str, Any]] = []
    customerName: Optional[str] = None
    storeName: Optional[str] = None
    storeType: Optional[str] = None
    approxWidth: Optional[str] = None
    approxHeight: Optional[str] = None
    surveyDate: Optional[str] = None
    updatedAt: Optional[str] = None
