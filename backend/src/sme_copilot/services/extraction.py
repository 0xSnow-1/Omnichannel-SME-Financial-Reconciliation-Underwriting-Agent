import logging
import re
from typing import Any

from pydantic import BaseModel, Field

from sme_copilot.interfaces.contracts import LLMProvider
from sme_copilot.schemas.models import (
    DocumentType,
    ExtractedDocument,
    FileRef,
    SourcePointer,
    TransactionLine,
)
from sme_copilot.services.docling_parser import ParsedDocument
from sme_copilot.services.llm_provider import get_llm_provider

logger = logging.getLogger(__name__)


class RawExtractedLine(BaseModel):
    date: str = Field(default="")
    description: str = Field(default="")
    amount: float = Field(default=0.0)
    balance: float | None = None
    page: int = 1
    snippet: str = ""


class RawExtractedPayload(BaseModel):
    transactions: list[RawExtractedLine] = Field(default_factory=list)
    summary_fields: dict[str, Any] = Field(default_factory=dict)
    confidence: float = Field(default=0.95, ge=0.0, le=1.0)


PROMPT_TEMPLATES: dict[DocumentType, str] = {
    DocumentType.BANK_STATEMENT: (
        "You are an expert financial document parser. Extract all transaction lines, "
        "beginning and ending balances, total deposits, and withdrawals from this bank statement."
    ),
    DocumentType.EWALLET_EXPORT: (
        "You are an expert financial document parser. Extract all transaction records, "
        "including reference ID, transfer amounts, transaction fees, and running balances."
    ),
    DocumentType.PLATFORM_SALES: (
        "You are an expert financial document parser. Extract all sales orders, gross revenue, "
        "marketplace commission fees, return deductions, and net payout amounts."
    ),
    DocumentType.RECEIPT: (
        "You are an expert financial document parser. Extract the receipt date, vendor name, "
        "line items, tax amount, and total stated payment."
    ),
}


class ExtractionService:
    def __init__(self, provider: LLMProvider | None = None) -> None:
        self.provider = provider or get_llm_provider()

    def _detect_document_type(self, filename: str, content_preview: str) -> DocumentType:
        name_lower = filename.lower()
        content_lower = content_preview.lower()

        if any(w in name_lower or w in content_lower for w in ["bank", "statement", "bdo", "bpi"]):
            return DocumentType.BANK_STATEMENT
        if any(w in name_lower or w in content_lower for w in ["gcash", "maya", "wallet"]):
            return DocumentType.EWALLET_EXPORT
        if any(
            w in name_lower or w in content_lower
            for w in ["sales", "shopee", "lazada", "order", "payout"]
        ):
            return DocumentType.PLATFORM_SALES
        if any(w in name_lower or w in content_lower for w in ["receipt", "invoice", "or#", "tin"]):
            return DocumentType.RECEIPT

        return DocumentType.BANK_STATEMENT

    def _fallback_parse_table_rows(
        self, parsed_doc: ParsedDocument, doc_type: DocumentType
    ) -> list[TransactionLine]:
        """Deterministic table parsing fallback for CSV and structured tables."""
        txns: list[TransactionLine] = []
        for table in parsed_doc.tables:
            headers = [h.strip().lower() for h in table.headers]
            date_idx = next((i for i, h in enumerate(headers) if "date" in h), -1)
            desc_idx = next(
                (
                    i
                    for i, h in enumerate(headers)
                    if any(k in h for k in ["desc", "detail", "item", "ref", "type"])
                ),
                -1,
            )
            amt_idx = next(
                (
                    i
                    for i, h in enumerate(headers)
                    if any(k in h for k in ["amount", "total", "sales", "net"])
                ),
                -1,
            )
            bal_idx = next((i for i, h in enumerate(headers) if "bal" in h), -1)
            fee_idx = next((i for i, h in enumerate(headers) if "fee" in h), -1)

            for row_idx, row in enumerate(table.rows):
                if not row or len(row) <= max(date_idx, amt_idx):
                    continue
                raw_amt = row[amt_idx] if amt_idx >= 0 else "0"
                cleaned_amt = re.sub(r"[^\d.-]", "", raw_amt)
                try:
                    amount = float(cleaned_amt) if cleaned_amt else 0.0
                except ValueError:
                    continue

                if fee_idx >= 0 and fee_idx < len(row):
                    raw_fee = re.sub(r"[^\d.-]", "", row[fee_idx])
                    try:
                        fee = float(raw_fee) if raw_fee else 0.0
                        if amount > 0:
                            amount = round(amount - fee, 2)
                    except ValueError:
                        pass

                balance = None
                if bal_idx >= 0 and bal_idx < len(row):
                    cleaned_bal = re.sub(r"[^\d.-]", "", row[bal_idx])
                    try:
                        balance = float(cleaned_bal) if cleaned_bal else None
                    except ValueError:
                        balance = None

                date_val = row[date_idx] if date_idx >= 0 and date_idx < len(row) else "2024-01-01"
                desc_val = (
                    row[desc_idx] if desc_idx >= 0 and desc_idx < len(row) else f"Row {row_idx + 1}"
                )

                txns.append(
                    TransactionLine(
                        date=date_val,
                        description=desc_val,
                        amount=amount,
                        balance=balance,
                        source_pointer=SourcePointer(
                            page=1,
                            text_snippet=f"Row {row_idx + 1}: {', '.join(row[:4])}",
                        ),
                    )
                )
        return txns

    def extract(
        self,
        application_id: str,
        file_ref: FileRef,
        parsed_doc: ParsedDocument,
        document_type: DocumentType | None = None,
    ) -> ExtractedDocument:
        """Extract structured financial data from a parsed document with retry."""
        if parsed_doc.parse_status == "failed":
            return ExtractedDocument(
                application_id=application_id,
                file_ref=file_ref,
                document_type=document_type or DocumentType.BANK_STATEMENT,
                confidence=0.0,
                extraction_status="failed",
            )

        doc_type = document_type or self._detect_document_type(file_ref.filename, parsed_doc.text)
        prompt_instruction = PROMPT_TEMPLATES.get(
            doc_type, PROMPT_TEMPLATES[DocumentType.BANK_STATEMENT]
        )

        prompt = (
            f"{prompt_instruction}\n\n"
            f"Document Filename: {file_ref.filename}\n"
            f"Document Text:\n{parsed_doc.text[:8000]}\n"
        )

        # Attempt 1
        raw_result: RawExtractedPayload | None = None
        try:
            raw_result = self.provider.extract_structured(prompt, RawExtractedPayload)
        except Exception as exc:
            logger.info("First extraction attempt failed: %s. Retrying with stricter prompt.", exc)
            # Retry with stricter prompt
            strict_prompt = (
                f"{prompt}\n\n"
                f"STRICT INSTRUCTION: Output valid JSON adhering exactly to the schema. "
                f"Ensure amounts are floating point numbers."
            )
            try:
                raw_result = self.provider.extract_structured(strict_prompt, RawExtractedPayload)
            except Exception as retry_exc:
                logger.warning("Retry extraction attempt failed: %s", retry_exc)

        # Process results
        transactions: list[TransactionLine] = []
        source_pointers: list[SourcePointer] = []
        summary_fields: dict[str, Any] = {}
        confidence = 0.95

        if raw_result and raw_result.transactions:
            confidence = raw_result.confidence
            summary_fields = raw_result.summary_fields
            for t in raw_result.transactions:
                sp = SourcePointer(page=max(1, t.page), text_snippet=t.snippet or t.description)
                source_pointers.append(sp)
                transactions.append(
                    TransactionLine(
                        date=t.date,
                        description=t.description,
                        amount=t.amount,
                        balance=t.balance,
                        source_pointer=sp,
                    )
                )
        else:
            # Check table rows fallback if LLM returned no transactions
            fallback_txns = self._fallback_parse_table_rows(parsed_doc, doc_type)
            if fallback_txns:
                transactions = fallback_txns
                confidence = 0.85
                source_pointers = [t.source_pointer for t in fallback_txns if t.source_pointer]

        return ExtractedDocument(
            application_id=application_id,
            file_ref=file_ref,
            document_type=doc_type,
            transactions=transactions,
            summary_fields=summary_fields,
            confidence=confidence,
            source_pointers=source_pointers,
            extraction_status="success",
        )
