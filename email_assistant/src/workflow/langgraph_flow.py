from langgraph.graph import StateGraph, END
from langgraph.graph.state import CompiledStateGraph

from ..state import EmailAgentState
from ..agents.input_parser_agent import run_input_parser
from ..agents.intent_detection_agent import run_intent_detection
from ..agents.tone_stylist_agent import run_tone_stylist
from ..agents.draft_writer_agent import run_draft_writer
from ..agents.personalization_agent import run_personalization
from ..agents.review_agent import run_review
from ..agents.router_agent import run_router, route_after_router


def route_after_input(state: EmailAgentState) -> str:
    if state.get("errors"):
        return "end"
    return "intent_detection"


workflow = StateGraph(EmailAgentState)

workflow.add_node("input_parser", run_input_parser)
workflow.add_node("intent_detection", run_intent_detection)
workflow.add_node("tone_stylist", run_tone_stylist)
workflow.add_node("draft_writer", run_draft_writer)
workflow.add_node("personalization", run_personalization)
workflow.add_node("review", run_review)
workflow.add_node("router", run_router)

workflow.set_entry_point("input_parser")
workflow.add_conditional_edges("input_parser", route_after_input, {"intent_detection": "intent_detection", "end": END})
workflow.add_edge("intent_detection", "tone_stylist")
workflow.add_edge("tone_stylist", "draft_writer")
workflow.add_edge("draft_writer", "personalization")
workflow.add_edge("personalization", "review")
workflow.add_edge("review", "router")
workflow.add_conditional_edges("router", route_after_router, {"end": END, "draft_writer": "draft_writer"})

app: CompiledStateGraph = workflow.compile()


def run_email_pipeline(
    user_prompt: str,
    user_id: str,
    selected_tone: str,
    selected_intent: str = "",
    recipient_name: str = "",
    recipient_company: str = "",
) -> EmailAgentState:
    initial: EmailAgentState = {
        "user_prompt": user_prompt,
        "user_id": user_id,
        "selected_tone": selected_tone,
        "selected_intent": selected_intent,
        "recipient_name": recipient_name,
        "recipient_company": recipient_company,
        "parsed_input": {},
        "detected_intent": "",
        "tone_instructions": "",
        "raw_draft": "",
        "personalized_draft": "",
        "reviewed_draft": "",
        "final_email": "",
        "subject_line": "",
        "draft_components": {},
        "retry_count": 0,
        "fallback_triggered": False,
        "model_used": "openai",
        "validation_passed": False,
        "errors": [],
        "review_report": {},
        "user_profile": {},
        "draft_history": [],
        "routing_log": [],
    }
    result = app.invoke(initial)
    return result
