from fastapi import APIRouter, Depends, HTTPException, Response, UploadFile, File
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.services.cad_service import get_project_by_id
from app.services.survey_service import get_survey_by_id, get_store_details_by_customer
from app.services.pdf_service import generate_architectural_pdf
import json

router = APIRouter(prefix="/projects", tags=["export"])

@router.get("/{project_id}/export/pdf")
@router.post("/{project_id}/export/pdf")
async def export_project_pdf(project_id: str, db: AsyncSession = Depends(get_db)):
    project = await get_project_by_id(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    survey = project.survey
    if not survey:
        raise HTTPException(status_code=404, detail="Associated survey not found")

    store = await get_store_details_by_customer(db, survey.customer_id)

    # Format entities data for PDF generator
    entities_data = []
    for ent in (project.entities or []):
        try:
            geom = json.loads(ent.geometry_json) if ent.geometry_json else {}
            props = json.loads(ent.properties_json) if ent.properties_json else {}
            entities_data.append({
                "id": ent.entity_id,
                "type": ent.entity_type,
                "geometry": geom,
                "properties": props
            })
        except Exception:
            continue

    project_dict = {
        "title": project.title,
        "revision": project.revision,
        "scale": project.scale,
        "unit": project.unit,
        "notes": project.notes,
        "entities": entities_data
    }

    survey_dict = {
        "surveyId": survey.survey_id,
        "surveyDate": survey.survey_date,
        "customer": {
            "customerName": survey.customer.customer_name if survey.customer else "Customer",
            "ownerName": survey.customer.owner_name if survey.customer else "",
            "mobileNumber": survey.customer.mobile_number if survey.customer else "",
            "city": survey.customer.city if survey.customer else "",
            "state": survey.customer.state if survey.customer else ""
        },
        "store": {
            "storeName": store.store_name if store else "Retail Store",
            "storeType": store.store_type if store else "Supermarket",
            "storeArea": store.store_area if store else ""
        },
        "survey": {
            "salesmanName": survey.salesman_name or "RetailFix Surveyor",
            "siteContactPerson": survey.site_contact_person or ""
        }
    }

    pdf_buffer = generate_architectural_pdf(project_dict, survey_dict)
    filename = f"RETAILFIX_{survey.survey_id}_{project.revision}.pdf"

    return StreamingResponse(
        pdf_buffer,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"'
        }
    )


@router.post("/transcode-mp4")
async def transcode_video_to_mp4(file: UploadFile = File(...)):
    """
    Transcodes an uploaded video file (e.g. WebM recorded in browser)
    into a standardized, WhatsApp and mobile-friendly H.264 MP4 file.
    """
    import os
    import tempfile
    import subprocess
    import imageio_ffmpeg

    ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
    
    with tempfile.NamedTemporaryFile(suffix=".webm", delete=False) as in_temp:
        in_path = in_temp.name
        content = await file.read()
        in_temp.write(content)
        
    out_path = in_path.replace(".webm", ".mp4")
    
    try:
        # Run ffmpeg conversion to universal H.264 baseline/high MP4
        cmd = [
            ffmpeg_exe,
            "-y",
            "-i", in_path,
            "-c:v", "libx264",
            "-preset", "fast",
            "-crf", "22",
            "-pix_fmt", "yuv420p",
            "-movflags", "+faststart",
            out_path
        ]
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if proc.returncode != 0:
            raise HTTPException(status_code=500, detail=f"Transcode failed: {proc.stderr[:300]}")
            
        with open(out_path, "rb") as out_f:
            mp4_bytes = out_f.read()
            
        filename = file.filename or "RetailFix_Store_Walkthrough.mp4"
        if not filename.endswith(".mp4"):
            filename = os.path.splitext(filename)[0] + ".mp4"
            
        return Response(
            content=mp4_bytes,
            media_type="video/mp4",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"'
            }
        )
    finally:
        if os.path.exists(in_path):
            try:
                os.unlink(in_path)
            except Exception:
                pass
        if os.path.exists(out_path):
            try:
                os.unlink(out_path)
            except Exception:
                pass
