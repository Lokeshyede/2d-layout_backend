from pydantic import BaseModel, EmailStr
from typing import Optional, List, Dict, Any

class AdminLoginRequest(BaseModel):
    username: str
    password: str

class AdminTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: Dict[str, Any]

class DashboardStats(BaseModel):
    totalSurveys: int
    todaySurveys: int
    completedLayouts: int
    draftLayouts: int
    storeTypeDistribution: Dict[str, int]
    recentSurveys: List[Dict[str, Any]]
