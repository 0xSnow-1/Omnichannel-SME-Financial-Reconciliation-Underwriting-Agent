# Tech Stack — SME Underwriting Copilot

## Language & data models
- **Python 3.11+** — primary language.
- **Pydantic V2** — strict schemas for all extracted data and LLM structured output.

## API layer
- **FastAPI** — streaming multipart upload, background jobs, status endpoints.

## Document parsing
- **Docling** — local document-to-structured-layout/table conversion (privacy-first; runs on-prem/in-VPC).

## LLM layer (recommendation: OpenAI GPT-4o via LangChain structured output)
- **Primary:** OpenAI GPT-4o with structured outputs (Pydantic V2 schemas) through LangChain.
  - Rationale: most reliable schema enforcement for strict Pydantic extraction, mature Python SDK, and easy to swap behind the LLM abstraction.
- **Alternative (documented, swap-ready):** Anthropic Claude 3.5 Sonnet — strong document reasoning; keep the LLM interface provider-agnostic so either can be dropped in.
- All LLM use is at the edges: reading messy documents and writing qualitative prose. Money math and decisions are deterministic Python.

## Orchestration
- **LangGraph StateGraph** — connects pipeline stages as plain, unit-testable functions; Postgres checkpointer for pause/resume and human-in-the-loop interrupts.

## Storage & databases
- **SQLite** — local development.
- **PostgreSQL** — deployment (also serves as LangGraph checkpointer).
- Append-only, hash-chained audit log stored in Postgres.

## Review UI
- **Streamlit** — underwriter review screen (evidence + Approve / Deny / Counter).

## Testing, packaging, & evals
- **pytest** — unit tests for every pure function stage.
- **Docker Compose** — local dev environment (API + Postgres + Streamlit).
- **Eval harness** — synthetic merchants with known true revenue and planted problems; measures field-extraction accuracy, discrepancy catch rate, false-positive rate, and end-to-end upload-to-review time.

## Deployment & infrastructure
- **PaaS:** Fly.io or Railway (Docker Compose-friendly).
- **Containers:** Docker; local dev via Docker Compose, deployed to PaaS.
- **Encryption:** at rest and in transit (baseline).
- **Data residency:** local-first document processing (Docling runs locally); LLM API calls are the only data egress.

## Styling conventions
- Python: Black formatting, Ruff linting, type hints throughout.
- Pydantic V2 models for all inter-stage data contracts.
- Streamlit UI: default theme, minimal custom CSS; functional over decorative.

## Repository convention
- **Monorepo:** backend (FastAPI + LangGraph), Streamlit UI, and eval harness in one repository.
- Small team (1–3 engineers); single trunk, feature branches, PRs required.

## Architectural principles (constraints)
1. Deterministic core, LLM at the edges.
2. Validate outside the model — structured output guarantees shape, not correctness; arithmetic checks + source pointers catch wrong numbers.
3. Human-in-the-loop by design — LangGraph interrupts on low confidence, fraud flags, or final decision; resume from checkpoint.
4. Pure functions first, orchestration second — every stage is a plain, unit-testable function; LangGraph only connects them.
5. Connector interface — data sources behind one interface; ships with file-based adapters.
6. Synthetic ground truth — generate merchants with known true revenue and planted problems; accuracy is measured, not claimed.
7. Append-only, hash-chained audit log — tamper-evident by construction.