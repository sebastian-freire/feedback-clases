from fastapi import APIRouter, HTTPException, status
from sqlalchemy import exists, select
from sqlalchemy.exc import IntegrityError

from app.db import DbSession
from app.deps import StudentUser
from app.feedback_window import WindowState, closes_on, window_state
from app.models import ClassSession, Enrollment, Feedback, Subject, SubjectTeacher, User
from app.schemas import (
    EnrollRequest,
    FeedbackIn,
    StudentClassDetailOut,
    StudentClassOut,
    StudentFeedbackOut,
    StudentSubjectClassesOut,
    StudentSubjectOut,
)

router = APIRouter(prefix="/student", tags=["alumno"])

SUBJECT_NOT_FOUND = "Materia no encontrada."
CLASS_NOT_FOUND = "Clase no encontrada."


def to_subject_out(subject: Subject) -> StudentSubjectOut:
    return StudentSubjectOut(
        id=subject.id, name=subject.name, teachers=[t.full_name for t in subject.teachers]
    )


def get_enrolled_subject(db: DbSession, student: User, subject_id: int) -> Subject:
    """Materia en la que el alumno está inscripto; si no, 404 (igual que si no existiera)."""
    subject = db.scalar(
        select(Subject)
        .join(Enrollment, Enrollment.subject_id == Subject.id)
        .where(Subject.id == subject_id, Enrollment.student_id == student.id)
    )
    if subject is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, SUBJECT_NOT_FOUND)
    return subject


def get_enrolled_class(db: DbSession, student: User, class_id: int) -> ClassSession:
    """Clase de una materia en la que el alumno está inscripto (regla R2); si no, 404."""
    class_session = db.scalar(
        select(ClassSession)
        .join(Enrollment, Enrollment.subject_id == ClassSession.subject_id)
        .where(ClassSession.id == class_id, Enrollment.student_id == student.id)
    )
    if class_session is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, CLASS_NOT_FOUND)
    return class_session


def ensure_window_open(class_session: ClassSession) -> None:
    """Regla R3: solo se crea o edita feedback dentro de la ventana de la clase."""
    state = window_state(class_session.date)
    if state is WindowState.UPCOMING:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN, "La clase todavía no ocurrió: podés opinar desde ese día."
        )
    if state is WindowState.CLOSED:
        deadline = closes_on(class_session.date).strftime("%d/%m/%Y")
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            f"El plazo para opinar sobre esta clase venció el {deadline}.",
        )


def to_feedback_out(feedback: Feedback, class_session: ClassSession) -> StudentFeedbackOut:
    return StudentFeedbackOut(
        class_session_id=class_session.id,
        rating=feedback.rating,
        liked=feedback.liked,
        disliked=feedback.disliked,
        editable=window_state(class_session.date) is WindowState.OPEN,
        closes_on=closes_on(class_session.date),
    )


def to_class_out(class_session: ClassSession, has_feedback: bool) -> StudentClassOut:
    return StudentClassOut(
        id=class_session.id,
        date=class_session.date,
        start_time=class_session.start_time,
        window_state=window_state(class_session.date),
        closes_on=closes_on(class_session.date),
        has_feedback=has_feedback,
    )


def find_own_feedback(db: DbSession, student: User, class_id: int) -> Feedback | None:
    return db.scalar(
        select(Feedback).where(
            Feedback.class_session_id == class_id, Feedback.student_id == student.id
        )
    )


@router.post("/enrollments", response_model=StudentSubjectOut, status_code=status.HTTP_201_CREATED)
def enroll(body: EnrollRequest, student: StudentUser, db: DbSession) -> StudentSubjectOut:
    """Inscripción con el código de la materia (D-008)."""
    subject = db.scalar(select(Subject).where(Subject.enrollment_code == body.code))
    if subject is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Código inválido.")
    is_teacher = db.scalar(
        select(
            exists().where(
                SubjectTeacher.subject_id == subject.id, SubjectTeacher.teacher_id == student.id
            )
        )
    )
    if is_teacher:  # Regla R11: conflicto de interés
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Sos docente de esta materia: no podés inscribirte como alumno.",
        )
    if db.get(Enrollment, (subject.id, student.id)):
        raise HTTPException(status.HTTP_409_CONFLICT, "Ya estás inscripto en esta materia.")
    db.add(Enrollment(subject_id=subject.id, student_id=student.id))
    db.commit()
    return to_subject_out(subject)


@router.get("/subjects", response_model=list[StudentSubjectOut])
def my_subjects(student: StudentUser, db: DbSession) -> list[StudentSubjectOut]:
    subjects = db.scalars(
        select(Subject)
        .join(Enrollment, Enrollment.subject_id == Subject.id)
        .where(Enrollment.student_id == student.id)
        .order_by(Subject.name)
    )
    return [to_subject_out(s) for s in subjects]


@router.get("/subjects/{subject_id}/classes", response_model=StudentSubjectClassesOut)
def subject_classes(
    subject_id: int, student: StudentUser, db: DbSession
) -> StudentSubjectClassesOut:
    subject = get_enrolled_subject(db, student, subject_id)
    has_feedback = (
        exists()
        .where(Feedback.class_session_id == ClassSession.id, Feedback.student_id == student.id)
        .label("has_feedback")
    )
    rows = db.execute(
        select(ClassSession, has_feedback)
        .where(ClassSession.subject_id == subject.id)
        .order_by(ClassSession.date, ClassSession.start_time)
    )
    classes = [to_class_out(c, done) for c, done in rows]
    return StudentSubjectClassesOut(subject=to_subject_out(subject), classes=classes)


@router.get("/classes/{class_id}", response_model=StudentClassDetailOut)
def class_detail(class_id: int, student: StudentUser, db: DbSession) -> StudentClassDetailOut:
    class_session = get_enrolled_class(db, student, class_id)
    return StudentClassDetailOut(
        subject=to_subject_out(class_session.subject),
        class_session=to_class_out(
            class_session, find_own_feedback(db, student, class_id) is not None
        ),
    )


@router.get("/classes/{class_id}/feedback", response_model=StudentFeedbackOut)
def get_my_feedback(class_id: int, student: StudentUser, db: DbSession) -> StudentFeedbackOut:
    class_session = get_enrolled_class(db, student, class_id)
    feedback = find_own_feedback(db, student, class_id)
    if feedback is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Todavía no dejaste feedback en esta clase.")
    return to_feedback_out(feedback, class_session)


@router.post(
    "/classes/{class_id}/feedback",
    response_model=StudentFeedbackOut,
    status_code=status.HTTP_201_CREATED,
)
def create_feedback(
    class_id: int, body: FeedbackIn, student: StudentUser, db: DbSession
) -> StudentFeedbackOut:
    class_session = get_enrolled_class(db, student, class_id)
    ensure_window_open(class_session)
    duplicate = HTTPException(status.HTTP_409_CONFLICT, "Ya enviaste feedback para esta clase.")
    if find_own_feedback(db, student, class_id):
        raise duplicate
    feedback = Feedback(class_session_id=class_id, student_id=student.id, **body.model_dump())
    db.add(feedback)
    try:
        db.commit()
    except IntegrityError:  # dos envíos simultáneos: la restricción única de la base decide
        db.rollback()
        raise duplicate from None
    return to_feedback_out(feedback, class_session)


@router.put("/classes/{class_id}/feedback", response_model=StudentFeedbackOut)
def update_feedback(
    class_id: int, body: FeedbackIn, student: StudentUser, db: DbSession
) -> StudentFeedbackOut:
    class_session = get_enrolled_class(db, student, class_id)
    feedback = find_own_feedback(db, student, class_id)
    if feedback is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Todavía no dejaste feedback en esta clase.")
    ensure_window_open(class_session)
    for field, value in body.model_dump().items():
        setattr(feedback, field, value)
    db.commit()
    return to_feedback_out(feedback, class_session)
