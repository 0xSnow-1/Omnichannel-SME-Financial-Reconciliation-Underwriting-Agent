
from sme_copilot.services.validators import (
    date_continuity_check,
    line_item_sum_check,
    run_validation,
    running_balance_check,
)

# ---------------------------------------------------------------------------
# running_balance_check
# ---------------------------------------------------------------------------


def test_running_balance_empty():
    result = running_balance_check([])
    assert result.passed is True
    assert "No transactions" in result.details


def test_running_balance_ok():
    txns = [
        {"date": "2024-01-01", "amount": 1000.0, "balance": 1000.0},
        {"date": "2024-01-02", "amount": -200.0, "balance": 800.0},
        {"date": "2024-01-03", "amount": 500.0, "balance": 1300.0},
    ]
    result = running_balance_check(txns)
    assert result.passed is True


def test_running_balance_mismatch():
    txns = [
        {"date": "2024-01-01", "amount": 1000.0, "balance": 1000.0},
        {"date": "2024-01-02", "amount": 200.0, "balance": 1300.0},  # wrong: should be 1200
    ]
    result = running_balance_check(txns)
    assert result.passed is False
    assert "Mismatch" in result.details


def test_running_balance_skips_none_balance():
    txns = [
        {"date": "2024-01-01", "amount": 1000.0, "balance": None},
        {"date": "2024-01-02", "amount": 200.0, "balance": None},
    ]
    result = running_balance_check(txns)
    assert result.passed is True


# ---------------------------------------------------------------------------
# line_item_sum_check
# ---------------------------------------------------------------------------


def test_line_item_sum_ok():
    items = [{"amount": 100.0}, {"amount": 200.0}, {"amount": 50.0}]
    result = line_item_sum_check(items, 350.0)
    assert result.passed is True


def test_line_item_sum_mismatch():
    items = [{"amount": 100.0}, {"amount": 200.0}]
    result = line_item_sum_check(items, 400.0)
    assert result.passed is False
    assert "400" in result.details or "300" in result.details


def test_line_item_sum_empty():
    result = line_item_sum_check([], 0.0)
    assert result.passed is True


def test_line_item_sum_rounding():
    items = [{"amount": 0.1}, {"amount": 0.2}]
    result = line_item_sum_check(items, 0.3)
    assert result.passed is True


# ---------------------------------------------------------------------------
# date_continuity_check
# ---------------------------------------------------------------------------


def test_date_continuity_ok():
    txns = [
        {"date": "2024-01-01"},
        {"date": "2024-01-15"},
        {"date": "2024-01-28"},
    ]
    result = date_continuity_check(txns, max_gap_days=30)
    assert result.passed is True


def test_date_continuity_gap():
    txns = [
        {"date": "2024-01-01"},
        {"date": "2024-03-01"},  # 60-day gap
    ]
    result = date_continuity_check(txns, max_gap_days=30)
    assert result.passed is False
    assert "Gap" in result.details


def test_date_continuity_insufficient():
    result = date_continuity_check([{"date": "2024-01-01"}])
    assert result.passed is True
    assert "Insufficient" in result.details


def test_date_continuity_no_dates():
    txns = [{"amount": 100}, {"amount": 200}]
    result = date_continuity_check(txns)
    assert result.passed is True


def test_date_continuity_bad_format_skipped():
    txns = [
        {"date": "not-a-date"},
        {"date": "2024-01-01"},
    ]
    # Only 1 valid date, so insufficient
    result = date_continuity_check(txns)
    assert result.passed is True


# ---------------------------------------------------------------------------
# run_validation (integration)
# ---------------------------------------------------------------------------


def test_run_validation_all_pass():
    txns = [
        {"date": "2024-01-01", "amount": 500.0, "balance": 500.0},
        {"date": "2024-01-10", "amount": 100.0, "balance": 600.0},
    ]
    result = run_validation(txns, stated_total=600.0)
    assert result.passed is True
    assert result.errors == []


def test_run_validation_balance_fail():
    txns = [
        {"date": "2024-01-01", "amount": 500.0, "balance": 500.0},
        {"date": "2024-01-10", "amount": 100.0, "balance": 700.0},  # wrong
    ]
    result = run_validation(txns)
    assert result.passed is False
    assert len(result.errors) >= 1


def test_run_validation_no_stated_total():
    txns = [
        {"date": "2024-01-01", "amount": 100.0, "balance": 100.0},
    ]
    # line_item_sum not included when stated_total is None
    result = run_validation(txns)
    assert isinstance(result.passed, bool)


def test_run_validation_empty_application_id():
    # run_validation always sets application_id to "" — acceptable for pure function usage
    result = run_validation([])
    assert result.application_id == ""
