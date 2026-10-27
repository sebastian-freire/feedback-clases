from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.routers import admin, auth, health, student, teacher


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="Feedback de clases API",
        description=(
            "API para que los alumnos opinen sobre cada clase y los docentes vean lo agregado."
        ),
        version="0.1.0",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_methods=["*"],
        allow_headers=["*"],
        # Para que el frontend lea el nombre del archivo de la planilla exportada.
        expose_headers=["Content-Disposition"],
    )
    for module in (health, auth, student, teacher, admin):
        app.include_router(module.router, prefix="/api")
    return app


app = create_app()
