from datetime import timedelta

from fastapi import APIRouter, HTTPException, Response, status
from sqlalchemy import delete, exists, func, select

from app.codes import generate_enrollment_code
from app.db import DbSession
from app.deps import AdminUser
from app.models import (
    ClassSession,
    Enrollment,
    Feedback,
    Role,
    Subject,
    SubjectTeacher,
    User,
    UserRole,
)
from app.routers.auth import find_user_by_email
from app.schemas import (
    AdminClassOut,
    AdminSubjectDetailOut,
    AdminSubjectOut,
    CreateSubjectRequest,
    CreateUserRequest,
    GenerateClassesOut,
    GenerateClassesRequest,
    UpdateRolesRequest,
    UpdateTeachersRequest,
    UserBrief,
    UserOut,
)
from app.security import hash_password

# Regla R7: ningún endpoint de este router devuelve feedback, promedios ni comentarios.
router = APIRouter(prefix="/admin", tags=["administrador"])

MAX_GENERATION_DAYS = 400


# --- Usuarios ---


@router.get("/users", response_model=list[UserOut])
def list_users(_: AdminUser, db: DbSession, role: Role | None = None) -> list[User]:
    query = select(User).order_by(User.full_name)
    if role is not None:
        query = query.where(User.role_rows.any(UserRole.role == role))
    return list(db.scalars(query))


@router.post("/users", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def create_user(body: CreateUserRequest, _: AdminUser, db: DbSession) -> User:
    """Alta de docentes, admins u otras cuentas con los roles indicados (D-038)."""
    if find_user_by_email(db, body.email):
        raise HTTPException(status.HTTP_409_CONFLICT, "Ya existe una cuenta con ese email.")
    user = User(
        email=body.email.lower(),
        full_name=body.full_name,
        password_hash=hash_password(body.password),
        role_rows=[UserRole(role=role) for role in set(body.roles)],
    )
    db.add(user)
    db.commit()
    return user


@router.put("/users/{user_id}/roles", response_model=UserOut)
def update_roles(user_id: int, body: UpdateRolesRequest, admin: AdminUser, db: DbSession) -> User:
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Usuario no encontrado.")
    new_roles = set(body.roles)
    if user.id == admin.id and Role.ADMIN not in new_roles:
        raise HTTPException(
            status.HTTP_409_CONFLICT, "No podés quitarte a vos mismo el rol de administrador."
        )
    if Role.TEACHER not in new_roles:  # deja de ser docente: se lo desasigna de sus materias
        db.execute(delete(SubjectTeacher).where(SubjectTeacher.teacher_id == user.id))
    user.role_rows = [row for row in user.role_rows if row.role in new_roles] + [
        UserRole(role=role) for role in new_roles - user.roles
    ]
    db.commit()
    db.refresh(user)
    return user


# --- Materias ---


def subjects_query():
    class_count = (
        select(func.count(ClassSession.id))
        .where(ClassSession.subject_id == Subject.id)
        .scalar_subquery()
    )
    student_count = (
        select(func.count()).where(Enrollment.subject_id == Subject.id).scalar_subquery()
    )
    return select(Subject, class_count, student_count).order_by(Subject.name)


def to_admin_subject_out(row) -> AdminSubjectOut:
    subject, class_count, student_count = row
    return AdminSubjectOut(
        id=subject.id,
        name=subject.name,
        enrollment_code=subject.enrollment_code,
        teachers=[UserBrief.model_validate(t) for t in subject.teachers],
        class_count=class_count,
        student_count=student_count,
    )


def get_subject_or_404(db: DbSession, subject_id: int) -> Subject:
    subject = db.get(Subject, subject_id)
    if subject is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Materia no encontrada.")
    return subject


def validate_teachers(db: DbSession, teacher_ids: list[int], subject_id: int | None) -> list[User]:
    """Los ids deben ser usuarios con rol docente y no estar inscriptos como alumnos (R11)."""
    ids = set(teacher_ids)
    users = list(db.scalars(select(User).where(User.id.in_(ids))))
    if len(users) != len(ids):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Algún docente no existe.")
    not_teachers = [u.full_name for u in users if not u.has_role(Role.TEACHER)]
    if not_teachers:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            f"No tienen rol docente: {', '.join(not_teachers)}.",
        )
    if subject_id is not None:
        enrolled = db.scalars(
            select(User.full_name)
            .join(Enrollment, Enrollment.student_id == User.id)
            .where(Enrollment.subject_id == subject_id, User.id.in_(ids))
        ).all()
        if enrolled:
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                f"Están inscriptos como alumnos en esta materia: {', '.join(enrolled)}.",
            )
    return users


@router.get("/subjects", response_model=list[AdminSubjectOut])
def list_subjects(_: AdminUser, db: DbSession) -> list[AdminSubjectOut]:
    return [to_admin_subject_out(row) for row in db.execute(subjects_query())]


@router.post("/subjects", response_model=AdminSubjectOut, status_code=status.HTTP_201_CREATED)
def create_subject(body: CreateSubjectRequest, _: AdminUser, db: DbSession) -> AdminSubjectOut:
    teachers = validate_teachers(db, body.teacher_ids, subject_id=None)
    subject = Subject(
        name=body.name, enrollment_code=generate_enrollment_code(db), teachers=teachers
    )
    db.add(subject)
    db.commit()
    return to_admin_subject_out((subject, 0, 0))


@router.get("/subjects/{subject_id}", response_model=AdminSubjectDetailOut)
def subject_detail(subject_id: int, _: AdminUser, db: DbSession) -> AdminSubjectDetailOut:
    row = db.execute(subjects_query().where(Subject.id == subject_id)).first()
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Materia no encontrada.")
    has_feedback = exists().where(Feedback.class_session_id == ClassSession.id).label("has_fb")
    classes = [
        AdminClassOut(id=c.id, date=c.date, start_time=c.start_time, can_delete=not used)
        for c, used in db.execute(
            select(ClassSession, has_feedback)
            .where(ClassSession.subject_id == subject_id)
            .order_by(ClassSession.date, ClassSession.start_time)
        )
    ]
    return AdminSubjectDetailOut(**to_admin_subject_out(row).model_dump(), classes=classes)


@router.put("/subjects/{subject_id}/teachers", response_model=AdminSubjectOut)
def update_teachers(
    subject_id: int, body: UpdateTeachersRequest, _: AdminUser, db: DbSession
) -> AdminSubjectOut:
    subject = get_subject_or_404(db, subject_id)
    subject.teachers = validate_teachers(db, body.teacher_ids, subject_id=subject.id)
    db.commit()
    return to_admin_subject_out(db.execute(subjects_query().where(Subject.id == subject_id)).one())


# --- Clases ---


@router.post("/subjects/{subject_id}/classes/generate", response_model=GenerateClassesOut)
def generate_classes(
    subject_id: int, body: GenerateClassesRequest, _: AdminUser, db: DbSession
) -> GenerateClassesOut:
    """Crea una clase por cada fecha del rango que coincide con alguna regla día + hora (R9)."""
    subject = get_subject_or_404(db, subject_id)
    if body.end_date < body.start_date:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT, "La fecha de fin es anterior a la de inicio."
        )
    if (body.end_date - body.start_date).days > MAX_GENERATION_DAYS:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            f"El rango no puede superar {MAX_GENERATION_DAYS} días.",
        )
    existing = {
        (row.date, row.start_time)
        for row in db.execute(
            select(ClassSession.date, ClassSession.start_time).where(
                ClassSession.subject_id == subject.id
            )
        )
    }
    rules = {(r.weekday, r.start_time) for r in body.rules}
    created = skipped = 0
    day = body.start_date
    while day <= body.end_date:
        for weekday, start_time in sorted(rules, key=lambda r: r[1]):
            if weekday != day.weekday():
                continue
            if (day, start_time) in existing:
                skipped += 1
                continue
            db.add(ClassSession(subject_id=subject.id, date=day, start_time=start_time))
            created += 1
        day += timedelta(days=1)
    db.commit()
    return GenerateClassesOut(created=created, skipped=skipped)


@router.delete("/classes/{class_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_class(class_id: int, _: AdminUser, db: DbSession) -> Response:
    class_session = db.get(ClassSession, class_id)
    if class_session is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Clase no encontrada.")
    if db.scalar(select(exists().where(Feedback.class_session_id == class_id))):
        raise HTTPException(
            status.HTTP_409_CONFLICT, "La clase tiene feedback: no se puede eliminar."
        )
    db.delete(class_session)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
