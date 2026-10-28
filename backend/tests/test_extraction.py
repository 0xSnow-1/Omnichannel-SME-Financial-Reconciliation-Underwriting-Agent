from sme_copilot.interfaces.contracts import LLMProvider
from sme_copilot.schemas.models import DocumentType, FileRef
from sme_copilot.services.docling_parser import ParsedDocument, TableData
from sme_copilot.services.extraction import (
    ExtractionService,
    RawExtractedLine,
    RawExtractedPayload,
)


class MockLLMProvider(LLMProvider):
    def __init__(self, payload: RawExtractedPayload | None = None) -> None:
        self.payload = payload or RawExtractedPayload(
            transactions=[
                RawExtractedLine(
                    date="2024-01-01",
                    description="Opening balance",
                    amount=50000.0,
                    balance=50000.0,
                    page=1,
                    snippet="Opening balance 50,000",
                )
            ],
            summary_fields={"total_revenue": 50000.0},
            confidence=0.92,
        )

    def extract_structured(self, prompt: str, schema: type) -> object:
        return self.payload

    def summarize(self, text: str) -> str:
        return "Mock summary"


class FailingLLMProvider(LLMProvider):
    def extract_structured(self, prompt: str, schema: type) -> object:
        raise ValueError("Simulated LLM failure")

    def summarize(self, text: str) -> str:
        return "Fail summary"


def test_extraction_service_success():
    provider = MockLLMProvider()
    service = ExtractionService(provider=provider)

    file_ref = FileRef(
        filename="bank_stmt.pdf",
        content_type="application/pdf",
        size_bytes=1024,
        storage_path="/tmp/fake.pdf",
    )
    parsed = ParsedDocument(text="Bank Statement 2024", parse_status="success")

    doc = service.extract("app-1", file_ref, parsed)
    assert doc.extraction_status == "success"
    assert doc.document_type == DocumentType.BANK_STATEMENT
    assert len(doc.transactions) == 1
    assert doc.transactions[0].amount == 50000.0
    assert doc.confidence == 0.92


def test_extraction_service_fallback_to_tables():
    # When LLM fails, extraction should fall back to parsed tabular data
    service = ExtractionService(provider=FailingLLMProvider())

    file_ref = FileRef(
        filename="sales_report.csv",
        content_type="text/csv",
        size_bytes=512,
        storage_path="/tmp/sales.csv",
    )
    parsed = ParsedDocument(
        text="Sales data",
        tables=[
            TableData(
                headers=["Date", "Description", "Amount", "Balance"],
                rows=[
                    ["2024-02-01", "Order #101", "1500.00", "1500.00"],
                    ["2024-02-02", "Order #102", "2500.00", "4000.00"],
                ],
            )
        ],
        parse_status="success",
    )

    doc = service.extract("app-2", file_ref, parsed)
    assert doc.extraction_status == "success"
    assert len(doc.transactions) == 2
    assert doc.transactions[0].amount == 1500.0
    assert doc.transactions[1].balance == 4000.0


def test_extraction_service_failed_parse_doc():
    service = ExtractionService(provider=MockLLMProvider())
    file_ref = FileRef(
        filename="corrupt.pdf",
        content_type="application/pdf",
        size_bytes=0,
        storage_path="/tmp/corrupt.pdf",
    )
    parsed = ParsedDocument(parse_status="failed")

    doc = service.extract("app-3", file_ref, parsed)
    assert doc.extraction_status == "failed"
    assert doc.confidence == 0.0


def test_document_type_detection():
    service = ExtractionService()
    assert (
        service._detect_document_type("gcash_transactions.csv", "") == DocumentType.EWALLET_EXPORT
    )
    assert (
        service._detect_document_type("shopee_seller_report.xlsx", "")
        == DocumentType.PLATFORM_SALES
    )
    assert service._detect_document_type("official_receipt.png", "") == DocumentType.RECEIPT
