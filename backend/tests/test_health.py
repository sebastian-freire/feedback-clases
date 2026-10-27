def test_health_reports_ok_when_database_is_reachable(client):
    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "ok"}


def test_live_does_not_need_the_database(client):
    from app import db

    def broken_session():
        raise AssertionError("/api/live no debe usar la base")
        yield

    client.app.dependency_overrides[db.get_db] = broken_session

    response = client.get("/api/live")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
