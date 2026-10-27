import re

from app.codes import ALPHABET
from app.models import Role
from tests.factories import auth

# --- Usuarios ---


def test_admin_creates_a_user_with_several_roles(client, factory):
    response = client.post(
        "/api/admin/users",
        json={
            "email": "nuevo.docente@test.uy",
            "full_name": "Nuevo Docente",
            "password": "clave-segura",
            "roles": ["teacher", "admin", "teacher"],
        },
        headers=auth(factory.admin()),
    )

    assert response.status_code == 201
    assert response.json()["roles"] == ["teacher", "admin"]


def test_admin_lists_users_filtered_by_role(client, factory):
    admin = factory.admin(full_name="Admin")
    factory.teacher(full_name="Docente A")
    factory.student(full_name="Alumno A")

    response = client.get("/api/admin/users?role=teacher", headers=auth(admin))

    assert [u["full_name"] for u in response.json()] == ["Docente A"]


def test_only_admins_can_manage_users(client, factory):
    teacher = factory.teacher()

    assert client.get("/api/admin/users", headers=auth(teacher)).status_code == 403


def test_admin_cannot_remove_own_admin_role(client, factory):
    admin = factory.admin()

    response = client.put(
        f"/api/admin/users/{admin.id}/roles", json={"roles": ["teacher"]}, headers=auth(admin)
    )

    assert response.status_code == 409


def test_removing_teacher_role_unassigns_the_teacher(client, factory):
    admin = factory.admin()
    teacher = factory.teacher()
    subject = factory.subject(teachers=(teacher,))

    response = client.put(
        f"/api/admin/users/{teacher.id}/roles", json={"roles": ["student"]}, headers=auth(admin)
    )

    assert response.status_code == 200
    assert response.json()["roles"] == ["student"]
    detail = client.get(f"/api/admin/subjects/{subject.id}", headers=auth(admin)).json()
    assert detail["teachers"] == []
    assert client.get("/api/teacher/subjects", headers=auth(teacher)).status_code == 403


# --- Materias ---


def test_admin_creates_a_subject_with_an_automatic_code(client, factory):
    admin = factory.admin()
    teacher = factory.teacher(full_name="Docente")

    response = client.post(
        "/api/admin/subjects",
        json={"name": "Sistemas Operativos", "teacher_ids": [teacher.id]},
        headers=auth(admin),
    )

    assert response.status_code == 201
    body = response.json()
    assert re.fullmatch(f"[{ALPHABET}]{{8}}", body["enrollment_code"])
    assert [t["full_name"] for t in body["teachers"]] == ["Docente"]


def test_assigning_a_user_without_teacher_role_is_rejected(client, factory):
    response = client.post(
        "/api/admin/subjects",
        json={"name": "Materia", "teacher_ids": [factory.student().id]},
        headers=auth(factory.admin()),
    )

    assert response.status_code == 422


def test_assigning_an_enrolled_student_as_teacher_is_rejected(client, factory):
    admin = factory.admin()
    person = factory.user(Role.STUDENT, Role.TEACHER)
    subject = factory.subject()
    factory.enroll(person, subject)

    response = client.put(
        f"/api/admin/subjects/{subject.id}/teachers",
        json={"teacher_ids": [person.id]},
        headers=auth(admin),
    )

    assert response.status_code == 409


def test_admin_responses_never_include_feedback(client, factory):
    admin = factory.admin()
    subject = factory.subject()
    student = factory.student()
    factory.enroll(student, subject)
    factory.feedback(factory.class_session(subject, days_ago=1), student, liked="Secreto")

    listing = client.get("/api/admin/subjects", headers=auth(admin))
    detail = client.get(f"/api/admin/subjects/{subject.id}", headers=auth(admin))

    for response in (listing, detail):
        assert response.status_code == 200
        assert "rating" not in response.text and "average" not in response.text
        assert "Secreto" not in response.text


def test_admin_without_teacher_role_cannot_use_teacher_endpoints(client, factory):
    admin = factory.admin()
    subject = factory.subject()

    response = client.get(f"/api/teacher/subjects/{subject.id}/summary", headers=auth(admin))

    assert response.status_code == 403


# --- Clases ---


def test_generate_classes_from_weekly_rules(client, factory):
    admin = factory.admin()
    subject = factory.subject()
    payload = {
        "start_date": "2026-03-02",  # lunes
        "end_date": "2026-03-15",
        "rules": [
            {"weekday": 0, "start_time": "08:00"},
            {"weekday": 0, "start_time": "18:00"},
            {"weekday": 3, "start_time": "08:00"},
        ],
    }
    url = f"/api/admin/subjects/{subject.id}/classes/generate"

    first = client.post(url, json=payload, headers=auth(admin))
    again = client.post(url, json=payload, headers=auth(admin))

    assert first.json() == {"created": 6, "skipped": 0}  # 2 lunes x 2 horarios + 2 jueves
    assert again.json() == {"created": 0, "skipped": 6}
    classes = client.get(f"/api/admin/subjects/{subject.id}", headers=auth(admin)).json()["classes"]
    assert [(c["date"], c["start_time"]) for c in classes[:3]] == [
        ("2026-03-02", "08:00:00"),
        ("2026-03-02", "18:00:00"),
        ("2026-03-05", "08:00:00"),
    ]


def test_generate_rejects_end_before_start(client, factory):
    subject = factory.subject()

    response = client.post(
        f"/api/admin/subjects/{subject.id}/classes/generate",
        json={
            "start_date": "2026-03-10",
            "end_date": "2026-03-01",
            "rules": [{"weekday": 0, "start_time": "08:00"}],
        },
        headers=auth(factory.admin()),
    )

    assert response.status_code == 422


def test_generate_requires_at_least_one_rule(client, factory):
    subject = factory.subject()

    response = client.post(
        f"/api/admin/subjects/{subject.id}/classes/generate",
        json={"start_date": "2026-03-01", "end_date": "2026-03-10", "rules": []},
        headers=auth(factory.admin()),
    )

    assert response.status_code == 422


def test_admin_deletes_a_class_without_feedback(client, factory):
    admin = factory.admin()
    class_session = factory.class_session(factory.subject(), days_ago=-5)

    response = client.delete(f"/api/admin/classes/{class_session.id}", headers=auth(admin))

    assert response.status_code == 204


def test_class_with_feedback_cannot_be_deleted(client, factory):
    admin = factory.admin()
    subject = factory.subject()
    student = factory.student()
    factory.enroll(student, subject)
    class_session = factory.class_session(subject, days_ago=1)
    factory.feedback(class_session, student)

    response = client.delete(f"/api/admin/classes/{class_session.id}", headers=auth(admin))
    detail = client.get(f"/api/admin/subjects/{subject.id}", headers=auth(admin)).json()

    assert response.status_code == 409
    assert detail["classes"][0]["can_delete"] is False
