import uuid
import secrets
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from sqlalchemy import func
import json
from app.models import Customer, StoreDetails, Survey, Project, ProjectVersion, SurveyPhoto, AuditLog
from app.schemas.survey import SurveyCreateRequest

async def generate_survey_id(db: AsyncSession) -> str:
    current_year = datetime.now(timezone.utc).year
    query = select(func.count(Survey.id))
    result = await db.execute(query)
    count = result.scalar() or 0
    next_num = count + 1
    return f"RF-SUR-{current_year}-{next_num:04d}"

async def generate_customer_id(db: AsyncSession) -> str:
    current_year = datetime.now(timezone.utc).year
    query = select(func.count(Customer.id))
    result = await db.execute(query)
    count = result.scalar() or 0
    next_num = count + 1
    return f"RF-CUST-{current_year}-{next_num:04d}"

def generate_secure_token() -> str:
    return secrets.token_urlsafe(32)

async def create_survey(db: AsyncSession, data: SurveyCreateRequest) -> Survey:
    survey_id = await generate_survey_id(db)
    secure_token = generate_secure_token()
    
    # 1. Create or Link Customer
    query = select(Customer).where(Customer.mobile_number == data.customer.mobileNumber)
    result = await db.execute(query)
    customer = result.scalar_one_or_none()

    if not customer:
        cust_id_str = await generate_customer_id(db)
        customer = Customer(
            customer_id=cust_id_str,
            customer_name=data.customer.customerName,
            owner_name=data.customer.ownerName,
            mobile_number=data.customer.mobileNumber,
            whatsapp_number=data.customer.whatsAppNumber or data.customer.mobileNumber,
            email=data.customer.email,
            store_address=data.customer.storeAddress,
            city=data.customer.city,
            state=data.customer.state,
            pincode=data.customer.pincode
        )
        db.add(customer)
        await db.flush()

    # 2. Create Store Details
    store_details = StoreDetails(
        customer_id=customer.id,
        store_name=data.store.storeName,
        store_type=data.store.storeType,
        store_area=data.store.storeArea,
        approx_width=data.store.approxWidth,
        approx_height=data.store.approxHeight,
        unit=data.store.unit or "Feet + Inches"
    )
    db.add(store_details)
    await db.flush()

    # 3. Create Survey
    survey = Survey(
        survey_id=survey_id,
        customer_id=customer.id,
        survey_date=data.survey.surveyDate,
        salesman_name=data.survey.salesmanName,
        site_contact_person=data.survey.siteContactPerson,
        remarks=data.survey.remarks,
        special_requirements=data.survey.specialRequirements,
        status="survey_completed",
        secure_token=secure_token
    )
    db.add(survey)
    await db.flush()

    # 4. Create initial Project linked to survey
    viewport_json = {
        "zoom": 1.0, 
        "panX": 0, 
        "panY": 0,
        "roomShapeMode": data.store.roomShapeMode or "AUTO"
    }
    project = Project(
        project_id=survey_id,
        survey_id=survey.id,
        title=f"{data.store.storeName} - 2D CAD Store Layout",
        revision="REV 1",
        viewport_data=json.dumps(viewport_json),
        scale='1/4" = 1\'-0"',
        unit="Feet + Inches",
        notes=f"Initial survey created on {data.survey.surveyDate}. Store Type: {data.store.storeType}"
    )
    db.add(project)
    await db.flush()

    # 5. Create initial Version snapshot (REV 1)
    version = ProjectVersion(
        project_id=project.id,
        revision_name="REV 1",
        snapshot_json='{"entities": [], "viewport": {"zoom": 1.0, "panX": 0, "panY": 0}}',
        created_by="system"
    )
    db.add(version)

    # 6. Audit Log
    audit = AuditLog(
        event_type="SURVEY_CREATED",
        survey_id=survey_id,
        project_id=survey_id,
        user_type="customer",
        details=f"Survey {survey_id} created for {data.customer.customerName} ({data.store.storeName})"
    )
    db.add(audit)

    await db.flush()
    
    # Reload survey with relations cleanly
    reloaded = await get_survey_by_id(db, survey_id)
    return reloaded

async def get_survey_by_id(db: AsyncSession, survey_id: str):
    query = (
        select(Survey)
        .where(Survey.survey_id == survey_id)
        .options(
            selectinload(Survey.customer),
            selectinload(Survey.project),
            selectinload(Survey.photos)
        )
    )
    result = await db.execute(query)
    return result.scalar_one_or_none()

async def get_store_details_by_customer(db: AsyncSession, customer_id: int):
    query = select(StoreDetails).where(StoreDetails.customer_id == customer_id).order_by(StoreDetails.created_at.desc())
    result = await db.execute(query)
    return result.scalars().first()
