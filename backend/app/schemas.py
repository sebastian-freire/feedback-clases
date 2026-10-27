"""Esquemas de entrada y salida de la API (Pydantic)."""

from datetime import date, time
from typing import Annotated

from pydantic import BaseModel, ConfigDict, EmailStr, Field, StringConstraints, field_validator

from app.feedback_window import WindowState
from app.models import TEXT_MAX_LENGTH, Role

Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=2, max_length=120)]
Password = Annotated[str, Field(min_length=8, max_length=128)]


class OrmModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# --- Autenticación ---


class RegisterRequest(BaseModel):
    email: EmailStr
    full_name: Name
    password: Password


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class UserOut(OrmModel):
    id: int
    email: str
    full_name: str
    roles: list[Role]

    @field_validator("roles", mode="before")
    @classmethod
    def sorted_roles(cls, value: set[Role] | list[Role]) -> list[Role]:
        order = list(Role)
        return sorted(value, key=order.index)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


# --- Alumno ---


class EnrollRequest(BaseModel):
    code: Annotated[str, StringConstraints(strip_whitespace=True, to_upper=True, min_length=1)]


class StudentSubjectOut(BaseModel):
    id: int
    name: str
    teachers: list[str]


class StudentClassOut(BaseModel):
    id: int
    date: date
    start_time: time
    window_state: WindowState
    closes_on: date
    has_feedback: bool


class StudentClassDetailOut(BaseModel):
    subject: StudentSubjectOut
    class_session: StudentClassOut


class StudentSubjectClassesOut(BaseModel):
    subject: StudentSubjectOut
    classes: list[StudentClassOut]


class FeedbackIn(BaseModel):
    rating: Annotated[int, Field(ge=1, le=5, strict=True)]
    liked: str | None = None
    disliked: str | None = None

    @field_validator("liked", "disliked")
    @classmethod
    def normalize_text(cls, value: str | None) -> str | None:
        """Regla R10: opcional, máx. 500 caracteres; vacío o solo espacios = sin comentario."""
        if value is None:
            return None
        value = value.strip()
        if len(value) > TEXT_MAX_LENGTH:
            raise ValueError(f"Máximo {TEXT_MAX_LENGTH} caracteres")
        return value or None


class StudentFeedbackOut(BaseModel):
    class_session_id: int
    rating: int
    liked: str | None
    disliked: str | None
    editable: bool
    closes_on: date


# --- Docente ---


class TeacherSubjectOut(BaseModel):
    id: int
    name: str
    enrollment_code: str
    class_count: int
    response_count: int
    average: float | None


class ClassSummaryOut(BaseModel):
    id: int
    date: date
    start_time: time
    window_state: WindowState
    response_count: int
    average: float | None


class SubjectSummaryOut(BaseModel):
    subject: TeacherSubjectOut
    classes: list[ClassSummaryOut]


class AnonymousFeedbackOut(BaseModel):
    """Lo único que ve el docente de cada feedback (D-018, D-020): sin autor ni fechas."""

    model_config = ConfigDict(extra="forbid")

    rating: int
    liked: str | None
    disliked: str | None


class ClassCommentsOut(BaseModel):
    id: int
    subject_id: int
    subject_name: str
    date: date
    start_time: time
    response_count: int
    average: float | None
    comments: list[AnonymousFeedbackOut]


# --- Administrador ---


class UserBrief(OrmModel):
    id: int
    full_name: str
    email: str


class CreateUserRequest(BaseModel):
    email: EmailStr
    full_name: Name
    password: Password
    roles: Annotated[list[Role], Field(min_length=1)]


class UpdateRolesRequest(BaseModel):
    roles: Annotated[list[Role], Field(min_length=1)]


class AdminSubjectOut(BaseModel):
    id: int
    name: str
    enrollment_code: str
    teachers: list[UserBrief]
    class_count: int
    student_count: int


class AdminClassOut(BaseModel):
    id: int
    date: date
    start_time: time
    can_delete: bool


class AdminSubjectDetailOut(AdminSubjectOut):
    classes: list[AdminClassOut]


class CreateSubjectRequest(BaseModel):
    name: Name
    teacher_ids: list[int] = []


class UpdateTeachersRequest(BaseModel):
    teacher_ids: list[int]


class ScheduleRule(BaseModel):
    weekday: Annotated[int, Field(ge=0, le=6, description="0 = lunes … 6 = domingo")]
    start_time: time


class GenerateClassesRequest(BaseModel):
    start_date: date
    end_date: date
    rules: Annotated[list[ScheduleRule], Field(min_length=1)]


class GenerateClassesOut(BaseModel):
    created: int
    skipped: int


# --- Docente: extras (Fase 6) ---


class WordCount(BaseModel):
    word: str
    count: int


class TopWordsOut(BaseModel):
    liked: list[WordCount]
    disliked: list[WordCount]


class SubjectComparisonOut(BaseModel):
    id: int
    name: str
    average: float | None
    response_count: int
    past_class_count: int
    student_count: int
    participation: float | None = Field(
        description="Respuestas / (alumnos inscriptos × clases dictadas), entre 0 y 1"
    )
