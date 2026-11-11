from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import Project, Video
from ..schemas import ProjectCreate, ProjectOut
from ..security import safe_storage_path
from ..config import get_settings

router = APIRouter(prefix="/projects", tags=["projects"])


def serialize(project: Project) -> ProjectOut:
    return ProjectOut(id=project.id, name=project.name, created_at=project.created_at,
                      updated_at=project.updated_at, video_count=len(project.videos))


@router.get("", response_model=list[ProjectOut])
def list_projects(db: Session = Depends(get_db)):
    return [serialize(p) for p in db.query(Project).order_by(Project.updated_at.desc()).all()]


@router.post("", response_model=ProjectOut, status_code=201)
def create_project(payload: ProjectCreate, db: Session = Depends(get_db)):
    project = Project(name=payload.name.strip())
    db.add(project)
    db.commit()
    db.refresh(project)
    return serialize(project)


@router.patch("/{project_id}", response_model=ProjectOut)
def rename_project(project_id: int, payload: ProjectCreate, db: Session = Depends(get_db)):
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(404, "Project not found")
    project.name = payload.name.strip()
    db.commit()
    return serialize(project)


@router.delete("/{project_id}", status_code=204)
def delete_project(project_id: int, delete_files: bool = False, db: Session = Depends(get_db)):
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(404, "Project not found")
    if delete_files:
        settings = get_settings()
        for video in project.videos:
            for raw_path, root in [(video.file_path, settings.videos_dir), (video.thumbnail_path, settings.thumbnails_dir)]:
                if raw_path:
                    try:
                        safe_storage_path(raw_path, root).unlink(missing_ok=True)
                    except ValueError:
                        pass
            for reel in video.reels:
                if reel.output_path:
                    try:
                        safe_storage_path(reel.output_path, settings.reels_dir).unlink(missing_ok=True)
                    except ValueError:
                        pass
    db.delete(project)
    db.commit()
