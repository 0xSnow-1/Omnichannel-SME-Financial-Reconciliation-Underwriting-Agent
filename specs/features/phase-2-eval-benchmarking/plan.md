# Implementation Plan — Phase 2: Agent Evaluation Harness & Benchmarking

## Feature
Phase 2 — Agent Evaluation Harness & Benchmarking (Anthropic EDD Framework)

## Sequential Task Checklist

### Group 1 — Grader Architecture (`evals/graders/`)
- [x] 1.1 Create `evals/graders/base.py`: Define `BaseGrader` interface and `GradingResult` schema.
- [x] 1.2 Implement `evals/graders/code_graders.py`:
  - `SchemaComplianceGrader`
  - `NumericAccuracyGrader`
  - `ArithmeticIntegrityGrader`
  - `SourcePointerGrader`
- [x] 1.3 Implement `evals/graders/llm_judge.py`:
  - Structured evaluation prompt (Clarity, Fact-grounding, Hallucination check).
  - Dry-run / mock by default (Zero API cost constraint).
  - Explicit activation toggle (`enabled: bool = False`).
- [x] 1.4 Implement `evals/graders/human_calibration.py`:
  - Record underwriter spot-check decisions and rubric calibration scores.

### Group 2 — Capability & Regression Test Suites
- [x] 2.1 Define dataset generator for capability edge cases (noisy OCR text, missing totals, multi-currency notes).
- [x] 2.2 Define regression dataset generator (clean merchants, guaranteed deterministic pass).
- [x] 2.3 Implement statistical calculator for `pass@k` and `pass^k`.

### Group 3 — Evaluation Runner & CLI Enhancements
- [x] 3.1 Upgrade `evals/runner.py` with multi-suite execution (`--suite regression|capability|all`).
- [x] 3.2 Add multi-iteration support (`--iterations K`) for non-determinism scoring (`pass@k`, `pass^k`).
- [x] 3.3 Add `--enable-llm-judge` flag (defaults to `False`).
- [x] 3.4 Produce structured JSON report and Markdown benchmark scorecard.

### Group 4 — Tests & Verification
- [x] 4.1 Unit tests for all code graders in `backend/tests/test_phase2_evals.py`.
- [x] 4.2 Unit tests verifying LLM Judge does NOT make network calls in default/test mode.
- [x] 4.3 Unit tests for `pass@k` and `pass^k` metric algorithms.
- [x] 4.4 Run full regression & capability suites.
- [x] 4.5 Ensure `ruff`, `black`, and `mypy --strict` pass.
