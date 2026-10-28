# Mission — SME Underwriting Copilot

## Product vision
An AI back-office system that turns a small business owner's scattered financial proof — bank PDFs, e-wallet exports, platform sales reports, and receipts — into a verified, explained credit file, so a human underwriter can decide in minutes instead of days.

## Core user value
- **Speed:** compress underwriting from days to minutes by automating document ingestion, extraction, validation, and reconciliation-adjacent checks.
- **Defensibility:** every extracted figure carries a pointer to its source location; all money math runs on deterministic, tested Python — not LLM guesswork.
- **Accessibility:** serve micro-merchants (like Aling Rosa) who need ₱100k–₱500k in working capital but have no audited books.
- **Human-in-the-loop:** the underwriter remains the decision-maker; the system surfaces evidence and pauses for Approve / Deny / Counter.

## Target audience
- **Customer (buyer):** lenders, fintechs, and B2B platforms that want to serve small merchants.
- **End user (underwriter):** reviews extracted evidence and renders the credit decision.
- **End user (merchant):** submits a loan request and uploads files or links a connector (e.g., Aling Rosa).

## Non-goals (explicitly out of scope)
- Facial recognition / biometric identity verification.
- Training models on loan-default outcomes (the schema records outcomes later, but no model training in MVP).
- Real KYC/KYB integrations (stubbed in MVP; real registry checks deferred).
- Reconciliation engine and formal audit export (deferred to Phase 2).
- Formal compliance certifications (SOC 2, ISO 27001, PCI-DSS) — baseline security only.

## MVP scope (Phase 1)
Application → Ingestion → Parsing & Extraction → Validation → Human Review.
Reconciliation and Audit Export are intentionally deferred to Phase 2.