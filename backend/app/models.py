"""Modelos de la base de datos. Ver el diagrama ER en docs/ARQUITECTURA.md."""

import enum
from datetime import date, datetime, time

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    SmallInteger,
    String,
    Time,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base

TEXT_MAX_LENGTH = 500
ENROLLMENT_CODE_LENGTH = 8


class Role(enum.StrEnum):
    STUDENT = "student"
    TEACHER = "teacher"
    ADMIN = "admin"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True)
    full_name: Mapped[str] = mapped_column(String(120))
    password_hash: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    role_rows: Mapped[list["UserRole"]] = relationship(
        back_populates="user", cascade="all, delete-orphan", lazy="selectin"
    )

    @property
    def roles(self) -> set[Role]:
        return {row.role for row in self.role_rows}

    def has_role(self, role: Role) -> bool:
        return role in self.roles


class UserRole(Base):
    __tablename__ = "user_roles"

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    role: Mapped[Role] = mapped_column(
        Enum(Role, name="role", values_callable=lambda roles: [r.value for r in roles]),
        primary_key=True,
    )

    user: Mapped[User] = relationship(back_populates="role_rows")


class Subject(Base):
    __tablename__ = "subjects"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    enrollment_code: Mapped[str] = mapped_column(String(ENROLLMENT_CODE_LENGTH), unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    teachers: Mapped[list[User]] = relationship(
        secondary="subject_teachers", order_by="User.full_name", lazy="selectin"
    )


class SubjectTeacher(Base):
    __tablename__ = "subject_teachers"

    subject_id: Mapped[int] = mapped_column(
        ForeignKey("subjects.id", ondelete="CASCADE"), primary_key=True
    )
    teacher_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )


class Enrollment(Base):
    __tablename__ = "enrollments"

    subject_id: Mapped[int] = mapped_column(
        ForeignKey("subjects.id", ondelete="CASCADE"), primary_key=True
    )
    student_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ClassSession(Base):
    """Una clase de una materia en una fecha y hora (la hora es informativa, ver D-027)."""

    __tablename__ = "class_sessions"
    __table_args__ = (
        UniqueConstraint("subject_id", "date", "start_time", name="uq_class_session_slot"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    subject_id: Mapped[int] = mapped_column(
        ForeignKey("subjects.id", ondelete="CASCADE"), index=True
    )
    date: Mapped[date] = mapped_column(Date)
    start_time: Mapped[time] = mapped_column(Time)

    subject: Mapped[Subject] = relationship()


class Feedback(Base):
    __tablename__ = "feedback"
    __table_args__ = (
        # Regla R1: un solo feedback por alumno y clase, también a nivel base.
        UniqueConstraint("class_session_id", "student_id", name="uq_feedback_student_class"),
        CheckConstraint("rating BETWEEN 1 AND 5", name="ck_feedback_rating_range"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    # RESTRICT: una clase con feedback no se puede borrar (regla R9).
    class_session_id: Mapped[int] = mapped_column(
        ForeignKey("class_sessions.id", ondelete="RESTRICT"), index=True
    )
    # Solo para unicidad y para que el alumno edite el suyo; nunca se expone al docente (D-018).
    student_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    rating: Mapped[int] = mapped_column(SmallInteger)
    liked: Mapped[str | None] = mapped_column(String(TEXT_MAX_LENGTH))
    disliked: Mapped[str | None] = mapped_column(String(TEXT_MAX_LENGTH))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
