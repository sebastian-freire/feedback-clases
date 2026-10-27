"""Helpers para crear datos de prueba directamente en la base."""

from datetime import time, timedelta
from itertools import count

from sqlalchemy.orm import Session

from app.codes import generate_enrollment_code
from app.feedback_window import today
from app.models import ClassSession, Enrollment, Feedback, Role, Subject, User, UserRole
from app.security import create_access_token, hash_password

TEST_PASSWORD = "contrasenia-de-prueba"
# Hashear con Argon2 es lento a propósito: se calcula una sola vez para todas las pruebas.
_TEST_PASSWORD_HASH = hash_password(TEST_PASSWORD)


def auth(user: User) -> dict[str, str]:
    return {"Authorization": f"Bearer {create_access_token(user.id)}"}


class Factory:
    def __init__(self, db: Session):
        self.db = db
        self._seq = count(1)

    def user(self, *roles: Role, full_name: str | None = None, email: str | None = None) -> User:
        n = next(self._seq)
        user = User(
            email=email or f"usuario{n}@test.uy",
            full_name=full_name or f"Usuario {n}",
            password_hash=_TEST_PASSWORD_HASH,
            role_rows=[UserRole(role=r) for r in roles],
        )
        self.db.add(user)
        self.db.commit()
        return user

    def student(self, **kwargs) -> User:
        return self.user(Role.STUDENT, **kwargs)

    def teacher(self, **kwargs) -> User:
        return self.user(Role.TEACHER, **kwargs)

    def admin(self, **kwargs) -> User:
        return self.user(Role.ADMIN, **kwargs)

    def subject(self, name: str = "Materia", teachers: tuple[User, ...] = ()) -> Subject:
        subject = Subject(
            name=name, enrollment_code=generate_enrollment_code(self.db), teachers=list(teachers)
        )
        self.db.add(subject)
        self.db.commit()
        return subject

    def enroll(self, student: User, subject: Subject) -> None:
        self.db.add(Enrollment(subject_id=subject.id, student_id=student.id))
        self.db.commit()

    def class_session(
        self, subject: Subject, days_ago: int = 0, start_time: time = time(8, 0)
    ) -> ClassSession:
        """Clase con fecha relativa a hoy: days_ago=-1 es mañana; 8 o más, plazo vencido."""
        class_session = ClassSession(
            subject_id=subject.id, date=today() - timedelta(days=days_ago), start_time=start_time
        )
        self.db.add(class_session)
        self.db.commit()
        return class_session

    def feedback(
        self,
        class_session: ClassSession,
        student: User,
        rating: int = 4,
        liked: str | None = None,
        disliked: str | None = None,
    ) -> Feedback:
        feedback = Feedback(
            class_session_id=class_session.id,
            student_id=student.id,
            rating=rating,
            liked=liked,
            disliked=disliked,
        )
        self.db.add(feedback)
        self.db.commit()
        return feedback
