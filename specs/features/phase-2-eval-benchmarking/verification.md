# Verification Scorecard — Phase 2: Agent Evaluation Harness & Benchmarking

## Feature
Phase 2 — Agent Evaluation Harness & Benchmarking

## Automated Tests
| Test | Location | What It Validates |
|---|---|---|
| Code graders | `backend/tests/test_phase2_evals.py` | Schema compliance, numeric accuracy, arithmetic check, source pointer check |
| LLM Judge dry-run | `backend/tests/test_phase2_evals.py` | Verifies zero live API/network calls are made when LLM judge is not enabled |
| Non-determinism metrics | `backend/tests/test_phase2_evals.py` | Correct math for `pass@k` and `pass^k` |
| Regression suite run | `evals.runner` | Regression suite achieves 100% pass rate |
| Capability suite run | `evals.runner` | Capability suite stress-tests edge cases and catches planted anomalies |

## Exit Criteria
- [x] Graders modularized in `evals/graders/`.
- [x] LLM judge implemented with zero-cost default (dry-run/mock).
- [x] Regression suite passes at 100%.
- [x] Capability suite stress tests noisy data & planted discrepancies.
- [x] `pass@k` and `pass^k` metrics computed and reported.
- [x] All unit and integration tests pass with coverage $\ge 80\%$.
- [x] `ruff`, `black`, and `mypy --strict` all exit 0.
- [x] Git commit and push to branch.
