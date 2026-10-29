from datetime import datetime
from enum import StrEnum
from uuid import uuid4

from pydantic import BaseModel, Field


class ApplicationStatus(StrEnum):
    PENDING = "pending"
    AWAITING_REVIEW = "awaiting_review"
    APPROVED = "approved"
    DENIED = "denied"
    COUNTERED = "countered"


class ProblemType(StrEnum):
    MISSING_PAYOUT = "missing_payout"
    HIDDEN_FEE = "hidden_fee"
    ABNORMAL_RETURN = "abnormal_return"
    DEPOSIT_SPIKE = "deposit_spike"
    INFLATED_REVENUE = "inflated_revenue"


class DocumentType(StrEnum):
    BANK_STATEMENT = "bank_statement"
    EWALLET_EXPORT = "ewallet_export"
    PLATFORM_SALES = "platform_sales"
    RECEIPT = "receipt"


class ProcessingStatus(StrEnum):
    PENDING = "pending"
    PROCESSING = "processing"
    AWAITING_REVIEW = "awaiting_review"
    APPROVED = "approved"
    DENIED = "denied"
    COUNTERED = "countered"
    FAILED = "failed"


class ValidationCheck(StrEnum):
    RUNNING_BALANCE = "running_balance"
    LINE_ITEM_SUM = "line_item_sum"
    DATE_CONTINUITY = "date_continuity"


class FileRef(BaseModel):
    filename: str
    content_type: str
    size_bytes: int = Field(ge=0)
    storage_path: str
    uploaded_at: datetime = Field(default_factory=datetime.utcnow)


class SourcePointer(BaseModel):
    page: int = Field(ge=1)
    bbox: list[float] | None = None
    text_snippet: str = ""


class TransactionLine(BaseModel):
    date: str
    description: str = ""
    amount: float
    balance: float | None = None
    source_pointer: SourcePointer | None = None


class ExtractedDocument(BaseModel):
    application_id: str
    file_ref: FileRef
    document_type: DocumentType
    transactions: list[TransactionLine] = Field(default_factory=list)
    summary_fields: dict[str, object] = Field(default_factory=dict)
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    source_pointers: list[SourcePointer] = Field(default_factory=list)
    extraction_status: str = "success"


class EvidenceBundle(BaseModel):
    application_id: str
    documents: list[ExtractedDocument] = Field(default_factory=list)
    validation_results: list["ValidationResult"] = Field(default_factory=list)
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    fraud_flags: list[str] = Field(default_factory=list)


class Application(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    merchant_name: str = Field(min_length=1)
    loan_amount: float = Field(gt=0)
    files: list[FileRef] = Field(default_factory=list)
    idempotency_key: str | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    status: ApplicationStatus = ApplicationStatus.PENDING
    processing_status: ProcessingStatus = ProcessingStatus.PENDING
    validation_results: list["ValidationResult"] = Field(default_factory=list)
    extracted_documents: list["ExtractedDocument"] = Field(default_factory=list)
    reconciliation_status: str = "pending"


class ExtractionResult(BaseModel):
    application_id: str
    document_type: str
    fields: dict[str, object] = Field(default_factory=dict)
    confidence: float = Field(ge=0.0, le=1.0)
    source_pointers: list[SourcePointer] = Field(default_factory=list)


class CheckResult(BaseModel):
    check_name: str
    passed: bool
    details: str = ""


class ValidationResult(BaseModel):
    application_id: str
    checks: list[CheckResult] = Field(default_factory=list)
    passed: bool = False
    errors: list[str] = Field(default_factory=list)


class KYCResult(BaseModel):
    passed: bool
    reason: str = ""
    checked_at: datetime = Field(default_factory=datetime.utcnow)


class MatchedPair(BaseModel):
    order_id: str
    payout_ref: str
    amount: float
    date: str
    source_pointer: SourcePointer | None = None


class ReconciliationFlag(BaseModel):
    flag_type: str
    severity: str
    description: str


class ReconciliationResult(BaseModel):
    matched_pairs: list[MatchedPair]
    flags: list[ReconciliationFlag]
    status: str
    total_amount: float | None = None
    unmatched_amount: float | None = None


class ReviewState(BaseModel):
    application_id: str
    status: ApplicationStatus = ApplicationStatus.PENDING
    kyc_result: KYCResult | None = None
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    fraud_flags: list[str] = Field(default_factory=list)
    decision: str | None = None
    reviewer_notes: str | None = None
    reconciliation_result: "ReconciliationResult | None" = None


class Merchant(BaseModel):
    merchant_id: str = Field(default_factory=lambda: str(uuid4()))
    name: str
    true_revenue: float = Field(gt=0)
    planted_problems: list[ProblemType] = Field(default_factory=list)
    documents: list[FileRef] = Field(default_factory=list)


class AuditEntry(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    application_id: str
    action: str
    actor: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    prev_hash: str = ""
    entry_hash: str = ""
