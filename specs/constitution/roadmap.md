# Roadmap — SME Underwriting Copilot

## Phase 0 — Scaffold & foundations (now)
- Initialize monorepo and adopt this constitution (`specs/constitution/`).
- Set up Docker Compose local dev (FastAPI + Postgres + Streamlit).
- CI pipeline: pytest, Ruff, Black, type checks.
- Define Pydantic V2 schemas for application, extraction, validation, and review states.
- Implement LangGraph StateGraph skeleton with Postgres checkpointer.
- Stub KYC/KYB (pass/fail mock registry check).
- Synthetic merchant generator with known true revenue and planted problems.
- **Exit criteria:** repo builds in Docker Compose; an empty application can be submitted and lands in a reviewable state.

## Phase 1 — MVP: core pipeline (Application → Ingestion → Extraction → Validation → Human Review)
- **Application:** merchant submits loan request + uploads files (bank PDFs, e-wallet exports, platform sales reports, receipts).
- **Ingestion:** file validation, storage, and background queue.
- **Parsing & extraction:** Docling → structured layout/tables; LLM (OpenAI GPT-4o via LangChain structured output) maps into strict Pydantic schemas.
- **Validation:** non-LLM checks — running balances add up, line items sum to totals; every value keeps a source-location pointer.
- **Human review:** graph pauses; underwriter sees evidence and chooses Approve / Deny / Counter.
- **Eval harness:** measure field-extraction accuracy per document type, % of planted discrepancies caught, false-positive rate, end-to-end upload-to-review time.
- **Exit criteria:** end-to-end flow works on synthetic data; underwriter can approve/deny/counter; eval metrics documented.

## Phase 2 — Reconciliation & audit export (post-MVP)
- **Reconciliation:** match order IDs to payout references across platform exports, e-wallet logs, and bank deposits; flag missing payouts, hidden fees, abnormal returns, deposit spikes.
- **Audit export:** tamper-evident, hash-chained log + standardized credit memo for the credit committee.
- **Exit criteria:** reconciliation flags surface in review UI; credit memo and audit log exportable.

## Phase 3 — Hardening & scale (future)
- Real API connectors behind the connector interface (file-based adapters replaced by OAuth platform connectors).
- Real KYC/KYB provider replaces the stub.
- Production monitoring, alerting, and rate limiting.
- Deployment to Fly.io or Railway with public demo endpoint.
- Schema hooks to record loan outcomes (no model training).
- **Exit criteria:** public demo live; SOC 2 / ISO readiness optional future work.