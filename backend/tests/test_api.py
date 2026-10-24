from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_endpoint_does_not_depend_on_upstream_source():
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_dashboard_rejects_invalid_cutoff_before_fetching_data():
    response = client.get("/api/dashboard?cutoff=25:99")
    assert response.status_code == 422


def test_forecast_day_rejects_date_outside_january():
    response = client.get("/api/forecast/day?date=2026-02-01&cutoff=09:00")
    assert response.status_code == 422
