from pydantic import BaseModel, EmailStr
from typing import Optional, List, Dict, Any
from datetime import datetime

class CustomerInfoSchema(BaseModel):
    customerName: str
    ownerName: Optional[str] = None
    mobileNumber: str
    whatsAppNumber: Optional[str] = None
    email: Optional[str] = None
    storeAddress: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    pincode: Optional[str] = None

class StoreInfoSchema(BaseModel):
    storeName: str
    storeType: str = "Supermarket"
    storeArea: Optional[str] = None
    approxWidth: Optional[str] = None
    approxHeight: Optional[str] = None
    unit: str = "Feet + Inches"
    roomShapeMode: Optional[str] = "AUTO"

class SurveyInfoSchema(BaseModel):
    surveyDate: str
    salesmanName: Optional[str] = None
    siteContactPerson: Optional[str] = None
    remarks: Optional[str] = None
    specialRequirements: Optional[str] = None

class SurveyCreateRequest(BaseModel):
    customer: CustomerInfoSchema
    store: StoreInfoSchema
    survey: SurveyInfoSchema

class SurveyPhotoResponse(BaseModel):
    id: int
    photoType: str
    fileName: str
    filePath: str
    fileSize: Optional[int] = None
    createdAt: str

class SurveyResponse(BaseModel):
    id: int
    surveyId: str
    projectId: str
    customerId: str
    secureToken: str
    status: str
    customer: CustomerInfoSchema
    store: StoreInfoSchema
    survey: SurveyInfoSchema
    photos: List[SurveyPhotoResponse] = []
    revision: str = "REV 1"
    createdAt: str
    updatedAt: str

class SurveyListItem(BaseModel):
    id: int
    surveyId: str
    projectId: str
    customerName: str
    storeName: str
    ownerName: Optional[str] = None
    mobileNumber: str
    city: Optional[str] = None
    storeType: str
    surveyDate: str
    status: str
    createdAt: str
    entityCount: int = 0
    revision: str = "REV 1"
