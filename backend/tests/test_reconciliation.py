from sme_copilot.graph.pipeline import reconcile_node
from sme_copilot.schemas.models import (
    Application,
    ApplicationStatus,
    ExtractedDocument,
    FileRef,
    ReviewState,
    TransactionLine,
)


def test_reconcile_node_success():
    """Test reconcile_node when reconciliation succeeds."""
    app = Application(merchant_name="Test", loan_amount=100000)
    app.extracted_documents = []

    platform_sales_doc = ExtractedDocument(
        application_id=app.id,
        file_ref=FileRef(
            filename="sales.csv",
            content_type="text/csv",
            size_bytes=100,
            storage_path="/tmp/sales.csv",
        ),
        document_type="platform_sales",
        transactions=[
            TransactionLine(
                date="2024-01-01",
                description="123456",
                amount=5000.0,
                balance=None,
            )
        ],
        summary_fields={"orders": [{"order_id": "123456", "amount": 5000.0, "date": "2024-01-01"}]},
        confidence=0.9,
    )

    ewallet_doc = ExtractedDocument(
        application_id=app.id,
        file_ref=FileRef(
            filename="ewallet.csv",
            content_type="text/csv",
            size_bytes=100,
            storage_path="/tmp/ewallet.csv",
        ),
        document_type="ewallet_export",
        transactions=[
            TransactionLine(
                date="2024-01-01",
                description="123456",
                amount=5000.0,
                balance=None,
            )
        ],
        confidence=0.9,
    )

    app.extracted_documents = [platform_sales_doc, ewallet_doc]

    state = {
        "application": app,
        "review_state": ReviewState(application_id=app.id, status=ApplicationStatus.AWAITING_REVIEW),
        "parsed_documents": [],
        "extracted_documents": [platform_sales_doc, ewallet_doc],
        "validation_results": [],
        "confidence": 1.0,
        "fraud_flags": [],
        "reconciliation_result": None,
        "should_end": False,
    }

    result = reconcile_node(state)

    # Check that reconciliation was performed
    assert result["review_state"].reconciliation_result is not None
    assert result["review_state"].reconciliation_result.status == "success"
    assert len(result["review_state"].reconciliation_result.matched_pairs) == 1
    assert len(result["review_state"].reconciliation_result.flags) == 0
    assert result["application"].reconciliation_status == "success"
