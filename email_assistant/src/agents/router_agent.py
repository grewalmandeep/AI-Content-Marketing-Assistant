import datetime
import json
import os
import logging

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


def _save_final_to_history(state: EmailAgentState):
    user_id = state.get("user_id", "user_001")
    final_email = state.get("final_email", "")
    subject = state.get("subject_line", "")
    profiles = _load_profiles()
    if user_id not in profiles.get("users", {}):
        profiles.setdefault("users", {})[user_id] = {"draft_history": []}
    hist = profiles["users"][user_id].get("draft_history") or []
    hist.append({
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "subject_line": subject,
        "final_email": final_email,
        "recipient_name": state.get("recipient_name", ""),
        "recipient_company": state.get("recipient_company", ""),
        "detected_intent": state.get("detected_intent", ""),
        "selected_tone": state.get("selected_tone", ""),
        "validation_passed": state.get("validation_passed", False),
    })
    profiles["users"][user_id]["draft_history"] = hist[-config.memory.get("max_history_per_user", 10):]
    _save_profiles(profiles)


def run_router(state: EmailAgentState) -> EmailAgentState:
    logger.info("Running Router Agent...")
    routing_log = list(state.get("routing_log", []))
    final_email = state.get("reviewed_draft") or state.get("personalized_draft") or state.get("raw_draft") or ""
    state = {**state, "final_email": final_email, "routing_log": routing_log}

    validation_passed = state.get("validation_passed", False)
    retry_count = state.get("retry_count", 0)
    max_retries = config.routing.get("max_retries", 2)
    fallback_triggered = state.get("fallback_triggered", False)

    entry = {
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "decision": "",
        "model_used": state.get("model_used", ""),
        "retry_count": retry_count,
        "validation_passed": validation_passed,
    }

    if validation_passed:
        entry["decision"] = "END (validation passed)"
        routing_log.append(entry)
        _save_final_to_history(state)
        return {**state, "routing_log": routing_log, "_next_node": "end"}

    if retry_count < max_retries:
        entry["decision"] = f"RETRY draft_writer (attempt {retry_count + 1})"
        routing_log.append(entry)
        return {**state, "retry_count": retry_count + 1, "routing_log": routing_log, "_next_node": "draft_writer"}

    if not fallback_triggered:
        entry["decision"] = "FALLBACK to Cohere"
        routing_log.append(entry)
        return {**state, "fallback_triggered": True, "model_used": "cohere", "routing_log": routing_log, "_next_node": "draft_writer"}

    entry["decision"] = "END (max retries and fallback used)"
    routing_log.append(entry)
    _save_final_to_history(state)
    return {**state, "routing_log": routing_log, "_next_node": "end"}


def route_after_router(state: EmailAgentState) -> str:
    """Return the next node name for LangGraph conditional edge."""
    return state.get("_next_node", "end")
