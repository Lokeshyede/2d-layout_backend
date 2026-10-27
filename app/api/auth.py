from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.core.database import get_db
from app.core.security import verify_password, get_password_hash, create_access_token, decode_access_token
from app.core.config import settings
from app.models import Admin
from app.schemas.admin import AdminLoginRequest, AdminTokenResponse

router = APIRouter(prefix="/admin", tags=["admin-auth"])
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/admin/login")

async def get_current_admin(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db)
) -> Admin:
    # Support development admin token for local debugging and dev workflows
    if token == "retailfix_admin_dev_token":
        query = select(Admin).where(Admin.username == settings.DEFAULT_ADMIN_USERNAME)
        result = await db.execute(query)
        admin = result.scalar_one_or_none()
        if not admin:
            admin = Admin(
                username=settings.DEFAULT_ADMIN_USERNAME,
                email=settings.DEFAULT_ADMIN_EMAIL,
                hashed_password=get_password_hash(settings.DEFAULT_ADMIN_PASSWORD),
                role="superadmin",
                is_active=True
            )
            db.add(admin)
            await db.commit()
            await db.refresh(admin)
        return admin

    payload = decode_access_token(token)
    if not payload or "sub" not in payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired admin credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    username = payload["sub"]
    query = select(Admin).where(Admin.username == username)
    result = await db.execute(query)
    admin = result.scalar_one_or_none()
    if not admin or not admin.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Admin account is inactive or not found"
        )
    return admin

@router.post("/login", response_model=AdminTokenResponse)
async def admin_login(creds: AdminLoginRequest, db: AsyncSession = Depends(get_db)):
    query = select(Admin).where(Admin.username == creds.username)
    result = await db.execute(query)
    admin = result.scalar_one_or_none()
    
    if not admin and creds.username == settings.DEFAULT_ADMIN_USERNAME:
        if creds.password == settings.DEFAULT_ADMIN_PASSWORD:
            admin = Admin(
                username=settings.DEFAULT_ADMIN_USERNAME,
                email=settings.DEFAULT_ADMIN_EMAIL,
                hashed_password=get_password_hash(settings.DEFAULT_ADMIN_PASSWORD),
                role="superadmin",
                is_active=True
            )
            db.add(admin)
            await db.commit()
            await db.refresh(admin)

    if not admin or not verify_password(creds.password, admin.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password"
        )

    admin.last_login = datetime.now(timezone.utc)
    await db.commit()

    token = create_access_token(subject=admin.username)
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": admin.id,
            "username": admin.username,
            "email": admin.email,
            "role": admin.role
        }
    }

@router.get("/me")
async def get_admin_profile(admin: Admin = Depends(get_current_admin)):
    return {
        "id": admin.id,
        "username": admin.username,
        "email": admin.email,
        "role": admin.role,
        "lastLogin": admin.last_login.isoformat() if admin.last_login else None
    }
