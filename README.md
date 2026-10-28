# Project description

**Working title: SME Underwriting Copilot**

**One-line pitch:** an AI back-office system that turns a small business owner's scattered financial proof (bank PDFs, e-wallet exports, platform sales reports, receipts) into a verified, explained credit file, so a human underwriter can decide in minutes instead of days.

**Who it's for:** the customer is a lender, fintech, or B2B platform that wants to serve small merchants. The user is Aling Rosa, a micro-business owner who needs ₱100k–₱500k in working capital but has no audited books.

## Workflow

1. **Application:** the merchant submits a loan request and uploads files or links a connector.
2. **KYC/KYB (stubbed):** a mock registry check returns pass or fail.
3. **Ingestion:** files are validated, stored, and queued for background processing.
4. **Parsing and extraction:** Docling converts each document to structured layout and tables. An LLM maps it into strict Pydantic schemas.
5. **Validation:** non-LLM checks run on the extracted data (running balances add up, line items sum to totals). Each value keeps a pointer to its source location in the document.
6. **Reconciliation:** the system matches order IDs to payout references across platform exports, e-wallet logs, and bank deposits. It flags missing payouts, hidden fees, abnormal returns, and deposit spikes.
7. **Underwriting analysis:** deterministic Python computes cash-flow metrics and a repayment stress test. One LLM call then writes a qualitative risk summary from those computed facts.
8. **Human review:** the graph pauses. The underwriter sees the evidence and chooses Approve, Deny, or Counter.
9. **Audit export:** a tamper-evident log and a standardized credit memo are produced for the credit committee.

## Architectural decisions (and why)

- **Deterministic core, LLM at the edges.** The LLM reads messy documents and writes prose. All money math and decisions rest on tested Python. This makes the system defensible to a lender.
- **Validate outside the model.** Structured output guarantees the shape of data, not its correctness. Arithmetic checks and source pointers catch wrong numbers.
- **Human-in-the-loop by design.** LangGraph interrupts pause the workflow on low confidence, fraud flags, or the final decision, and resume from a saved checkpoint.
- **Pure functions first, orchestration second.** Every stage is a plain, unit-testable function. LangGraph only connects them.
- **Connector interface.** Data sources sit behind one interface. The project ships with file-based adapters, so real API integrations could be added without changing the core.
- **Synthetic ground truth.** The project generates its own merchants with known true revenue and planted problems, so accuracy is measured instead of claimed.
- **Append-only, hash-chained audit log.** Each entry includes the hash of the previous one, so tampering is detectable.
- **Local-first document processing.** Docling runs locally, which is a privacy argument for financial data.

## Tech stack

- **Language and data models:** Python, Pydantic V2
- **API:** FastAPI (streaming multipart upload, background jobs, status endpoint)
- **Document parsing:** Docling
- **Extraction and summaries:** an LLM via LangChain's structured-output interface
- **Orchestration:** LangGraph StateGraph, with a Postgres checkpointer for pause and resume
- **Storage:** SQLite while developing, Postgres for deployment
- **Review UI:** Streamlit
- **Packaging and testing:** Docker Compose, pytest, and an eval harness
- **Deployment:** a cloud host with a public demo

## What is real and what is mocked

- **Real:** extraction, validation, reconciliation, underwriting math, stress testing, human review, the audit log, and the evals.
- **Mocked:** OAuth connectors to platforms (file-based adapters instead) and KYC/KYB (stub service).
- **Out of scope:** facial recognition and training models on loan defaults. The schema leaves room to record loan outcomes later.

## How you'll prove it works

The README reports the following, measured on synthetic data:

- field-extraction accuracy per document type
- percentage of planted discrepancies caught, and the false-positive rate
- end-to-end time from upload to review-ready file
- a 2-minute demo told through Rosa's story, ending on the underwriter's screen

https://www.anthropic.com/research/demystifying-evals-for-ai-agents