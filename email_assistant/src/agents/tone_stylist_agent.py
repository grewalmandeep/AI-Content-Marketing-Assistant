import os
import logging

from ..state import EmailAgentState
from ..integrations.openai_client import OpenAIClient
from ..config import mcp as config

logger = logging.getLogger(__name__)

TONE_RULES = {
    "formal": "Use professional salutations (Dear Mr./Ms./Dr.). Avoid contractions. Use passive voice where appropriate. Sign off: Sincerely, Best regards, Yours faithfully.",
    "casual": "Use first names. Contractions allowed. Conversational, warm language. Short sentences. Sign off: Thanks!, Cheers, Best.",
    "assertive": "Direct, confident language. Action-oriented verbs. Clear deadlines and expectations. No hedging. Sign off: Best regards, Regards.",
}


def _load_tone_sample(tone: str) -> str:
    base = os.path.dirname(os.path.abspath(__file__))
    path = os.path.join(base, "..", "..", "data", "tone_samples", f"{tone.lower()}.txt")
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        logger.warning("Could not load tone sample %s: %s", tone, e)
        return ""


def run_tone_stylist(state: EmailAgentState) -> EmailAgentState:
    logger.info("Running Tone Stylist Agent...")
    if state.get("errors"):
        return state

    tone = (state.get("selected_tone") or "formal").lower()
    intent = state.get("detected_intent", "information")
    user_profile = state.get("user_profile", {})
    errors = list(state.get("errors", []))

    rules = TONE_RULES.get(tone, TONE_RULES["formal"])
    sample = _load_tone_sample(tone)
    pref = user_profile.get("preferred_phrases", [])
    sign_off = user_profile.get("sign_off", "")

    combined = f"Apply {tone.upper()} tone.\n{rules}\nIntent: {intent}."
    if pref:
        combined += f"\nPreferred phrases: {', '.join(pref)}."
    if sign_off:
        combined += f"\nSign off: {sign_off}."
    if sample:
        combined += f"\n\nExample style:\n{sample[:1500]}"

    client = OpenAIClient()
    try:
        instructions = client.complete(
            f"Generate concise email style instructions (2-4 sentences) for the following. Output only the instructions, no JSON.\n\n{combined}",
            system_prompt="You are an email style guide generator.",
            temperature=config.agents.get("tone_stylist", {}).get("temperature", 0.3),
            max_tokens=500,
        )
        return {
            **state,
            "tone_instructions": instructions.strip() or combined,
            "errors": errors,
            "model_used": client.model,
        }
    except Exception as e:
        errors.append(f"Tone stylist failed: {e}")
        return {**state, "tone_instructions": combined, "errors": errors}
