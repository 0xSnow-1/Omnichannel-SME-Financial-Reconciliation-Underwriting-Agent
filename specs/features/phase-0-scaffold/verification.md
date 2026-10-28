# Verification Scorecard — Phase 0: Scaffold & Foundations

## Feature
Phase 0 — Scaffold & Foundations

## Automated Tests

### Unit Tests (pytest)
| Test | Location | What It Validates |
|---|---|---|
| Schema round-trip | `tests/test_schemas.py` | All Pydantic schemas serialize → deserialize without data loss |
| LLM provider interface | `tests/test_llm_provider.py` | `LLMProvider` protocol; `StubLLMProvider` returns canned responses; factory reads env var |
| Connector interface | `tests/test_connector.py` | `FileConnector` reads local files; protocol compliance |
| KYC stub | `tests/test_kyc.py` | Pass, fail, env default, per-request override |
| Merchant generator | `tests/test_merchant_generator.py` | Count, true_revenue presence, planted problems in range, seed reproducibility |
| Hash chain | `tests/test_audit_hash.py` | Hash computation correct; tamper detection (modified entry breaks chain) |
| Graph skeleton | `tests/test_graph.py` | Graph runs to interrupt; state persists in Postgres; resume with decision works |

### Integration Tests
| Test | Location | What It Validates |
|---|---|---|
| API health | `tests/test_api.py::test_health` | `GET /health` returns 200 |
| Create application | `tests/test_api.py::test_create_application` | `POST /applications` returns 201 + application ID |
| Application status | `tests/test_api.py::test_application_status` | `GET /applications/{id}/status` returns `awaiting_review` |
| Review decision | `tests/test_api.py::test_review_decision` | `POST /applications/{id}/review` resumes graph with Approve/Deny/Counter |
| File upload validation | `tests/test_api.py::test_file_upload` | Valid files accepted; oversized/invalid types return 422 |
| Idempotency | `tests/test_api.py::test_idempotency` | Duplicate idempotency key returns existing application |

### Lint & Format
| Command | Expected |
|---|---|
| `ruff check .` | Exit 0, no warnings |
| `black --check .` | Exit 0, no reformatting needed |
| `mypy backend/` | Exit 0, strict mode |

### Type Check
| Command | Expected |
|---|---|
| `mypy backend/ --strict` | Exit 0 |

## Manual Validation

### Docker Compose
1. Run `docker compose up -d`.
2. Wait 30 seconds.
3. `curl -s http://localhost:8000/health` → expect `{"status": "ok"}`.
4. `curl -s http://localhost:8501` → Streamlit UI loads.
5. `docker compose down` cleans up without errors.

### End-to-End Smoke Test
1. `POST /applications` with body `{"merchant_name": "Test Merchant", "loan_amount": 100000}`.
2. Verify response: 201, `id` field present.
3. `GET /applications/{id}/status` → `{"status": "awaiting_review"}`.
4. `POST /applications/{id}/review` with body `{"decision": "approve"}`.
5. `GET /applications/{id}/status` → `{"status": "approved"}`.

### Synthetic Merchant Generator
1. Run `python -m evals.generate_merchants --count 10 --seed 42`.
2. Verify output: 10 merchants, each with `true_revenue` > 0 and `planted_problems` non-empty.
3. Re-run with same seed → identical output (determinism).

### KYC Stub
1. Set `KYC_STUB_RESULT=fail` in `.env`.
2. Submit application → status should reflect KYC failure (if wired in graph) or KYC result in response.
3. Set `KYC_STUB_RESULT=pass` → application proceeds to review.

## Runtime curl Checks
```bash
# Health
curl -s http://localhost:8000/health

# Create application
curl -s -X POST http://localhost:8000/applications \
  -H "Content-Type: application/json" \
  -d '{"merchant_name": "Aling Rosa Sari-Sari Store", "loan_amount": 150000}'

# Check status (replace {id})
curl -s http://localhost:8000/applications/{id}/status

# Submit review decision (replace {id})
curl -s -X POST http://localhost:8000/applications/{id}/review \
  -H "Content-Type: application/json" \
  -d '{"decision": "approve", "notes": "Looks good"}'

# File upload (replace {id})
curl -s -X POST http://localhost:8000/applications/{id}/files \
  -F "file=@sample.pdf"
```

## CI Verification
1. Push branch to GitHub.
2. Verify CI workflow triggers.
3. All jobs (lint, format, type-check, test) pass.
4. Coverage report ≥ 80%.

## Exit Criteria (Phase 0 Complete When All Pass)
- [ ] `docker compose up` starts all 3 services without errors.
- [ ] `GET /health` returns 200 within 30s of startup.
- [ ] Empty application reaches `awaiting_review` state.
- [ ] Synthetic generator produces ≥10 merchants with verifiable true revenue and planted problems.
- [ ] All unit and integration tests pass.
- [ ] ruff, black, mypy all exit 0.
- [ ] CI pipeline green.
- [ ] README updated with Phase 0 completion status.
- [ ] Git tag `v0.1.0-phase0` created.