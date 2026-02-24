import logging

from ..state import EmailAgentState
from ..integrations.openai_client import OpenAIClient
from ..config import mcp as config

logger = logging.getLogger(__name__)


def run_draft_writer(state: EmailAgentState) -> EmailAgentState:
    logger.info("Running Draft Writer Agent...")
    if state.get("errors"):
        return state

    parsed = state.get("parsed_input", {})
    intent = state.get("detected_intent", "information")
    tone_instructions = state.get("tone_instructions", "Write a professional email.")
    user_profile = state.get("user_profile", {})
    errors = list(state.get("errors", []))

    recipient_name = parsed.get("recipient_name") or state.get("recipient_name") or "Valued Recipient"
    recipient_company = parsed.get("recipient_company") or state.get("recipient_company") or ""
    key_points = parsed.get("key_points", [])
    constraints = parsed.get("constraints", [])
    word_limit = parsed.get("word_limit")
    sender_name = user_profile.get("name", "Sender")
    sender_company = user_profile.get("company", "")
    sender_role = user_profile.get("role", "")

    system = "You are a professional email copywriter. Generate a complete email. Return only valid JSON with: subject, greeting, body, call_to_action, closing, full_email (complete email text)."
    prompt = f"""Tone: {tone_instructions}
Intent: {intent}
Recipient: {recipient_name}, {recipient_company}
Key points: {', '.join(key_points) if key_points else 'General professional email'}
Constraints: {', '.join(constraints) if constraints else 'None'}
Word limit: {word_limit or 'None'}
Sender: {sender_name}, {sender_role}, {sender_company}

Output JSON: subject, greeting, body, call_to_action, closing, full_email."""

    use_fallback = state.get("fallback_triggered", False)
    client = OpenAIClient()
    if use_fallback:
        try:
            from ..integrations.cohere_client import CohereClient
            client = CohereClient()
        except Exception as e:
            logger.warning("Fallback Cohere not available: %s", e)

    temp = config.agents.get("draft_writer", {}).get("temperature", 0.7)
    try:
        out = client.complete_json(prompt, system_prompt=system)
        subject = out.get("subject", "No Subject")
        full_email = out.get("full_email", "")
        if not full_email:
            parts = [
                out.get("greeting", ""),
                out.get("body", ""),
                out.get("call_to_action", ""),
                out.get("closing", ""),
            ]
            full_email = "\n\n".join(p for p in parts if p)
        return {
            **state,
            "raw_draft": full_email,
            "subject_line": subject,
            "draft_components": {
                "greeting": out.get("greeting", ""),
                "opening_line": out.get("body", "").split("\n")[0] if out.get("body") else "",
                "body": out.get("body", ""),
                "call_to_action": out.get("call_to_action", ""),
                "closing": out.get("closing", ""),
                "signature": f"{sender_name}\n{sender_role}\n{sender_company}",
            },
            "errors": errors,
            "model_used": getattr(client, "model", "openai"),
        }
    except Exception as e:
        errors.append(f"Draft writing failed: {e}")
        logger.exception("Draft writer error")
        return {**state, "raw_draft": "", "subject_line": "Error", "errors": errors}
