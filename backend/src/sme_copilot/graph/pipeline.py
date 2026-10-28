from typing import Any, TypedDict

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph

from sme_copilot.schemas.models import Application, ApplicationStatus, ReviewState
from sme_copilot.services.kyc import KYCService


class GraphState(TypedDict):
    application: Application
    review_state: ReviewState


def kyc_check_node(state: GraphState) -> GraphState:
    kyc = KYCService()
    result = kyc.check(
        state["application"].merchant_name
        if hasattr(state["application"], "merchant_name")
        else "unknown"
    )
    rs = state["review_state"]
    rs.kyc_result = result
    if not result.passed:
        rs.status = ApplicationStatus.DENIED
    return {"application": state["application"], "review_state": rs}


def human_review_node(state: GraphState) -> GraphState:
    # Interrupt point — graph pauses here for human decision
    return state


def build_graph(checkpointer: Any = None) -> Any:
    graph = StateGraph(GraphState)
    graph.add_node("kyc_check", kyc_check_node)
    graph.add_node("human_review", human_review_node)
    graph.set_entry_point("kyc_check")
    graph.add_edge("kyc_check", "human_review")
    graph.add_edge("human_review", END)
    if checkpointer is None:
        checkpointer = MemorySaver()
    return graph.compile(checkpointer=checkpointer)
