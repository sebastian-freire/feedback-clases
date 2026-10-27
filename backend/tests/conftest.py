import os
from pathlib import Path

from app.config import get_settings

# Las pruebas corren contra TEST_DATABASE_URL, nunca contra la base de desarrollo.
_settings = get_settings()
if not _settings.test_database_url:
    raise RuntimeError("Falta TEST_DATABASE_URL en el .env (ver .env.example)")
if _settings.test_database_url == _settings.database_url:
    raise RuntimeError(
        "TEST_DATABASE_URL no puede ser igual a DATABASE_URL: las pruebas borran datos"
    )
os.environ["DATABASE_URL"] = _settings.test_database_url
# Las pruebas asumen el plazo de 7 días de los requisitos, sin importar lo que diga el .env.
os.environ["FEEDBACK_WINDOW_DAYS"] = "7"
get_settings.cache_clear()

import pytest  # noqa: E402
from alembic.config import Config  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import text  # noqa: E402

from alembic import command  # noqa: E402
from app.db import SessionLocal, engine  # noqa: E402
from app.main import create_app  # noqa: E402
from tests.factories import Factory  # noqa: E402

BACKEND_DIR = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="session", autouse=True)
def migrated_database():
    """Recrea el esquema desde cero aplicando las migraciones reales (también las prueba)."""
    with engine.begin() as conn:
        conn.execute(text("DROP SCHEMA public CASCADE"))
        conn.execute(text("CREATE SCHEMA public"))
    config = Config(str(BACKEND_DIR / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
    config.set_main_option("sqlalchemy.url", _settings.test_database_url.replace("%", "%%"))
    command.upgrade(config, "head")


@pytest.fixture(autouse=True)
def clean_tables():
    with engine.begin() as conn:
        conn.execute(text("TRUNCATE users, subjects RESTART IDENTITY CASCADE"))


@pytest.fixture
def client() -> TestClient:
    return TestClient(create_app())


@pytest.fixture
def db():
    with SessionLocal() as session:
        yield session


@pytest.fixture
def factory(db) -> Factory:
    return Factory(db)
