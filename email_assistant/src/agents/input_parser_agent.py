import os
import logging

from ..state import EmailAgentState
from ..integrations.openai_client import OpenAIClient
from ..config import mcp as config

logger = logging.getLogger(__name__)


def run_input_parser(state: EmailAgentState) -> EmailAgentState:
    logger.info("Running Input Parser Agent...")
    user_prompt = state.get("user_prompt", "")
    errors = list(state.get("errors", []))

    if not user_prompt or not user_prompt.strip():
        errors.append("User prompt cannot be empty.")
        return {**state, "errors": errors}

    client = OpenAIClient()
    agent_cfg = config.agents.get("input_parser", {})
    model_cfg = config.models.get(agent_cfg.get("model", "primary"), {})

    system = "You are an input parser for an email assistant. Extract structured information. Return only valid JSON."
    prompt = f"""Extract structured information from this user request: {user_prompt}

Return a JSON object with: recipient_name (string), recipient_company (string), key_points (array of strings), constraints (array of strings), word_limit (integer or null), urgency_level (one of: Normal, Urgent, Low Priority)."""

    try:
        out = client.complete_json(prompt, system_prompt=system)
        recipient_name = out.get("recipient_name") or ""
        recipient_company = out.get("recipient_company") or ""
        key_points = out.get("key_points") or []
        constraints = out.get("constraints") or []
        word_limit = out.get("word_limit")
        urgency_level = out.get("urgency_level") or "Normal"

        if not recipient_name and not recipient_company and not key_points and len(user_prompt.strip()) < 10:
            errors.append("Please provide more context about the recipient or email content.")

        parsed = {
            "recipient_name": recipient_name,
            "recipient_company": recipient_company,
            "key_points": key_points,
            "constraints": constraints,
            "word_limit": word_limit,
            "urgency_level": urgency_level,
        }
        new_state = {**state, "parsed_input": parsed, "errors": errors, "model_used": client.model}
        if recipient_name and not state.get("recipient_name"):
            new_state["recipient_name"] = recipient_name
        if recipient_company and not state.get("recipient_company"):
            new_state["recipient_company"] = recipient_company
        return new_state
    except Exception as e:
        errors.append(f"Input parsing failed: {e}")
        logger.exception("Input parser error")
        return {**state, "errors": errors, "parsed_input": {}}
