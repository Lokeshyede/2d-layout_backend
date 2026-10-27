import json
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from sqlalchemy import delete
from app.models import Project, CADEntity, ProjectVersion, Survey, Customer, StoreDetails, AuditLog
from app.schemas.cad import ProjectSaveRequest, CADEntitySchema

async def get_project_by_id(db: AsyncSession, project_id: str) -> Optional[Project]:
    query = (
        select(Project)
        .where(Project.project_id == project_id)
        .options(
            selectinload(Project.entities),
            selectinload(Project.versions),
            selectinload(Project.survey).selectinload(Survey.customer)
        )
    )
    result = await db.execute(query)
    return result.scalar_one_or_none()

async def save_project_state(
    db: AsyncSession,
    project_id: str,
    save_req: ProjectSaveRequest,
    user_type: str = "customer",
    username: Optional[str] = None
) -> Project:
    query = (
        select(Project)
        .where(Project.project_id == project_id)
        .with_for_update()
        .options(
            selectinload(Project.entities),
            selectinload(Project.versions),
            selectinload(Project.survey).selectinload(Survey.customer)
        )
    )
    result = await db.execute(query)
    project = result.scalar_one_or_none()
    
    if not project:
        raise ValueError(f"Project with ID {project_id} not found")

    # Update project properties
    if save_req.title:
        project.title = save_req.title
    if save_req.scale:
        project.scale = save_req.scale
    if save_req.unit:
        project.unit = save_req.unit
    if save_req.notes is not None:
        project.notes = save_req.notes
    if save_req.viewport:
        project.viewport_data = json.dumps(save_req.viewport.model_dump())

    # Replace entities with new snapshot
    await db.execute(delete(CADEntity).where(CADEntity.project_id == project.id))
    
    for ent in save_req.entities:
        db_entity = CADEntity(
            project_id=project.id,
            entity_id=ent.id,
            entity_type=ent.type,
            geometry_json=json.dumps(ent.geometry),
            properties_json=json.dumps(ent.properties or {}),
            layer=ent.layer or "default",
            z_index=ent.zIndex or 0
        )
        db.add(db_entity)

    # If a new revision is requested, advance revision and create version snapshot
    if save_req.createRevision or save_req.revisionName:
        rev_name = save_req.revisionName
        if not rev_name:
            current_rev_num = len(project.versions) + 1
            rev_name = f"REV {current_rev_num}"
        
        project.revision = rev_name
        
        snapshot = {
            "revision": rev_name,
            "viewport": save_req.viewport.model_dump() if save_req.viewport else json.loads(project.viewport_data or "{}"),
            "scale": project.scale,
            "entities": [e.model_dump() for e in save_req.entities],
            "savedAt": datetime.now(timezone.utc).isoformat()
        }
        
        new_version = ProjectVersion(
            project_id=project.id,
            revision_name=rev_name,
            snapshot_json=json.dumps(snapshot),
            created_by=username or user_type
        )
        db.add(new_version)

    if save_req.entities and project.survey:
        project.survey.status = "layout_completed" if len(save_req.entities) > 3 else "layout_in_progress"

    audit = AuditLog(
        event_type="PROJECT_SAVED",
        project_id=project_id,
        survey_id=project.survey.survey_id if project.survey else None,
        user_type=user_type,
        details=f"Saved {len(save_req.entities)} entities. Revision: {project.revision}"
    )
    db.add(audit)

    await db.commit()
    await db.refresh(project)
    return project
