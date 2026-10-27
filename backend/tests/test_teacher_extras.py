import csv
import io

import pytest

from app.text_stats import top_words
from tests.factories import auth


@pytest.fixture
def subject_with_feedback(factory):
    teacher = factory.teacher()
    subject = factory.subject("Bases de Datos", teachers=(teacher,))
    students = [
        factory.student(full_name=f"Alumna Oculta {i}", email=f"oculta{i}@test.uy")
        for i in range(3)
    ]
    for s in students:
        factory.enroll(s, subject)
    return teacher, subject, students


# --- Exportar a planilla ---


def test_export_csv_contains_anonymous_rows(client, factory, subject_with_feedback):
    teacher, subject, students = subject_with_feedback
    class_session = factory.class_session(subject, days_ago=2)
    factory.feedback(class_session, students[0], rating=5, liked="Los ejemplos; muy claros")
    factory.feedback(class_session, students[1], rating=2, disliked="Muy rápido")

    response = client.get(f"/api/teacher/subjects/{subject.id}/export.csv", headers=auth(teacher))

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    assert "attachment" in response.headers["content-disposition"]
    text = response.content.decode("utf-8-sig")
    rows = list(csv.reader(io.StringIO(text), delimiter=";"))
    assert rows[0] == ["fecha", "hora", "calificacion", "que_gusto", "que_no_gusto"]
    assert sorted(r[2] for r in rows[1:]) == ["2", "5"]
    assert "Los ejemplos; muy claros" in [r[3] for r in rows[1:]]
    for student in students:
        assert student.full_name not in text and student.email not in text


def test_export_csv_neutralizes_formulas(client, factory, subject_with_feedback):
    teacher, subject, students = subject_with_feedback
    factory.feedback(factory.class_session(subject, days_ago=1), students[0], liked="=HYPERLINK(1)")

    response = client.get(f"/api/teacher/subjects/{subject.id}/export.csv", headers=auth(teacher))

    rows = list(csv.reader(io.StringIO(response.content.decode("utf-8-sig")), delimiter=";"))
    assert rows[1][3] == "'=HYPERLINK(1)"


def test_export_csv_of_another_subject_is_404(client, factory, subject_with_feedback):
    _, subject, _ = subject_with_feedback

    response = client.get(
        f"/api/teacher/subjects/{subject.id}/export.csv", headers=auth(factory.teacher())
    )

    assert response.status_code == 404


# --- Palabras más repetidas ---


def test_top_words_ignores_stopwords_case_and_accents():
    texts = ["Los EJEMPLOS prácticos", "los ejemplos y la práctica", None, "Ejemplos claros"]

    result = top_words(texts, limit=3)

    assert result == [("ejemplos", 3), ("claros", 1), ("práctica", 1)]


def test_top_words_endpoint_splits_liked_and_disliked(client, factory, subject_with_feedback):
    teacher, subject, students = subject_with_feedback
    class_session = factory.class_session(subject, days_ago=1)
    factory.feedback(class_session, students[0], liked="Los ejemplos", disliked="El ruido")
    factory.feedback(class_session, students[1], liked="Ejemplos y ejercicios", disliked="Ruido")

    response = client.get(
        f"/api/teacher/subjects/{subject.id}/top-words?limit=5", headers=auth(teacher)
    )

    assert response.status_code == 200
    body = response.json()
    assert body["liked"][0] == {"word": "ejemplos", "count": 2}
    assert body["disliked"] == [{"word": "ruido", "count": 2}]


def test_top_words_of_another_subject_is_404(client, factory, subject_with_feedback):
    _, subject, _ = subject_with_feedback

    response = client.get(
        f"/api/teacher/subjects/{subject.id}/top-words", headers=auth(factory.teacher())
    )

    assert response.status_code == 404


# --- Comparación entre materias ---


def test_comparison_only_includes_own_subjects_with_participation(client, factory):
    teacher = factory.teacher()
    bases = factory.subject("Bases", teachers=(teacher,))
    factory.subject("Redes", teachers=(teacher,))
    factory.subject("Ajena", teachers=(factory.teacher(),))
    students = [factory.student() for _ in range(2)]
    for s in students:
        factory.enroll(s, bases)
    first = factory.class_session(bases, days_ago=3)
    factory.class_session(bases, days_ago=1)
    factory.class_session(bases, days_ago=-5)  # futura: no cuenta como dictada
    factory.feedback(first, students[0], rating=4)
    factory.feedback(first, students[1], rating=2)

    response = client.get("/api/teacher/comparison", headers=auth(teacher))

    assert response.status_code == 200
    by_name = {s["name"]: s for s in response.json()}
    assert set(by_name) == {"Bases", "Redes"}
    assert by_name["Bases"]["average"] == 3.0
    assert by_name["Bases"]["past_class_count"] == 2
    assert by_name["Bases"]["participation"] == 0.5  # 2 respuestas / (2 alumnos x 2 clases)
    assert by_name["Redes"]["participation"] is None
