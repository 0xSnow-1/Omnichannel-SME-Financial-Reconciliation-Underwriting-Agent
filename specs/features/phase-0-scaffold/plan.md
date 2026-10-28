# Implementation Plan — Phase 0: Scaffold & Foundations

## Feature
Phase 0 — Scaffold & Foundations

## LLM Provider
Claude Haiku 4.5 via AWS Bedrock, behind a provider-agnostic `LLMProvider` interface. No LLM calls in Phase 0; interface + stub only.

## Sequential Task Checklist

### Group 1 — Repository & Project Setup
- [ ] 1.1 Create monorepo directories: `backend/`, `ui/`, `evals/`, `tests/`.
- [ ] 1.2 Add `pyproject.toml` with project metadata, dependencies (FastAPI, Pydantic V2, LangGraph, LangChain, boto3/bedrock, Streamlit, pytest, ruff, black, mypy), and tool config.
- [ ] 1.3 Add `.env.example` documenting: `AWS_REGION`, `AWS_BEARER_TOKEN_BEDROCK`, `DATABASE_URL`, `KYC_STUB_RESULT`, `LLM_PROVIDER`, `MAX_UPLOAD_SIZE_MB`, `MAX_FILES_PER_APP`.
- [ ] 1.4 Add `.gitignore` entries for `.env`, `__pycache__`, `.pytest_cache`, `.mypy_cache`, `*.pyc`, `node_modules`.
- [ ] 1.5 Add `README.md` quick-start section (how to run locally).

### Group 2 — Docker Compose Local Dev
- [ ] 2.1 Write `Dockerfile` for backend (Python 3.11, install deps, run uvicorn).
- [ ] 2.2 Write `Dockerfile` for Streamlit UI.
- [ ] 2.3 Write `docker-compose.yml` with services: `api` (FastAPI), `db` (Postgres 15), `ui` (Streamlit). Add healthchecks and depends_on.
- [ ] 2.4 Verify `docker compose up` starts all services and `curl localhost:8000/health` returns 200.

### Group 3 — CI Pipeline
- [ ] 3.1 Create `.github/workflows/ci.yml` with jobs: lint (ruff), format (black --check), type-check (mypy), test (pytest).
- [ ] 3.2 Add pytest config in `pyproject.toml` (testpaths, coverage threshold 80%).
- [ ] 3.3 Add ruff config (select rules: E, F, I, B, UP; line length 100).
- [ ] 3.4 Add black config (line length 100).
- [ ] 3.5 Add mypy config (strict mode on `backend/`).

### Group 4 — Pydantic V2 Schemas
- [ ] 4.1 Define `Application` schema: `id`, `merchant_name`, `loan_amount`, `files: list[FileRef]`, `idempotency_key`, `created_at`, `status`.
- [ ] 4.2 Define `FileRef` schema: `filename`, `content_type`, `size_bytes`, `storage_path`, `uploaded_at`.
- [ ] 4.3 Define `ExtractionResult` schema: `application_id`, `document_type`, `fields: dict`, `confidence: float`, `source_pointers: list[SourcePointer]`.
- [ ] 4.4 Define `SourcePointer` schema: `page`, `bbox` (optional), `text_snippet`.
- [ ] 4.5 Define `ValidationResult` schema: `application_id`, `checks: list[CheckResult]`, `passed: bool`, `errors: list[str]`.
- [ ] 4.6 Define `CheckResult` schema: `check_name`, `passed: bool`, `details: str`.
- [ ] 4.7 Define `ReviewState` schema: `application_id`, `status` (enum: pending, awaiting_review, approved, denied, countered), `kyc_result`, `confidence`, `fraud_flags`, `decision`, `reviewer_notes`.
- [ ] 4.8 Define `Merchant` schema (synthetic): `merchant_id`, `name`, `true_revenue`, `planted_problems: list[ProblemType]`, `documents: list[FileRef]`.
- [ ] 4.9 Define `ProblemType` enum: `missing_payout`, `hidden_fee`, `abnormal_return`, `deposit_spike`, `inflated_revenue`.
- [ ] 4.10 Write round-trip serialization tests for all schemas.

### Group 5 — LLM Provider Interface
- [ ] 5.1 Define `LLMProvider` protocol/interface with methods: `extract_structured(prompt, schema) -> BaseModel`, `summarize(text) -> str`.
- [ ] 5.2 Implement `BedrockHaikuProvider` (Claude Haiku 4.5) using LangChain structured output. Mark as default in config.
- [ ] 5.3 Implement `StubLLMProvider` for tests (returns canned responses).
- [ ] 5.4 Add factory function `get_llm_provider()` reading `LLM_PROVIDER` env var.
- [ ] 5.5 Write unit tests for provider interface (mock-based, no real API calls).

### Group 6 — Connector Interface
- [ ] 6.1 Define `Connector` protocol: `fetch_documents(source_id) -> list[FileRef]`, `validate_source(source_id) -> bool`.
- [ ] 6.2 Implement `FileConnector` (reads from local filesystem).
- [ ] 6.3 Write unit tests for FileConnector.

### Group 7 — KYC/KYB Stub Service
- [ ] 7.1 Implement `KYCService` with method `check(merchant_id, override=None) -> KYCResult`.
- [ ] 7.2 Read default from `KYC_STUB_RESULT` env var; support per-request override via query param.
- [ ] 7.3 Define `KYCResult` schema: `passed: bool`, `reason: str`, `checked_at`.
- [ ] 7.4 Write unit tests (pass, fail, override).

### Group 8 — Synthetic Merchant Generator
- [ ] 8.1 Implement `MerchantGenerator` with parameters: `count`, `problem_types`, `problems_per_merchant` (range).
- [ ] 8.2 Generate merchants with known `true_revenue` (random within realistic range for micro-businesses: ₱50k–₱500k/month).
- [ ] 8.3 Plant problems per merchant (configurable types and counts).
- [ ] 8.4 Generate placeholder document file references (no real files yet; Phase 1 creates them).
- [ ] 8.5 Write unit tests verifying: count, true_revenue presence, planted problems within range, reproducibility with seed.

### Group 9 — LangGraph StateGraph Skeleton
- [ ] 9.1 Define `GraphState` TypedDict matching `ReviewState` + application context.
- [ ] 9.2 Create `StateGraph` with nodes: `kyc_check`, `human_review` (interrupt).
- [ ] 9.3 Wire Postgres checkpointer for state persistence.
- [ ] 9.4 Add interrupt at `human_review` node (LangGraph `interrupt()`).
- [ ] 9.5 Implement `run_graph(application) -> thread_id` and `resume_graph(thread_id, decision) -> ReviewState`.
- [ ] 9.6 Write integration tests: graph runs to interrupt, state persists, resume works.

### Group 10 — FastAPI Application
- [ ] 10.1 Create FastAPI app with `GET /health`.
- [ ] 10.2 Implement `POST /applications` (accepts JSON payload, creates application, triggers graph, returns 201 + ID).
- [ ] 10.3 Implement `GET /applications/{id}/status` (returns current graph state).
- [ ] 10.4 Implement `POST /applications/{id}/review` (resume graph with Approve/Deny/Counter decision).
- [ ] 10.5 Add file upload endpoint `POST /applications/{id}/files` with validation (type, size, count limits).
- [ ] 10.6 Add idempotency key support on `POST /applications`.
- [ ] 10.7 Write API integration tests (httpx TestClient).

### Group 11 — Streamlit Review UI (Skeleton)
- [ ] 11.1 Create Streamlit app with application list view.
- [ ] 11.2 Add application detail view showing status and KYC result.
- [ ] 11.3 Add Approve / Deny / Counter buttons that call `POST /applications/{id}/review`.
- [ ] 11.4 Verify UI loads and connects to API.

### Group 12 — Hash-Chained Audit Log (Schema Only)
- [ ] 12.1 Define `AuditEntry` schema: `id`, `application_id`, `action`, `actor`, `timestamp`, `prev_hash`, `entry_hash`.
- [ ] 12.2 Implement hash computation: `entry_hash = SHA256(prev_hash + serialized_entry)`.
- [ ] 12.3 Create DB table for audit log (migration or init script).
- [ ] 12.4 Write unit tests for hash chain integrity (tamper detection).

### Group 13 — Verification & Polish
- [ ] 13.1 Run full test suite; fix failures.
- [ ] 13.2 Run ruff, black, mypy; fix all issues.
- [ ] 13.3 Verify Docker Compose end-to-end.
- [ ] 13.4 Update README with Phase 0 completion status.
- [ ] 13.5 Tag release `v0.1.0-phase0`.

## Implementation Order
Groups 1–3 (setup) → Group 4 (schemas) → Groups 5–8 (interfaces, stubs, generator) → Group 9 (graph) → Group 10 (API) → Group 11 (UI) → Group 12 (audit schema) → Group 13 (verification).
Groups 5, 6, 7, 8 are independent after Group 4 and can be parallelized.