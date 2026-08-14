from datetime import date, datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.v1.deps import get_current_user, require_roles
from app.db.session import get_db
from app.models.employee import Employee, UserRole
from app.models.project import EmployeeProject, Project, ProjectStatus

router = APIRouter(tags=["projects"])


# ---------- Schemas ----------

class AssignEmployeeToProject(BaseModel):
    project_id: int
    role: str | None = None
    joined_at: date | None = None


class EmployeeProjectOut(BaseModel):
    id: int
    employee_id: int
    project_id: int
    role: str | None
    joined_at: date | None

    model_config = {"from_attributes": True}


class ProjectOut(BaseModel):
    id: int
    name: str
    description: str | None
    start_date: date | None
    end_date: date | None
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}


# ---------- Endpoints ----------

@router.post(
    "/employees/{employee_id}/projects",
    response_model=EmployeeProjectOut,
    status_code=status.HTTP_201_CREATED,
)
def assign_employee_to_project(
    employee_id: int,
    payload: AssignEmployeeToProject,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(require_roles(UserRole.MANAGER, UserRole.ADMIN)),
):
    employee = db.query(Employee).filter(Employee.id == employee_id).first()
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")

    project = db.query(Project).filter(Project.id == payload.project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    existing = db.query(EmployeeProject).filter(
        EmployeeProject.employee_id == employee_id,
        EmployeeProject.project_id == payload.project_id,
    ).first()
    if existing:
        raise HTTPException(status_code=409, detail="Employee is already assigned to this project")

    assignment = EmployeeProject(
        employee_id=employee_id,
        project_id=payload.project_id,
        role=payload.role,
        joined_at=payload.joined_at or date.today(),
    )
    db.add(assignment)
    db.commit()
    db.refresh(assignment)
    return assignment


@router.get("/employees/{employee_id}/projects", response_model=list[EmployeeProjectOut])
def get_employee_projects(
    employee_id: int,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_user),
):
    if current_user.role == UserRole.EMPLOYEE and current_user.id != employee_id:
        raise HTTPException(status_code=403, detail="Access denied")

    employee = db.query(Employee).filter(Employee.id == employee_id).first()
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")

    return db.query(EmployeeProject).filter(EmployeeProject.employee_id == employee_id).all()


@router.get("/projects", response_model=list[ProjectOut])
def list_projects(
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_user),
):
    return db.query(Project).order_by(Project.created_at.desc()).all()


@router.get("/projects/{project_id}", response_model=ProjectOut)
def get_project(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_user),
):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project
