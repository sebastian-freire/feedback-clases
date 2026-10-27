from datetime import time

import pytest
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from app.models import Feedback, Role
from tests.factories import auth

VALID_FEEDBACK = {"rating": 4, "liked": "Los ejemplos", "disliked": "Terminó tarde"}


@pytest.fixture
def setup(factory):
    """Alumno inscripto en una materia con un docente."""
    teacher = factory.teacher(full_name="Docente Uno")
    subject = factory.subject("Bases de Datos", teachers=(teacher,))
    student = factory.student()
    factory.enroll(student, subject)
    return student, subject, teacher


def post_feedback(client, student, class_session, payload=None):
    return client.post(
        f"/api/student/classes/{class_session.id}/feedback",
        json=payload or VALID_FEEDBACK,
        headers=auth(student),
    )


# --- Inscripción ---


def test_enroll_with_a_valid_code(client, factory):
    subject = factory.subject("Redes")
    student = factory.student()

    response = client.post(
        "/api/student/enrollments",
        json={"code": f"  {subject.enrollment_code.lower()} "},
        headers=auth(student),
    )

    assert response.status_code == 201
    assert response.json()["name"] == "Redes"
    subjects = client.get("/api/student/subjects", headers=auth(student)).json()
    assert [s["name"] for s in subjects] == ["Redes"]


def test_enroll_with_an_invalid_code(client, factory):
    response = client.post(
        "/api/student/enrollments", json={"code": "NOEXISTE"}, headers=auth(factory.student())
    )

    assert response.status_code == 404


def test_enroll_twice_is_rejected(client, setup):
    student, subject, _ = setup

    response = client.post(
        "/api/student/enrollments", json={"code": subject.enrollment_code}, headers=auth(student)
    )

    assert response.status_code == 409


def test_teacher_cannot_enroll_as_student_in_own_subject(client, factory):
    teacher_and_student = factory.user(Role.TEACHER, Role.STUDENT)
    subject = factory.subject(teachers=(teacher_and_student,))

    response = client.post(
        "/api/student/enrollments",
        json={"code": subject.enrollment_code},
        headers=auth(teacher_and_student),
    )

    assert response.status_code == 409


def test_student_only_sees_enrolled_subjects(client, factory, setup):
    student, _, _ = setup
    factory.subject("Otra materia")

    subjects = client.get("/api/student/subjects", headers=auth(student)).json()

    assert [s["name"] for s in subjects] == ["Bases de Datos"]
    assert subjects[0]["teachers"] == ["Docente Uno"]


# --- Clases ---


def test_class_list_shows_window_state_and_own_feedback(client, factory, setup):
    student, subject, _ = setup
    past = factory.class_session(subject, days_ago=10)
    answered = factory.class_session(subject, days_ago=2)
    pending = factory.class_session(subject, days_ago=1)
    future = factory.class_session(subject, days_ago=-3)
    factory.feedback(answered, student)

    response = client.get(f"/api/student/subjects/{subject.id}/classes", headers=auth(student))

    assert response.status_code == 200
    classes = {c["id"]: c for c in response.json()["classes"]}
    assert classes[past.id]["window_state"] == "closed"
    assert (classes[answered.id]["window_state"], classes[answered.id]["has_feedback"]) == (
        "open",
        True,
    )
    assert (classes[pending.id]["window_state"], classes[pending.id]["has_feedback"]) == (
        "open",
        False,
    )
    assert classes[future.id]["window_state"] == "upcoming"


def test_class_list_of_a_subject_not_enrolled_is_404(client, factory):
    subject = factory.subject()

    response = client.get(
        f"/api/student/subjects/{subject.id}/classes", headers=auth(factory.student())
    )

    assert response.status_code == 404


# --- Crear feedback ---


def test_create_feedback_within_the_window(client, factory, setup):
    student, subject, _ = setup
    class_session = factory.class_session(subject, days_ago=0)

    response = post_feedback(client, student, class_session)

    assert response.status_code == 201
    assert response.json()["rating"] == 4
    assert response.json()["editable"] is True


def test_second_feedback_for_the_same_class_is_rejected(client, factory, setup, db):
    student, subject, _ = setup
    class_session = factory.class_session(subject, days_ago=1)
    post_feedback(client, student, class_session)

    response = post_feedback(client, student, class_session, {"rating": 1})

    assert response.status_code == 409
    total = db.scalar(select(func.count()).select_from(Feedback))
    assert total == 1


def test_database_rejects_duplicate_feedback_even_without_the_api(factory, setup, db):
    student, subject, _ = setup
    class_session = factory.class_session(subject, days_ago=1)
    factory.feedback(class_session, student)

    with pytest.raises(IntegrityError):
        factory.feedback(class_session, student)
    db.rollback()


def test_feedback_for_a_future_class_is_rejected(client, factory, setup):
    student, subject, _ = setup
    class_session = factory.class_session(subject, days_ago=-1)

    response = post_feedback(client, student, class_session)

    assert response.status_code == 403
    assert "todavía no ocurrió" in response.json()["detail"]


def test_feedback_on_the_last_day_of_the_window_is_accepted(client, factory, setup):
    student, subject, _ = setup
    class_session = factory.class_session(subject, days_ago=7)

    assert post_feedback(client, student, class_session).status_code == 201


def test_feedback_after_the_window_is_rejected(client, factory, setup):
    student, subject, _ = setup
    class_session = factory.class_session(subject, days_ago=8)

    response = post_feedback(client, student, class_session)

    assert response.status_code == 403
    assert "venció" in response.json()["detail"]


def test_feedback_on_a_class_of_a_subject_not_enrolled_is_404(client, factory):
    class_session = factory.class_session(factory.subject(), days_ago=1)

    response = post_feedback(client, factory.student(), class_session)

    assert response.status_code == 404


def test_two_classes_on_the_same_day_accept_one_feedback_each(client, factory, setup):
    student, subject, _ = setup
    morning = factory.class_session(subject, days_ago=1, start_time=time(8))
    evening = factory.class_session(subject, days_ago=1, start_time=time(18))

    assert post_feedback(client, student, morning).status_code == 201
    assert post_feedback(client, student, evening).status_code == 201


@pytest.mark.parametrize("rating", [0, 6, 3.5, "5", None])
def test_invalid_ratings_are_rejected(client, factory, setup, rating):
    student, subject, _ = setup
    class_session = factory.class_session(subject, days_ago=1)

    response = post_feedback(client, student, class_session, {"rating": rating})

    assert response.status_code == 422


def test_text_longer_than_500_characters_is_rejected(client, factory, setup):
    student, subject, _ = setup
    class_session = factory.class_session(subject, days_ago=1)

    response = post_feedback(client, student, class_session, {"rating": 3, "liked": "a" * 501})

    assert response.status_code == 422


def test_text_fields_are_optional_and_blank_means_no_comment(client, factory, setup):
    student, subject, _ = setup
    class_session = factory.class_session(subject, days_ago=1)

    response = post_feedback(
        client, student, class_session, {"rating": 5, "liked": "   ", "disliked": "a" * 500}
    )

    assert response.status_code == 201
    assert response.json()["liked"] is None
    assert len(response.json()["disliked"]) == 500


# --- Ver y editar el propio feedback ---


def test_student_can_read_own_feedback(client, factory, setup):
    student, subject, _ = setup
    class_session = factory.class_session(subject, days_ago=1)
    factory.feedback(class_session, student, rating=2, liked="Nada")

    response = client.get(
        f"/api/student/classes/{class_session.id}/feedback", headers=auth(student)
    )

    assert response.status_code == 200
    assert (response.json()["rating"], response.json()["liked"]) == (2, "Nada")


def test_edit_feedback_within_the_window(client, factory, setup):
    student, subject, _ = setup
    class_session = factory.class_session(subject, days_ago=3)
    factory.feedback(class_session, student, rating=2)

    response = client.put(
        f"/api/student/classes/{class_session.id}/feedback",
        json={"rating": 5, "liked": "Mejoró"},
        headers=auth(student),
    )

    assert response.status_code == 200
    assert (response.json()["rating"], response.json()["liked"]) == (5, "Mejoró")


def test_edit_feedback_after_the_window_is_rejected(client, factory, setup, db):
    student, subject, _ = setup
    class_session = factory.class_session(subject, days_ago=8)
    feedback = factory.feedback(class_session, student, rating=2)

    response = client.put(
        f"/api/student/classes/{class_session.id}/feedback",
        json={"rating": 5},
        headers=auth(student),
    )

    assert response.status_code == 403
    db.refresh(feedback)
    assert feedback.rating == 2


def test_edit_without_previous_feedback_is_404(client, factory, setup):
    student, subject, _ = setup
    class_session = factory.class_session(subject, days_ago=1)

    response = client.put(
        f"/api/student/classes/{class_session.id}/feedback",
        json={"rating": 5},
        headers=auth(student),
    )

    assert response.status_code == 404


def test_student_cannot_edit_someone_elses_feedback(client, factory, setup, db):
    student, subject, _ = setup
    class_session = factory.class_session(subject, days_ago=1)
    other = factory.student()
    factory.enroll(other, subject)
    others_feedback = factory.feedback(class_session, other, rating=1)

    response = client.put(
        f"/api/student/classes/{class_session.id}/feedback",
        json={"rating": 5},
        headers=auth(student),
    )

    assert response.status_code == 404
    db.refresh(others_feedback)
    assert others_feedback.rating == 1


# --- Permisos ---


def test_student_cannot_use_teacher_or_admin_endpoints(client, setup):
    student, subject, _ = setup

    assert client.get("/api/teacher/subjects", headers=auth(student)).status_code == 403
    assert client.get("/api/admin/subjects", headers=auth(student)).status_code == 403


def test_student_endpoints_require_login(client):
    assert client.get("/api/student/subjects").status_code == 401


def test_class_detail_includes_subject_and_own_status(client, factory, setup):
    student, subject, _ = setup
    class_session = factory.class_session(subject, days_ago=2)
    factory.feedback(class_session, student)

    response = client.get(f"/api/student/classes/{class_session.id}", headers=auth(student))

    assert response.status_code == 200
    body = response.json()
    assert body["subject"]["name"] == "Bases de Datos"
    assert body["class_session"]["has_feedback"] is True
    assert body["class_session"]["window_state"] == "open"


def test_class_detail_of_a_subject_not_enrolled_is_404(client, factory):
    class_session = factory.class_session(factory.subject(), days_ago=1)

    response = client.get(
        f"/api/student/classes/{class_session.id}", headers=auth(factory.student())
    )

    assert response.status_code == 404
