# Requirements — Phase 1: MVP Core Pipeline

## Feature Name
Phase 1 — MVP: Core Pipeline (Application → Ingestion → Extraction → Validation → Human Review)

## Scope
Build the end-to-end pipeline that takes a merchant's uploaded financial documents through ingestion, Docling parsing, LLM extraction into strict Pydantic schemas, deterministic validation with source pointers, and pauses at a human-review interrupt. This is the first phase that delivers a working, demoable product on synthetic data.

### In Scope
1. **Application & Ingestion:** Merchant submits loan request + uploads files (bank PDFs, e-wallet exports, platform sales reports, receipts). Files are validated (type, size, count), stored, and queued for background processing.
2. **Parsing & Extraction:** Docling converts each document to structured layout and tables (local). LLM (Claude Haiku 4.5 via Bedrock, behind `LLMProvider` interface) maps structured output into strict Pydantic schemas with source-location pointers.
3. **Validation:** Non-LLM deterministic checks — running balances add up, line items sum to totals. Each extracted value carries a source pointer. Failures are recorded, not silently dropped.
4. **Human Review:** LangGraph interrupts on low confidence, fraud flags, or final decision. Underwriter sees evidence (extracted fields + source pointers + validation results) and chooses Approve / Deny / Counter.
5. **Eval Harness:** Measure field-extraction accuracy per document type, % of planted discrepancies caught, false-positive rate, end-to-end upload-to-review time.
6. **Synthetic Data Generator (extended):** Generate synthetic merchants with known true revenue, planted problems, and real synthetic documents (bank PDFs, e-wallet CSVs, platform sales reports, receipts) with ground-truth labels.

### Out of Scope (Explicit Non-Requirements)
- Reconciliation engine (Phase 2).
- Audit export / credit memo (Phase 2).
- Real KYC/KYB provider (Phase 3).
- Real OAuth connectors (Phase 3).
- Cloud deployment (Phase 3).
- Facial recognition / model training (permanent non-goal).

## Functional Acceptance Criteria
1. `POST /applications` accepts a loan request + file uploads (multipart). Returns 201 + application ID.
2. Files are validated: supported types (PDF, CSV, XLSX, PNG, JPG), max 25 MB/file, max 5 files/app. Invalid files return 422 with details.
3. Each uploaded file is stored and a `FileRef` recorded on the `Application`.
4. Background processing (FastAPI `BackgroundTasks`) runs ingestion → parsing → extraction → validation → graph interrupt. Application status transitions: `pending` → `processing` → `awaiting_review`.
5. Docling parses each document into structured layout (text + tables). Output is cached per file.
6. LLM extracts structured fields (amounts, dates, merchant names, transaction lines) into Pydantic schemas with `source_pointers`.
7. Validation checks run: running balance continuity, line-item-to-total sums. Results stored in `ValidationResult`.
8. If validation fails or confidence < 0.7, graph interrupts at `human_review` with full evidence.
9. Underwriter can `POST /applications/{id}/review` with Approve/Deny/Counter. Graph resumes and status updates.
10. `GET /applications/{id}/status` returns status, KYC result, confidence, validation results, and extracted summary.
11. `GET /applications/{id}/evidence` returns extracted fields + source pointers + validation results.
12. Eval harness runs on ≥10 synthetic merchants and reports: field-extraction accuracy per doc type, discrepancy catch rate, FP rate, end-to-end time.
13. All pure functions have unit tests; pipeline has integration tests.
14. `ruff check`, `black --check`, `mypy` exit 0.

## Boundary Rules
- **Deterministic core, LLM at edges:** All money math and validation in pure Python. LLM only reads documents and writes prose/structured extraction. No LLM in validation.
- **Validate outside the model:** Pydantic guarantees shape; arithmetic checks guarantee correctness. Every extracted value has a `source_pointer`.
- **Pure functions first:** Each stage (parse, extract, validate) is a pure function taking inputs and returning outputs. LangGraph only connects them.
- **Provider-agnostic LLM:** `LLMProvider` interface; default Haiku 4.5 via Bedrock. Swap-ready.
- **Synthetic ground truth:** Eval measures against known true revenue and planted problems.
- **Human-in-the-loop:** Graph interrupts on low confidence (< 0.7), any validation failure, or final decision.

## Edge Cases (All)
1. **Empty application (no files):** Valid. Creates application, KYC stub runs, graph reaches review with empty evidence.
2. **Unsupported file type:** Returns 422 with `"Unsupported file type: {ext}"`.
3. **Oversized file (>25 MB):** Returns 422 with `"File exceeds 25 MB limit"`.
4. **Too many files (>5):** Returns 422 with `"Maximum 5 files per application"`.
5. **Corrupt/unreadable PDF:** Docling raises; pipeline catches, marks document as `parse_failed`, continues with other documents. Application still reaches review with partial evidence.
6. **LLM extraction returns invalid JSON / schema mismatch:** Retry once with stricter prompt. If still fails, mark document as `extraction_failed`, continue.
7. **Validation failure (balances don't add up):** Recorded in `ValidationResult.errors`, confidence lowered, graph interrupts.
8. **Confidence below 0.7:** Graph interrupts at human_review regardless of validation status.
9. **Duplicate idempotency key:** Returns existing application (from Phase 0).
10. **Concurrent review decisions:** First decision wins; subsequent return 409 Conflict.
11. **File storage failure:** Returns 500 with retry suggestion. Application not created.

## Non-Functional Requirements
- Python 3.11+ (3.12 acceptable for dev).
- Type hints throughout; mypy strict on `backend/`.
- Black formatting, Ruff linting.
- All pure functions unit-tested; pipeline integration-tested.
- Docling runs locally (no cloud document processing).
- End-to-end upload-to-review < 60 seconds for 5 documents on synthetic data.
- API responds to health check < 100 ms.

## Dependencies
- Docling (`docling` package) — local document parsing.
- LangChain + LangChain-AWS (Bedrock) — LLM structured output.
- boto3 — AWS Bedrock client.
- Already installed: FastAPI, Pydantic V2, LangGraph, SQLAlchemy, psycopg, Streamlit, pytest, ruff, black, mypy.

## Success Metrics
- End-to-end flow works on ≥10 synthetic merchants.
- Field-extraction accuracy ≥ 85% per document type (measured against ground truth).
- ≥ 90% of planted discrepancies caught.
- False-positive rate < 10%.
- End-to-end upload-to-review < 60 seconds.
- Underwriter can approve/deny/counter via API and UI.
- All tests pass, lint/type checks clean.