# Requirements — Phase 2: Agent Evaluation Harness & Benchmarking (Anthropic EDD Framework)

## Feature Name
Phase 2 — Agent Evaluation Harness & Benchmarking

## Scope
Implement a complete evaluation and benchmarking infrastructure modeled after Anthropic's "Demystifying Evals for AI Agents". The framework enables Evaluation-Driven Development (EDD) with three-tier graders (Code, Model-Judge, Human Calibration), capability vs. regression test suites, non-determinism metrics (`pass@k`, `pass^k`), and automated scorecard reporting.

### In Scope
1. **Three-Tier Grader Architecture**:
   - Code-based deterministic graders: Schema compliance, numeric accuracy, arithmetic integrity, source pointer validity.
   - Model-based grader (LLM-as-Judge): Structured prompt and rubric evaluating qualitative risk narratives against computed numbers. **Constraint**: Disabled by default / dry-run mode to avoid unwanted token costs; requires explicit CLI opt-in.
   - Human calibration protocol: Schema and recording mechanism for underwriter spot-checks and rubric calibration.
2. **Capability vs. Regression Suites**:
   - Regression suite: High-confidence baseline cases that must maintain a 100% pass rate across releases.
   - Capability suite: Stress tests covering noisy text, missing line items, planted fraud, deposit spikes, and revenue inflation.
3. **Statistical Metrics for Non-Determinism**:
   - `pass@k`: Probability of at least 1 success in $k$ attempts.
   - `pass^k`: Probability of consistent success across all $k$ attempts.
   - Field extraction accuracy %, discrepancy catch rate %, false-positive rate %, latency percentiles.
4. **Automated Benchmark Reporting**:
   - Machine-readable `report.json` and underwriter-friendly `report.md` scorecards.

### Out of Scope (Explicit Non-Requirements)
- Executing live, paid LLM calls for LLM-as-judge during automated tests or default runs (must remain opt-in / dry-run).
- Cross-source multi-platform reconciliation engine (Phase 3).
- Tamper-evident hash chain audit export for credit committee (Phase 3).
- Real OAuth platform connectors (Phase 4).

## Functional Acceptance Criteria
1. `evals/graders/` module provides modular graders: `SchemaComplianceGrader`, `NumericAccuracyGrader`, `ArithmeticIntegrityGrader`, `SourcePointerGrader`, and `LLMJudgeGrader`.
2. `LLMJudgeGrader` defaults to dry-run / mock evaluation unless `--enable-llm-judge` is explicitly provided.
3. `evals.runner` supports `--suite {regression,capability,all}`, `--iterations K`, and `--seed`.
4. Statistical calculator correctly computes `pass@k` and `pass^k` over $k$ iterations.
5. All automated unit and integration tests pass with $\ge 80\%$ test coverage.
6. `ruff check .`, `black --check .`, and `mypy backend/src --strict` exit 0 without warnings.
