# Implementation Plan — Phase 1: MVP Core Pipeline

## Feature
Phase 1 — MVP: Core Pipeline (Application → Ingestion → Extraction → Validation → Human Review)

## LLM Provider
Claude Haiku 4.5 via AWS Bedrock, behind `LLMProvider` interface (from Phase 0).

## Sequential Task Checklist

### Group 1 — Extended Schemas
- [x] 1.1 Add `DocumentType` enum: `bank_statement`, `ewallet_export`, `platform_sales`, `receipt`.
- [x] 1.2 Add `TransactionLine` schema: `date`, `description`, `amount`, `balance`, `source_pointer`.
- [x] 1.3 Add `ExtractedDocument` schema: `application_id`, `file_ref`, `document_type`, `transactions: list[TransactionLine]`, `summary_fields: dict`, `confidence`, `source_pointers`, `extraction_status` (success/failed).
- [x] 1.4 Add `ValidationCheck` enum: `running_balance`, `line_item_sum`, `date_continuity`.
- [x] 1.5 Add `ProcessingStatus` enum: `pending`, `processing`, `awaiting_review`, `approved`, `denied`, `countered`, `failed`.
- [x] 1.6 Update `Application` schema: add `processing_status`, `extracted_documents: list[ExtractedDocument]`, `validation_results: list[ValidationResult]`.
- [x] 1.7 Add `EvidenceBundle` schema: `application_id`, `documents: list[ExtractedDocument]`, `validation_results`, `confidence`, `fraud_flags`.

### Group 2 — File Ingestion & Storage
- [x] 2.1 Implement `FileStorage` service: save uploaded file to local disk (`data/uploads/{app_id}/`), return `FileRef`.
- [x] 2.2 Implement file validation: type check (PDF/CSV/XLSX/PNG/JPG), size check (≤25MB), count check (≤5).
- [x] 2.3 Add `POST /applications/{id}/files` endpoint (multipart upload) with validation.
- [x] 2.4 Add `POST /applications` multipart variant accepting files inline.
- [x] 2.5 Implement storage cleanup on application deletion.

### Group 3 — Docling Parser
- [x] 3.1 Add `docling` dependency to pyproject.toml.
- [x] 3.2 Implement `DoclingParser` service: `parse(file_path) -> ParsedDocument` with text + tables.
- [x] 3.3 Define `ParsedDocument` schema: `text: str`, `tables: list[TableData]`, `page_count`, `parse_status`.
- [x] 3.4 Implement parse caching (disk cache keyed by file hash).
- [x] 3.5 Handle corrupt/unreadable files: catch exception, return `parse_status=failed`.

### Group 4 — LLM Extraction
- [x] 4.1 Add Bedrock Haiku 4.5 implementation to `LLMProvider` interface.
- [x] 4.2 Implement `ExtractionService`: takes `ParsedDocument` + `DocumentType`, calls LLM with structured output schema, returns `ExtractedDocument`.
- [x] 4.3 Define extraction prompts per document type (bank statement, e-wallet, platform sales, receipt).
- [x] 4.4 Implement retry logic: 1 retry with stricter prompt on schema failure.
- [x] 4.5 Implement source pointer extraction: LLM returns page numbers / table refs alongside values.
- [x] 4.6 Handle extraction failure: mark `extraction_status=failed`, continue pipeline.

### Group 5 — Deterministic Validation
- [x] 5.1 Implement `RunningBalanceValidator`: checks that each transaction's balance = previous balance + amount.
- [x] 5.2 Implement `LineItemSumValidator`: checks that line items sum to stated total.
- [x] 5.3 Implement `DateContinuityValidator`: checks no gaps > 30 days in transaction dates (warning, not failure).
- [x] 5.4 Implement `ValidationService`: runs all validators, returns `ValidationResult`.
- [x] 5.5 Lower confidence on validation failures.

### Group 6 — LangGraph Pipeline (Full)
- [x] 6.1 Update `GraphState` to include `extracted_documents`, `validation_results`, `evidence_bundle`.
- [x] 6.2 Add nodes: `ingest`, `parse`, `extract`, `validate`, `human_review` (interrupt).
- [x] 6.3 Wire edges: ingest → parse → extract → validate → human_review → END.
- [x] 6.4 Add conditional interrupt: if confidence < 0.7 or validation failed → interrupt at human_review.
- [x] 6.5 Implement `run_pipeline(application) -> thread_id` and `resume_pipeline(thread_id, decision)`.
- [x] 6.6 Add Postgres checkpointer (replace MemorySaver for deployment).

### Group 7 — Background Processing
- [x] 7.1 Implement FastAPI `BackgroundTasks` integration: on application creation, queue pipeline run.
- [x] 7.2 Update application status during processing: `pending` → `processing` → `awaiting_review`.
- [x] 7.3 Handle pipeline errors: set status to `failed`, store error message.

### Group 8 — API Enhancements
- [x] 8.1 Update `GET /applications/{id}/status` to include confidence, validation results, extracted summary.
- [x] 8.2 Add `GET /applications/{id}/evidence` endpoint returning `EvidenceBundle`.
- [x] 8.3 Add `POST /applications/{id}/review` with concurrent-decision protection (409 on duplicate).
- [x] 8.4 Add multipart `POST /applications` accepting files inline.

### Group 9 — Streamlit Review UI (Full)
- [x] 9.1 Application list view with status badges.
- [x] 9.2 Application detail view: extracted fields, source pointers, validation results.
- [x] 9.3 Evidence viewer: per-document extracted transactions with source snippets.
- [x] 9.4 Approve / Deny / Counter buttons with notes input.
- [x] 9.5 Status polling (auto-refresh).

### Group 10 — Synthetic Data Generator (Extended)
- [x] 10.1 Extend `MerchantGenerator` to produce synthetic documents (bank PDFs, e-wallet CSVs, platform sales reports, receipts).
- [x] 10.2 Generate ground-truth labels for field-extraction accuracy measurement.
- [x] 10.3 Plant discrepancies: missing payouts, hidden fees, abnormal returns, deposit spikes, inflated revenue.
- [x] 10.4 Implement document generators per type with realistic data.

### Group 11 — Eval Harness
- [x] 11.1 Implement `EvalRunner`: runs pipeline on synthetic merchants, collects metrics.
- [x] 11.2 Measure field-extraction accuracy per document type (compare extracted vs ground truth).
- [x] 11.3 Measure discrepancy catch rate (% of planted problems flagged).
- [x] 11.4 Measure false-positive rate.
- [x] 11.5 Measure end-to-end upload-to-review time.
- [x] 11.6 Output eval report (JSON + markdown summary).

### Group 12 — Tests & Verification
- [x] 12.1 Unit tests for all validators.
- [x] 12.2 Unit tests for Docling parser (mock).
- [x] 12.3 Unit tests for extraction service (mock LLM).
- [x] 12.4 Integration tests for full pipeline (synthetic data).
- [x] 12.5 API integration tests (multipart upload, status, review, evidence).
- [x] 12.6 Eval harness test (runs on 3 merchants, checks metrics format).
- [x] 12.7 Run ruff, black, mypy — all clean.

### Group 13 — Verification & Polish
- [x] 13.1 Run full test suite; fix failures.
- [x] 13.2 Run eval harness on 10 synthetic merchants; document metrics.
- [x] 13.3 Update README with Phase 1 results.
- [x] 13.4 Tag release `v0.2.0-phase1`.
