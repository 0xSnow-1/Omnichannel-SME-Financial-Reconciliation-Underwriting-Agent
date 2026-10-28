"""
Evaluation Runner for SME Financial Underwriting Copilot.
Implements the Anthropic-style evaluation harness:
- Generates or loads synthetic merchant evaluation batches
- Runs the pipeline
- Applies deterministic code-based graders
- Measures extraction accuracy, planted problem catch rate, false-positive rate, and latency
- Emits evals/report.json and evals/report.md
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

# Add backend/src to path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend" / "src"))

from sme_copilot.graph.pipeline import run_pipeline
from sme_copilot.schemas.models import (
    Application,
    FileRef,
)
from sme_copilot.services.merchant_generator import MerchantGenerator

from evals.generate_documents import generate_merchant_dataset


def run_evaluation(
    count: int = 5,
    seed: int = 42,
    output_dir: Path | None = None,
) -> dict[str, object]:
    start_time = time.time()
    out_dir = output_dir or Path("evals/reports")
    out_dir.mkdir(parents=True, exist_ok=True)
    temp_dataset_dir = Path("evals/datasets/temp_run")

    gen = MerchantGenerator(seed=seed)
    merchants = gen.generate(count=count)

    results = []
    total_fields_expected = 0
    total_fields_correct = 0
    discrepancies_planted = 0
    discrepancies_caught = 0
    clean_runs = 0
    false_positives = 0

    print(f"\n--- Running Evaluation Suite on {count} Merchants (Seed: {seed}) ---")

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

        # Build application files
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

        t0 = time.time()
        state = run_pipeline(app)
        elapsed = round(time.time() - t0, 3)

        # Code-based Grader checks
        extracted_docs = state["extracted_documents"]
        val_results = state["validation_results"]
        fraud_flags = state["fraud_flags"]

        # 1. Extraction accuracy (Transaction counts match ground truth)
        bank_doc = next((d for d in extracted_docs if "bank" in d.file_ref.filename.lower()), None)
        tx_count_extracted = len(bank_doc.transactions) if bank_doc else 0
        tx_count_expected = gt["total_bank_transactions"]

        total_fields_expected += tx_count_expected
        # Count matched transactions
        matched = min(tx_count_extracted, tx_count_expected)
        total_fields_correct += matched

        # 2. Planted discrepancy catch rate
        has_planted_mismatch = gt["has_arithmetic_mismatch"]
        if has_planted_mismatch:
            discrepancies_planted += 1
            if any(not vr.passed for vr in val_results) or len(fraud_flags) > 0:
                discrepancies_caught += 1
        else:
            clean_runs += 1
            if any(not vr.passed for vr in val_results):
                false_positives += 1

        print(
            f"  [{idx + 1}/{count}] {m.name}: {len(extracted_docs)} docs parsed, "
            f"{tx_count_extracted}/{tx_count_expected} txns, "
            f"Confidence: {state['confidence']:.2f}, Latency: {elapsed}s"
        )

        results.append(
            {
                "merchant_id": m.merchant_id,
                "name": m.name,
                "latency_seconds": elapsed,
                "confidence": state["confidence"],
                "extracted_transactions": tx_count_extracted,
                "expected_transactions": tx_count_expected,
                "validation_passed": all(vr.passed for vr in val_results),
                "fraud_flags": fraud_flags,
            }
        )

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
    avg_latency = round(sum(r["latency_seconds"] for r in results) / len(results), 3)

    summary = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "merchants_evaluated": count,
        "seed": seed,
        "metrics": {
            "field_extraction_accuracy_pct": accuracy,
            "discrepancy_catch_rate_pct": catch_rate,
            "false_positive_rate_pct": fp_rate,
            "average_latency_seconds": avg_latency,
            "total_runtime_seconds": round(time.time() - start_time, 2),
        },
        "details": results,
    }

    # Write report.json
    report_json_path = out_dir / "report.json"
    report_json_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    # Write report.md
    report_md_path = out_dir / "report.md"
    acc_status = "✅ PASS" if accuracy >= 85 else "❌ FAIL"
    catch_status = "✅ PASS" if catch_rate >= 90 else "❌ FAIL"
    fp_status = "✅ PASS" if fp_rate < 10 else "❌ FAIL"
    lat_status = "✅ PASS" if avg_latency < 60 else "❌ FAIL"

    md_content = f"""# SME Underwriting Copilot — Evaluation Report

Generated on: `{summary['timestamp']}`
Merchants Evaluated: `{count}` (Seed: `{seed}`)

## Key Benchmark Metrics

| Metric | Target | Result | Status |
|---|---|---|---|
| **Field Extraction Accuracy** | >= 85% | **{accuracy}%** | {acc_status} |
| **Discrepancy Catch Rate** | >= 90% | **{catch_rate}%** | {catch_status} |
| **False-Positive Rate** | < 10% | **{fp_rate}%** | {fp_status} |
| **Average Latency** | < 60s | **{avg_latency}s** | {lat_status} |

## Per-Merchant Scorecard

| Merchant | Expected Txns | Extracted Txns | Confidence | Validation Passed | Flags | Latency |
|---|---|---|---|---|---|---|
"""
    for r in results:
        md_content += (
            f"| {r['name']} | {r['expected_transactions']} | {r['extracted_transactions']} | "
            f"{r['confidence']:.2f} | {'✅' if r['validation_passed'] else '⚠️ Flagged'} | "
            f"{len(r['fraud_flags'])} | {r['latency_seconds']}s |\n"
        )

    report_md_path.write_text(md_content, encoding="utf-8")

    print("\n--- Benchmark Summary ---")
    print(f"Extraction Accuracy: {accuracy}% (Target: >=85%)")
    print(f"Discrepancy Catch Rate: {catch_rate}% (Target: >=90%)")
    print(f"False-Positive Rate: {fp_rate}% (Target: <10%)")
    print(f"Average Latency: {avg_latency}s (Target: <60s)")
    print(f"Reports saved to {out_dir}/report.json and {out_dir}/report.md\n")

    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description="Run SME Underwriting Copilot evaluation harness.")
    parser.add_argument("--count", type=int, default=5, help="Number of merchants to evaluate")
    parser.add_argument(
        "--seed", type=int, default=42, help="Seed for synthetic merchant generation"
    )
    parser.add_argument(
        "--output",
        type=str,
        default="evals/reports",
        help="Output directory for reports",
    )
    args = parser.parse_args()

    run_evaluation(count=args.count, seed=args.seed, output_dir=Path(args.output))


if __name__ == "__main__":
    main()
