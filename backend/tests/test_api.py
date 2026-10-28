from fastapi.testclient import TestClient
from sme_copilot.api.main import app

client = TestClient(app)


def test_health():
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_create_application():
    resp = client.post("/applications", json={"merchant_name": "Test", "loan_amount": 100000})
    assert resp.status_code == 201
    data = resp.json()
    assert "id" in data
    assert data["status"] == "awaiting_review"


def test_application_status():
    resp = client.post("/applications", json={"merchant_name": "Test2", "loan_amount": 50000})
    app_id = resp.json()["id"]
    status_resp = client.get(f"/applications/{app_id}/status")
    assert status_resp.status_code == 200
    assert status_resp.json()["status"] == "awaiting_review"


def test_review_decision():
    resp = client.post("/applications", json={"merchant_name": "Test3", "loan_amount": 75000})
    app_id = resp.json()["id"]
    review_resp = client.post(f"/applications/{app_id}/review", json={"decision": "approve"})
    assert review_resp.status_code == 200
    assert review_resp.json()["status"] == "approved"


def test_idempotency():
    key = "idem-123"
    r1 = client.post(
        "/applications",
        json={"merchant_name": "Idem", "loan_amount": 10000, "idempotency_key": key},
    )
    r2 = client.post(
        "/applications",
        json={"merchant_name": "Idem", "loan_amount": 10000, "idempotency_key": key},
    )
    assert r1.json()["id"] == r2.json()["id"]
