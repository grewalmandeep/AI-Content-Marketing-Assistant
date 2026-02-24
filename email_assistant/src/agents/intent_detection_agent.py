import logging

INTENTS = [
    "outreach", "follow_up", "apology", "information",
    "request", "negotiation", "rejection", "thank_you"
]

from ..state import EmailAgentState
from ..integrations.openai_client import OpenAIClient
from ..config import mcp as config

logger = logging.getLogger(__name__)


def run_intent_detection(state: EmailAgentState) -> EmailAgentState:
    logger.info("Running Intent Detection Agent...")
    if state.get("errors"):
        return state

    user_prompt = state.get("user_prompt", "")
    parsed_input = state.get("parsed_input", {})
    selected_intent = (state.get("selected_intent") or "").strip().lower()
    errors = list(state.get("errors", []))

    client = OpenAIClient()
    system = "You classify email intents. Return only valid JSON with keys: intent (string), confidence (float), reasoning (string)."
    prompt = f"Classify this email request into exactly one category: {', '.join(INTENTS)}\n\nRequest: {user_prompt}\nParsed context: {parsed_input}\n\nReturn JSON: intent, confidence (0-1), reasoning."

    try:
        if selected_intent and selected_intent in INTENTS:
            prompt = f"User selected intent: {selected_intent}. Confirm or suggest a different intent.\n{prompt}"
        out = client.complete_json(prompt, system_prompt=system)
        intent = (out.get("intent") or "unknown").lower()
        if intent not in INTENTS:
            intent = "unknown"
        confidence = float(out.get("confidence", 0))
        reasoning = out.get("reasoning", "")

        parsed = dict(parsed_input)
        parsed["detected_intent_confidence"] = confidence
        parsed["detected_intent_reasoning"] = reasoning

        return {
            **state,
            "detected_intent": intent,
            "parsed_input": parsed,
            "errors": errors,
            "model_used": client.model,
        }
    except Exception as e:
        errors.append(f"Intent detection failed: {e}")
        logger.exception("Intent detection error")
        return {**state, "detected_intent": "unknown", "errors": errors}
