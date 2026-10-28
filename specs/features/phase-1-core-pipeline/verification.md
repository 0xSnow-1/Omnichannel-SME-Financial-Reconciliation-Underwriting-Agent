# Verification Scorecard — Phase 1: MVP Core Pipeline

## Feature
Phase 1 — MVP: Core Pipeline (Application → Ingestion → Extraction → Validation → Human Review)

## Automated Tests

### Unit Tests (pytest)
| Test | Location | What It Validates |
|---|---|---|
| File validation | `tests/test_file_validation.py` | Type check, size check, count check; returns 422 on violations |
| File storage | `tests/test_file_storage.py` | Save file, return FileRef, cleanup on delete |
| Docling parser | `tests/test_docling_parser.py` | Parse text + tables; corrupt file → parse_status=failed |
| Running balance validator | `tests/test_validators.py::test_running_balance` | Correct balances pass; mismatch fails |
| Line item sum validator | `tests/test_validators.py::test_line_item_sum` | Correct sums pass; mismatch fails |
| Date continuity validator | `tests/test_validators.py::test_date_continuity` | Gaps > 30 days produce warning |
| Validation service | `tests/test_validation_service.py` | Runs all validators, returns ValidationResult |
| Extraction service | `tests/test_extraction.py` | Mock LLM returns structured output; retry on failure |
| LLM provider (Bedrock) | `tests/test_llm_provider.py` | Haiku 4.5 implementation behind interface |
| Graph pipeline | `tests/test_graph_pipeline.py` | Full graph runs to interrupt; state persists; resume works |
| Synthetic data gen | `tests/test_synthetic_docs.py` | Generates documents with ground truth labels |

### Integration Tests
| Test | Location | What It Validates |
|---|---|---|
| Multipart upload | `tests/test_api.py::test_multipart_upload` | `POST /applications` with files returns 201 + ID |
| File upload endpoint | `tests/test_api.py::test_file_upload` | `POST /applications/{id}/files` validates and stores |
| Status with evidence | `tests/test_api.py::test_status_evidence` | `GET /applications/{id}/status` includes confidence + validation |
| Evidence endpoint | `tests/test_api.py::test_evidence` | `GET /applications/{id}/evidence` returns EvidenceBundle |
| Review decision | `tests/test_api.py::test_review` | Approve/Deny/Counter updates status |
| Concurrent review | `tests/test_api.py::test_concurrent_review` | Second review returns 409 |
| End-to-end pipeline | `tests/test_e2e.py` | Upload → process → review-ready on synthetic data |
| Empty application | `tests/test_e2e.py::test_empty_app` | No files → still reaches awaiting_review |

### Eval Harness
| Metric | Target | How Measured |
|---|---|---|
| Field-extraction accuracy per doc type | ≥ 85% | Compare extracted fields vs ground truth labels |
| Discrepancy catch rate | ≥ 90% | % of planted problems flagged by validation |
| False-positive rate | < 10% | % of clean documents flagged incorrectly |
| End-to-end upload-to-review time | < 60s | Time from upload to awaiting_review status |

### Lint & Format
| Command | Expected |
|---|---|
| `ruff check backend/` | Exit 0 |
| `black --check backend/` | Exit 0 |
| `mypy backend/src` | Exit 0 |

### Type Check
| Command | Expected |
|---|---|
| `mypy backend/src --strict` | Exit 0 |

## Manual Validation

### End-to-End Smoke Test
1. Start services: `docker compose up -d`.
2. Generate synthetic merchant: `python -m evals.generate_merchant --seed 42`.
3. Upload documents via `POST /applications` (multipart).
4. Poll `GET /applications/{id}/status` until `awaiting_review`.
5. `GET /applications/{id}/evidence` — verify extracted fields + source pointers.
6. `POST /applications/{id}/review` with `{"decision": "approve"}`.
7. Verify status → `approved`.

### Eval Harness Run
1. `python -m evals.run --count 10 --seed 42`.
2. Verify output: accuracy per doc type, catch rate, FP rate, timing.
3. Check `evals/report.json` and `evals/report.md`.

### Docling Parsing
1. Upload a bank statement PDF.
2. Verify Docling extracts text + tables.
3. Verify cached parse on second request.

### LLM Extraction
1. Set `LLM_PROVIDER=bedrock-haiku` with valid AWS credentials.
2. Upload document, verify extracted fields match ground truth.
3. Test retry: simulate LLM returning invalid JSON, verify retry + failure handling.

## Runtime curl Checks
```bash
# Health
curl -s http://localhost:8000/health

# Create application with files
curl -s -X POST http://localhost:8000/applications \
  -F "merchant_name=Aling Rosa Sari-Sari Store" \
  -F "loan_amount=150000" \
  -F "files=@bank_statement.pdf" \
  -F "files=@ewallet_export.csv"

# Check status
curl -s http://localhost:8000/applications/{id}/status

# Get evidence
curl -s http://localhost:8000/applications/{id}/evidence

# Submit review
curl -s -X POST http://localhost:8000/applications/{id}/review \
  -H "Content-Type: application/json" \
  -d '{"decision": "approve", "notes": "All checks pass"}'
```

## Exit Criteria (Phase 1 Complete When All Pass)
- [ ] End-to-end flow works on ≥10 synthetic merchants.
- [ ] Field-extraction accuracy ≥ 85% per document type.
- [ ] ≥ 90% of planted discrepancies caught.
- [ ] False-positive rate < 10%.
- [ ] End-to-end upload-to-review < 60 seconds.
- [ ] Underwriter can approve/deny/counter via API and UI.
- [ ] All unit and integration tests pass.
- [ ] ruff, black, mypy all exit 0.
- [ ] CI pipeline green.
- [ ] Eval report documented with real metrics.
- [ ] README updated with Phase 1 results.
- [ ] Git tag `v0.2.0-phase1` created.
- [ ] PR opened and merged to main.