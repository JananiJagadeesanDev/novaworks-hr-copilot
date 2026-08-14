from datetime import date, datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.v1.deps import get_current_user, require_roles
from app.db.session import get_db
from app.models.employee import Employee, UserRole
from app.models.leave import LeaveBalance, LeaveRequest, LeaveStatus, LeaveType

router = APIRouter(prefix="/leaves", tags=["leaves"])


# ---------- Schemas ----------

class CreateLeaveRequest(BaseModel):
    leave_type: LeaveType
    start_date: date
    end_date: date
    reason: str | None = None
    is_half_day: bool = False
    half_day_period: str | None = None


class UpdateLeaveRequest(BaseModel):
    status: LeaveStatus
    approver_notes: str | None = None


class LeaveRequestOut(BaseModel):
    id: int
    employee_id: int
    leave_type: str
    start_date: date
    end_date: date
    status: str
    reason: str | None
    approved_by: int | None
    approver_notes: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class LeaveBalanceOut(BaseModel):
    leave_type: str
    total_days: float
    used_days: float
    available_days: float
    year: int

    model_config = {"from_attributes": True}


# ---------- Helpers ----------

def _calc_days(start: date, end: date, is_half_day: bool) -> float:
    if start > end:
        raise HTTPException(status_code=400, detail="start_date must be before or equal to end_date")
    days = (end - start).days + 1
    return 0.5 if is_half_day else float(days)


# ---------- Endpoints ----------

@router.post("/requests", response_model=LeaveRequestOut, status_code=status.HTTP_201_CREATED)
def create_leave_request(
    payload: CreateLeaveRequest,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_user),
):
    days = _calc_days(payload.start_date, payload.end_date, payload.is_half_day)
    year = payload.start_date.year

    balance = db.query(LeaveBalance).filter(
        LeaveBalance.employee_id == current_user.id,
        LeaveBalance.leave_type == payload.leave_type,
        LeaveBalance.year == year,
    ).first()

    if not balance:
        raise HTTPException(status_code=400, detail=f"No {payload.leave_type} balance found for {year}")
    if (balance.total_days - balance.used_days) < days:
        raise HTTPException(
            status_code=400,
            detail=f"Insufficient balance. Available: {balance.total_days - balance.used_days} days",
        )

    leave = LeaveRequest(
        employee_id=current_user.id,
        leave_type=payload.leave_type,
        start_date=payload.start_date,
        end_date=payload.end_date,
        reason=payload.reason,
        status=LeaveStatus.PENDING,
    )
    db.add(leave)
    db.commit()
    db.refresh(leave)
    return leave


@router.get("/requests", response_model=list[LeaveRequestOut])
def list_leave_requests(
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_user),
):
    query = db.query(LeaveRequest)
    if current_user.role == UserRole.EMPLOYEE:
        query = query.filter(LeaveRequest.employee_id == current_user.id)
    elif current_user.role == UserRole.MANAGER:
        subordinate_ids = [e.id for e in db.query(Employee).filter(Employee.manager_id == current_user.id).all()]
        subordinate_ids.append(current_user.id)
        query = query.filter(LeaveRequest.employee_id.in_(subordinate_ids))
    return query.order_by(LeaveRequest.created_at.desc()).all()


@router.patch("/requests/{request_id}", response_model=LeaveRequestOut)
def update_leave_request(
    request_id: int,
    payload: UpdateLeaveRequest,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_user),
):
    leave = db.query(LeaveRequest).filter(LeaveRequest.id == request_id).first()
    if not leave:
        raise HTTPException(status_code=404, detail="Leave request not found")

    if current_user.role == UserRole.EMPLOYEE:
        if leave.employee_id != current_user.id:
            raise HTTPException(status_code=403, detail="You can only modify your own leave requests")
        if payload.status != LeaveStatus.CANCELLED:
            raise HTTPException(status_code=403, detail="Employees can only cancel their own requests")
        if leave.status != LeaveStatus.PENDING:
            raise HTTPException(status_code=400, detail="Only PENDING requests can be cancelled")
    else:
        if payload.status not in (LeaveStatus.APPROVED, LeaveStatus.REJECTED):
            raise HTTPException(status_code=400, detail="Managers/Admins can only APPROVE or REJECT requests")
        if leave.status != LeaveStatus.PENDING:
            raise HTTPException(status_code=400, detail="Only PENDING requests can be approved or rejected")

    prev_status = leave.status
    leave.status = payload.status
    leave.approver_notes = payload.approver_notes

    if payload.status == LeaveStatus.APPROVED:
        leave.approved_by = current_user.id
        days = (leave.end_date - leave.start_date).days + 1
        balance = db.query(LeaveBalance).filter(
            LeaveBalance.employee_id == leave.employee_id,
            LeaveBalance.leave_type == leave.leave_type,
            LeaveBalance.year == leave.start_date.year,
        ).first()
        if balance:
            balance.used_days += float(days)

    db.commit()
    db.refresh(leave)
    return leave


@router.get("/balance", response_model=list[LeaveBalanceOut])
def get_leave_balance(
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_user),
):
    from datetime import date as dt
    year = dt.today().year
    balances = db.query(LeaveBalance).filter(
        LeaveBalance.employee_id == current_user.id,
        LeaveBalance.year == year,
    ).all()
    return [
        LeaveBalanceOut(
            leave_type=b.leave_type,
            total_days=b.total_days,
            used_days=b.used_days,
            available_days=b.total_days - b.used_days,
            year=b.year,
        )
        for b in balances
    ]
