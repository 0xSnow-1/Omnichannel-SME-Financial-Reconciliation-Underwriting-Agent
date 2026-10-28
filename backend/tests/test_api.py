import io

from fastapi.testclient import TestClient
from sme_copilot.api.main import app

client = TestClient(app)


def test_health():
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_create_application():
    resp = client.post(
        "/applications",
        data={"merchant_name": "Test", "loan_amount": "100000"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert "id" in data
    assert "status" in data


def test_application_status():
    resp = client.post(
        "/applications",
        data={"merchant_name": "Test2", "loan_amount": "50000"},
    )
    assert resp.status_code == 201
    app_id = resp.json()["id"]
    status_resp = client.get(f"/applications/{app_id}/status")
    assert status_resp.status_code == 200
    body = status_resp.json()
    assert body["status"] in ("awaiting_review", "pending", "processing")


def test_application_status_not_found():
    resp = client.get("/applications/does-not-exist/status")
    assert resp.status_code == 404


def test_review_decision():
    resp = client.post(
        "/applications",
        data={"merchant_name": "Test3", "loan_amount": "75000"},
    )
    assert resp.status_code == 201
    app_id = resp.json()["id"]

    # Force the review state to awaiting_review so we can act on it
    from sme_copilot.api.main import _review_states
    from sme_copilot.schemas.models import ApplicationStatus

    _review_states[app_id].status = ApplicationStatus.AWAITING_REVIEW

    review_resp = client.post(
        f"/applications/{app_id}/review", json={"decision": "approve"}
    )
    assert review_resp.status_code == 200
    assert review_resp.json()["status"] == "approved"


def test_review_decision_deny():
    resp = client.post(
        "/applications",
        data={"merchant_name": "Test4", "loan_amount": "75000"},
    )
    app_id = resp.json()["id"]

    from sme_copilot.api.main import _review_states
    from sme_copilot.schemas.models import ApplicationStatus

    _review_states[app_id].status = ApplicationStatus.AWAITING_REVIEW

    review_resp = client.post(
        f"/applications/{app_id}/review", json={"decision": "deny", "notes": "Too risky"}
    )
    assert review_resp.status_code == 200
    assert review_resp.json()["status"] == "denied"


def test_review_decision_counter():
    resp = client.post(
        "/applications",
        data={"merchant_name": "Test5", "loan_amount": "75000"},
    )
    app_id = resp.json()["id"]

    from sme_copilot.api.main import _review_states
    from sme_copilot.schemas.models import ApplicationStatus

    _review_states[app_id].status = ApplicationStatus.AWAITING_REVIEW

    review_resp = client.post(
        f"/applications/{app_id}/review", json={"decision": "counter"}
    )
    assert review_resp.status_code == 200
    assert review_resp.json()["status"] == "countered"


def test_review_invalid_decision():
    resp = client.post(
        "/applications",
        data={"merchant_name": "Test6", "loan_amount": "75000"},
    )
    app_id = resp.json()["id"]

    from sme_copilot.api.main import _review_states
    from sme_copilot.schemas.models import ApplicationStatus

    _review_states[app_id].status = ApplicationStatus.AWAITING_REVIEW

    review_resp = client.post(
        f"/applications/{app_id}/review", json={"decision": "yolo"}
    )
    assert review_resp.status_code == 422


def test_review_not_found():
    resp = client.post(
        "/applications/does-not-exist/review", json={"decision": "approve"}
    )
    assert resp.status_code == 404


def test_idempotency():
    key = "idem-test-key-xyz"
    r1 = client.post(
        "/applications",
        data={"merchant_name": "Idem", "loan_amount": "10000", "idempotency_key": key},
    )
    r2 = client.post(
        "/applications",
        data={"merchant_name": "Idem", "loan_amount": "10000", "idempotency_key": key},
    )
    assert r1.status_code == 201
    assert r1.json()["id"] == r2.json()["id"]


def test_file_upload_valid():
    resp = client.post(
        "/applications",
        data={"merchant_name": "FileTest", "loan_amount": "50000"},
    )
    app_id = resp.json()["id"]
    pdf_bytes = b"%PDF-1.4 fake pdf content"
    file_resp = client.post(
        f"/applications/{app_id}/files",
        files=[("files", ("statement.pdf", io.BytesIO(pdf_bytes), "application/pdf"))],
    )
    assert file_resp.status_code == 201
    data = file_resp.json()
    assert data["id"] == app_id
    assert len(data["files"]) >= 1


def test_file_upload_invalid_type():
    resp = client.post(
        "/applications",
        data={"merchant_name": "FileTest2", "loan_amount": "50000"},
    )
    app_id = resp.json()["id"]
    file_resp = client.post(
        f"/applications/{app_id}/files",
        files=[("files", ("malware.exe", io.BytesIO(b"MZ"), "application/x-msdownload"))],
    )
    assert file_resp.status_code == 422


def test_file_upload_too_many():
    resp = client.post(
        "/applications",
        data={"merchant_name": "FileTest3", "loan_amount": "50000"},
    )
    app_id = resp.json()["id"]
    files = [
        ("files", (f"file{i}.pdf", io.BytesIO(b"%PDF fake"), "application/pdf"))
        for i in range(6)
    ]
    file_resp = client.post(f"/applications/{app_id}/files", files=files)
    assert file_resp.status_code == 422


def test_evidence_endpoint():
    resp = client.post(
        "/applications",
        data={"merchant_name": "EvidTest", "loan_amount": "80000"},
    )
    app_id = resp.json()["id"]
    evid_resp = client.get(f"/applications/{app_id}/evidence")
    assert evid_resp.status_code == 200
    body = evid_resp.json()
    assert "documents" in body
    assert "validation_results" in body
    assert "fraud_flags" in body


def test_evidence_not_found():
    resp = client.get("/applications/does-not-exist/evidence")
    assert resp.status_code == 404
