import secrets

from sqlalchemy import exists, select
from sqlalchemy.orm import Session

from app.models import ENROLLMENT_CODE_LENGTH, Subject

# Sin caracteres ambiguos (0/O, 1/I/L) para que sea fácil de dictar en clase.
ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"


def generate_enrollment_code(db: Session) -> str:
    """Código de inscripción único (D-013)."""
    while True:
        code = "".join(secrets.choice(ALPHABET) for _ in range(ENROLLMENT_CODE_LENGTH))
        if not db.scalar(select(exists().where(Subject.enrollment_code == code))):
            return code
