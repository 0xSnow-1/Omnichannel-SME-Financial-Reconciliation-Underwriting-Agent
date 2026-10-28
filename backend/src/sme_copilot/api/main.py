from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from sme_copilot.schemas.models import Application, ApplicationStatus, ReviewState

# In-memory store for Phase 0 (Postgres persistence in Phase 1)
_applications: dict[str, Application] = {}
_review_states: dict[str, ReviewState] = {}


class CreateApplicationRequest(BaseModel):
    merchant_name: str
    loan_amount: float
    idempotency_key: str | None = None


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    yield


app = FastAPI(title="SME Underwriting Copilot", lifespan=lifespan)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/applications", status_code=201)
def create_application(req: CreateApplicationRequest) -> dict[str, str]:
    if req.idempotency_key:
        for app_id, existing in _applications.items():
            if existing.idempotency_key == req.idempotency_key:
                return {"id": app_id, "status": existing.status.value}

    application = Application(
        merchant_name=req.merchant_name,
        loan_amount=req.loan_amount,
        idempotency_key=req.idempotency_key,
    )
    review_state = ReviewState(
        application_id=application.id, status=ApplicationStatus.AWAITING_REVIEW
    )
    _applications[application.id] = application
    _review_states[application.id] = review_state
    application.status = ApplicationStatus.AWAITING_REVIEW
    return {"id": application.id, "status": application.status.value}


@app.get("/applications/{app_id}/status")
def get_status(app_id: str) -> dict[str, object]:
    if app_id not in _review_states:
        raise HTTPException(status_code=404, detail="Application not found")
    rs = _review_states[app_id]
    return {"id": app_id, "status": rs.status.value, "kyc_result": rs.kyc_result}


@app.post("/applications/{app_id}/review")
def review_application(app_id: str, body: dict[str, object]) -> dict[str, str]:
    if app_id not in _review_states:
        raise HTTPException(status_code=404, detail="Application not found")
    rs = _review_states[app_id]
    decision = str(body.get("decision", "")).lower()
    if decision == "approve":
        rs.status = ApplicationStatus.APPROVED
    elif decision == "deny":
        rs.status = ApplicationStatus.DENIED
    elif decision == "counter":
        rs.status = ApplicationStatus.COUNTERED
    else:
        raise HTTPException(status_code=422, detail="Invalid decision")
    rs.decision = decision
    rs.reviewer_notes = str(body.get("notes")) if body.get("notes") is not None else None
    return {"id": app_id, "status": rs.status.value}
