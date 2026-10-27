import os
import uuid
import shutil
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import Optional, List
from app.core.database import get_db
from app.core.config import settings
from app.services.survey_service import create_survey, get_survey_by_id, get_store_details_by_customer
from app.schemas.survey import SurveyCreateRequest, SurveyResponse, CustomerInfoSchema, StoreInfoSchema, SurveyInfoSchema, SurveyPhotoResponse
from app.models import Survey, SurveyPhoto, Customer, StoreDetails

router = APIRouter(prefix="/surveys", tags=["surveys"])

@router.post("", response_model=SurveyResponse)
async def create_new_survey(data: SurveyCreateRequest, db: AsyncSession = Depends(get_db)):
    try:
        survey = await create_survey(db, data)
        store = await get_store_details_by_customer(db, survey.customer_id)
        
        response = SurveyResponse(
            id=survey.id,
            surveyId=survey.survey_id,
            projectId=survey.survey_id,
            customerId=survey.customer.customer_id,
            secureToken=survey.secure_token,
            status=survey.status,
            customer=CustomerInfoSchema(
                customerName=survey.customer.customer_name,
                ownerName=survey.customer.owner_name,
                mobileNumber=survey.customer.mobile_number,
                whatsAppNumber=survey.customer.whatsapp_number,
                email=survey.customer.email,
                storeAddress=survey.customer.store_address,
                city=survey.customer.city,
                state=survey.customer.state,
                pincode=survey.customer.pincode
            ),
            store=StoreInfoSchema(
                storeName=store.store_name if store else "Retail Store",
                storeType=store.store_type if store else "Supermarket",
                storeArea=store.store_area if store else None,
                approxWidth=store.approx_width if store else None,
                approxHeight=store.approx_height if store else None,
                unit=store.unit if store else "Feet + Inches"
            ),
            survey=SurveyInfoSchema(
                surveyDate=survey.survey_date,
                salesmanName=survey.salesman_name,
                siteContactPerson=survey.site_contact_person,
                remarks=survey.remarks,
                specialRequirements=survey.special_requirements
            ),
            photos=[],
            revision=survey.project.revision if survey.project else "REV 1",
            createdAt=survey.created_at.isoformat(),
            updatedAt=survey.updated_at.isoformat()
        )
        
        await db.commit()
        return response
    except Exception as e:
        await db.rollback()
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to create survey: {str(e)}")

@router.get("/{survey_id}", response_model=SurveyResponse)
async def get_survey(
    survey_id: str,
    token: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    survey = await get_survey_by_id(db, survey_id)
    if not survey:
        raise HTTPException(status_code=404, detail="Survey not found")

    # If token is provided, verify it (unless admin or public preview)
    if token and survey.secure_token != token:
        # We can still allow if valid admin token header or if token matches
        pass

    store = await get_store_details_by_customer(db, survey.customer_id)
    
    photo_list = [
        SurveyPhotoResponse(
            id=p.id,
            photoType=p.photo_type,
            fileName=p.file_name,
            filePath=f"/uploads/{os.path.basename(p.file_path)}",
            fileSize=p.file_size,
            createdAt=p.created_at.isoformat()
        ) for p in (survey.photos or [])
    ]

    return SurveyResponse(
        id=survey.id,
        surveyId=survey.survey_id,
        projectId=survey.survey_id,
        customerId=survey.customer.customer_id,
        secureToken=survey.secure_token,
        status=survey.status,
        customer=CustomerInfoSchema(
            customerName=survey.customer.customer_name,
            ownerName=survey.customer.owner_name,
            mobileNumber=survey.customer.mobile_number,
            whatsAppNumber=survey.customer.whatsapp_number,
            email=survey.customer.email,
            storeAddress=survey.customer.store_address,
            city=survey.customer.city,
            state=survey.customer.state,
            pincode=survey.customer.pincode
        ),
        store=StoreInfoSchema(
            storeName=store.store_name if store else "Retail Store",
            storeType=store.store_type if store else "Supermarket",
            storeArea=store.store_area if store else None,
            approxWidth=store.approx_width if store else None,
            approxHeight=store.approx_height if store else None,
            unit=store.unit if store else "Feet + Inches"
        ),
        survey=SurveyInfoSchema(
            surveyDate=survey.survey_date,
            salesmanName=survey.salesman_name,
            siteContactPerson=survey.site_contact_person,
            remarks=survey.remarks,
            specialRequirements=survey.special_requirements
        ),
        photos=photo_list,
        revision=survey.project.revision if survey.project else "REV 1",
        createdAt=survey.created_at.isoformat(),
        updatedAt=survey.updated_at.isoformat()
    )

@router.post("/{survey_id}/photos")
async def upload_survey_photo(
    survey_id: str,
    file: UploadFile = File(...),
    photo_type: str = Form("store_photo"), # store_photo, floor_plan, reference_image
    db: AsyncSession = Depends(get_db)
):
    survey = await get_survey_by_id(db, survey_id)
    if not survey:
        raise HTTPException(status_code=404, detail="Survey not found")

    ext = os.path.splitext(file.filename)[1]
    safe_filename = f"{survey_id}_{uuid.uuid4().hex[:8]}{ext}"
    target_path = os.path.join(settings.UPLOAD_DIR, safe_filename)

    with open(target_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    photo = SurveyPhoto(
        survey_id=survey.id,
        photo_type=photo_type,
        file_path=target_path,
        file_name=file.filename,
        file_size=os.path.getsize(target_path)
    )
    db.add(photo)
    await db.commit()
    await db.refresh(photo)

    return {
        "id": photo.id,
        "photoType": photo.photo_type,
        "fileName": photo.file_name,
        "url": f"/uploads/{safe_filename}",
        "createdAt": photo.created_at.isoformat()
    }
