# Requirements — Phase 0: Scaffold & Foundations

## Feature Name
Phase 0 — Scaffold & Foundations

## Scope
Establish the monorepo skeleton, local dev environment, CI pipeline, core Pydantic schemas, LangGraph StateGraph skeleton with Postgres checkpointer, stubbed KYC/KYB, and the synthetic merchant generator. This phase produces a runnable, testable, lint-clean skeleton with no real extraction or validation logic yet — every later phase builds on this.

### In Scope
1. Monorepo layout: `backend/` (FastAPI + LangGraph), `ui/` (Streamlit), `evals/` (eval harness), `specs/` (already present).
2. Docker Compose local dev: FastAPI service, Postgres service, Streamlit service; single `docker compose up` brings up the full stack.
3. CI pipeline: pytest, Ruff, Black, and type checks (mypy or pyright) on push/PR.
4. Pydantic V2 schemas for: `Application`, `ExtractionResult`, `ValidationResult`, `ReviewState`, and supporting enums.
5. LangGraph `StateGraph` skeleton with Postgres checkpointer; graph accepts an application, runs KYC stub, and pauses at a human-review interrupt.
6. Stub KYC/KYB service returning pass/fail deterministically (configurable).
7. Synthetic merchant generator producing merchants with known true revenue and planted problems.
8. LLM abstraction layer behind a provider-agnostic interface; default implementation targets Claude Haiku 4.5 via AWS Bedrock (LangChain structured output).

### Out of Scope (Explicit Non-Requirements)
- No real document parsing (Docling) or LLM extraction (Phase 1).
- No validation arithmetic checks (Phase 1).
- No reconciliation engine (Phase 2).
- No audit log or credit memo export (Phase 2).
- No real KYC/KYB provider integration (Phase 3).
- No production monitoring, rate limiting, or SOC 2 / ISO readiness (Phase 3).
- No real OAuth connectors (Phase 3).
- No facial recognition or model training on loan defaults (permanent non-goal).
- No cloud deployment in this phase (local Docker Compose only).

## Functional Acceptance Criteria
1. `docker compose up` starts all three services (API, Postgres, Streamlit) without errors.
2. `POST /applications` accepts a minimal application payload and returns a 201 with an application ID.
3. The LangGraph graph runs to the human-review interrupt and pauses, persisting state in Postgres.
4. `GET /applications/{id}/status` returns the current graph state (e.g., `awaiting_review`).
5. The KYC stub returns configurable pass/fail based on a request parameter or env config.
6. The synthetic merchant generator produces at least 10 merchants with known true revenue and at least one planted problem per merchant (configurable problem types).
7. All Pydantic schemas serialize/deserialize round-trip without data loss.
8. `pytest` passes with ≥80% coverage on pure-function modules.
9. `ruff check`, `black --check`, and type-check commands exit 0.
10. CI workflow file (`.github/workflows/ci.yml`) exists and runs the above.

## Boundary Rules
- **Deterministic core, LLM at edges:** All money math and decisions remain in pure Python. The LLM (Haiku 4.5) is only used for extraction and prose; in Phase 0, no LLM calls are made — the interface exists but is stubbed or unused.
- **Pure functions first, orchestration second:** Every stage is a plain, unit-testable function. LangGraph only connects them. No business logic inside graph nodes.
- **LLM provider-agnostic interface:** The LLM client is behind an interface (`LLMProvider`) so OpenAI GPT-4o or Anthropic Claude can be swapped without changing call sites. Default: AWS Bedrock Claude Haiku 4.5.
- **Connector interface:** Data sources sit behind one interface (`Connector`); ships with a file-based adapter. No real API integrations in Phase 0.
- **Synthetic ground truth:** The merchant generator must produce merchants with a known `true_revenue` field and a list of `planted_problems` so accuracy can be measured later.
- **Append-only, hash-chained audit log:** Schema and storage hooks are defined in Phase 0 (tables, hash chain logic) but not populated until Phase 2.
- **Local-first document processing:** Docling runs locally; no cloud document processing. In Phase 0, Docling is a dependency but not yet invoked.
- **Secrets handling:** AWS credentials, DB passwords, and API keys live in `.env` (gitignored). No secrets in committed code. `.env.example` documents required variables.

## Edge Cases (All)
1. **Invalid upload / file type:** Application submission with unsupported file types or oversized files returns 422 with a clear error message. Max upload size: 25 MB per file, 5 files per application.
2. **Duplicate application (idempotency):** Submitting the same application twice (same idempotency key) returns the existing application instead of creating a duplicate. Idempotency key is optional but recommended.
3. **KYC stub configuration:** KYC result is configurable via env var `KYC_STUB_RESULT` (pass/fail) and per-request override via query param `?kyc_override=pass|fail`. Default: pass.
4. **Confidence threshold interrupt:** The graph interrupts on low confidence (< 0.7), fraud flags, or final decision. In Phase 0, the interrupt fires at the human-review node regardless; threshold logic is wired but uses a mock confidence value.
5. **Synthetic merchant planted problems:** Each merchant gets 0–3 planted problems drawn from: `missing_payout`, `hidden_fee`, `abnormal_return`, `deposit_spike`, `inflated_revenue`. Problem types and counts are configurable via generator parameters.
6. **Database connection failure:** If Postgres is unreachable, the API returns 503 with a retry-after header. SQLite fallback is available for unit tests only.
7. **Empty application submission:** An application with no files attached still creates a valid application record and proceeds through the graph to the review interrupt (empty file list is valid).

## Non-Functional Requirements
- Python 3.11+.
- Type hints throughout; mypy/pyright strict mode on `backend/`.
- Black formatting, Ruff linting (default rules + pyflakes, isort).
- All pure functions have unit tests; graph nodes have integration tests.
- Docker images build in < 5 minutes on a standard laptop.
- API responds to health check (`GET /health`) in < 100 ms.

## Dependencies
- Python 3.11+, Docker, Docker Compose.
- AWS account with Bedrock access (Haiku 4.5) — for LLM interface only; no calls in Phase 0.
- Postgres 15+ (via Docker).
- No external API dependencies for Phase 0 (all mocked/stubbed).

## Success Metrics
- All 10 acceptance criteria pass.
- `docker compose up` → `curl /health` returns 200 within 30 seconds.
- An empty application submitted via `POST /applications` reaches `awaiting_review` state.
- Synthetic generator produces ≥10 merchants with verifiable true revenue and planted problems.
- CI pipeline green on first push.