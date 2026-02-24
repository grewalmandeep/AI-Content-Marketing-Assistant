import logging

from ..state import EmailAgentState
from ..integrations.openai_client import OpenAIClient
from ..config import mcp as config

logger = logging.getLogger(__name__)


def run_review(state: EmailAgentState) -> EmailAgentState:
    logger.info("Running Review Agent...")
    draft = state.get("personalized_draft", "")
    if not draft:
        return {**state, "reviewed_draft": "", "validation_passed": False, "errors": list(state.get("errors", [])) + ["No draft to review"]}

    tone = state.get("selected_tone", "formal")
    intent = state.get("detected_intent", "information")
    word_limit = state.get("parsed_input", {}).get("word_limit")
    errors = list(state.get("errors", []))

    client = OpenAIClient()
    report = {
        "tone_score": 0.0,
        "grammar_issues": [],
        "coherence_score": 0.0,
        "word_count": len(draft.split()),
        "corrected_email": draft,
        "passed": True,
        "review_summary": "",
    }

    try:
        tone_prompt = f"Does this email match a {tone} tone? Score 1-10 and list violations. Email:\n{draft[:2000]}\nReturn JSON: score (float), violations (array of strings)."
        tone_out = client.complete_json(tone_prompt, system_prompt="Return only valid JSON.")
        report["tone_score"] = float(tone_out.get("score", 7))
        if report["tone_score"] < 7:
            report["grammar_issues"].extend(tone_out.get("violations", [])[:5])
            report["passed"] = False

        gram_prompt = f"List grammar/spelling/punctuation errors in this email. If none, return empty array. Email:\n{draft[:2000]}\nReturn JSON: errors_list (array of strings)."
        gram_out = client.complete_json(gram_prompt, system_prompt="Return only valid JSON.")
        issues = gram_out.get("errors_list", []) or gram_out.get("errors", [])
        if issues and not (len(issues) == 1 and "no error" in str(issues[0]).lower()):
            report["grammar_issues"].extend(issues[:10])
            report["passed"] = False

        coh_prompt = f"Does this email clearly communicate intent '{intent}'? Score 1-10. Email:\n{draft[:2000]}\nReturn JSON: score (float)."
        coh_out = client.complete_json(coh_prompt, system_prompt="Return only valid JSON.")
        report["coherence_score"] = float(coh_out.get("score", 7))
        if report["coherence_score"] < 7:
            report["passed"] = False

        if word_limit and report["word_count"] > int(word_limit) * 1.15:
            report["grammar_issues"].append(f"Length {report['word_count']} exceeds limit {word_limit}")
            report["passed"] = False

        if not report["passed"]:
            fix_prompt = f"Fix the following email. Address tone, grammar, and clarity. Return only the corrected full email text.\n\nOriginal:\n{draft}"
            try:
                corrected = client.complete(fix_prompt, system_prompt="You are an email editor. Output only the corrected email.", temperature=0.3, max_tokens=2000)
                report["corrected_email"] = corrected.strip() or draft
                report["passed"] = True
            except Exception:
                report["corrected_email"] = draft
        else:
            report["corrected_email"] = draft

        report["review_summary"] = f"Tone: {report['tone_score']}/10, Coherence: {report['coherence_score']}/10, Words: {report['word_count']}."
    except Exception as e:
        errors.append(f"Review failed: {e}")
        logger.exception("Review error")
        report["passed"] = False
        report["corrected_email"] = draft

    return {
        **state,
        "reviewed_draft": report["corrected_email"],
        "validation_passed": report["passed"],
        "review_report": report,
        "errors": errors,
        "model_used": client.model,
    }
