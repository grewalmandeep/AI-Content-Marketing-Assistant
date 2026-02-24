"""Shared state schema for the LangGraph email pipeline."""
from typing import TypedDict, List, Dict, Any


class EmailAgentState(TypedDict, total=False):
    # Input
    user_prompt: str
    user_id: str
    selected_tone: str
    selected_intent: str
    recipient_name: str
    recipient_company: str
    # Agent outputs
    parsed_input: Dict[str, Any]
    detected_intent: str
    tone_instructions: str
    raw_draft: str
    personalized_draft: str
    reviewed_draft: str
    final_email: str
    subject_line: str
    draft_components: Dict[str, str]
    # Control flow
    retry_count: int
    fallback_triggered: bool
    model_used: str
    validation_passed: bool
    errors: List[str]
    review_report: Dict[str, Any]
    # Memory
    user_profile: Dict[str, Any]
    draft_history: List[Dict[str, Any]]
    routing_log: List[Dict[str, Any]]
