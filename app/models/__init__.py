from datetime import datetime, timezone
import json
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey, Float
from sqlalchemy.orm import relationship
from app.core.database import Base

def utcnow():
    return datetime.now(timezone.utc)

class Admin(Base):
    __tablename__ = "admins"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    username = Column(String(100), unique=True, index=True, nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    role = Column(String(50), default="admin")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=utcnow)
    last_login = Column(DateTime(timezone=True), nullable=True)


class Customer(Base):
    __tablename__ = "customers"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    customer_id = Column(String(50), unique=True, index=True, nullable=False)
    customer_name = Column(String(255), nullable=False)
    owner_name = Column(String(255), nullable=True)
    mobile_number = Column(String(20), index=True, nullable=False)
    whatsapp_number = Column(String(20), nullable=True)
    email = Column(String(255), nullable=True)
    store_address = Column(Text, nullable=True)
    city = Column(String(100), index=True, nullable=True)
    state = Column(String(100), nullable=True)
    pincode = Column(String(20), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    # Relationships with selectin lazy loading for clean async access
    surveys = relationship("Survey", back_populates="customer", cascade="all, delete-orphan", lazy="selectin")


class StoreDetails(Base):
    __tablename__ = "store_details"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    store_name = Column(String(255), nullable=False)
    store_type = Column(String(100), nullable=False, default="Supermarket")
    store_area = Column(String(50), nullable=True)
    approx_width = Column(String(50), nullable=True)
    approx_height = Column(String(50), nullable=True)
    unit = Column(String(50), default="Feet + Inches")
    created_at = Column(DateTime(timezone=True), default=utcnow)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class Survey(Base):
    __tablename__ = "surveys"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    survey_id = Column(String(50), unique=True, index=True, nullable=False) # e.g. RF-SUR-2026-0001
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    survey_date = Column(String(50), nullable=False)
    salesman_name = Column(String(255), nullable=True)
    site_contact_person = Column(String(255), nullable=True)
    remarks = Column(Text, nullable=True)
    special_requirements = Column(Text, nullable=True)
    status = Column(String(50), default="survey_completed") # draft, survey_completed, layout_in_progress, layout_completed
    secure_token = Column(String(100), unique=True, index=True, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utcnow)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    # Relationships with selectin lazy loading
    customer = relationship("Customer", back_populates="surveys", lazy="selectin")
    project = relationship("Project", back_populates="survey", uselist=False, cascade="all, delete-orphan", lazy="selectin")
    photos = relationship("SurveyPhoto", back_populates="survey", cascade="all, delete-orphan", lazy="selectin")


class SurveyPhoto(Base):
    __tablename__ = "survey_photos"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    survey_id = Column(Integer, ForeignKey("surveys.id"), nullable=False)
    photo_type = Column(String(50), default="store_photo") # store_photo, floor_plan, reference_image
    file_path = Column(String(500), nullable=False)
    file_name = Column(String(255), nullable=False)
    file_size = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow)

    survey = relationship("Survey", back_populates="photos", lazy="selectin")


class Project(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    project_id = Column(String(50), unique=True, index=True, nullable=False) # matches survey_id or custom
    survey_id = Column(Integer, ForeignKey("surveys.id"), unique=True, nullable=False)
    title = Column(String(255), nullable=False)
    revision = Column(String(20), default="REV 1")
    viewport_data = Column(Text, default='{"zoom": 1.0, "panX": 0, "panY": 0}')
    scale = Column(String(50), default='1/4" = 1\'-0"')
    unit = Column(String(50), default="Feet + Inches")
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    # Relationships with selectin lazy loading
    survey = relationship("Survey", back_populates="project", lazy="selectin")
    entities = relationship("CADEntity", back_populates="project", cascade="all, delete-orphan", lazy="selectin")
    versions = relationship("ProjectVersion", back_populates="project", cascade="all, delete-orphan", lazy="selectin")
    shares = relationship("ProjectShare", back_populates="project", cascade="all, delete-orphan", lazy="selectin")


class CADEntity(Base):
    __tablename__ = "cad_entities"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    entity_id = Column(String(100), index=True, nullable=False)
    entity_type = Column(String(50), index=True, nullable=False) # wall, door, window, column, rack, shutter, glass_gate, partition, dimension, text
    geometry_json = Column(Text, nullable=False) # JSON serialized geometry (points, bounds, rotation, dimensions)
    properties_json = Column(Text, nullable=True) # JSON serialized properties (thickness, color, label, rack_type, projection)
    layer = Column(String(50), default="default")
    z_index = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), default=utcnow)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    project = relationship("Project", back_populates="entities", lazy="selectin")


class ProjectVersion(Base):
    __tablename__ = "project_versions"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    revision_name = Column(String(20), nullable=False) # REV 1, REV 2, etc.
    snapshot_json = Column(Text, nullable=False) # Full state snapshot of entities & metadata
    created_by = Column(String(100), default="system")
    created_at = Column(DateTime(timezone=True), default=utcnow)

    project = relationship("Project", back_populates="versions", lazy="selectin")


class ProjectShare(Base):
    __tablename__ = "project_shares"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    share_token = Column(String(100), unique=True, index=True, nullable=False)
    share_token_hash = Column(String(128), index=True, nullable=True)
    is_enabled = Column(Boolean, default=True, nullable=False)
    allow_pdf_download = Column(Boolean, default=True)
    allow_png_download = Column(Boolean, default=True)
    allow_video_download = Column(Boolean, default=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    view_count = Column(Integer, default=0)
    last_viewed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    project = relationship("Project", back_populates="shares", lazy="selectin")


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    event_type = Column(String(100), nullable=False)
    survey_id = Column(String(50), nullable=True)
    project_id = Column(String(50), nullable=True)
    user_type = Column(String(50), default="customer") # customer, admin
    details = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow)


class Product3DModel(Base):
    __tablename__ = "product_3d_models"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    product_id = Column(String(50), unique=True, index=True, nullable=False)
    product_name = Column(String(255), nullable=False)
    product_type = Column(String(100), nullable=False, default="Wall Rack")
    sku = Column(String(100), index=True, nullable=True)
    category = Column(String(100), nullable=True, default="Display Racks")
    width = Column(Float, nullable=False)  # inches
    height = Column(Float, nullable=False)  # inches
    depth = Column(Float, nullable=False)  # inches
    glb_url = Column(String(500), nullable=False)
    storage_path = Column(String(500), nullable=False)
    thumbnail_url = Column(String(500), nullable=True)
    scaling_mode = Column(String(50), nullable=False, default="stretch")
    shelf_count = Column(Integer, nullable=True, default=5)
    min_shelves = Column(Integer, nullable=True, default=1)
    max_shelves = Column(Integer, nullable=True, default=10)
    shelf_mode = Column(String(50), nullable=True, default="AUTO_SPACING")
    shelf_thickness = Column(Float, nullable=True, default=1.0)
    version = Column(Integer, default=1)
    active = Column(Boolean, default=True)
    metadata_json = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

