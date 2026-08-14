from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from app.api.v1.deps import get_current_user
from app.core.security import create_access_token, verify_password
from app.db.session import get_db
from app.models.employee import Employee

router = APIRouter(prefix="/auth", tags=["auth"])


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    employee_id: str
    role: str
    full_name: str


class UserOut(BaseModel):
    id: int
    employee_id: str
    email: str
    first_name: str
    last_name: str
    role: str
    job_title: str | None
    department_id: int | None
    is_active: bool

    model_config = {"from_attributes": True}


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    employee = db.query(Employee).filter(Employee.email == payload.email).first()
    if not employee or not verify_password(payload.password, employee.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )
    if not employee.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is inactive")

    token = create_access_token(subject=employee.id, role=employee.role.value)
    return TokenResponse(
        access_token=token,
        employee_id=employee.employee_id,
        role=employee.role.value,
        full_name=f"{employee.first_name} {employee.last_name}",
    )


@router.get("/me", response_model=UserOut)
def get_me(current_user: Employee = Depends(get_current_user)):
    return current_user
