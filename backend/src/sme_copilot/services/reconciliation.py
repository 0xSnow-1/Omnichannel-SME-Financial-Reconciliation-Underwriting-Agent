import logging
from datetime import datetime
from typing import Any, Dict, List

from sme_copilot.schemas.models import (
    Application,
    DocumentType,
    ExtractedDocument,
    MatchedPair,
    ReconciliationFlag,
    ReconciliationResult,
    SourcePointer,
    TransactionLine,
)

logger = logging.getLogger(__name__)


class ReconciliationService:
    """Deterministic reconciliation of financial documents to match orders with payouts."""

    def run(self, application: Application) -> ReconciliationResult:
        """Run reconciliation for an application.

        Args:
            application: The application containing extracted documents

        Returns:
            ReconciliationResult with matched pairs, flags, and status
        """
        logger.info(f"Starting reconciliation for application {application.id}")

        # Extract order IDs from platform_sales
        platform_sales_doc = self._find_document_by_type(
            application.extracted_documents, DocumentType.PLATFORM_SALES
        )
        order_ids = self._extract_order_ids(platform_sales_doc)

        # Extract payout references from ewallet_export and bank_statement
        ewallet_doc = self._find_document_by_type(
            application.extracted_documents, DocumentType.EWALLET_EXPORT
        )
        bank_stmt_doc = self._find_document_by_type(
            application.extracted_documents, DocumentType.BANK_STATEMENT
        )

        payout_refs = self._extract_payout_refs(ewallet_doc, bank_stmt_doc)

        # Perform deterministic matching
        matched_pairs = self._match_orders_to_payouts(order_ids, payout_refs)

        # Identify missing payouts
        flags = self._identify_missing_payouts(order_ids, matched_pairs)

        # Calculate totals
        total_amount = sum(pair.amount for pair in matched_pairs)
        unmatched_amount = sum(order["amount"] for order in order_ids if not order["matched"])

        # Determine overall status
        status = "success"
        if unmatched_amount > 0.1:  # Threshold for considering it a failure
            status = "failed"

        result = ReconciliationResult(
            matched_pairs=matched_pairs,
            flags=flags,
            status=status,
            total_amount=total_amount if total_amount > 0 else None,
            unmatched_amount=unmatched_amount if unmatched_amount > 0 else None,
        )

        application.reconciliation_status = status
        logger.info(f"Reconciliation completed for application {application.id}: {status}")
        return result

    def _find_document_by_type(
        self, documents: List[ExtractedDocument], doc_type: DocumentType
    ) -> ExtractedDocument | None:
        """Find a document by its type."""
        for doc in documents:
            if doc.document_type == doc_type:
                return doc
        return None

    def _extract_order_ids(self, platform_sales_doc: ExtractedDocument | None) -> List[Dict[str, Any]]:
        """Extract order IDs from platform_sales document summary fields or transactions."""
        if not platform_sales_doc:
            return []

        order_ids = []

        # Try to get from summary_fields first
        if platform_sales_doc.summary_fields and "orders" in platform_sales_doc.summary_fields:
            orders = platform_sales_doc.summary_fields["orders"]
            if isinstance(orders, list):
                for order in orders:
                    order_ids.append({
                        "order_id": order.get("order_id", ""),
                        "amount": float(order.get("amount", 0)),
                        "date": order.get("date", ""),
                        "matched": False,
                    })

        # If not in summary_fields, try to extract from transactions
        if not order_ids and platform_sales_doc.transactions:
            for txn in platform_sales_doc.transactions:
                # Look for order IDs in description or amount patterns
                desc_lower = txn.description.lower()
                if any(keyword in desc_lower for keyword in ["order", "payout", "sale"]):
                    order_ids.append({
                        "order_id": txn.description,
                        "amount": txn.amount,
                        "date": txn.date,
                        "matched": False,
                        "source_pointer": txn.source_pointer,
                    })

        return order_ids

    def _extract_payout_refs(
        self, ewallet_doc: ExtractedDocument | None, bank_stmt_doc: ExtractedDocument | None
    ) -> List[Dict[str, Any]]:
        """Extract payout references from ewallet_export and bank_statement."""
        payout_refs = []

        # Extract from ewallet_export
        if ewallet_doc and ewallet_doc.transactions:
            for txn in ewallet_doc.transactions:
                # Look for payout references in description or amount patterns
                desc_lower = txn.description.lower()
                # Check if it looks like a payout (contains payment/amount indicators)
                is_payout = any(keyword in desc_lower for keyword in ["payout", "withdrawal", "transfer", "disbursement", "payment", "refund"])
                # Also include transactions that have numeric amounts and no balance (likely standalone payouts)
                has_amount = txn.amount is not None and txn.amount != 0
                is_standalone = txn.balance is None
                
                if is_payout or (has_amount and is_standalone):
                    payout_refs.append({
                        "payout_ref": txn.description,
                        "amount": txn.amount,
                        "date": txn.date,
                        "source_pointer": txn.source_pointer,
                    })

        # Extract from bank_statement
        if bank_stmt_doc and bank_stmt_doc.transactions:
            for txn in bank_stmt_doc.transactions:
                # Look for payout references in description or amount patterns
                desc_lower = txn.description.lower()
                # Check if it looks like a payout (contains payment/amount indicators)
                is_payout = any(keyword in desc_lower for keyword in ["payout", "withdrawal", "transfer", "disbursement", "payment", "refund"])
                # Also include transactions that have numeric amounts and no balance (likely standalone payouts)
                has_amount = txn.amount is not None and txn.amount != 0
                is_standalone = txn.balance is None
                
                if is_payout or (has_amount and is_standalone):
                    payout_refs.append({
                        "payout_ref": txn.description,
                        "amount": txn.amount,
                        "date": txn.date,
                        "source_pointer": txn.source_pointer,
                    })

        return payout_refs

    def _match_orders_to_payouts(
        self, order_ids: List[Dict[str, Any]], payout_refs: List[Dict[str, Any]]
    ) -> List[MatchedPair]:
        """Perform deterministic matching between orders and payouts."""
        matched_pairs = []

        for order in order_ids:
            # Find matching payout (exact description and amount match)
            for payout in payout_refs:
                if (order["order_id"] and payout["payout_ref"] and
                    order["order_id"] == payout["payout_ref"] and
                    abs(order["amount"] - payout["amount"]) < 0.01):  # Allow for small rounding differences

                    matched_pairs.append(
                        MatchedPair(
                            order_id=order["order_id"],
                            payout_ref=payout["payout_ref"],
                            amount=order["amount"],
                            date=order["date"],
                            source_pointer=payout.get("source_pointer"),
                        )
                    )

                    # Mark as matched
                    order["matched"] = True

                    # Remove the payout from available pool to avoid duplicate matching
                    payout_refs.remove(payout)
                    break

        return matched_pairs

    def _identify_missing_payouts(
        self, order_ids: List[Dict[str, Any]], matched_pairs: List[MatchedPair]
    ) -> List[ReconciliationFlag]:
        """Identify orders with missing payouts."""
        flags = []

        for order in order_ids:
            if not order.get("matched", False):
                flags.append(
                    ReconciliationFlag(
                        flag_type="missing_payout",
                        severity="high",
                        description=f"Order {order['order_id']} with amount {order['amount']} has no matching payout.",
                    )
                )

        return flags
