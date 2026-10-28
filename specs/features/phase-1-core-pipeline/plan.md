# Implementation Plan — Phase 1: MVP Core Pipeline

## Feature
Phase 1 — MVP: Core Pipeline (Application → Ingestion → Extraction → Validation → Human Review)

## LLM Provider
Claude Haiku 4.5 via AWS Bedrock, behind `LLMProvider` interface (from Phase 0).

## Sequential Task Checklist

### Group 1 — Extended Schemas
- [ ] 1.1 Add `DocumentType` enum: `bank_statement`, `ewallet_export`, `platform_sales`, `receipt`.
- [ ] 1.2 Add `TransactionLine` schema: `date`, `description`, `amount`, `balance`, `source_pointer`.
- [ ] 1.3 Add `ExtractedDocument` schema: `application_id`, `file_ref`, `document_type`, `transactions: list[TransactionLine]`, `summary_fields: dict`, `confidence`, `source_pointers`, `extraction_status` (success/failed).
- [ ] 1.4 Add `ValidationCheck` enum: `running_balance`, `line_item_sum`, `date_continuity`.
- [ ] 1.5 Add `ProcessingStatus` enum: `pending`, `processing`, `awaiting_review`, `approved`, `denied`, `countered`, `failed`.
- [ ] 1.6 Update `Application` schema: add `processing_status`, `extracted_documents: list[ExtractedDocument]`, `validation_results: list[ValidationResult]`.
- [ ] 1.7 Add `EvidenceBundle` schema: `application_id`, `documents: list[ExtractedDocument]`, `validation_results`, `confidence`, `fraud_flags`.

### Group 2 — File Ingestion & Storage
- [ ] 2.1 Implement `FileStorage` service: save uploaded file to local disk (`data/uploads/{app_id}/`), return `FileRef`.
- [ ] 2.2 Implement file validation: type check (PDF/CSV/XLSX/PNG/JPG), size check (≤25MB), count check (≤5).
- [ ] 2.3 Add `POST /applications/{id}/files` endpoint (multipart upload) with validation.
- [ ] 2.4 Add `POST /applications` multipart variant accepting files inline.
- [ ] 2.5 Implement storage cleanup on application deletion.

### Group 3 — Docling Parser
- [ ] 3.1 Add `docling` dependency to pyproject.toml.
- [ ] 3.2 Implement `DoclingParser` service: `parse(file_path) -> ParsedDocument` with text + tables.
- [ ] 3.3 Define `ParsedDocument` schema: `text: str`, `tables: list[TableData]`, `page_count`, `parse_status`.
- [ ] 3.4 Implement parse caching (disk cache keyed by file hash).
- [ ] 3.5 Handle corrupt/unreadable files: catch exception, return `parse_status=failed`.

### Group 4 — LLM Extraction
- [ ] 4.1 Add Bedrock Haiku 4.5 implementation to `LLMProvider` interface.
- [ ] 4.2 Implement `ExtractionService`: takes `ParsedDocument` + `DocumentType`, calls LLM with structured output schema, returns `ExtractedDocument`.
- [ ] 4.3 Define extraction prompts per document type (bank statement, e-wallet, platform sales, receipt).
- [ ] 4.4 Implement retry logic: 1 retry with stricter prompt on schema failure.
- [ ] 4.5 Implement source pointer extraction: LLM returns page numbers / table refs alongside values.
- [ ] 4.6 Handle extraction failure: mark `extraction_status=failed`, continue pipeline.

### Group 5 — Deterministic Validation
- [ ] 5.1 Implement `RunningBalanceValidator`: checks that each transaction's balance = previous balance + amount.
- [ ] 5.2 Implement `LineItemSumValidator`: checks that line items sum to stated total.
- [ ] 5.3 Implement `DateContinuityValidator`: checks no gaps > 30 days in transaction dates (warning, not failure).
- [ ] 5.4 Implement `ValidationService`: runs all validators, returns `ValidationResult`.
- [ ] 5.5 Lower confidence on validation failures.

### Group 6 — LangGraph Pipeline (Full)
- [ ] 6.1 Update `GraphState` to include `extracted_documents`, `validation_results`, `evidence_bundle`.
- [ ] 6.2 Add nodes: `ingest`, `parse`, `extract`, `validate`, `human_review` (interrupt).
- [ ] 6.3 Wire edges: ingest → parse → extract → validate → human_review → END.
- [ ] 6.4 Add conditional interrupt: if confidence < 0.7 or validation failed → interrupt at human_review.
- [ ] 6.5 Implement `run_pipeline(application) -> thread_id` and `resume_pipeline(thread_id, decision)`.
- [ ] 6.6 Add Postgres checkpointer (replace MemorySaver for deployment).

### Group 7 — Background Processing
- [ ] 7.1 Implement FastAPI `BackgroundTasks` integration: on application creation, queue pipeline run.
- [ ] 7.2 Update application status during processing: `pending` → `processing` → `awaiting_review`.
- [ ] 7.3 Handle pipeline errors: set status to `failed`, store error message.

### Group 8 — API Enhancements
- [ ] 8.1 Update `GET /applications/{id}/status` to include confidence, validation results, extracted summary.
- [ ] 8.2 Add `GET /applications/{id}/evidence` endpoint returning `EvidenceBundle`.
- [ ] 8.3 Add `POST /applications/{id}/review` with concurrent-decision protection (409 on duplicate).
- [ ] 8.4 Add multipart `POST /applications` accepting files inline.

### Group 9 — Streamlit Review UI (Full)
- [ ] 9.1 Application list view with status badges.
- [ ] 9.2 Application detail view: extracted fields, source pointers, validation results.
- [ ] 9.3 Evidence viewer: per-document extracted transactions with source snippets.
- [ ] 9.4 Approve / Deny / Counter buttons with notes input.
- [ ] 9.5 Status polling (auto-refresh).

### Group 10 — Synthetic Data Generator (Extended)
- [ ] 10.1 Extend `MerchantGenerator` to produce synthetic documents (bank PDFs, e-wallet CSVs, platform sales reports, receipts).
- [ ] 10.2 Generate ground-truth labels for field-extraction accuracy measurement.
- [ ] 10.3 Plant discrepancies: missing payouts, hidden fees, abnormal returns, deposit spikes, inflated revenue.
- [ ] 10.4 Implement document generators per type with realistic data.

### Group 11 — Eval Harness
- [ ] 11.1 Implement `EvalRunner`: runs pipeline on synthetic merchants, collects metrics.
- [ ] 11.2 Measure field-extraction accuracy per document type (compare extracted vs ground truth).
- [ ] 11.3 Measure discrepancy catch rate (% of planted problems flagged).
- [ ] 11.4 Measure false-positive rate.
- [ ] 11.5 Measure end-to-end upload-to-review time.
- [ ] 11.6 Output eval report (JSON + markdown summary).

### Group 12 — Tests & Verification
- [ ] 12.1 Unit tests for all validators.
- [ ] 12.2 Unit tests for Docling parser (mock).
- [ ] 12.3 Unit tests for extraction service (mock LLM).
- [ ] 12.4 Integration tests for full pipeline (synthetic data).
- [ ] 12.5 API integration tests (multipart upload, status, review, evidence).
- [ ] 12.6 Eval harness test (runs on 3 merchants, checks metrics format).
- [ ] 12.7 Run ruff, black, mypy — all clean.

### Group 13 — Verification & Polish
- [ ] 13.1 Run full test suite; fix failures.
- [ ] 13.2 Run eval harness on 10 synthetic merchants; document metrics.
- [ ] 13.3 Update README with Phase 1 results.
- [ ] 13.4 Tag release `v0.2.0-phase1`.

## Implementation Order
Groups 1 (schemas) → 2 (ingestion) → 3 (Docling) → 4 (extraction) → 5 (validation) → 6 (graph) → 7 (background) → 8 (API) → 9 (UI) → 10 (synthetic data) → 11 (eval) → 12 (tests) → 13 (polish).
Groups 3, 4, 5 can be parallelized after Group 2.
Groups 9, 10 can be parallelized after Group 8.