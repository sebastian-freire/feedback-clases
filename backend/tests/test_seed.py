from sqlalchemy import exists, func, select

from app.feedback_window import today
from app.models import ClassSession, Enrollment, Feedback, SubjectTeacher
from app.seed import reset, seed


def test_seed_loads_consistent_demo_data(db):
    counts = seed(db)

    assert counts["materias"] == 3
    assert counts["feedback"] > 50
    teachers_with_subjects = db.scalar(select(func.count(func.distinct(SubjectTeacher.teacher_id))))
    assert teachers_with_subjects >= 2
    feedback_on_future_classes = db.scalar(
        select(func.count())
        .select_from(Feedback)
        .join(ClassSession, ClassSession.id == Feedback.class_session_id)
        .where(ClassSession.date > today())
    )
    assert feedback_on_future_classes == 0
    teacher_enrolled_in_own_subject = db.scalar(
        select(
            exists().where(
                Enrollment.subject_id == SubjectTeacher.subject_id,
                Enrollment.student_id == SubjectTeacher.teacher_id,
            )
        )
    )
    assert not teacher_enrolled_in_own_subject


def test_seed_is_reproducible(db):
    first = seed(db)
    reset(db)
    db.commit()
    second = seed(db)

    assert first == second
