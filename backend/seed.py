"""
Seed script — run once from the backend/ directory:
    python seed.py
Idempotent: skips if employees already exist.
"""
from datetime import date

from passlib.context import CryptContext
from sqlalchemy.orm import Session

import app.db.base_import  # noqa: F401 — registers all models
from app.db.base import Base
from app.db.session import SessionLocal, engine
from app.models.ai_audit_log import AgentType, AIAuditLog
from app.models.announcement import Announcement
from app.models.department import Department
from app.models.employee import Employee, UserRole
from app.models.hr_policy import HRPolicy
from app.models.leave import LeaveBalance, LeaveType
from app.models.project import EmployeeProject, Project, ProjectStatus
from app.models.skill import EmployeeSkill, ProficiencyLevel, Skill
from app.models.ticket import Ticket, TicketPriority, TicketStatus

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(plain: str) -> str:
    return pwd_context.hash(plain)


def seed(db: Session) -> None:
    if db.query(Employee).count() > 0:
        print("Database already seeded — skipping.")
        return

    # ------------------------------------------------------------------
    # Departments
    # ------------------------------------------------------------------
    dept_hr = Department(name="Human Resources", description="People operations and HR policy management")
    dept_eng = Department(name="Engineering", description="Software development and infrastructure")
    dept_fin = Department(name="Finance", description="Financial planning, payroll, and accounting")
    dept_mkt = Department(name="Marketing", description="Brand, growth, and communications")
    dept_ops = Department(name="Operations", description="Business operations and administration")

    db.add_all([dept_hr, dept_eng, dept_fin, dept_mkt, dept_ops])
    db.flush()

    # ------------------------------------------------------------------
    # Employees
    # ------------------------------------------------------------------
    admin = Employee(
        employee_id="EMP001",
        first_name="Nova",
        last_name="Admin",
        email="admin@novaworks.com",
        hashed_password=hash_password("Admin@123"),
        role=UserRole.ADMIN,
        job_title="System Administrator",
        hire_date=date(2019, 6, 1),
        is_active=True,
        department_id=dept_hr.id,
    )

    hr_manager = Employee(
        employee_id="EMP002",
        first_name="Priya",
        last_name="Sharma",
        email="priya.sharma@novaworks.com",
        hashed_password=hash_password("Manager@123"),
        role=UserRole.MANAGER,
        job_title="HR Manager",
        hire_date=date(2020, 3, 15),
        is_active=True,
        department_id=dept_hr.id,
    )

    eng_manager = Employee(
        employee_id="EMP003",
        first_name="Arjun",
        last_name="Mehta",
        email="arjun.mehta@novaworks.com",
        hashed_password=hash_password("Manager@123"),
        role=UserRole.MANAGER,
        job_title="Engineering Manager",
        hire_date=date(2020, 1, 10),
        is_active=True,
        department_id=dept_eng.id,
    )

    emp_raj = Employee(
        employee_id="EMP004",
        first_name="Raj",
        last_name="Kumar",
        email="raj.kumar@novaworks.com",
        hashed_password=hash_password("Employee@123"),
        role=UserRole.EMPLOYEE,
        job_title="Software Engineer",
        hire_date=date(2021, 7, 19),
        is_active=True,
        department_id=dept_eng.id,
    )

    emp_sara = Employee(
        employee_id="EMP005",
        first_name="Sara",
        last_name="Thomas",
        email="sara.thomas@novaworks.com",
        hashed_password=hash_password("Employee@123"),
        role=UserRole.EMPLOYEE,
        job_title="Frontend Developer",
        hire_date=date(2022, 2, 7),
        is_active=True,
        department_id=dept_eng.id,
    )

    emp_anil = Employee(
        employee_id="EMP006",
        first_name="Anil",
        last_name="Verma",
        email="anil.verma@novaworks.com",
        hashed_password=hash_password("Employee@123"),
        role=UserRole.EMPLOYEE,
        job_title="Financial Analyst",
        hire_date=date(2021, 11, 1),
        is_active=True,
        department_id=dept_fin.id,
    )

    emp_meena = Employee(
        employee_id="EMP007",
        first_name="Meena",
        last_name="Nair",
        email="meena.nair@novaworks.com",
        hashed_password=hash_password("Employee@123"),
        role=UserRole.EMPLOYEE,
        job_title="Marketing Specialist",
        hire_date=date(2023, 4, 3),
        is_active=True,
        department_id=dept_mkt.id,
    )

    db.add_all([admin, hr_manager, eng_manager, emp_raj, emp_sara, emp_anil, emp_meena])
    db.flush()

    # Wire manager relationships
    emp_raj.manager_id = eng_manager.id
    emp_sara.manager_id = eng_manager.id
    emp_anil.manager_id = admin.id
    emp_meena.manager_id = admin.id
    hr_manager.manager_id = admin.id
    eng_manager.manager_id = admin.id

    # Wire department managers
    dept_hr.manager_id = hr_manager.id
    dept_eng.manager_id = eng_manager.id

    db.flush()

    # ------------------------------------------------------------------
    # HR Policies
    # ------------------------------------------------------------------
    policies = [
        HRPolicy(
            title="Annual Leave Policy",
            category="leave",
            content=(
                "Employees are entitled to 18 days of annual leave per calendar year. "
                "Leave must be applied at least 3 working days in advance and approved by the line manager. "
                "Unused leave up to 5 days may be carried forward to the next year. "
                "Leave encashment is not permitted except upon resignation."
            ),
        ),
        HRPolicy(
            title="Sick Leave Policy",
            category="leave",
            content=(
                "Employees are entitled to 10 days of paid sick leave per year. "
                "A medical certificate is required for absences exceeding 2 consecutive days. "
                "Sick leave cannot be carried forward or encashed."
            ),
        ),
        HRPolicy(
            title="Remote Work Policy",
            category="remote_work",
            content=(
                "Employees may work remotely up to 2 days per week subject to manager approval. "
                "Core hours are 10 AM–4 PM in the employee's local timezone. "
                "Remote employees are responsible for maintaining a secure and productive work environment. "
                "All company data must be accessed over a VPN when working remotely."
            ),
        ),
        HRPolicy(
            title="Code of Conduct",
            category="conduct",
            content=(
                "All employees are expected to maintain professional conduct at all times. "
                "Harassment, discrimination, or bullying of any kind is strictly prohibited and may result in termination. "
                "Conflicts of interest must be disclosed to the HR department immediately. "
                "Employees must protect confidential company and customer information."
            ),
        ),
        HRPolicy(
            title="Performance Review Policy",
            category="performance",
            content=(
                "Performance reviews are conducted bi-annually in June and December. "
                "Each employee sets goals at the start of the review cycle in collaboration with their manager. "
                "Ratings are: Exceeds Expectations, Meets Expectations, Needs Improvement. "
                "Salary revisions are linked to performance review outcomes."
            ),
        ),
        HRPolicy(
            title="Employee Benefits Policy",
            category="benefits",
            content=(
                "All full-time employees are entitled to health insurance coverage for themselves and immediate family. "
                "Employees are eligible for a learning & development budget of INR 25,000 per year. "
                "Provident fund contributions are made at 12% of basic salary by both employee and employer. "
                "Gratuity is payable after 5 years of continuous service."
            ),
        ),
    ]
    db.add_all(policies)
    db.flush()

    # ------------------------------------------------------------------
    # Skills
    # ------------------------------------------------------------------
    skill_python = Skill(name="Python", category="Programming")
    skill_js = Skill(name="JavaScript", category="Programming")
    skill_sql = Skill(name="SQL", category="Database")
    skill_react = Skill(name="React", category="Frontend")
    skill_fastapi = Skill(name="FastAPI", category="Backend Framework")
    skill_excel = Skill(name="Excel / Financial Modelling", category="Finance")
    skill_hr = Skill(name="HR Operations", category="HR")

    db.add_all([skill_python, skill_js, skill_sql, skill_react, skill_fastapi, skill_excel, skill_hr])
    db.flush()

    # Employee skills
    db.add_all([
        EmployeeSkill(employee_id=emp_raj.id, skill_id=skill_python.id, proficiency_level=ProficiencyLevel.ADVANCED),
        EmployeeSkill(employee_id=emp_raj.id, skill_id=skill_sql.id, proficiency_level=ProficiencyLevel.INTERMEDIATE),
        EmployeeSkill(employee_id=emp_raj.id, skill_id=skill_fastapi.id, proficiency_level=ProficiencyLevel.INTERMEDIATE),
        EmployeeSkill(employee_id=emp_sara.id, skill_id=skill_js.id, proficiency_level=ProficiencyLevel.ADVANCED),
        EmployeeSkill(employee_id=emp_sara.id, skill_id=skill_react.id, proficiency_level=ProficiencyLevel.EXPERT),
        EmployeeSkill(employee_id=emp_anil.id, skill_id=skill_excel.id, proficiency_level=ProficiencyLevel.EXPERT),
        EmployeeSkill(employee_id=emp_anil.id, skill_id=skill_sql.id, proficiency_level=ProficiencyLevel.BEGINNER),
        EmployeeSkill(employee_id=hr_manager.id, skill_id=skill_hr.id, proficiency_level=ProficiencyLevel.EXPERT),
    ])
    db.flush()

    # ------------------------------------------------------------------
    # Projects
    # ------------------------------------------------------------------
    proj_copilot = Project(
        name="NovaWorks HR Copilot",
        description="AI-powered HR assistant for employee self-service",
        start_date=date(2025, 1, 1),
        status=ProjectStatus.ACTIVE,
    )
    proj_portal = Project(
        name="Employee Self-Service Portal",
        description="Web portal for leave, payslips and HR requests",
        start_date=date(2024, 6, 1),
        end_date=date(2025, 3, 31),
        status=ProjectStatus.COMPLETED,
    )

    db.add_all([proj_copilot, proj_portal])
    db.flush()

    db.add_all([
        EmployeeProject(employee_id=emp_raj.id, project_id=proj_copilot.id, role="Backend Developer", joined_at=date(2025, 1, 1)),
        EmployeeProject(employee_id=emp_sara.id, project_id=proj_copilot.id, role="Frontend Developer", joined_at=date(2025, 1, 1)),
        EmployeeProject(employee_id=eng_manager.id, project_id=proj_copilot.id, role="Tech Lead", joined_at=date(2025, 1, 1)),
        EmployeeProject(employee_id=emp_raj.id, project_id=proj_portal.id, role="Developer", joined_at=date(2024, 6, 1)),
    ])
    db.flush()

    # ------------------------------------------------------------------
    # Leave Balances (current year)
    # ------------------------------------------------------------------
    current_year = 2025
    leave_seeds = [
        (emp_raj.id, LeaveType.ANNUAL, 18.0, 3.0),
        (emp_raj.id, LeaveType.SICK, 10.0, 1.0),
        (emp_sara.id, LeaveType.ANNUAL, 18.0, 5.0),
        (emp_sara.id, LeaveType.SICK, 10.0, 0.0),
        (emp_anil.id, LeaveType.ANNUAL, 18.0, 7.0),
        (emp_anil.id, LeaveType.SICK, 10.0, 2.0),
        (emp_meena.id, LeaveType.ANNUAL, 18.0, 0.0),
        (emp_meena.id, LeaveType.SICK, 10.0, 0.0),
        (hr_manager.id, LeaveType.ANNUAL, 18.0, 4.0),
        (eng_manager.id, LeaveType.ANNUAL, 18.0, 6.0),
    ]
    for emp_id, ltype, total, used in leave_seeds:
        db.add(LeaveBalance(employee_id=emp_id, leave_type=ltype, total_days=total, used_days=used, year=current_year))
    db.flush()

    # ------------------------------------------------------------------
    # Tickets
    # ------------------------------------------------------------------
    db.add_all([
        Ticket(
            ticket_number="TKT-001",
            employee_id=emp_raj.id,
            title="Payslip not received for March 2025",
            description="I have not received my payslip for March 2025 in the portal.",
            category="payroll",
            status=TicketStatus.RESOLVED,
            priority=TicketPriority.HIGH,
            assigned_to=hr_manager.id,
            resolution="Payslip was regenerated and sent to employee email.",
        ),
        Ticket(
            ticket_number="TKT-002",
            employee_id=emp_sara.id,
            title="Request for experience letter",
            description="Requesting an experience letter for visa application purposes.",
            category="documents",
            status=TicketStatus.OPEN,
            priority=TicketPriority.MEDIUM,
            assigned_to=hr_manager.id,
        ),
    ])
    db.flush()

    # ------------------------------------------------------------------
    # Announcements
    # ------------------------------------------------------------------
    db.add_all([
        Announcement(
            title="Q2 2025 Performance Reviews Starting",
            content="Performance reviews for Q2 2025 will begin on June 16. Please complete your self-assessments by June 13.",
            author_id=hr_manager.id,
            target_role=None,
            is_active=True,
        ),
        Announcement(
            title="New Remote Work Policy Effective July 1",
            content="The updated Remote Work Policy is now in effect. Employees may work from home up to 2 days per week. Please review the full policy in the HR portal.",
            author_id=hr_manager.id,
            target_role=None,
            is_active=True,
        ),
        Announcement(
            title="Engineering Guild — Monthly Sync",
            content="The monthly engineering guild meeting is scheduled for June 20 at 3 PM. All engineers are requested to attend.",
            author_id=eng_manager.id,
            target_role="EMPLOYEE",
            is_active=True,
        ),
    ])
    db.flush()

    db.commit()
    print("Seed complete.")
    print(f"  Departments : 5")
    print(f"  Employees   : 7  (admin / 2 managers / 4 staff)")
    print(f"  HR Policies : {len(policies)}")
    print(f"  Skills      : 7")
    print(f"  Projects    : 2")
    print(f"  Tickets     : 2")
    print(f"  Announcements: 3")


if __name__ == "__main__":
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        seed(db)
    finally:
        db.close()
