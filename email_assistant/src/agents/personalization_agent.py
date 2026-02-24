import os
import json
import datetime
import logging
import re

from ..state import EmailAgentState
from ..config import mcp as config

logger = logging.getLogger(__name__)


def _load_profiles():
    persist = config.memory.get("persist_path", "src/memory/user_profiles.json")
    path = os.path.join(config.PROJECT_ROOT, persist)
    try:
        if os.path.isfile(path):
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception as e:
        logger.warning("Load user profiles failed: %s", e)
    return {"users": {}}


def _save_profiles(profiles: dict):
    persist = config.memory.get("persist_path", "src/memory/user_profiles.json")
    path = os.path.join(config.PROJECT_ROOT, persist)
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(profiles, f, indent=2)
    except Exception as e:
        logger.warning("Save user profiles failed: %s", e)


def run_personalization(state: EmailAgentState) -> EmailAgentState:
    logger.info("Running Personalization Agent...")
    raw_draft = state.get("raw_draft", "")
    if not raw_draft:
        return {**state, "personalized_draft": "", "errors": list(state.get("errors", [])) + ["Raw draft is empty"]}

    user_id = state.get("user_id", "user_001")
    recipient_name = state.get("recipient_name", "")
    recipient_company = state.get("recipient_company", "")
    detected_intent = state.get("detected_intent", "information")
    errors = list(state.get("errors", []))

    all_profiles = _load_profiles()
    user_profile = all_profiles.get("users", {}).get(user_id, {})
    state = {**state, "user_profile": user_profile}

    sender_name = user_profile.get("name", "Sender")
    sender_company = user_profile.get("company", "")
    sender_role = user_profile.get("role", "")
    sign_off = user_profile.get("sign_off", "Best regards")

    personalized = raw_draft
    personalized = personalized.replace("{sender_name}", sender_name)
    personalized = personalized.replace("{sender_company}", sender_company)
    personalized = personalized.replace("{sender_role}", sender_role)
    if sign_off and sign_off.lower() not in personalized.lower():
        for closing in ["Best regards", "Sincerely", "Thanks", "Cheers", "Regards"]:
            if closing.lower() in personalized.lower():
                personalized = re.sub(r"\b" + re.escape(closing) + r"\b", sign_off, personalized, flags=re.IGNORECASE, count=1)
                break

    draft_entry = {
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "subject_line": state.get("subject_line", ""),
        "final_email": personalized,
        "recipient_name": recipient_name,
        "recipient_company": recipient_company,
        "detected_intent": detected_intent,
        "selected_tone": state.get("selected_tone", ""),
    }
    if user_id not in all_profiles.get("users", {}):
        all_profiles.setdefault("users", {})[user_id] = user_profile
    hist = all_profiles["users"][user_id].get("draft_history") or []
    hist.append(draft_entry)
    max_hist = config.memory.get("max_history_per_user", 10)
    all_profiles["users"][user_id]["draft_history"] = hist[-max_hist:]
    _save_profiles(all_profiles)

    return {
        **state,
        "personalized_draft": personalized,
        "errors": errors,
    }
