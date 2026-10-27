"""Dependencias de autenticación y autorización por rol."""

from collections.abc import Callable
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.db import DbSession
from app.models import Role, User
from app.security import decode_access_token

_bearer = HTTPBearer(auto_error=False, description="Token JWT obtenido en /api/auth/login")


def get_current_user(
    db: DbSession,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> User:
    user_id = decode_access_token(credentials.credentials) if credentials else None
    user = db.get(User, user_id) if user_id is not None else None
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Sesión inválida o vencida. Volvé a iniciar sesión.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_role(role: Role) -> Callable[[User], User]:
    """Los roles se leen de la base en cada request, así un cambio de rol aplica al instante."""

    def dependency(user: CurrentUser) -> User:
        if not user.has_role(role):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tenés permiso para acceder a esta sección.",
            )
        return user

    return dependency


StudentUser = Annotated[User, Depends(require_role(Role.STUDENT))]
TeacherUser = Annotated[User, Depends(require_role(Role.TEACHER))]
AdminUser = Annotated[User, Depends(require_role(Role.ADMIN))]
