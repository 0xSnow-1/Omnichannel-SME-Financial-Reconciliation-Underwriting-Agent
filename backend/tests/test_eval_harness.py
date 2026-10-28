from pathlib import Path

from sme_copilot.schemas.models import ProblemType

from evals.generate_documents import generate_merchant_dataset
from evals.runner import run_evaluation


def test_generate_merchant_dataset(tmp_path: Path):
    out_dir = tmp_path / "merchant_test"
    gt = generate_merchant_dataset(
        merchant_id="m-123",
        name="Test Merchant",
        true_revenue=150000.0,
        planted_problems=[ProblemType.DEPOSIT_SPIKE],
        output_dir=out_dir,
        seed=1,
    )

    assert (out_dir / "bank_statement.csv").exists()
    assert (out_dir / "ewallet_export.csv").exists()
    assert (out_dir / "ground_truth.json").exists()
    assert gt["total_bank_transactions"] > 0
    assert gt["merchant_id"] == "m-123"


def test_eval_runner_execution(tmp_path: Path):
    reports_dir = tmp_path / "reports"
    summary = run_evaluation(count=3, seed=10, output_dir=reports_dir)

    assert summary["merchants_evaluated"] == 3
    assert (reports_dir / "report.json").exists()
    assert (reports_dir / "report.md").exists()
    assert summary["metrics"]["field_extraction_accuracy_pct"] >= 85.0
