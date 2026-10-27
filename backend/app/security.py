from datetime import UTC, datetime, timedelta

import jwt
from pwdlib import PasswordHash

from app.config import get_settings

JWT_ALGORITHM = "HS256"

_password_hash = PasswordHash.recommended()  # Argon2 (D-039)
# Hash de referencia para gastar el mismo tiempo cuando el email no existe (evita enumerar cuentas).
_DUMMY_HASH = _password_hash.hash("dummy-password-for-timing")


def hash_password(password: str) -> str:
    return _password_hash.hash(password)


def verify_password(password: str, password_hash: str | None) -> bool:
    if password_hash is None:
        _password_hash.verify(password, _DUMMY_HASH)
        return False
    return _password_hash.verify(password, password_hash)


def create_access_token(user_id: int) -> str:
    settings = get_settings()
    expires_at = datetime.now(UTC) + timedelta(minutes=settings.jwt_expire_minutes)
    payload = {"sub": str(user_id), "exp": expires_at}
    return jwt.encode(payload, settings.jwt_secret, algorithm=JWT_ALGORITHM)


def decode_access_token(token: str) -> int | None:
    """Devuelve el id del usuario si el token es válido y no venció; si no, None."""
    try:
        payload = jwt.decode(token, get_settings().jwt_secret, algorithms=[JWT_ALGORITHM])
        return int(payload["sub"])
    except (jwt.PyJWTError, KeyError, ValueError):
        return None
