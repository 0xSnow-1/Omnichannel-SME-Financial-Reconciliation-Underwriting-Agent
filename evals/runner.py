"""
Evaluation Runner for SME Financial Underwriting Copilot.
Implements the Anthropic-style evaluation harness:
- Generates or loads synthetic merchant evaluation batches
- Supports Capability vs Regression suites
- Applies 3-Tier Graders: Schema, Numeric, Arithmetic, Source Pointer, LLM-Judge (dry-run)
- Computes non-determinism metrics: pass@k and pass^k
- Emits evals/reports/report.json and report.md
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any

# Add backend/src to path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend" / "src"))

from sme_copilot.graph.pipeline import run_pipeline
from sme_copilot.schemas.models import Application, FileRef, ProblemType
from sme_copilot.services.merchant_generator import MerchantGenerator

from evals.generate_documents import generate_merchant_dataset
from evals.graders.code_graders import (
    ArithmeticIntegrityGrader,
    NumericAccuracyGrader,
    SchemaComplianceGrader,
    SourcePointerGrader,
)
from evals.graders.llm_judge import LLMJudgeGrader
from evals.metrics import calculate_pass_at_k, calculate_pass_pow_k


def run_evaluation(
    count: int = 5,
    seed: int = 42,
    suite: str = "all",  # "regression", "capability", or "all"
    iterations: int = 1,
    enable_llm_judge: bool = False,
    output_dir: Path | None = None,
) -> dict[str, Any]:
    start_time = time.time()
    out_dir = output_dir or Path("evals/reports")
    out_dir.mkdir(parents=True, exist_ok=True)
    temp_dataset_dir = Path("evals/datasets/temp_run")

    # Initialize Graders
    graders = [
        SchemaComplianceGrader(),
        NumericAccuracyGrader(),
        ArithmeticIntegrityGrader(),
        SourcePointerGrader(),
        LLMJudgeGrader(enabled=enable_llm_judge),
    ]

    # Generate merchants according to suite
    gen = MerchantGenerator(seed=seed)
    if suite == "regression":
        # Regression suite: clean, zero planted problems
        merchants = gen.generate(count=count, problem_types=[])
        for m in merchants:
            m.planted_problems = []
    elif suite == "capability":
        # Capability suite: stress cases with planted discrepancies
        stress_problems = [
            ProblemType.HIDDEN_FEE,
            ProblemType.DEPOSIT_SPIKE,
            ProblemType.INFLATED_REVENUE,
        ]
        merchants = gen.generate(
            count=count, problem_types=stress_problems, problems_per_merchant=(1, 3)
        )
    else:
        # Standard balanced distribution
        merchants = gen.generate(count=count)

    judge_status = "ENABLED" if enable_llm_judge else "OFF (Zero Cost)"
    print(
        f"\n--- Running Evaluation: {count} Merchants | Suite: {suite.upper()} | "
        f"Iterations: {iterations} | LLM Judge: {judge_status} ---"
    )

    all_merchant_records = []
    passed_runs_count = 0
    total_runs_count = 0

    total_fields_expected = 0
    total_fields_correct = 0
    discrepancies_planted = 0
    discrepancies_caught = 0
    clean_runs = 0
    false_positives = 0

    for idx, m in enumerate(merchants):
        m_dir = temp_dataset_dir / f"merchant_{idx + 1:03d}"
        gt = generate_merchant_dataset(
            merchant_id=m.merchant_id,
            name=m.name,
            true_revenue=m.true_revenue,
            planted_problems=m.planted_problems,
            output_dir=m_dir,
            seed=seed + idx,
        )

        files = []
        for file_path in [m_dir / "bank_statement.csv", m_dir / "ewallet_export.csv"]:
            if file_path.exists():
                files.append(
                    FileRef(
                        filename=file_path.name,
                        content_type="text/csv",
                        size_bytes=file_path.stat().st_size,
                        storage_path=str(file_path),
                    )
                )

        app = Application(
            merchant_name=m.name,
            loan_amount=round(m.true_revenue * 0.3, 2),
            files=files,
        )

        merchant_iter_passes = 0
        latest_grades = []
        iter_latencies = []

        for _ in range(iterations):
            total_runs_count += 1
            t0 = time.time()
            state = run_pipeline(app)
            elapsed = round(time.time() - t0, 3)
            iter_latencies.append(elapsed)

            # Grade with all graders
            grades = [g.grade(state, gt) for g in graders]
            latest_grades = grades

            all_passed = all(g.passed for g in grades)
            if all_passed:
                merchant_iter_passes += 1
                passed_runs_count += 1

        # Accuracy & Discrepancy stats
        extracted_docs = state["extracted_documents"]
        val_results = state["validation_results"]
        fraud_flags = state["fraud_flags"]

        bank_doc = next((d for d in extracted_docs if "bank" in d.file_ref.filename.lower()), None)
        tx_count_extracted = len(bank_doc.transactions) if bank_doc else 0
        tx_count_expected = gt["total_bank_transactions"]
        total_fields_expected += tx_count_expected
        total_fields_correct += min(tx_count_extracted, tx_count_expected)

        if gt["has_arithmetic_mismatch"]:
            discrepancies_planted += 1
            if any(not vr.passed for vr in val_results) or len(fraud_flags) > 0:
                discrepancies_caught += 1
        else:
            clean_runs += 1
            if any(not vr.passed for vr in val_results):
                false_positives += 1

        avg_lat = round(sum(iter_latencies) / len(iter_latencies), 3)
        print(
            f"  [{idx + 1}/{count}] {m.name}: {tx_count_extracted}/{tx_count_expected} txns | "
            f"Pass: {merchant_iter_passes}/{iterations} | Latency: {avg_lat}s | "
            f"Grades: {[f'{g.grader_name}:{round(g.score, 2)}' for g in latest_grades]}"
        )

        all_merchant_records.append(
            {
                "merchant_id": m.merchant_id,
                "name": m.name,
                "suite": suite,
                "latency_seconds": avg_lat,
                "confidence": state["confidence"],
                "extracted_transactions": tx_count_extracted,
                "expected_transactions": tx_count_expected,
                "iterations_passed": merchant_iter_passes,
                "total_iterations": iterations,
                "grades": [g.model_dump() for g in latest_grades],
                "fraud_flags": fraud_flags,
            }
        )

    # Statistical Metrics
    overall_pass_rate = passed_runs_count / total_runs_count if total_runs_count > 0 else 0.0
    k_metric = min(iterations, 3) if iterations > 1 else 1
    pass_at_k = calculate_pass_at_k(total_runs_count, passed_runs_count, k_metric)
    pass_pow_k = calculate_pass_pow_k(overall_pass_rate, k_metric)

    accuracy = (
        round((total_fields_correct / total_fields_expected) * 100, 2)
        if total_fields_expected > 0
        else 100.0
    )
    catch_rate = (
        round((discrepancies_caught / discrepancies_planted) * 100, 2)
        if discrepancies_planted > 0
        else 100.0
    )
    fp_rate = round((false_positives / clean_runs) * 100, 2) if clean_runs > 0 else 0.0
    avg_total_lat = round(
        sum(r["latency_seconds"] for r in all_merchant_records) / len(all_merchant_records), 3
    )

    summary: dict[str, Any] = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "suite": suite,
        "merchants_evaluated": count,
        "iterations_per_merchant": iterations,
        "llm_judge_enabled": enable_llm_judge,
        "metrics": {
            "field_extraction_accuracy_pct": accuracy,
            "discrepancy_catch_rate_pct": catch_rate,
            "false_positive_rate_pct": fp_rate,
            "single_run_pass_rate": round(overall_pass_rate, 4),
            f"pass@{k_metric}": pass_at_k,
            f"pass^{k_metric}": pass_pow_k,
            "average_latency_seconds": avg_total_lat,
            "total_runtime_seconds": round(time.time() - start_time, 2),
        },
        "graders_used": [g.name for g in graders],
        "details": all_merchant_records,
    }

    # Write JSON Report
    report_json_path = out_dir / "report.json"
    report_json_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    # Write Markdown Report
    report_md_path = out_dir / "report.md"
    acc_status = "✅ PASS" if accuracy >= 85 else "❌ FAIL"
    catch_status = "✅ PASS" if catch_rate >= 90 else "❌ FAIL"
    fp_status = "✅ PASS" if fp_rate < 10 else "❌ FAIL"
    lat_status = "✅ PASS" if avg_total_lat < 60 else "❌ FAIL"

    pass_k_status = "✅ PASS" if pass_at_k >= 0.95 else "⚠️ REVIEW"
    pass_pow_status = "✅ PASS" if pass_pow_k >= 0.8 else "⚠️ REVIEW"

    md_content = f"""# SME Underwriting Copilot — Phase 2 Evaluation Report

Generated on: `{summary['timestamp']}`
Suite: `{suite.upper()}` | Merchants: `{count}` | Iterations: `{iterations}`
LLM Judge: `{'ENABLED' if enable_llm_judge else 'OFF (Zero Cost)'}`

## Benchmark Metrics (Anthropic EDD Framework)

| Metric | Target | Result | Status |
|---|---|---|---|
| **Field Extraction Accuracy** | >= 85% | **{accuracy}%** | {acc_status} |
| **Discrepancy Catch Rate** | >= 90% | **{catch_rate}%** | {catch_status} |
| **False-Positive Rate** | < 10% | **{fp_rate}%** | {fp_status} |
| **pass@{k_metric} (At least 1 pass)** | >= 95% | **{pass_at_k:.1%}** | {pass_k_status} |
| **pass^{k_metric} (Consistent pass)** | >= 80% | **{pass_pow_k:.1%}** | {pass_pow_status} |
| **Average Latency** | < 60s | **{avg_total_lat}s** | {lat_status} |

## Active Grader Status
"""
    for g in graders:
        md_content += f"- **{g.name}** (`{g.grader_type}`): Active\n"

    md_content += """
## Per-Merchant Scorecard

| Merchant | Expected Txns | Extracted Txns | Confidence | Iterations Passed | Latency |
|---|---|---|---|---|---|
"""
    for r in all_merchant_records:
        n_pass = r["iterations_passed"]
        n_tot = r["total_iterations"]
        md_content += (
            f"| {r['name']} | {r['expected_transactions']} | {r['extracted_transactions']} | "
            f"{r['confidence']:.2f} | {n_pass}/{n_tot} | {r['latency_seconds']}s |\n"
        )

    report_md_path.write_text(md_content, encoding="utf-8")

    print("\n--- Phase 2 Benchmark Summary ---")
    print(f"Extraction Accuracy: {accuracy}% (Target: >=85%)")
    print(f"Discrepancy Catch Rate: {catch_rate}% (Target: >=90%)")
    print(f"False-Positive Rate: {fp_rate}% (Target: <10%)")
    print(f"pass@{k_metric}: {pass_at_k:.1%} | pass^{k_metric}: {pass_pow_k:.1%}")
    print(f"Average Latency: {avg_total_lat}s")
    print(f"Reports saved to {out_dir}/report.json and {out_dir}/report.md\n")

    return summary


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run SME Underwriting Copilot Anthropic-style evaluation harness."
    )
    parser.add_argument("--count", type=int, default=5, help="Number of merchants to evaluate")
    parser.add_argument(
        "--seed", type=int, default=42, help="Seed for synthetic merchant generation"
    )
    parser.add_argument(
        "--suite",
        type=str,
        default="all",
        choices=["regression", "capability", "all"],
        help="Evaluation suite to execute",
    )
    parser.add_argument(
        "--iterations",
        type=int,
        default=1,
        help="Number of iterations per merchant (for pass@k and pass^k)",
    )
    parser.add_argument(
        "--enable-llm-judge",
        action="store_true",
        default=False,
        help="Enable live LLM judge calls (default is False/dry-run to avoid token costs)",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="evals/reports",
        help="Output directory for reports",
    )
    args = parser.parse_args()

    run_evaluation(
        count=args.count,
        seed=args.seed,
        suite=args.suite,
        iterations=args.iterations,
        enable_llm_judge=args.enable_llm_judge,
        output_dir=Path(args.output),
    )


if __name__ == "__main__":
    main()
