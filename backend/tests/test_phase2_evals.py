from pathlib import Path
from unittest.mock import MagicMock

from sme_copilot.schemas.models import (
    DocumentType,
    ExtractedDocument,
    FileRef,
    SourcePointer,
    TransactionLine,
    ValidationResult,
)

from evals.graders.code_graders import (
    ArithmeticIntegrityGrader,
    NumericAccuracyGrader,
    SchemaComplianceGrader,
    SourcePointerGrader,
)
from evals.graders.human_calibration import (
    HumanCalibrationRecord,
    load_human_calibrations,
    save_human_calibration,
)
from evals.graders.llm_judge import LLMJudgeGrader
from evals.metrics import calculate_pass_at_k, calculate_pass_pow_k


def _make_dummy_doc() -> ExtractedDocument:
    return ExtractedDocument(
        application_id="app-test",
        file_ref=FileRef(
            filename="bank_statement.csv",
            content_type="text/csv",
            size_bytes=100,
            storage_path="/tmp/bank.csv",
        ),
        document_type=DocumentType.BANK_STATEMENT,
        transactions=[
            TransactionLine(
                date="2024-01-01",
                amount=1000.0,
                balance=1000.0,
                source_pointer=SourcePointer(page=1, text_snippet="Line 1"),
            ),
            TransactionLine(
                date="2024-01-02",
                amount=500.0,
                balance=1500.0,
                source_pointer=SourcePointer(page=1, text_snippet="Line 2"),
            ),
        ],
    )


def test_schema_compliance_grader():
    grader = SchemaComplianceGrader()
    state = {"extracted_documents": [_make_dummy_doc()]}
    res = grader.grade(state, {})
    assert res.passed is True
    assert res.score == 1.0

    # Failing state
    fail_res = grader.grade({"extracted_documents": []}, {})
    assert fail_res.passed is False


def test_numeric_accuracy_grader():
    grader = NumericAccuracyGrader()
    state = {"extracted_documents": [_make_dummy_doc()]}
    res = grader.grade(state, {"total_bank_transactions": 2})
    assert res.passed is True
    assert res.score == 1.0


def test_arithmetic_integrity_grader():
    grader = ArithmeticIntegrityGrader()
    # Case 1: Clean data, validation passed
    clean_state = {"validation_results": [ValidationResult(application_id="1", passed=True)]}
    res_clean = grader.grade(clean_state, {"has_arithmetic_mismatch": False})
    assert res_clean.passed is True

    # Case 2: Planted mismatch caught
    tampered_state = {"validation_results": [ValidationResult(application_id="1", passed=False)]}
    res_tampered = grader.grade(tampered_state, {"has_arithmetic_mismatch": True})
    assert res_tampered.passed is True
    assert "Correctly caught" in res_tampered.details


def test_source_pointer_grader():
    grader = SourcePointerGrader()
    state = {"extracted_documents": [_make_dummy_doc()]}
    res = grader.grade(state, {})
    assert res.passed is True
    assert res.score == 1.0


def test_llm_judge_grader_zero_cost_by_default():
    """Verify that by default LLM Judge is dry-run and incurs ZERO API cost."""
    grader = LLMJudgeGrader(enabled=False)
    state = {"extracted_documents": [_make_dummy_doc()]}
    res = grader.grade(state, {"true_revenue": 100000.0})

    assert res.passed is True
    assert res.cost_cents == 0.0
    assert "DRY-RUN / SKIPPED" in res.details


def test_llm_judge_grader_mock_enabled():
    """Verify that when enabled with a mock provider, evaluation parses pass/fail."""
    mock_provider = MagicMock()
    mock_provider.summarize.return_value = "PASS: The underwriter notes match true revenue."

    grader = LLMJudgeGrader(enabled=True, provider=mock_provider)
    state = {"extracted_documents": [_make_dummy_doc()]}
    res = grader.grade(state, {"true_revenue": 100000.0})

    assert res.passed is True
    assert res.cost_cents > 0.0
    assert "PASS" in res.details
    assert mock_provider.summarize.called


def test_human_calibration_persistence(tmp_path: Path, monkeypatch):
    import evals.graders.human_calibration as hc

    monkeypatch.setattr(hc, "CALIBRATION_DIR", tmp_path / "calibrations")

    record = HumanCalibrationRecord(
        sample_id="sample-001",
        reviewer_id="underwriter-sarah",
        overall_rating=5,
        factual_correctness=True,
        notes="All ledger lines checked against source PDF successfully.",
    )

    path = save_human_calibration(record)
    assert path.exists()

    loaded = load_human_calibrations()
    assert len(loaded) == 1
    assert loaded[0].sample_id == "sample-001"
    assert loaded[0].reviewer_id == "underwriter-sarah"


def test_metrics_pass_at_k():
    # If all passed, pass@k is 1.0
    assert calculate_pass_at_k(n=10, c=10, k=1) == 1.0
    assert calculate_pass_at_k(n=10, c=10, k=3) == 1.0

    # If 0 passed, pass@k is 0.0
    assert calculate_pass_at_k(n=10, c=0, k=1) == 0.0

    # If 5 passed out of 10, pass@1 is 0.5
    assert calculate_pass_at_k(n=10, c=5, k=1) == 0.5


def test_metrics_pass_pow_k():
    assert calculate_pass_pow_k(1.0, 3) == 1.0
    assert calculate_pass_pow_k(0.5, 2) == 0.25
    assert calculate_pass_pow_k(0.9, 1) == 0.9
