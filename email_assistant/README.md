# AI-Powered Email Assistant

Multi-agent email pipeline using LangGraph, OpenAI GPT-4o, and Streamlit.

## Setup

1. Create a virtualenv and install deps:
   ```bash
   cd email_assistant
   python3 -m venv venv
   source venv/bin/activate  # or venv\Scripts\activate on Windows
   pip install -r requirements.txt
   ```

2. Copy `.env.example` to `.env` and set:
   - `OPENAI_API_KEY`
   - `COHERE_API_KEY` (optional, for fallback)

3. Run the app:
   ```bash
   streamlit run src/ui/streamlit_app.py
   ```

## Pipeline

1. **Input parser** – Extracts recipient, company, key points, constraints, word limit, urgency.
2. **Intent detection** – Classifies intent (outreach, follow_up, apology, information, request, negotiation, rejection, thank_you).
3. **Tone stylist** – Builds style instructions (formal / casual / assertive) from `data/tone_samples/`.
4. **Draft writer** – Generates subject and body (OpenAI or Cohere fallback).
5. **Personalization** – Injects sender profile and saves to `src/memory/user_profiles.json`.
6. **Review** – Validates tone, grammar, coherence, length; corrects once if needed.
7. **Router** – On pass → end; on fail → retry draft (then fallback to Cohere if still failing).

## Validation test

From project root with `.env` set:

```bash
cd email_assistant
python -c "
from src.workflow.langgraph_flow import run_email_pipeline
r = run_email_pipeline(
    user_prompt='Write an email to Sarah at Google following up on our product demo last week. I want to schedule a next steps call.',
    user_id='user_001',
    selected_tone='formal',
    selected_intent='follow_up',
    recipient_name='Sarah',
    recipient_company='Google'
)
assert r.get('validation_passed') == True
assert r.get('subject_line')
assert r.get('final_email')
assert r.get('detected_intent') == 'follow_up'
assert 'Sarah' in (r.get('final_email') or '')
print('OK')
print('Subject:', r['subject_line'])
"
```

## Docker

```bash
cd email_assistant
cp .env.example .env
# edit .env with API keys
docker-compose up --build
```

Open http://localhost:8501.

Run the application: https://aicontentmarketemail.streamlit.app/

## Evaluation readiness

- **Functionality:** Drafts are intent/tone-aware; Review agent enforces tone, grammar, coherence.
- **Agentic architecture:** Seven distinct agents; LangGraph `StateGraph` with conditional edges; Router implements retry + fallback to Cohere.
- **User experience:** Tone/intent dropdowns, live preview, editable body, export TXT/PDF, profile editor in sidebar.
- **Routing & MCP:** `config/mcp.yaml`; Router logs decisions to `routing_log`; fallback model used when validation fails after retries.
- **Innovation:** Custom tones + `data/tone_samples/`; personalization memory in `user_profiles.json` (draft_history, sign_off, preferred_phrases).
- **Documentation:** See `PROJECT_BLUEPRINT.md` for architecture, agent design, workflow, deployment, and evaluation matrix.
