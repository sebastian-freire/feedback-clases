"""Carga datos de ejemplo. BORRA todos los datos existentes.

Uso (desde backend/):  uv run python -m app.seed

Es reproducible: el contenido es siempre el mismo (semilla aleatoria fija) y las fechas se calculan
relativas al día en que se ejecuta, así siempre hay clases pasadas, con plazo abierto y futuras.
"""

import random
from datetime import date, time, timedelta

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import SessionLocal
from app.feedback_window import WindowState, today, window_state
from app.models import ClassSession, Enrollment, Feedback, Role, Subject, User, UserRole
from app.security import hash_password

RANDOM_SEED = 2026
SEMESTER_WEEKS_BEFORE_TODAY = 10
SEMESTER_WEEKS_AFTER_TODAY = 5
EMAIL_DOMAIN = "example.com"  # dominio reservado para ejemplos (RFC 2606)

USERS = [
    # (usuario, nombre, roles)
    ("admin", "Administración", [Role.ADMIN]),
    ("laura.martinez", "Laura Martínez", [Role.TEACHER, Role.ADMIN]),
    ("diego.fernandez", "Diego Fernández", [Role.TEACHER]),
    ("sofia.rodriguez", "Sofía Rodríguez", [Role.TEACHER]),
    ("lucia.gomez", "Lucía Gómez", [Role.STUDENT]),
    ("mateo.silva", "Mateo Silva", [Role.STUDENT]),
    ("valentina.perez", "Valentina Pérez", [Role.STUDENT]),
    ("santiago.lopez", "Santiago López", [Role.STUDENT]),
    ("camila.sosa", "Camila Sosa", [Role.STUDENT]),
    ("joaquin.diaz", "Joaquín Díaz", [Role.STUDENT]),
    ("martina.castro", "Martina Castro", [Role.STUDENT]),
    ("bruno.vazquez", "Bruno Vázquez", [Role.STUDENT]),
    ("agustina.romero", "Agustina Romero", [Role.STUDENT]),
    ("tomas.alvarez", "Tomás Álvarez", [Role.STUDENT]),  # sin inscripciones: para probar el código
]

SUBJECTS = [
    # (nombre, código, docentes, reglas (día, hora), tendencia de la nota (inicio, fin), alumnos)
    (
        "Bases de Datos",
        "BASES226",
        ["laura.martinez", "sofia.rodriguez"],
        [(0, time(8, 0)), (2, time(8, 0))],
        (2.8, 4.4),
        [
            "lucia.gomez",
            "mateo.silva",
            "valentina.perez",
            "santiago.lopez",
            "camila.sosa",
            "joaquin.diaz",
            "martina.castro",
            "bruno.vazquez",
        ],
    ),
    (
        "Programación Web",
        "WEBDEV26",
        ["diego.fernandez"],
        [(1, time(18, 30)), (3, time(18, 30))],
        (4.3, 3.1),
        [
            "lucia.gomez",
            "valentina.perez",
            "camila.sosa",
            "martina.castro",
            "agustina.romero",
            "bruno.vazquez",
        ],
    ),
    (
        "Redes de Computadoras",
        "REDES226",
        ["diego.fernandez"],
        [(4, time(8, 0)), (4, time(10, 0))],  # dos clases el mismo día
        (3.5, 3.6),
        ["mateo.silva", "santiago.lopez", "joaquin.diaz", "agustina.romero", "lucia.gomez"],
    ),
]

LIKED = [
    "Los ejemplos prácticos ayudaron mucho.",
    "La explicación fue clara y ordenada.",
    "Me gustó que resolviéramos ejercicios en grupo.",
    "El ritmo estuvo bien.",
    "Las diapositivas estaban muy completas.",
    "Buen espacio para preguntas.",
    "El caso real que mostró el docente.",
    "La demo en vivo.",
    "Que se repasara lo de la clase anterior.",
]
DISLIKED = [
    "Fue muy rápido al final.",
    "Faltaron ejemplos.",
    "Se escuchaba mal desde el fondo.",
    "La clase empezó tarde.",
    "Mucha teoría seguida.",
    "No alcanzó el tiempo para los ejercicios.",
    "Los ejercicios eran muy repetitivos.",
    "Faltó material para leer después.",
]


def semester_dates(rules: list[tuple[int, time]], start: date, end: date):
    day = start
    while day <= end:
        for weekday, start_time in rules:
            if day.weekday() == weekday:
                yield day, start_time
        day += timedelta(days=1)


def pick_rating(rng: random.Random, trend: tuple[float, float], progress: float) -> int:
    center = trend[0] + (trend[1] - trend[0]) * progress
    return max(1, min(5, round(rng.gauss(center, 0.8))))


def maybe(rng: random.Random, pool: list[str], probability: float) -> str | None:
    return rng.choice(pool) if rng.random() < probability else None


def reset(db: Session) -> None:
    db.execute(text("TRUNCATE users, subjects RESTART IDENTITY CASCADE"))
    db.expunge_all()  # descarta objetos en memoria de antes del borrado


def seed(db: Session) -> dict[str, int]:
    rng = random.Random(RANDOM_SEED)
    current = today()
    monday = current - timedelta(days=current.weekday())
    start = monday - timedelta(weeks=SEMESTER_WEEKS_BEFORE_TODAY)
    end = monday + timedelta(weeks=SEMESTER_WEEKS_AFTER_TODAY) - timedelta(days=1)

    password_hash = hash_password(get_settings().seed_user_password)
    users: dict[str, User] = {}
    for username, full_name, roles in USERS:
        users[username] = User(
            email=f"{username}@{EMAIL_DOMAIN}",
            full_name=full_name,
            password_hash=password_hash,
            role_rows=[UserRole(role=r) for r in roles],
        )
    db.add_all(users.values())
    db.flush()

    feedback_count = class_count = 0
    for name, code, teachers, rules, trend, students in SUBJECTS:
        subject = Subject(name=name, enrollment_code=code, teachers=[users[t] for t in teachers])
        db.add(subject)
        db.flush()
        db.add_all(Enrollment(subject_id=subject.id, student_id=users[s].id) for s in students)

        slots = list(semester_dates(rules, start, end))
        for index, (day, start_time) in enumerate(slots):
            class_session = ClassSession(subject_id=subject.id, date=day, start_time=start_time)
            db.add(class_session)
            db.flush()
            class_count += 1
            state = window_state(day, current)
            if state is WindowState.UPCOMING:
                continue
            participation = 0.75 if state is WindowState.CLOSED else 0.45
            for username in students:
                # Lucía deja sin responder las clases abiertas para poder probar el formulario.
                if username == "lucia.gomez" and state is WindowState.OPEN:
                    continue
                if rng.random() > participation:
                    continue
                db.add(
                    Feedback(
                        class_session_id=class_session.id,
                        student_id=users[username].id,
                        rating=pick_rating(rng, trend, index / max(1, len(slots) - 1)),
                        liked=maybe(rng, LIKED, 0.7),
                        disliked=maybe(rng, DISLIKED, 0.5),
                    )
                )
                feedback_count += 1

    db.commit()
    return {
        "usuarios": len(users),
        "materias": len(SUBJECTS),
        "clases": class_count,
        "feedback": feedback_count,
    }


def main() -> None:
    with SessionLocal() as db:
        reset(db)
        counts = seed(db)
    resumen = ", ".join(f"{v} {k}" for k, v in counts.items())
    print(f"Seed cargado: {resumen}.")
    print(f"Usuarios @{EMAIL_DOMAIN}; la clave de todos es el valor de SEED_USER_PASSWORD.")


if __name__ == "__main__":
    main()
