from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.v1.deps import get_current_user, require_roles
from app.db.session import get_db
from app.models.announcement import Announcement
from app.models.employee import Employee, UserRole

router = APIRouter(prefix="/announcements", tags=["announcements"])


# ---------- Schemas ----------

class CreateAnnouncement(BaseModel):
    title: str
    content: str
    target_role: str | None = None


class AnnouncementOut(BaseModel):
    id: int
    title: str
    content: str
    author_id: int
    target_role: str | None
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


# ---------- Endpoints ----------

@router.post(
    "",
    response_model=AnnouncementOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_roles(UserRole.MANAGER, UserRole.ADMIN))],
)
def create_announcement(
    payload: CreateAnnouncement,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_user),
):
    announcement = Announcement(
        title=payload.title,
        content=payload.content,
        author_id=current_user.id,
        target_role=payload.target_role,
        is_active=True,
    )
    db.add(announcement)
    db.commit()
    db.refresh(announcement)
    return announcement


@router.get("", response_model=list[AnnouncementOut])
def list_announcements(
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_user),
):
    query = db.query(Announcement).filter(Announcement.is_active == True)
    if current_user.role != UserRole.ADMIN:
        query = query.filter(
            (Announcement.target_role == None) |
            (Announcement.target_role == current_user.role.value)
        )
    return query.order_by(Announcement.created_at.desc()).all()


@router.delete("/{announcement_id}", status_code=status.HTTP_204_NO_CONTENT)
def deactivate_announcement(
    announcement_id: int,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(require_roles(UserRole.MANAGER, UserRole.ADMIN)),
):
    ann = db.query(Announcement).filter(Announcement.id == announcement_id).first()
    if not ann:
        raise HTTPException(status_code=404, detail="Announcement not found")
    if current_user.role == UserRole.MANAGER and ann.author_id != current_user.id:
        raise HTTPException(status_code=403, detail="Managers can only deactivate their own announcements")
    ann.is_active = False
    db.commit()
