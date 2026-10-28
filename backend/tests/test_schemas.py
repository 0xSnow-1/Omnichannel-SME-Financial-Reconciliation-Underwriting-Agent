from sme_copilot.schemas.models import (
    Application,
    AuditEntry,
    CheckResult,
    ExtractionResult,
    FileRef,
    KYCResult,
    Merchant,
    ReviewState,
    SourcePointer,
    ValidationResult,
)


def test_application_roundtrip():
    app = Application(merchant_name="Test", loan_amount=100000)
    data = app.model_dump_json()
    restored = Application.model_validate_json(data)
    assert restored == app


def test_extraction_result_roundtrip():
    er = ExtractionResult(application_id="1", document_type="bank_pdf", confidence=0.95)
    data = er.model_dump_json()
    restored = ExtractionResult.model_validate_json(data)
    assert restored == er


def test_validation_result_roundtrip():
    vr = ValidationResult(application_id="1", passed=True)
    data = vr.model_dump_json()
    restored = ValidationResult.model_validate_json(data)
    assert restored == vr


def test_review_state_roundtrip():
    rs = ReviewState(application_id="1")
    data = rs.model_dump_json()
    restored = ReviewState.model_validate_json(data)
    assert restored == rs


def test_merchant_roundtrip():
    m = Merchant(name="Rosa", true_revenue=150000)
    data = m.model_dump_json()
    restored = Merchant.model_validate_json(data)
    assert restored == m


def test_audit_entry_roundtrip():
    ae = AuditEntry(application_id="1", action="create", actor="system")
    data = ae.model_dump_json()
    restored = AuditEntry.model_validate_json(data)
    assert restored == ae


def test_source_pointer_roundtrip():
    sp = SourcePointer(page=1, text_snippet="hello")
    data = sp.model_dump_json()
    restored = SourcePointer.model_validate_json(data)
    assert restored == sp


def test_check_result_roundtrip():
    cr = CheckResult(check_name="balance", passed=True)
    data = cr.model_dump_json()
    restored = CheckResult.model_validate_json(data)
    assert restored == cr


def test_kyc_result_roundtrip():
    kr = KYCResult(passed=True)
    data = kr.model_dump_json()
    restored = KYCResult.model_validate_json(data)
    assert restored == kr


def test_file_ref_roundtrip():
    fr = FileRef(
        filename="test.pdf",
        content_type="application/pdf",
        size_bytes=100,
        storage_path="/tmp/test.pdf",
    )
    data = fr.model_dump_json()
    restored = FileRef.model_validate_json(data)
    assert restored == fr
