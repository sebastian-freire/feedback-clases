from app.models import Role
from tests.factories import TEST_PASSWORD, auth


def test_register_creates_a_student_account(client):
    response = client.post(
        "/api/auth/register",
        json={"email": "Nueva@Test.uy", "full_name": "Ana Pérez", "password": "clave-segura"},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["access_token"]
    assert body["user"]["email"] == "nueva@test.uy"
    assert body["user"]["roles"] == ["student"]


def test_register_rejects_an_existing_email(client, factory):
    factory.student(email="ana@test.uy")

    response = client.post(
        "/api/auth/register",
        json={"email": "ANA@test.uy", "full_name": "Otra Ana", "password": "clave-segura"},
    )

    assert response.status_code == 409


def test_register_rejects_a_short_password(client):
    response = client.post(
        "/api/auth/register",
        json={"email": "a@test.uy", "full_name": "Ana", "password": "corta"},
    )

    assert response.status_code == 422


def test_login_returns_a_token_that_works_with_me(client, factory):
    teacher = factory.teacher(email="docente@test.uy")

    login = client.post(
        "/api/auth/login", json={"email": "docente@test.uy", "password": TEST_PASSWORD}
    )
    token = login.json()["access_token"]
    me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})

    assert login.status_code == 200
    assert me.status_code == 200
    assert me.json()["id"] == teacher.id
    assert me.json()["roles"] == ["teacher"]


def test_login_rejects_a_wrong_password(client, factory):
    factory.student(email="ana@test.uy")

    response = client.post("/api/auth/login", json={"email": "ana@test.uy", "password": "otra"})

    assert response.status_code == 401


def test_login_rejects_an_unknown_email(client):
    response = client.post(
        "/api/auth/login", json={"email": "nadie@test.uy", "password": TEST_PASSWORD}
    )

    assert response.status_code == 401


def test_me_requires_a_valid_token(client):
    assert client.get("/api/auth/me").status_code == 401
    bad = client.get("/api/auth/me", headers={"Authorization": "Bearer no-es-un-jwt"})
    assert bad.status_code == 401


def test_me_lists_every_role_of_a_multi_role_user(client, factory):
    user = factory.user(Role.ADMIN, Role.TEACHER)

    response = client.get("/api/auth/me", headers=auth(user))

    assert response.json()["roles"] == ["teacher", "admin"]
