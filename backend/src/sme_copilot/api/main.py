import threading
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from fastapi import BackgroundTasks, FastAPI, File, Form, HTTPException, UploadFile

from sme_copilot.schemas.models import (
    Application,
    ApplicationStatus,
    EvidenceBundle,
    ProcessingStatus,
    ReviewState,
)
from sme_copilot.services.file_storage import MAX_FILES, save_file, validate_file
from sme_copilot.services.kyc import KYCService

_applications: dict[str, Application] = {}
_review_states: dict[str, ReviewState] = {}
_locks: dict[str, threading.Lock] = {}


def _get_lock(app_id: str) -> threading.Lock:
    if app_id not in _locks:
        _locks[app_id] = threading.Lock()
    return _locks[app_id]


def _process_application(app_id: str) -> None:
    app = _applications.get(app_id)
    if not app:
        return
    app.processing_status = ProcessingStatus.PROCESSING
    # KYC stub
    kyc = KYCService()
    rs = _review_states[app_id]
    rs.kyc_result = kyc.check(app.merchant_name)
    if not rs.kyc_result.passed:
        app.processing_status = ProcessingStatus.FAILED
        rs.status = ApplicationStatus.DENIED
        return
    # For Phase 1: mark as awaiting review (extraction/validation wired in Group 3-5)
    app.processing_status = ProcessingStatus.AWAITING_REVIEW
    rs.status = ApplicationStatus.AWAITING_REVIEW


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    yield


app = FastAPI(title="SME Underwriting Copilot", lifespan=lifespan)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/applications", status_code=201)
def create_application(
    background_tasks: BackgroundTasks,
    merchant_name: str = Form(...),
    loan_amount: float = Form(...),
    idempotency_key: str | None = Form(None),
    files: list[UploadFile] = File(default=[]),  # noqa: B008
) -> dict[str, str]:
    # Idempotency check
    if idempotency_key:
        for aid, existing in _applications.items():
            if existing.idempotency_key == idempotency_key:
                return {"id": aid, "status": existing.processing_status.value}

    if len(files) > MAX_FILES:
        raise HTTPException(status_code=422, detail="Maximum 5 files per application")

    application = Application(
        merchant_name=merchant_name,
        loan_amount=loan_amount,
        idempotency_key=idempotency_key,
    )
    _applications[application.id] = application
    _review_states[application.id] = ReviewState(application_id=application.id)

    # Validate and store files
    for f in files:
        data = f.file.read()
        fname = f.filename or "unknown"
        ftype = f.content_type or "application/octet-stream"
        err = validate_file(fname, ftype, len(data))
        if err:
            del _applications[application.id]
            del _review_states[application.id]
            raise HTTPException(status_code=422, detail=err)
        file_ref = save_file(application.id, fname, ftype, data)
        application.files.append(file_ref)

    application.processing_status = ProcessingStatus.PENDING
    background_tasks.add_task(_process_application, application.id)
    return {"id": application.id, "status": application.processing_status.value}


@app.get("/applications/{app_id}/status")
def get_status(app_id: str) -> dict[str, Any]:
    if app_id not in _review_states:
        raise HTTPException(status_code=404, detail="Application not found")
    rs = _review_states[app_id]
    app = _applications[app_id]
    return {
        "id": app_id,
        "status": rs.status.value,
        "processing_status": app.processing_status.value,
        "kyc_result": rs.kyc_result,
        "confidence": rs.confidence,
        "validation_results": [vr.model_dump() for vr in app.validation_results],
        "extracted_documents": [ed.model_dump() for ed in app.extracted_documents],
    }


@app.get("/applications/{app_id}/evidence")
def get_evidence(app_id: str) -> dict[str, Any]:
    if app_id not in _applications:
        raise HTTPException(status_code=404, detail="Application not found")
    app = _applications[app_id]
    rs = _review_states[app_id]
    bundle = EvidenceBundle(
        application_id=app_id,
        documents=app.extracted_documents,
        validation_results=app.validation_results,
        confidence=rs.confidence,
        fraud_flags=rs.fraud_flags,
    )
    return bundle.model_dump()


@app.post("/applications/{app_id}/review")
def review_application(app_id: str, body: dict[str, Any]) -> dict[str, str]:
    if app_id not in _review_states:
        raise HTTPException(status_code=404, detail="Application not found")
    lock = _get_lock(app_id)
    if not lock.acquire(blocking=False):
        raise HTTPException(status_code=409, detail="Concurrent review in progress")
    try:
        rs = _review_states[app_id]
        if rs.status not in (ApplicationStatus.AWAITING_REVIEW,):
            raise HTTPException(status_code=409, detail="Application not in reviewable state")
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
        _applications[app_id].processing_status = ProcessingStatus(rs.status.value)
        return {"id": app_id, "status": rs.status.value}
    finally:
        lock.release()


@app.post("/applications/{app_id}/files", status_code=201)
def upload_files(app_id: str, files: list[UploadFile] = File(...)) -> dict[str, Any]:  # noqa: B008
    if app_id not in _applications:
        raise HTTPException(status_code=404, detail="Application not found")
    app = _applications[app_id]
    if len(app.files) + len(files) > MAX_FILES:
        raise HTTPException(status_code=422, detail="Maximum 5 files per application")
    for f in files:
        data = f.file.read()
        fname = f.filename or "unknown"
        ftype = f.content_type or "application/octet-stream"
        err = validate_file(fname, ftype, len(data))
        if err:
            raise HTTPException(status_code=422, detail=err)
        file_ref = save_file(app_id, fname, ftype, data)
        app.files.append(file_ref)
    return {"id": app_id, "files": [fr.model_dump() for fr in app.files]}
