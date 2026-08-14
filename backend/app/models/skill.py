import enum

from sqlalchemy import Enum, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class ProficiencyLevel(str, enum.Enum):
    BEGINNER = "BEGINNER"
    INTERMEDIATE = "INTERMEDIATE"
    ADVANCED = "ADVANCED"
    EXPERT = "EXPERT"


class Skill(Base):
    __tablename__ = "skills"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(150), unique=True, nullable=False)
    category: Mapped[str | None] = mapped_column(String(100), nullable=True)

    employee_skills: Mapped[list["EmployeeSkill"]] = relationship(
        "EmployeeSkill", back_populates="skill"
    )


class EmployeeSkill(Base):
    __tablename__ = "employee_skills"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    employee_id: Mapped[int] = mapped_column(Integer, ForeignKey("employees.id"), nullable=False)
    skill_id: Mapped[int] = mapped_column(Integer, ForeignKey("skills.id"), nullable=False)
    proficiency_level: Mapped[ProficiencyLevel] = mapped_column(
        Enum(ProficiencyLevel), default=ProficiencyLevel.BEGINNER, nullable=False
    )

    employee: Mapped["Employee"] = relationship(  # type: ignore[name-defined]
        "Employee", back_populates="skills"
    )
    skill: Mapped["Skill"] = relationship("Skill", back_populates="employee_skills")
