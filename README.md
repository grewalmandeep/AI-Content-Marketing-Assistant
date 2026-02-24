# AI-Powered Email Assistant — Capstone Project

Production-ready **Python** implementation of the AI-Powered Email Assistant capstone: multi-agent pipeline (Input Parser, Intent Detection, Tone Stylist, Draft Writer, Personalization, Review, Router) with **LangGraph** orchestration, **Streamlit** UI, JSON memory, and optional MCP-style fallback routing.

## Quick start (Python)

```bash
cd email_assistant
python3 -m venv venv
source venv/bin/activate   # or venv\Scripts\activate on Windows
pip install -r requirements.txt
cp .env.example .env       # set OPENAI_API_KEY, optionally COHERE_API_KEY
streamlit run src/ui/streamlit_app.py
```

Open http://localhost:8501.

## Project layout

- **`email_assistant/`** — Main Python project:
  - **Blueprint:** `email_assistant/PROJECT_BLUEPRINT.md` — Full technical blueprint (architecture, agents, workflow, 2-week plan, deployment, evaluation matrix).
  - **Agents:** `email_assistant/src/agents/` — Input Parser, Intent Detection, Tone Stylist, Draft Writer, Personalization, Review, Router.
  - **Workflow:** `email_assistant/src/workflow/langgraph_flow.py` — LangGraph StateGraph and `run_email_pipeline()`.
  - **UI:** `email_assistant/src/ui/streamlit_app.py` — Streamlit app (tone/intent, preview, export, profile editor).
  - **Memory:** `email_assistant/src/memory/user_profiles.json` — User profiles and draft history.
  - **Config:** `email_assistant/config/mcp.yaml` — Models, routing, agents, memory.

## Capstone alignment

- **Business use case:** Productivity (faster drafts), tone control, personalization.
- **Tech stack:** LangGraph, GPT-4/Claude-style LLM (OpenAI + Cohere fallback), Streamlit, JSON user store, `mcp.yaml` control plane.
- **Deliverables:** Working prototype with prompt + tone/intent → editable draft; UI with preview and export; Router fallback and routing log; personalization memory; optional Docker/Streamlit Cloud.
- **Evaluation:** See `email_assistant/PROJECT_BLUEPRINT.md` §9 Evaluation Alignment Matrix and `email_assistant/README.md` for the evaluation checklist.

---

*There is also an older Node.js prototype in this repo (see `package.json`); the canonical implementation is the Python app in `email_assistant/`.*
