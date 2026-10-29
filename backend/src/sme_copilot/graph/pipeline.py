import logging
import os
from typing import Any, TypedDict, cast

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph

from sme_copilot.schemas.models import (
    Application,
    ApplicationStatus,
    ExtractedDocument,
    ProcessingStatus,
    ReconciliationResult,
    ReviewState,
    ValidationResult,
)
from sme_copilot.services.docling_parser import ParsedDocument, parse_document
from sme_copilot.services.extraction import ExtractionService
from sme_copilot.services.kyc import KYCService
from sme_copilot.services.reconciliation import ReconciliationService
from sme_copilot.services.validators import ValidationService

logger = logging.getLogger(__name__)


class GraphState(TypedDict):
    application: Application
    review_state: ReviewState
    parsed_documents: list[ParsedDocument]
    extracted_documents: list[ExtractedDocument]
    validation_results: list[ValidationResult]
    confidence: float
    fraud_flags: list[str]
    reconciliation_result: ReconciliationResult | None
    should_end: bool


def kyc_check_node(state: GraphState) -> GraphState:
    kyc = KYCService()
    result = kyc.check(state["application"].merchant_name)
    rs = state["review_state"]
    rs.kyc_result = result
    if not result.passed:
        rs.status = ApplicationStatus.DENIED
        state["application"].status = ApplicationStatus.DENIED
        state["application"].processing_status = ProcessingStatus.FAILED
    return state


def parse_node(state: GraphState) -> GraphState:
    app = state["application"]
    parsed_docs: list[ParsedDocument] = []
    for file_ref in app.files:
        try:
            parsed = parse_document(file_ref.storage_path)
            parsed_docs.append(parsed)
        except Exception as exc:
            logger.warning("Failed to parse file %s: %s", file_ref.filename, exc)
            parsed_docs.append(
                ParsedDocument(
                    text="",
                    tables=[],
                    page_count=0,
                    parse_status="failed",
                    file_hash="",
                )
            )
    state["parsed_documents"] = parsed_docs
    return state


def extract_node(state: GraphState) -> GraphState:
    app = state["application"]
    service = ExtractionService()
    extracted: list[ExtractedDocument] = []

    for file_ref, parsed in zip(app.files, state["parsed_documents"], strict=False):
        try:
            doc = service.extract(
                application_id=app.id,
                file_ref=file_ref,
                parsed_doc=parsed,
            )
            extracted.append(doc)
        except Exception as exc:
            logger.warning("Extraction error for %s: %s", file_ref.filename, exc)
            extracted.append(
                ExtractedDocument(
                    application_id=app.id,
                    file_ref=file_ref,
                    document_type=doc.document_type if "doc" in locals() else None,  # type: ignore[arg-type]
                    confidence=0.0,
                    extraction_status="failed",
                )
            )

    state["extracted_documents"] = extracted
    app.extracted_documents = extracted
    return state


def validate_node(state: GraphState) -> GraphState:
    app = state["application"]
    rs = state["review_state"]
    results, confidence, fraud_flags = ValidationService.validate_documents(
        state["extracted_documents"]
    )
    state["validation_results"] = results
    state["confidence"] = confidence
    state["fraud_flags"] = fraud_flags
    app.validation_results = results
    rs.confidence = confidence
    rs.fraud_flags = fraud_flags

    # If confidence drops below 0.7 or validation errors exist, ensure flagged
    if confidence < 0.7 or any(not r.passed for r in results):
        rs.status = ApplicationStatus.AWAITING_REVIEW
        app.processing_status = ProcessingStatus.AWAITING_REVIEW
    else:
        rs.status = ApplicationStatus.AWAITING_REVIEW
        app.processing_status = ProcessingStatus.AWAITING_REVIEW

    return state


def reconcile_node(state: GraphState) -> GraphState:
    """Node that performs reconciliation between extracted financial data."""
    app = state["application"]
    rs = state["review_state"]
    
    # Check if validation passed
    validation_failed = False
    for vr in state["validation_results"]:
        if not vr.passed:
            validation_failed = True
            break
    
    # Run reconciliation service
    reconciliation_service = ReconciliationService()
    reconciliation_result = reconciliation_service.run(app)
    
    # Store reconciliation result in state
    rs.reconciliation_result = reconciliation_result
    
    # Update application status based on reconciliation
    if validation_failed or reconciliation_result.status == "failed" or reconciliation_result.flags:
        rs.status = ApplicationStatus.DENIED
        app.status = ApplicationStatus.DENIED
        app.processing_status = ProcessingStatus.FAILED
        app.reconciliation_status = "failed"
        # End the graph - don't proceed to human_review
        state["should_end"] = True
    else:
        app.reconciliation_status = "success"
    
    return state


def human_review_node(state: GraphState) -> GraphState:
    """Execute human underwriter review decision when graph resumes."""
    rs = state["review_state"]
    app = state["application"]
    if rs.decision == "approve":
        rs.status = ApplicationStatus.APPROVED
        app.status = ApplicationStatus.APPROVED
        app.processing_status = ProcessingStatus.APPROVED
    elif rs.decision == "deny":
        rs.status = ApplicationStatus.DENIED
        app.status = ApplicationStatus.DENIED
        app.processing_status = ProcessingStatus.DENIED
    elif rs.decision == "counter":
        rs.status = ApplicationStatus.COUNTERED
        app.status = ApplicationStatus.COUNTERED
        app.processing_status = ProcessingStatus.COUNTERED
    return state


def check_kyc_condition(state: GraphState) -> str:
    rs = state["review_state"]
    if rs.kyc_result and not rs.kyc_result.passed:
        return "human_review"
    return "parse"


def build_graph(checkpointer: Any = None) -> Any:
    graph = StateGraph(GraphState)
    graph.add_node("kyc_check", kyc_check_node)
    graph.add_node("parse", parse_node)
    graph.add_node("extract", extract_node)
    graph.add_node("validate", validate_node)
    graph.add_node("reconcile", reconcile_node)
    graph.add_node("human_review", human_review_node)

    graph.set_entry_point("kyc_check")
    graph.add_conditional_edges(
        "kyc_check",
        check_kyc_condition,
        {"human_review": "human_review", "parse": "parse"},
    )
    graph.add_edge("parse", "extract")
    graph.add_edge("extract", "validate")
    graph.add_edge("validate", "reconcile")
    
    # Conditional edge from reconcile to human_review or END
    def reconcile_condition(state: GraphState) -> str:
        if state.get("should_end", False):
            return "END"
        return "human_review"
    
    graph.add_conditional_edges(
        "reconcile",
        reconcile_condition,
        {"human_review": "human_review", "END": END},
    )
    graph.add_edge("human_review", END)

    if checkpointer is None:
        db_url = os.getenv("DATABASE_URL")
        if db_url and "postgres" in db_url:
            try:
                from langgraph.checkpoint.postgres import PostgresSaver  # type: ignore[import-not-found]

                # Can use PostgresSaver if available
                checkpointer = PostgresSaver.from_conn_string(db_url)
            except Exception:
                checkpointer = MemorySaver()
        else:
            checkpointer = MemorySaver()

    return graph.compile(
        checkpointer=checkpointer,
        interrupt_before=["human_review"],
    )


_default_checkpointer = MemorySaver()
_compiled_graph: Any = None


def get_pipeline_graph() -> Any:
    global _compiled_graph
    if _compiled_graph is None:
        _compiled_graph = build_graph(checkpointer=_default_checkpointer)
    return _compiled_graph


def run_pipeline(application: Application) -> GraphState:
    """Execute pipeline up to human_review interrupt."""
    graph = get_pipeline_graph()
    initial_review = ReviewState(
        application_id=application.id,
        status=ApplicationStatus.PENDING,
    )
    initial_state: GraphState = {
        "application": application,
        "review_state": initial_review,
        "parsed_documents": [],
        "extracted_documents": [],
        "validation_results": [],
        "confidence": 1.0,
        "fraud_flags": [],
        "reconciliation_result": None,
        "should_end": False,
    }

    config = {"configurable": {"thread_id": application.id}}
    result_state = graph.invoke(initial_state, config=config)
    return cast(GraphState, result_state)


def resume_pipeline(application_id: str, decision: str, notes: str | None = None) -> GraphState:
    """Resume pipeline from human_review interrupt with underwriter decision."""
    graph = get_pipeline_graph()
    config = {"configurable": {"thread_id": application_id}}

    current = graph.get_state(config)
    if not current or not current.values:
        raise ValueError(f"No checkpoint found for thread {application_id}")

    state: GraphState = dict(current.values)  # type: ignore[assignment]
    state["review_state"].decision = decision
    state["review_state"].reviewer_notes = notes

    graph.update_state(config, state)
    resumed = graph.invoke(None, config=config)
    return cast(GraphState, resumed)
