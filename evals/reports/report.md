# SME Underwriting Copilot — Phase 2 Evaluation Report

Generated on: `2026-10-28T13:52:00Z`
Suite: `CAPABILITY` | Merchants: `5` | Iterations: `2`
LLM Judge: `OFF (Zero Cost)`

## Benchmark Metrics (Anthropic EDD Framework)

| Metric | Target | Result | Status |
|---|---|---|---|
| **Field Extraction Accuracy** | >= 85% | **100.0%** | ✅ PASS |
| **Discrepancy Catch Rate** | >= 90% | **100.0%** | ✅ PASS |
| **False-Positive Rate** | < 10% | **0.0%** | ✅ PASS |
| **pass@2 (At least 1 pass)** | >= 95% | **100.0%** | ✅ PASS |
| **pass^2 (Consistent pass)** | >= 80% | **100.0%** | ✅ PASS |
| **Average Latency** | < 60s | **0.009s** | ✅ PASS |

## Active Grader Status
- **schema_compliance** (`code`): Active
- **numeric_accuracy** (`code`): Active
- **arithmetic_integrity** (`code`): Active
- **source_pointer_validity** (`code`): Active
- **llm_qualitative_judge** (`model`): Active

## Per-Merchant Scorecard

| Merchant | Expected Txns | Extracted Txns | Confidence | Iterations Passed | Latency |
|---|---|---|---|---|---|
| Merchant-001 | 9 | 9 | 0.95 | 2/2 | 0.014s |
| Merchant-002 | 8 | 8 | 0.60 | 2/2 | 0.009s |
| Merchant-003 | 14 | 14 | 0.60 | 2/2 | 0.008s |
| Merchant-004 | 12 | 12 | 0.60 | 2/2 | 0.009s |
| Merchant-005 | 9 | 9 | 0.60 | 2/2 | 0.007s |
