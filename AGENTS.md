# AGENTS.md — SME Underwriting Copilot

This file tells AI coding agents how this project is structured, what the rules are, and what each file does. Read this before touching anything.

---

## Project in one sentence

An AI back-office system that turns a small business owner's scattered financial proof (bank PDFs, e-wallet exports, platform sales reports, receipts) into a verified, explained credit file so a human underwriter can decide in minutes instead of days.

---

## Repo layout

```
.
├── backend/
│   └── src/sme_copilot/
│       ├── api/
│       │   └── main.py          # FastAPI app — all HTTP endpoints
│       ├── graph/
│       │   └── pipeline.py      # LangGraph StateGraph — pipeline orchestration
│       ├── interfaces/
│       │   └── contracts.py     # ABCs: LLMProvider, Connector
│       ├── schemas/
│       │   └── models.py        # All Pydantic V2 schemas (single source of truth)
│       └── services/
│           ├── audit.py         # Hash-chain audit log
│           ├── docling_parser.py # Docling document parsing
│           ├── file_storage.py  # File save / validate / cleanup
│           ├── kyc.py           # KYC stub service
│           ├── llm_provider.py  # LLMProvider factory + StubLLMProvider
│           ├── merchant_generator.py  # Synthetic merchant generator
│           └── validators.py    # Deterministic validation checks
├── backend/tests/               # pytest test suite
├── evals/
│   ├── __init__.py
│   └── generate_merchants.py    # CLI: python -m evals.generate_merchants --count 10 --seed 42
├── ui/
│   └── app.py                   # Streamlit underwriter review UI
├── specs/
│   ├── constitution/            # Mission, roadmap, tech stack — read these first
│   └── features/                # Per-phase plan, requirements, verification scorecards
├── pyproject.toml               # Dependencies, pytest config, ruff/black/mypy config
├── docker-compose.yml           # Local dev: db (Postgres) + api (FastAPI) + ui (Streamlit)
├── Dockerfile.backend
└── Dockerfile.ui
```

---

## Architecture rules (non-negotiable)

1. **Deterministic core, LLM at the edges.** All money math and decision logic lives in pure Python. The LLM only reads messy documents and writes prose/structured extraction. Never put arithmetic or validation inside an LLM call.

2. **Validate outside the model.** Pydantic guarantees the *shape* of data; it does not guarantee *correctness*. Arithmetic checks (`validators.py`) and source pointers catch wrong numbers.

3. **Human-in-the-loop by design.** The LangGraph graph *must* interrupt at `human_review` before a final decision is made. Never auto-approve or auto-deny without an interrupt.

4. **Pure functions first, orchestration second.** Every pipeline stage (`parse`, `extract`, `validate`) must be a plain Python function that can be called and tested without LangGraph. LangGraph only wires them together.

5. **Provider-agnostic LLM.** All LLM calls go through the `LLMProvider` interface in `contracts.py`. Never call `openai`, `boto3`, or any LLM SDK directly from business logic. Add implementations in `llm_provider.py` and select via `LLM_PROVIDER` env var.

6. **Append-only audit log.** The audit chain in `audit.py` is append-only and hash-chained. Never modify or delete audit entries. Verify chain integrity with `verify_chain()` before any audit export.

7. **No silent failures.** If parsing fails, mark `parse_status="failed"` and continue. If extraction fails, mark `extraction_status="failed"` and continue. Never swallow exceptions without recording them on the relevant schema.

---

## Schema conventions

- **Single source of truth:** all Pydantic models live in `schemas/models.py`. Do not define schemas elsewhere.
- **Pydantic V2 only** — use `model_dump()`, `model_validate_json()`, `Field(...)` with constraints.
- **`StrEnum` for all enums** — use `class Foo(StrEnum)` not `class Foo(str, Enum)`.
- **Source pointers:** every extracted monetary value must carry a `SourcePointer` (page, bbox, text_snippet) so underwriters can trace it back to the document.
- **`application_id` everywhere** — every result schema carries `application_id` so results can be correlated without global state.

---

## Code style

- **Python 3.11+** (3.12 acceptable for dev). Type hints on every function signature.
- **Black** formatting (`line-length = 100`). Run `black .` before committing.
- **Ruff** linting (`ruff check .`). Fix all errors before committing. `noqa: B008` is acceptable on FastAPI `File()`/`Form()` argument defaults — that's a known false positive.
- **mypy strict** (`mypy backend/src --strict`). No `Any` unless truly unavoidable.
- Import order: stdlib → third-party → local (ruff's `I` rules enforce this automatically).

---

## Testing rules

- **Run tests with:** `PYTHONPATH=backend/src python -m pytest backend/tests -q`
- **Coverage target:** ≥ 80% (enforced via `--cov-fail-under=80` in `pyproject.toml`).
- **Every pure function must have a unit test.** If you add a new service function, add a matching test in `backend/tests/`.
- **API tests use `TestClient` with multipart form data** (`data={...}` for form fields, `files=[...]` for uploads). Do NOT use `json={...}` for endpoints declared with `Form(...)`.
- **Mock the LLM** in tests — never make real API calls in the test suite. Use `StubLLMProvider` or `unittest.mock.patch`.
- **Mock file I/O** in tests — use `monkeypatch` to redirect `UPLOAD_DIR` to `tmp_path`.

---

## Environment variables

| Variable | Default | Description |
|---|---|---|
| `LLM_PROVIDER` | `stub` | `stub`, `bedrock-haiku`, or `openai-gpt4o` |
| `KYC_STUB_RESULT` | `pass` | `pass` or `fail` — controls KYC stub outcome |
| `DATABASE_URL` | *(none)* | Postgres DSN for LangGraph checkpointer and audit log |
| `AWS_REGION` | `us-east-1` | For Bedrock LLM provider |
| `AWS_BEARER_TOKEN_BEDROCK` | *(none)* | Bedrock auth token |
| `OPENAI_API_KEY` | *(none)* | For OpenAI GPT-4o LLM provider |

See `.env.example` for a complete template.

---

## Running locally

```bash
# Start all services
docker compose up -d

# Run tests
PYTHONPATH=backend/src python -m pytest backend/tests -q

# Lint
python -m ruff check .

# Format check
python -m black --check .

# Type check
python -m mypy backend/src --strict

# Generate 10 synthetic merchants (seed 42)
python -m evals.generate_merchants --count 10 --seed 42

# Hit the API
curl http://localhost:8000/health
curl -X POST http://localhost:8000/applications \
  -F "merchant_name=Aling Rosa" \
  -F "loan_amount=150000"
```

---

## Phase status

| Phase | Status | Description |
|---|---|---|
| Phase 0 — Scaffold | ✅ Done | Repo, schemas, KYC stub, audit chain, LangGraph skeleton, CI |
| Phase 1 — MVP Core Pipeline | 🟠 In progress | Docling → LLM extraction → validation → human review |
| Phase 2 — Reconciliation & Audit Export | ⚪ Not started | Cross-source reconciliation, credit memo |
| Phase 3 — Hardening & Scale | ⚪ Not started | Real connectors, real KYC, public deployment |

See `specs/features/` for per-phase requirements, plans, and verification scorecards.

---

## What NOT to do

- ❌ Do not put money math or validation logic inside an LLM prompt.
- ❌ Do not call LLM APIs directly — always go through `LLMProvider`.
- ❌ Do not define new Pydantic schemas outside `schemas/models.py`.
- ❌ Do not auto-approve or skip the `human_review` interrupt.
- ❌ Do not paste shell commands into Python files (yes, this happened — see PR #1).
- ❌ Do not write tests that use `json={...}` for `Form(...)` endpoints.
- ❌ Do not make real LLM or external API calls in tests.
- ❌ Do not break the 80% coverage threshold.
- ❌ Do not commit with ruff or mypy errors.
