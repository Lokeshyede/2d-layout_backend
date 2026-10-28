import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy.future import select

from app.core.config import settings
from app.core.database import engine, Base, AsyncSessionLocal
from app.core.security import get_password_hash
from app.models import Admin
from app.api.auth import router as auth_router
from app.api.surveys import router as surveys_router
from app.api.projects import router as projects_router
from app.api.export import router as export_router
from app.api.admin import router as admin_router
from app.api.products import router as products_router
from app.api.share import router as share_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 1. Safely create admins table if it doesn't exist
    from sqlalchemy import text
    async with engine.begin() as conn:
        try:
            await conn.execute(text("""
                CREATE TABLE IF NOT EXISTS admins (
                    id SERIAL PRIMARY KEY,
                    username VARCHAR(100) UNIQUE NOT NULL,
                    email VARCHAR(255) UNIQUE NOT NULL,
                    hashed_password VARCHAR(255) NOT NULL,
                    role VARCHAR(50) DEFAULT 'admin',
                    is_active BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    last_login TIMESTAMP WITH TIME ZONE
                );
            """))
            await conn.execute(text("CREATE INDEX IF NOT EXISTS ix_admins_username ON admins(username);"))
            await conn.execute(text("CREATE INDEX IF NOT EXISTS ix_admins_email ON admins(email);"))

            await conn.execute(text("""
                CREATE TABLE IF NOT EXISTS project_shares (
                    id SERIAL PRIMARY KEY,
                    project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
                    share_token VARCHAR(100) UNIQUE NOT NULL,
                    share_token_hash VARCHAR(128),
                    is_enabled BOOLEAN DEFAULT TRUE NOT NULL,
                    allow_pdf_download BOOLEAN DEFAULT TRUE,
                    allow_png_download BOOLEAN DEFAULT TRUE,
                    allow_video_download BOOLEAN DEFAULT TRUE,
                    expires_at TIMESTAMP WITH TIME ZONE,
                    view_count INTEGER DEFAULT 0,
                    last_viewed_at TIMESTAMP WITH TIME ZONE,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                );
            """))
            await conn.execute(text("CREATE INDEX IF NOT EXISTS ix_project_shares_share_token ON project_shares(share_token);"))
            await conn.execute(text("CREATE INDEX IF NOT EXISTS ix_project_shares_project_id ON project_shares(project_id);"))
        except Exception as e:
            print(f"Error creating tables: {e}")
    
    # 2. Seed default admin if not existing
    async with AsyncSessionLocal() as session:
        query = select(Admin).where(Admin.username == settings.DEFAULT_ADMIN_USERNAME)
        result = await session.execute(query)
        admin = result.scalar_one_or_none()
        if not admin:
            default_admin = Admin(
                username=settings.DEFAULT_ADMIN_USERNAME,
                email=settings.DEFAULT_ADMIN_EMAIL,
                hashed_password=get_password_hash(settings.DEFAULT_ADMIN_PASSWORD),
                role="superadmin",
                is_active=True
            )
            session.add(default_admin)
            await session.commit()
            print(f"[RETAILFIX] Initialized default admin: {settings.DEFAULT_ADMIN_USERNAME}")
        
        # 3. Dynamic Admin GLB System: Database is the sole source of truth.
        # No automatic hardcoded product seeding on startup.
    
    yield
    # Cleanup if needed

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    lifespan=lifespan
)

from fastapi import Request
from fastapi.responses import JSONResponse

# Global error handler middleware placed inside CORSMiddleware
# This ensures that any unhandled exception (e.g. 500) returns a proper JSON response
# and is wrapped by CORSMiddleware, guaranteeing that Access-Control-Allow-Origin is never missing.
@app.middleware("http")
async def cors_exception_middleware(request: Request, call_next):
    try:
        return await call_next(request)
    except Exception as exc:
        import traceback
        traceback.print_exc()
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error occurred", "error": str(exc)},
        )

# CORS Configuration (added last so it is the outermost middleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_origin_regex=settings.BACKEND_CORS_ORIGIN_REGEX,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH", "HEAD"],
    allow_headers=["*"],
    expose_headers=["*"],
    max_age=86400,
)

# Mount uploads static folder
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=settings.UPLOAD_DIR), name="uploads")

# Include Routers
app.include_router(auth_router, prefix=settings.API_V1_STR)
app.include_router(surveys_router, prefix=settings.API_V1_STR)
app.include_router(projects_router, prefix=settings.API_V1_STR)
app.include_router(export_router, prefix=settings.API_V1_STR)
app.include_router(admin_router, prefix=settings.API_V1_STR)
app.include_router(products_router, prefix=settings.API_V1_STR)
app.include_router(share_router, prefix=settings.API_V1_STR)


@app.get("/")
async def root():
    return {
        "app": settings.PROJECT_NAME,
        "version": "1.0.0",
        "status": "online",
        "docs": "/docs"
    }

@app.get("/health")
async def root_health_check():
    return {"status": "healthy", "service": "retailfix-cad-backend"}

@app.get("/api/health")
async def health_check():
    return {"status": "healthy", "service": "retailfix-cad-backend"}
