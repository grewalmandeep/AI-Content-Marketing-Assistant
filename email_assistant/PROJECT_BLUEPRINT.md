# AI-Powered Email Assistant — Technical Project Blueprint

## 1. Executive Summary

This blueprint describes a **production-oriented, multi-agent AI Email Assistant** that reduces email drafting time from 15–20 minutes to under 2 minutes while keeping tone consistent and context-aware. The system uses a **modular agentic architecture** orchestrated with **LangGraph**, a **Streamlit** UI, a **JSON-backed memory layer** for user profiles and draft history, and optional **MCP-style routing** (primary/fallback models, retry logic). It satisfies the capstone requirements: Input Parser, Intent Detection, Tone Stylist, Draft Writer, Personalization, Review & Validator, and Routing & Memory agents, with clear fallback handling and evaluation alignment.

**Key outcomes:** Accurate tone-aligned drafts, distinct modular agents, LangGraph workflow, fallback/retry routing, intuitive UI with live preview and export, personalization memory, and documentation suitable for submission and deployment.

---

## 2. High-Level Architecture Diagram (Text)

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           STREAMLIT UI LAYER                                      │
│  Context + tone/intent selectors | Prompt input | Preview/editor | Export TXT/PDF │
└───────────────────────────────────────────┬─────────────────────────────────────┘
                                            │
                                            ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                        LANGGRAPH ORCHESTRATION                                    │
│  Entry → input_parser → [conditional] → intent_detection → tone_stylist          │
│         → draft_writer → personalization → review → router → [conditional]       │
│         → END | RETRY draft_writer (with optional fallback model)                 │
└───────────────────────────────────────────┬─────────────────────────────────────┘
                                            │
        ┌───────────────────────────────────┼───────────────────────────────────┐
        ▼                   ▼                ▼                ▼                   ▼
┌───────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│ Input Parser  │  │ Intent       │  │ Tone Stylist │  │ Draft Writer │  │ Personalize  │
│ (validate,    │  │ Detection    │  │ (formal/     │  │ (LLM body +  │  │ (profile +   │
│ extract)      │  │ (classify)   │  │ casual/      │  │ subject)     │  │ history)     │
└───────────────┘  └──────────────┘  │ assertive)   │  └──────────────┘  └──────────────┘
                                     └──────────────┘
        │                   │                │                │                   │
        └───────────────────┴────────────────┴────────────────┴───────────────────┘
                                            │
                    ┌───────────────────────┼───────────────────────┐
                    ▼                       ▼                       ▼
            ┌──────────────┐        ┌──────────────┐        ┌──────────────┐
            │ Review       │        │ Router       │        │ Memory       │
            │ (tone/       │        │ (retry/      │        │ (user_       │
            │ grammar/     │        │ fallback)    │        │ profiles.json)│
            │ coherence)   │        │              │        │ draft_history │
            └──────────────┘        └──────────────┘        └──────────────┘
                                            │
                    ┌───────────────────────┴───────────────────────┐
                    ▼                                               ▼
            ┌──────────────┐                                ┌──────────────┐
            │ MCP Config   │                                │ LLM Clients  │
            │ mcp.yaml     │                                │ OpenAI /     │
            │ (models,     │                                │ Cohere       │
            │ routing)     │                                │ (fallback)   │
            └──────────────┘                                └──────────────┘
```

**Data flow:** User prompt + tone/intent/recipient → shared **EmailAgentState** (TypedDict) → each agent reads/updates state → Router decides END or RETRY (with optional Cohere fallback) → final email and routing log persisted; draft history and profile updates written to JSON.

---

## 3. Agent-by-Agent Technical Design

| Agent | Input (from state) | Output (into state) | Implementation notes |
|-------|-------------------|---------------------|----------------------|
| **Input Parsing** | `user_prompt` | `parsed_input` (recipient_name, recipient_company, key_points, constraints, word_limit, urgency_level); `errors` | Validates non-empty prompt; uses LLM with JSON schema to extract structured fields; appends to `errors` and can short-circuit to END if invalid. |
| **Intent Detection** | `user_prompt`, `parsed_input`, `selected_intent` | `detected_intent`, `parsed_input` (confidence, reasoning) | Classification over fixed intents (outreach, follow_up, apology, information, request, negotiation, rejection, thank_you); respects user override; returns JSON: intent, confidence, reasoning. |
| **Tone Stylist** | `selected_tone`, `detected_intent`, `user_profile` | `tone_instructions` | Tokenized rules (formal/casual/assertive) + optional tone_samples/*.txt + profile preferred_phrases/sign_off; produces short style instructions for Draft Writer. |
| **Draft Writer** | `parsed_input`, `detected_intent`, `tone_instructions`, `user_profile`, `fallback_triggered` | `raw_draft`, `subject_line`, `draft_components` | Uses primary (OpenAI) or fallback (Cohere) when `fallback_triggered`; structured JSON output: subject, greeting, body, call_to_action, closing, full_email. |
| **Personalization** | `raw_draft`, `user_id`, recipient/metadata | `personalized_draft`, `user_profile`, draft_history append | Loads profile from JSON; replaces placeholders; applies sign_off preference; appends draft to user’s `draft_history` (capped by config). |
| **Review & Validator** | `personalized_draft`, `selected_tone`, `detected_intent`, `parsed_input.word_limit` | `reviewed_draft`, `validation_passed`, `review_report` | Three checks: tone alignment (score), grammar/spelling (errors_list), coherence (score); optional word_limit check; if failed, calls LLM to produce corrected_email; report has tone_score, coherence_score, word_count, grammar_issues. |
| **Routing & Memory** | `reviewed_draft`, `validation_passed`, `retry_count`, `fallback_triggered` | `final_email`, `routing_log`, `retry_count`, `fallback_triggered`, _next_node | If validation passed → END, persist final to history. Else if retries left → RETRY to draft_writer. Else if fallback not used → set fallback_triggered, RETRY. Else → END and persist. Logs each decision to `routing_log`. |

**Fallback logic:** Router triggers Cohere only when validation has failed and max retries exhausted; Draft Writer reads `fallback_triggered` and swaps to CohereClient for the next attempt.

---

## 4. Data & Memory Design

- **EmailAgentState (TypedDict):** Single shared state object for the graph. Fields: user_prompt, user_id, selected_tone, selected_intent, recipient_name/company; parsed_input, detected_intent, tone_instructions; raw_draft, personalized_draft, reviewed_draft, final_email, subject_line, draft_components; retry_count, fallback_triggered, model_used, validation_passed, errors, review_report; user_profile, draft_history, routing_log.
- **User profile store:** JSON file at `config.memory.persist_path` (e.g. `src/memory/user_profiles.json`). Schema per user: `name`, `email`, `company`, `role`, `preferred_tone`, `preferred_phrases` (list), `sign_off`, `draft_history` (list of entries). Each draft entry: timestamp, subject_line, final_email, recipient_name/company, detected_intent, selected_tone, (optional validation_passed).
- **Persistence:** Profile load/save in Personalization and Router; path resolved from project root + `persist_path`. `max_history_per_user` caps draft_history length.
- **MCP config (mcp.yaml):** models (primary/fallback with provider, model, temperature, max_tokens, timeout); routing (max_retries, fallback_on_timeout, fallback_on_error, log_all_requests); agents (per-agent model and temperature); memory (max_history_per_user, persist_path).

---

## 5. Workflow Execution Flow

1. **Invoke** `run_email_pipeline(user_prompt, user_id, selected_tone, selected_intent, recipient_name, recipient_company)` with initial state.
2. **input_parser:** Validate prompt; extract structured fields; on error set errors and transition to END.
3. **intent_detection:** Classify intent; merge confidence/reasoning into parsed_input.
4. **tone_stylist:** Build tone instructions from tone + intent + profile + samples.
5. **draft_writer:** Generate subject + full email (OpenAI or Cohere if fallback).
6. **personalization:** Inject profile, sign_off; append draft to user’s history; write profiles JSON.
7. **review:** Tone/grammar/coherence checks; optionally fix and set reviewed_draft and validation_passed.
8. **router:** If validation_passed → END, persist final. Else if retry_count < max_retries → increment retry_count, go to draft_writer. Else if not fallback_triggered → set fallback_triggered, go to draft_writer. Else → END, persist. Append entry to routing_log each time.
9. **Output:** State containing final_email, subject_line, review_report, routing_log, errors (if any).

---

## 6. Folder Structure

```
email_assistant/
├── src/
│   ├── __init__.py
│   ├── state.py                    # EmailAgentState TypedDict
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── input_parser_agent.py
│   │   ├── intent_detection_agent.py
│   │   ├── tone_stylist_agent.py
│   │   ├── draft_writer_agent.py
│   │   ├── personalization_agent.py
│   │   ├── review_agent.py
│   │   └── router_agent.py
│   ├── workflow/
│   │   ├── __init__.py
│   │   └── langgraph_flow.py       # StateGraph, compile(), run_email_pipeline()
│   ├── ui/
│   │   └── streamlit_app.py        # Streamlit UI: prompt, tone/intent, preview, export
│   ├── memory/                     # Runtime use; persist_path points here
│   │   └── user_profiles.json
│   ├── integrations/
│   │   ├── __init__.py
│   │   ├── openai_client.py        # OpenAIClient: complete, complete_json
│   │   └── cohere_client.py       # CohereClient: complete, complete_json (fallback)
│   └── config/
│       ├── __init__.py
│       └── mcp.py                  # Load mcp.yaml; expose models, agents, routing, memory
├── data/
│   └── tone_samples/
│       ├── formal.txt
│       ├── casual.txt
│       └── assertive.txt
├── config/
│   └── mcp.yaml                    # Models, routing, agents, memory
├── requirements.txt
├── .env.example
├── Dockerfile
├── docker-compose.yml              # Optional
├── README.md
└── PROJECT_BLUEPRINT.md            # This document
```

---

## 7. 2-Week Implementation Plan

**Week 1 — Core agent workflow**

| Day | Focus | Tasks |
|-----|--------|-------|
| 1 | Setup + Input | Project scaffold, state.py, mcp.yaml; Input Parser agent (validate, extract JSON). |
| 2 | Intent + Tone | Intent Detection agent (classification prompts); Tone Stylist (3 modes, tone_samples). |
| 3 | Draft + Personalization | Draft Writer (structured JSON, subject + full_email); Personalization (load profile, replace placeholders, append draft_history, persist JSON). |
| 4 | Review + Router | Review agent (tone/grammar/coherence, corrected_email); Router (retry/fallback, routing_log, persist final). |
| 5 | LangGraph | StateGraph with all nodes and conditional edges (input_parser → end|intent; router → end|draft_writer). |

**Week 2 — UI, memory, deployment**

| Day | Focus | Tasks |
|-----|--------|-------|
| 6 | Streamlit UI | Context + tone/intent selectors; prompt input; run pipeline; preview + editable textarea; copy/export TXT and PDF. |
| 7 | Memory + UX | Ensure profile load from correct path; recent drafts in sidebar; optional profile editor; log draft edits for personalization. |
| 8 | MCP + Fallback | Verify mcp.yaml usage in agents; test fallback path (e.g. force validation fail); routing_log visible in UI. |
| 9 | Polish + Docs | README (quick start, env vars, run instructions); agent flow and prompt logic notes; evaluation checklist. |
| 10 | Deploy | Dockerfile + Streamlit run; optional Streamlit Cloud or local; smoke test end-to-end. |

---

## 8. Deployment Strategy

- **Local:** `pip install -r requirements.txt`, set `.env` (OPENAI_API_KEY, optionally COHERE_API_KEY), `streamlit run src/ui/streamlit_app.py` from project root (with PYTHONPATH or run from `email_assistant/`).
- **Docker:** Build from Dockerfile; CMD runs Streamlit on 8501; mount or volume for `src/memory` if persisting profiles across restarts.
- **Streamlit Cloud:** Connect repo, set secrets (OPENAI_API_KEY, COHERE_API_KEY), main file `src/ui/streamlit_app.py`; ensure working directory and PYTHONPATH so config and memory paths resolve.
- **Production hardening:** Use env-based config; restrict CORS if adding API layer; consider Redis/Pinecone for memory at scale; rate limiting and auth for multi-tenant.

---

## 9. Evaluation Alignment Matrix

| Criterion | Weight | How the project addresses it |
|-----------|--------|------------------------------|
| **Functionality** | 30% | Drafts are accurate and relevant (Input Parser + Intent + Draft Writer); tone-aligned (Tone Stylist + Review tone score and correction). |
| **Agentic architecture** | 25% | Distinct modules per agent; LangGraph StateGraph with conditional edges; fallback (Router → Cohere) and retry loop. |
| **User experience** | 20% | Streamlit UI with tone/intent dropdowns, real-time preview, editable body, copy/export TXT/PDF. |
| **Routing & MCP** | 10% | Fallback on validation failure; routing_log records decision and model; mcp.yaml drives model/routing config. |
| **Innovation** | 10% | Custom tones + tone_samples; personalization memory (profiles + draft_history); optional template extension. |
| **Documentation** | 10% | README (setup, run, env); PROJECT_BLUEPRINT (architecture, agents, workflow, deployment); inline agent/prompt logic. |

---

## 10. Optional Enhancements

- **Additional tones/templates:** More entries in TONE_RULES and tone_samples; template library in `data/templates/` with placeholders.
- **LiteLLM / LangSmith:** Route requests through LiteLLM for multi-provider abstraction; LangSmith tracing for debugging and eval.
- **Redis/Pinecone memory:** Replace JSON with Redis for session cache and Pinecone for semantic draft search.
- **Auth and multi-tenancy:** User login; per-user profile and history; rate limits per user.
- **Email sending:** Optional integration (e.g. SendGrid) to send from UI with “Send” button.
- **A/B tone comparison:** Generate two drafts (e.g. formal vs casual) and show side-by-side in UI.

---

*Blueprint aligned to the AI-Powered Email Assistant capstone document and evaluation criteria. Implementation lives in `email_assistant/` with LangGraph orchestration, Streamlit UI, and JSON memory.*
