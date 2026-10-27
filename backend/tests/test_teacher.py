import pytest

from app.models import Role
from app.routers import teacher as teacher_router
from tests.factories import auth


@pytest.fixture
def two_subjects(factory):
    """Dos docentes, cada uno con su materia y alumnos que opinaron."""
    ana = factory.teacher(full_name="Ana Docente")
    beto = factory.teacher(full_name="Beto Docente")
    bases = factory.subject("Bases de Datos", teachers=(ana,))
    redes = factory.subject("Redes", teachers=(beto,))
    students = [
        factory.student(full_name=f"Alumno Secreto {i}", email=f"secreto{i}@test.uy")
        for i in range(3)
    ]
    for s in students:
        factory.enroll(s, bases)
        factory.enroll(s, redes)
    return ana, beto, bases, redes, students


# --- Autorización por materia ---


def test_teacher_only_sees_own_subjects(client, two_subjects):
    ana, _, bases, _, _ = two_subjects

    response = client.get("/api/teacher/subjects", headers=auth(ana))

    assert response.status_code == 200
    assert [s["name"] for s in response.json()] == ["Bases de Datos"]
    assert response.json()[0]["enrollment_code"] == bases.enrollment_code


def test_teacher_cannot_see_summary_of_another_subject(client, two_subjects):
    ana, _, _, redes, _ = two_subjects

    response = client.get(f"/api/teacher/subjects/{redes.id}/summary", headers=auth(ana))

    assert response.status_code == 404


def test_teacher_cannot_see_comments_of_another_subjects_class(client, factory, two_subjects):
    ana, _, _, redes, students = two_subjects
    class_session = factory.class_session(redes, days_ago=1)
    factory.feedback(class_session, students[0], liked="Comentario de Redes")

    response = client.get(f"/api/teacher/classes/{class_session.id}/comments", headers=auth(ana))

    assert response.status_code == 404
    assert "Comentario de Redes" not in response.text


def test_nonexistent_subject_looks_the_same_as_a_foreign_one(client, two_subjects):
    ana, _, _, _, _ = two_subjects

    response = client.get("/api/teacher/subjects/999999/summary", headers=auth(ana))

    assert response.status_code == 404


def test_every_teacher_of_a_subject_sees_the_same_data(client, factory):
    titular, ayudante = factory.teacher(), factory.teacher()
    subject = factory.subject(teachers=(titular, ayudante))
    student = factory.student()
    factory.enroll(student, subject)
    factory.feedback(factory.class_session(subject, days_ago=1), student, rating=3)

    first = client.get(f"/api/teacher/subjects/{subject.id}/summary", headers=auth(titular))
    second = client.get(f"/api/teacher/subjects/{subject.id}/summary", headers=auth(ayudante))

    assert first.status_code == second.status_code == 200
    assert first.json() == second.json()


def test_user_without_teacher_role_gets_403(client, factory):
    admin = factory.admin()

    assert client.get("/api/teacher/subjects", headers=auth(admin)).status_code == 403


# --- Promedios y tendencia ---


def test_summary_computes_average_per_class_and_overall(client, factory, two_subjects):
    ana, _, bases, _, students = two_subjects
    first = factory.class_session(bases, days_ago=20)
    second = factory.class_session(bases, days_ago=13)
    empty = factory.class_session(bases, days_ago=6)
    for student, rating in zip(students, [5, 4, 3], strict=True):
        factory.feedback(first, student, rating=rating)
    factory.feedback(second, students[0], rating=1)
    factory.feedback(second, students[1], rating=2)

    response = client.get(f"/api/teacher/subjects/{bases.id}/summary", headers=auth(ana))

    assert response.status_code == 200
    body = response.json()
    assert body["subject"]["response_count"] == 5
    assert body["subject"]["average"] == 3.0  # (5+4+3+1+2) / 5
    assert body["subject"]["class_count"] == 3
    by_id = {c["id"]: c for c in body["classes"]}
    assert (by_id[first.id]["average"], by_id[first.id]["response_count"]) == (4.0, 3)
    assert (by_id[second.id]["average"], by_id[second.id]["response_count"]) == (1.5, 2)
    assert (by_id[empty.id]["average"], by_id[empty.id]["response_count"]) == (None, 0)
    assert [c["id"] for c in body["classes"]] == [first.id, second.id, empty.id]


def test_average_is_rounded_to_two_decimals(client, factory, two_subjects):
    ana, _, bases, _, students = two_subjects
    class_session = factory.class_session(bases, days_ago=1)
    for student, rating in zip(students, [5, 5, 4], strict=True):
        factory.feedback(class_session, student, rating=rating)

    body = client.get(f"/api/teacher/subjects/{bases.id}/summary", headers=auth(ana)).json()

    assert body["classes"][0]["average"] == 4.67


def test_feedback_of_other_subjects_does_not_affect_the_average(client, factory, two_subjects):
    ana, _, bases, redes, students = two_subjects
    factory.feedback(factory.class_session(bases, days_ago=1), students[0], rating=5)
    factory.feedback(factory.class_session(redes, days_ago=1), students[0], rating=1)

    subjects = client.get("/api/teacher/subjects", headers=auth(ana)).json()

    assert subjects[0]["average"] == 5.0


# --- Anonimato ---


def test_comments_never_include_author_data(client, factory, two_subjects):
    ana, _, bases, _, students = two_subjects
    class_session = factory.class_session(bases, days_ago=1)
    for i, student in enumerate(students):
        factory.feedback(class_session, student, rating=i + 3, liked=f"Gustó {i}", disliked=None)

    response = client.get(f"/api/teacher/classes/{class_session.id}/comments", headers=auth(ana))

    assert response.status_code == 200
    body = response.json()
    assert body["response_count"] == 3
    assert body["average"] == 4.0
    for comment in body["comments"]:
        assert set(comment) == {"rating", "liked", "disliked"}
    for student in students:
        assert student.full_name not in response.text
        assert student.email not in response.text
    assert "student" not in response.text
    assert "created_at" not in response.text and "updated_at" not in response.text


def test_comments_are_shuffled(client, factory, two_subjects, monkeypatch):
    ana, _, bases, _, students = two_subjects
    class_session = factory.class_session(bases, days_ago=1)
    for i, student in enumerate(students):
        factory.feedback(class_session, student, rating=3, liked=f"Comentario {i}")
    calls = []
    monkeypatch.setattr(teacher_router.random, "shuffle", lambda items: calls.append(len(items)))

    client.get(f"/api/teacher/classes/{class_session.id}/comments", headers=auth(ana))

    assert calls == [3]


def test_summary_never_includes_author_data(client, factory, two_subjects):
    ana, _, bases, _, students = two_subjects
    factory.feedback(factory.class_session(bases, days_ago=1), students[0], rating=4)

    response = client.get(f"/api/teacher/subjects/{bases.id}/summary", headers=auth(ana))

    assert students[0].full_name not in response.text
    assert students[0].email not in response.text


def test_teacher_who_is_also_admin_still_only_sees_own_subjects(client, factory, two_subjects):
    _, _, _, redes, _ = two_subjects
    admin_teacher = factory.user(Role.ADMIN, Role.TEACHER)

    response = client.get(f"/api/teacher/subjects/{redes.id}/summary", headers=auth(admin_teacher))

    assert response.status_code == 404
