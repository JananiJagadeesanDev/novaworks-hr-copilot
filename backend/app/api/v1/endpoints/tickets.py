from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.v1.deps import get_current_user, require_roles
from app.db.session import get_db
from app.models.employee import Employee, UserRole
from app.models.ticket import Ticket, TicketPriority, TicketStatus

router = APIRouter(prefix="/tickets", tags=["tickets"])


# ---------- Schemas ----------

class CreateTicket(BaseModel):
    title: str
    description: str
    category: str
    priority: TicketPriority = TicketPriority.MEDIUM


class UpdateTicket(BaseModel):
    status: TicketStatus | None = None
    priority: TicketPriority | None = None
    assigned_to: int | None = None
    resolution: str | None = None


class TicketOut(BaseModel):
    id: int
    ticket_number: str
    employee_id: int
    title: str
    description: str
    category: str
    status: str
    priority: str
    assigned_to: int | None
    resolution: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


# ---------- Helpers ----------

def _generate_ticket_number(db: Session) -> str:
    count = db.query(Ticket).count()
    return f"TKT-{count + 1:04d}"


# ---------- Endpoints ----------

@router.post("", response_model=TicketOut, status_code=status.HTTP_201_CREATED)
def create_ticket(
    payload: CreateTicket,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_user),
):
    ticket = Ticket(
        ticket_number=_generate_ticket_number(db),
        employee_id=current_user.id,
        title=payload.title,
        description=payload.description,
        category=payload.category,
        priority=payload.priority,
        status=TicketStatus.OPEN,
    )
    db.add(ticket)
    db.commit()
    db.refresh(ticket)
    return ticket


@router.get("", response_model=list[TicketOut])
def list_tickets(
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_user),
):
    query = db.query(Ticket)
    if current_user.role == UserRole.EMPLOYEE:
        query = query.filter(Ticket.employee_id == current_user.id)
    return query.order_by(Ticket.created_at.desc()).all()


@router.get("/{ticket_id}", response_model=TicketOut)
def get_ticket(
    ticket_id: int,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_user),
):
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    if current_user.role == UserRole.EMPLOYEE and ticket.employee_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    return ticket


@router.patch("/{ticket_id}", response_model=TicketOut)
def update_ticket(
    ticket_id: int,
    payload: UpdateTicket,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_user),
):
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")

    if current_user.role == UserRole.EMPLOYEE:
        if ticket.employee_id != current_user.id:
            raise HTTPException(status_code=403, detail="Access denied")
        if payload.assigned_to is not None or payload.resolution is not None:
            raise HTTPException(status_code=403, detail="Employees cannot assign or resolve tickets")

    if payload.status is not None:
        ticket.status = payload.status
    if payload.priority is not None:
        ticket.priority = payload.priority
    if payload.assigned_to is not None:
        ticket.assigned_to = payload.assigned_to
    if payload.resolution is not None:
        ticket.resolution = payload.resolution

    db.commit()
    db.refresh(ticket)
    return ticket
