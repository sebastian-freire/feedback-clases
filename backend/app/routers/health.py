from fastapi import APIRouter, Response, status
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.db import DbSession

router = APIRouter(tags=["health"])


@router.get("/health")
def health(response: Response, db: DbSession) -> dict[str, str]:
    """Estado del servicio y de la conexión a la base (503 si la base no responde)."""
    try:
        db.execute(text("SELECT 1"))
    except SQLAlchemyError:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {"status": "error", "database": "unreachable"}
    return {"status": "ok", "database": "ok"}


@router.get("/live")
def live() -> dict[str, str]:
    """Liveness: el proceso responde. No consulta la base, para que una caída de la base
    no haga que Kubernetes reinicie los pods en cadena (eso lo cubre /health como readiness)."""
    return {"status": "ok"}
