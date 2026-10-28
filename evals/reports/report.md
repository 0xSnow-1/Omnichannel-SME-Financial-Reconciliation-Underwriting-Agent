# SME Underwriting Copilot — Evaluation Report

Generated on: `2026-10-28T13:13:19Z`
Merchants Evaluated: `10` (Seed: `42`)

## Key Benchmark Metrics

| Metric | Target | Result | Status |
|---|---|---|---|
| **Field Extraction Accuracy** | >= 85% | **100.0%** | ✅ PASS |
| **Discrepancy Catch Rate** | >= 90% | **100.0%** | ✅ PASS |
| **False-Positive Rate** | < 10% | **0.0%** | ✅ PASS |
| **Average Latency** | < 60s | **0.009s** | ✅ PASS |

## Per-Merchant Scorecard

| Merchant | Expected Txns | Extracted Txns | Confidence | Validation Passed | Flags | Latency |
|---|---|---|---|---|---|---|
| Merchant-001 | 9 | 9 | 0.95 | ✅ | 0 | 0.016s |
| Merchant-002 | 8 | 8 | 0.95 | ✅ | 0 | 0.007s |
| Merchant-003 | 14 | 14 | 0.95 | ✅ | 0 | 0.009s |
| Merchant-004 | 12 | 12 | 0.60 | ⚠️ Flagged | 1 | 0.007s |
| Merchant-005 | 9 | 9 | 0.95 | ✅ | 0 | 0.007s |
| Merchant-006 | 13 | 13 | 0.95 | ✅ | 0 | 0.009s |
| Merchant-007 | 13 | 13 | 0.60 | ⚠️ Flagged | 1 | 0.008s |
| Merchant-008 | 9 | 9 | 0.60 | ⚠️ Flagged | 1 | 0.009s |
| Merchant-009 | 15 | 15 | 0.95 | ✅ | 0 | 0.009s |
| Merchant-010 | 11 | 11 | 0.95 | ✅ | 0 | 0.008s |
