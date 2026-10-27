from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.db import DbSession
from app.deps import CurrentUser
from app.models import Role, User, UserRole
from app.schemas import LoginRequest, RegisterRequest, TokenResponse, UserOut
from app.security import create_access_token, hash_password, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])


def find_user_by_email(db: DbSession, email: str) -> User | None:
    return db.scalar(select(User).where(User.email == email.lower()))


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register(body: RegisterRequest, db: DbSession) -> TokenResponse:
    """Registro abierto: crea una cuenta con rol alumno (D-038)."""
    if find_user_by_email(db, body.email):
        raise HTTPException(status.HTTP_409_CONFLICT, "Ya existe una cuenta con ese email.")
    user = User(
        email=body.email.lower(),
        full_name=body.full_name,
        password_hash=hash_password(body.password),
        role_rows=[UserRole(role=Role.STUDENT)],
    )
    db.add(user)
    db.commit()
    return TokenResponse(
        access_token=create_access_token(user.id), user=UserOut.model_validate(user)
    )


@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest, db: DbSession) -> TokenResponse:
    user = find_user_by_email(db, body.email)
    if not verify_password(body.password, user.password_hash if user else None):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Email o contraseña incorrectos.")
    return TokenResponse(
        access_token=create_access_token(user.id), user=UserOut.model_validate(user)
    )


@router.get("/me", response_model=UserOut)
def me(user: CurrentUser) -> User:
    return user
