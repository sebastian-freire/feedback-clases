import csv
import io
import random
from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, Response, status
from sqlalchemy import func, select

from app.db import DbSession
from app.deps import TeacherUser
from app.feedback_window import today, window_state
from app.models import ClassSession, Enrollment, Feedback, Subject, SubjectTeacher, User
from app.schemas import (
    AnonymousFeedbackOut,
    ClassCommentsOut,
    ClassSummaryOut,
    SubjectComparisonOut,
    SubjectSummaryOut,
    TeacherSubjectOut,
    TopWordsOut,
    WordCount,
)
from app.text_stats import top_words

router = APIRouter(prefix="/teacher", tags=["docente"])


def rounded(value: Decimal | float | None) -> float | None:
    return round(float(value), 2) if value is not None else None


def teacher_subjects_query(teacher: User):
    """Regla R5: solo materias donde el docente está asignado (filtra por usuario autenticado)."""
    class_count = (
        select(func.count(ClassSession.id))
        .where(ClassSession.subject_id == Subject.id)
        .scalar_subquery()
    )

    def feedback_aggregate(aggregate):
        # Subconsulta escalar correlacionada con la materia de la consulta externa.
        return (
            select(aggregate)
            .join(ClassSession, ClassSession.id == Feedback.class_session_id)
            .where(ClassSession.subject_id == Subject.id)
            .scalar_subquery()
        )

    response_count = feedback_aggregate(func.count(Feedback.id))
    average = feedback_aggregate(func.avg(Feedback.rating))
    return (
        select(Subject, class_count, response_count, average)
        .join(SubjectTeacher, SubjectTeacher.subject_id == Subject.id)
        .where(SubjectTeacher.teacher_id == teacher.id)
        .order_by(Subject.name)
    )


def to_teacher_subject_out(row) -> TeacherSubjectOut:
    subject, class_count, response_count, average = row
    return TeacherSubjectOut(
        id=subject.id,
        name=subject.name,
        enrollment_code=subject.enrollment_code,
        class_count=class_count,
        response_count=response_count,
        average=rounded(average),
    )


@router.get("/subjects", response_model=list[TeacherSubjectOut])
def my_subjects(teacher: TeacherUser, db: DbSession) -> list[TeacherSubjectOut]:
    return [to_teacher_subject_out(row) for row in db.execute(teacher_subjects_query(teacher))]


def get_teacher_subject_row(db: DbSession, teacher: User, subject_id: int):
    row = db.execute(teacher_subjects_query(teacher).where(Subject.id == subject_id)).first()
    if row is None:  # ajena o inexistente: misma respuesta para no revelar que existe
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Materia no encontrada.")
    return row


@router.get("/subjects/{subject_id}/summary", response_model=SubjectSummaryOut)
def subject_summary(subject_id: int, teacher: TeacherUser, db: DbSession) -> SubjectSummaryOut:
    """Promedio y cantidad de respuestas por clase, ordenado por fecha (tendencia del semestre)."""
    row = get_teacher_subject_row(db, teacher, subject_id)
    rows = db.execute(
        select(ClassSession, func.count(Feedback.id), func.avg(Feedback.rating))
        .outerjoin(Feedback, Feedback.class_session_id == ClassSession.id)
        .where(ClassSession.subject_id == subject_id)
        .group_by(ClassSession.id)
        .order_by(ClassSession.date, ClassSession.start_time)
    )
    classes = [
        ClassSummaryOut(
            id=c.id,
            date=c.date,
            start_time=c.start_time,
            window_state=window_state(c.date),
            response_count=count,
            average=rounded(avg),
        )
        for c, count, avg in rows
    ]
    return SubjectSummaryOut(subject=to_teacher_subject_out(row), classes=classes)


@router.get("/classes/{class_id}/comments", response_model=ClassCommentsOut)
def class_comments(class_id: int, teacher: TeacherUser, db: DbSession) -> ClassCommentsOut:
    """Comentarios anónimos (D-018, D-020): sin datos del autor, sin fechas, en orden aleatorio."""
    row = db.execute(
        select(ClassSession, Subject.name)
        .join(Subject, Subject.id == ClassSession.subject_id)
        .join(SubjectTeacher, SubjectTeacher.subject_id == Subject.id)
        .where(ClassSession.id == class_id, SubjectTeacher.teacher_id == teacher.id)
    ).first()
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Clase no encontrada.")
    class_session, subject_name = row
    # Se seleccionan solo estas tres columnas: el id del alumno nunca sale de la base.
    comments = [
        AnonymousFeedbackOut(rating=rating, liked=liked, disliked=disliked)
        for rating, liked, disliked in db.execute(
            select(Feedback.rating, Feedback.liked, Feedback.disliked).where(
                Feedback.class_session_id == class_id
            )
        )
    ]
    random.shuffle(comments)
    ratings = [c.rating for c in comments]
    return ClassCommentsOut(
        id=class_session.id,
        subject_id=class_session.subject_id,
        subject_name=subject_name,
        date=class_session.date,
        start_time=class_session.start_time,
        response_count=len(ratings),
        average=rounded(sum(ratings) / len(ratings)) if ratings else None,
        comments=comments,
    )


# --- Extras (Fase 6) ---

CSV_HEADER = ["fecha", "hora", "calificacion", "que_gusto", "que_no_gusto"]
FORMULA_PREFIXES = ("=", "+", "-", "@", "\t", "\r")
UTF8_BOM = "﻿"


def safe_cell(value: str | None) -> str:
    """Evita inyección de fórmulas al abrir el CSV en una planilla."""
    if not value:
        return ""
    return f"'{value}" if value[0] in FORMULA_PREFIXES else value


@router.get(
    "/subjects/{subject_id}/export.csv",
    response_class=Response,
    responses={200: {"content": {"text/csv": {}}}},
)
def export_csv(subject_id: int, teacher: TeacherUser, db: DbSession) -> Response:
    """Planilla con todos los feedback de la materia, anónimos (sin autor ni fechas de envío).

    Separador `;` y BOM UTF-8 para que Excel en español la abra directamente.
    """
    row = get_teacher_subject_row(db, teacher, subject_id)
    rows = db.execute(
        select(
            ClassSession.id,
            ClassSession.date,
            ClassSession.start_time,
            Feedback.rating,
            Feedback.liked,
            Feedback.disliked,
        )
        .join(Feedback, Feedback.class_session_id == ClassSession.id)
        .where(ClassSession.subject_id == subject_id)
        .order_by(ClassSession.date, ClassSession.start_time)
    ).all()
    # Dentro de cada clase se mezcla el orden, igual que en la pantalla (D-020).
    by_class: dict[int, list] = {}
    for r in rows:
        by_class.setdefault(r.id, []).append(r)
    buffer = io.StringIO()
    writer = csv.writer(buffer, delimiter=";", lineterminator="\r\n")
    writer.writerow(CSV_HEADER)
    for class_rows in by_class.values():
        random.shuffle(class_rows)
        for r in class_rows:
            writer.writerow(
                [
                    r.date.isoformat(),
                    r.start_time.strftime("%H:%M"),
                    r.rating,
                    safe_cell(r.liked),
                    safe_cell(r.disliked),
                ]
            )
    subject = row[0]
    filename = f"feedback-{subject.enrollment_code.lower()}.csv"
    return Response(
        content=UTF8_BOM + buffer.getvalue(),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/subjects/{subject_id}/top-words", response_model=TopWordsOut)
def subject_top_words(
    subject_id: int,
    teacher: TeacherUser,
    db: DbSession,
    limit: Annotated[int, Query(ge=1, le=50)] = 10,
) -> TopWordsOut:
    """Palabras más repetidas en "qué gustó" y "qué no gustó", sin palabras vacías."""
    get_teacher_subject_row(db, teacher, subject_id)
    texts = db.execute(
        select(Feedback.liked, Feedback.disliked)
        .join(ClassSession, ClassSession.id == Feedback.class_session_id)
        .where(ClassSession.subject_id == subject_id)
    ).all()
    return TopWordsOut(
        liked=[WordCount(word=w, count=c) for w, c in top_words((t.liked for t in texts), limit)],
        disliked=[
            WordCount(word=w, count=c) for w, c in top_words((t.disliked for t in texts), limit)
        ],
    )


@router.get("/comparison", response_model=list[SubjectComparisonOut])
def compare_subjects(teacher: TeacherUser, db: DbSession) -> list[SubjectComparisonOut]:
    """Comparación entre las materias del docente (solo las suyas)."""
    past_classes = (
        select(func.count(ClassSession.id))
        .where(ClassSession.subject_id == Subject.id, ClassSession.date <= today())
        .scalar_subquery()
    )
    students = select(func.count()).where(Enrollment.subject_id == Subject.id).scalar_subquery()
    result = []
    for subject, _, response_count, average, past, student_count in db.execute(
        teacher_subjects_query(teacher).add_columns(past_classes, students)
    ):
        expected = past * student_count
        result.append(
            SubjectComparisonOut(
                id=subject.id,
                name=subject.name,
                average=rounded(average),
                response_count=response_count,
                past_class_count=past,
                student_count=student_count,
                participation=round(response_count / expected, 3) if expected else None,
            )
        )
    return result
