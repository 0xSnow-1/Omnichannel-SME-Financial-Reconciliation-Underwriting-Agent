from sme_copilot.graph.pipeline import human_review_node, kyc_check_node
from sme_copilot.schemas.models import Application, ReviewState


def test_kyc_check_node_pass():
    app = Application(merchant_name="Test", loan_amount=100000)
    rs = ReviewState(application_id=app.id)
    state = {"application": app, "review_state": rs}
    result = kyc_check_node(state)
    assert result["review_state"].kyc_result is not None
    assert result["review_state"].kyc_result.passed is True


def test_human_review_node():
    app = Application(merchant_name="Test", loan_amount=100000)
    rs = ReviewState(application_id=app.id)
    state = {"application": app, "review_state": rs}
    result = human_review_node(state)
    assert result == state
