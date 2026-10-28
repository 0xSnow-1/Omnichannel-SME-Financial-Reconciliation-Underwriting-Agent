# Evaluation Plan: SME Financial Reconciliation and Underwriting Agent

This document gives the evaluation plan for the SME Underwriting Copilot project.
The plan follows the recommendations from the Anthropic research paper: "Demystifying Evals for AI Agents".
The language follows Simplified Technical English (ASD-STE100 principles) to keep instructions short, clear, and direct.

---

## 1. Objective

The objective is to measure the performance, accuracy, and reliability of the agent.
You must test the system with synthetic ground-truth data before you deploy the system to human underwriters.

---

## 2. Core Concepts

Every evaluation has three primary parts:

1. **The Task**: Input documents (PDF bank statement, CSV e-wallet log, sales reports) given to the agent.
2. **The Transcript**: The log of agent steps, tool calls, and text outputs during execution.
3. **The Outcome**: The final state (extracted data, validation results, credit score, review decision).

> **Rule**: Do not judge the agent only by what it writes. Check the final database state and the numbers.

---

## 3. Grader System

Use three levels of graders to score agent performance:

```
+-------------------------------------------------------------+
| Grader 1: Code-Based Graders (Fast, Low Cost, Deterministic)|
| - Validate Pydantic schema structure                        |
| - Compare numbers to ground-truth values                    |
| - Verify arithmetic checks (running balance, item sum)      |
+-------------------------------------------------------------+
                              |
                              v
+-------------------------------------------------------------+
| Grader 2: Model-Based Graders (LLM as Judge)                |
| - Score clarity and quality of risk summaries               |
| - Verify qualitative risk statements match calculated facts |
+-------------------------------------------------------------+
                              |
                              v
+-------------------------------------------------------------+
| Grader 3: Human Calibration (Gold Standard)                 |
| - Underwriters inspect false-positive and edge-case results |
| - Calibrate automated grader rules                          |
+-------------------------------------------------------------+
```

### Grader 1: Code-Based Graders
- Check if all required fields exist in the output schema.
- Compare extracted numbers with ground-truth labels using a tolerance of 0.01.
- Verify source pointers (page number, bounding box, text snippet).
- Cost: free and instant.

### Grader 2: Model-Based Graders (LLM-Judge)
- An independent model reviews the qualitative risk text written by the agent.
- Verify that the risk text does not contradict calculated financial values.
- Output score: 1 (Poor) to 5 (Accurate).

### Grader 3: Human Reviewer Calibration
- Human underwriters review 10% of test runs to confirm automated grader decisions.

---

## 4. Test Suites

Split all test cases into two groups:

### A. Capability Tests ("Can the agent solve difficult cases?")
- Test hard edge cases:
  1. Low-quality scans with noisy OCR text.
  2. Invoices with missing totals.
  3. Mismatched order IDs between sales logs and bank deposits.
  4. Planted fraud patterns (revenue inflation, circular cash transfers).
- Initial pass rate target: 60% to 70%.
- Use these tests to guide agent improvements.

### B. Regression Tests ("Did new changes break working features?")
- Test standard, clean merchant files.
- Run on every git commit and pull request.
- Target pass rate: 100%.

---

## 5. Metrics

| Metric | Target | Formula / Description |
|---|---|---|
| **Field Extraction Accuracy** | >= 85% | `(Correct Fields Extracted) / (Total Ground-Truth Fields)` |
| **Discrepancy Catch Rate** | >= 90% | `(Planted Discrepancies Caught) / (Total Planted Discrepancies)` |
| **False-Positive Rate** | < 10% | `(Clean Transactions Flagged as Errors) / (Total Clean Transactions)` |
| **Processing Latency** | < 60 seconds | Total duration from file upload to review interrupt |
| **Consistency (pass^3)** | >= 80% | Probability that the agent succeeds on 3 consecutive runs |

---

## 6. Synthetic Ground-Truth Dataset

Generate controlled test cases using `evals/generate_merchants.py`:

1. **Merchant 001 - 010**: Clean data (standard revenue, correct balances).
2. **Merchant 011 - 020**: Planted arithmetic errors (running balance mismatches).
3. **Merchant 021 - 030**: Reconciliation errors (missing payout references).
4. **Merchant 031 - 040**: Deposit spikes and hidden fee deductions.
5. **Merchant 041 - 050**: Document quality errors (rotated pages, corrupt formats).

Each test case contains:
- Raw input files (`.pdf`, `.csv`, `.png`).
- Ground-truth file: `expected_output.json`.

---

## 7. Step-by-Step Implementation Plan

### Step 1: Create the Test Harness Runner
- File: `evals/runner.py`.
- Action: Load synthetic merchant files, run the agent pipeline, record the transcript and final state.

### Step 2: Implement Code Graders
- File: `evals/graders/code_graders.py`.
- Action: Write exact comparison functions for:
  - Total revenue.
  - Transaction count.
  - Running balance continuity.
  - Source pointer correctness.

### Step 3: Implement LLM Judge
- File: `evals/graders/llm_judge.py`.
- Action: Write prompt for judging the underwriter narrative summary against calculated figures.

### Step 4: Add Automated Reporting
- File: `evals/reporter.py`.
- Output: Generate `evals/report.json` and a readable `evals/report.md` with pass/fail tables and metric cards.

### Step 5: Integrate into Continuous Integration (CI)
- Add GitHub Actions step to run regression evals on every PR.

---

## 8. Command Line Usage

Run the complete evaluation suite:
```bash
python -m evals.runner --dataset evals/datasets/synthetic_v1 --output evals/reports/
```

Run only regression tests:
```bash
python -m evals.runner --type regression --seed 42
```

Run capability stress tests:
```bash
python -m evals.runner --type capability --iterations 3
```
