from sme_copilot.graph.pipeline import (
    human_review_node,
    kyc_check_node,
    resume_pipeline,
    run_pipeline,
)
from sme_copilot.schemas.models import (
    Application,
    ApplicationStatus,
    FileRef,
    ReviewState,
)


def test_kyc_check_node_pass():
    app = Application(merchant_name="Test", loan_amount=100000)
    rs = ReviewState(application_id=app.id)
    state = {
        "application": app,
        "review_state": rs,
        "parsed_documents": [],
        "extracted_documents": [],
        "validation_results": [],
        "confidence": 1.0,
        "fraud_flags": [],
    }
    result = kyc_check_node(state)
    assert result["review_state"].kyc_result is not None
    assert result["review_state"].kyc_result.passed is True


def test_kyc_check_node_fail():
    app = Application(merchant_name="Unknown", loan_amount=100000)
    rs = ReviewState(application_id=app.id)
    state = {
        "application": app,
        "review_state": rs,
        "parsed_documents": [],
        "extracted_documents": [],
        "validation_results": [],
        "confidence": 1.0,
        "fraud_flags": [],
    }
    # Override KYC to fail
    import os

    os.environ["KYC_STUB_RESULT"] = "fail"
    try:
        result = kyc_check_node(state)
        assert result["review_state"].kyc_result.passed is False
        assert result["review_state"].status == ApplicationStatus.DENIED
    finally:
        os.environ["KYC_STUB_RESULT"] = "pass"


def test_human_review_node_decisions():
    app = Application(merchant_name="Test", loan_amount=100000)
    rs = ReviewState(application_id=app.id, decision="approve")
    state = {
        "application": app,
        "review_state": rs,
        "parsed_documents": [],
        "extracted_documents": [],
        "validation_results": [],
        "confidence": 1.0,
        "fraud_flags": [],
    }
    res = human_review_node(state)
    assert res["review_state"].status == ApplicationStatus.APPROVED

    rs.decision = "deny"
    res = human_review_node(state)
    assert res["review_state"].status == ApplicationStatus.DENIED

    rs.decision = "counter"
    res = human_review_node(state)
    assert res["review_state"].status == ApplicationStatus.COUNTERED


def test_full_pipeline_run_to_interrupt(tmp_path):
    # Create sample file
    sample_file = tmp_path / "statement.csv"
    sample_file.write_text(
        "Date,Description,Amount,Balance\n"
        "2024-01-01,Deposit,10000.0,10000.0\n"
        "2024-01-05,Sales,5000.0,15000.0\n"
    )

    app = Application(
        merchant_name="Rosa Sari-Sari",
        loan_amount=50000,
        files=[
            FileRef(
                filename="statement.csv",
                content_type="text/csv",
                size_bytes=len(sample_file.read_bytes()),
                storage_path=str(sample_file),
            )
        ],
    )

    # Run pipeline up to human_review interrupt
    state = run_pipeline(app)
    assert state["review_state"].status == ApplicationStatus.AWAITING_REVIEW
    assert len(state["extracted_documents"]) == 1
    assert len(state["validation_results"]) >= 1
    assert state["confidence"] >= 0.7

    # Resume with approval decision
    resumed = resume_pipeline(app.id, decision="approve", notes="Verified ledger looks healthy")
    assert resumed["review_state"].status == ApplicationStatus.APPROVED
    assert resumed["application"].status == ApplicationStatus.APPROVED
