import base64
import json
import os
import sys

# Ensure project root is on path when running as streamlit run src/ui/streamlit_app.py
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_src = os.path.dirname(_SCRIPT_DIR)
if _src not in sys.path:
    sys.path.insert(0, os.path.dirname(_src))

import streamlit as st

from src.state import EmailAgentState
from src.workflow.langgraph_flow import run_email_pipeline
from src.config import mcp as config


def _load_profiles():
    persist = config.memory.get("persist_path", "src/memory/user_profiles.json")
    path = os.path.join(_project_root(), persist)
    try:
        if os.path.isfile(path):
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return {"users": {}}


def _project_root():
    # __file__ = .../email_assistant/src/ui/streamlit_app.py -> go up to email_assistant
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _save_profiles(profiles):
    persist = config.memory.get("persist_path", "src/memory/user_profiles.json")
    path = os.path.join(_project_root(), persist)
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(profiles, f, indent=2)
    except Exception:
        pass


st.set_page_config(layout="wide", page_title="AI Email Assistant")

if "result_state" not in st.session_state:
    st.session_state.result_state = None
if "user_id" not in st.session_state:
    st.session_state.user_id = "user_001"

# Sidebar
with st.sidebar:
    st.title("AI Email Assistant")
    st.caption("Multi-agent pipeline: parse → intent → tone → draft → personalize → review → route")
    st.session_state.user_id = st.selectbox("User", ["user_001", "user_002"], index=0)
    profiles = _load_profiles()
    users = profiles.get("users", {})
    up = users.get(st.session_state.user_id, {})

    st.subheader("Profile")
    with st.expander("Edit profile", expanded=False):
        name = st.text_input("Name", value=up.get("name", ""), key="profile_name")
        company = st.text_input("Company", value=up.get("company", ""), key="profile_company")
        role = st.text_input("Role", value=up.get("role", ""), key="profile_role")
        sign_off = st.text_input("Sign-off", value=up.get("sign_off", "Best regards"), key="profile_signoff")
        if st.button("Save profile"):
            if st.session_state.user_id not in users:
                users[st.session_state.user_id] = {"draft_history": []}
            users[st.session_state.user_id].update({
                "name": name or "Sender",
                "company": company,
                "role": role,
                "sign_off": sign_off or "Best regards",
                "preferred_phrases": users[st.session_state.user_id].get("preferred_phrases", []),
                "preferred_tone": users[st.session_state.user_id].get("preferred_tone", "formal"),
            })
            _save_profiles({"users": users})
            st.success("Profile saved.")
            st.rerun()
    st.text(f"Name: {up.get('name', '')}")
    st.text(f"Company: {up.get('company', '')}")
    hist = up.get("draft_history", [])[-5:]
    st.subheader("Recent drafts")
    for h in reversed(hist):
        st.caption(f"{h.get('subject_line', '')[:40]}...")

# Main
st.header("Compose Email")

user_prompt = st.text_area(
    "Describe your email",
    height=120,
    placeholder="e.g. Write an email to Sarah at Google following up on our product demo last week. I want to schedule a next steps call.",
)
col1, col2, col3 = st.columns(3)
with col1:
    tone = st.selectbox("Tone", ["formal", "casual", "assertive"], index=0)
with col2:
    intent_sel = st.selectbox("Intent", ["Auto-Detect"] + ["outreach", "follow_up", "apology", "information", "request", "negotiation", "rejection", "thank_you"], index=0)
with col3:
    urgency = st.selectbox("Urgency", ["Normal", "Urgent", "Low Priority"], index=0)
col4, col5 = st.columns(2)
with col4:
    recipient_name = st.text_input("Recipient Name", "")
with col5:
    recipient_company = st.text_input("Recipient Company", "")
word_limit = st.slider("Word limit", 50, 500, 150, 10)

if st.button("Generate Email", type="primary"):
    if not user_prompt.strip():
        st.error("Please enter a description.")
    else:
        with st.spinner("Running pipeline..."):
            try:
                intent = "" if intent_sel == "Auto-Detect" else intent_sel
                result = run_email_pipeline(
                    user_prompt=user_prompt,
                    user_id=st.session_state.user_id,
                    selected_tone=tone,
                    selected_intent=intent,
                    recipient_name=recipient_name,
                    recipient_company=recipient_company,
                )
                st.session_state.result_state = result
            except Exception as e:
                st.error(str(e))
                st.session_state.result_state = {"errors": [str(e)], "final_email": "", "subject_line": ""}
        st.rerun()

res = st.session_state.result_state
if res:
    st.divider()
    st.subheader("Email Preview")
    subject = res.get("subject_line", "")
    body = res.get("final_email", "")
    if subject:
        st.markdown(f"**Subject:** {subject}")
    edited = st.text_area("Body", value=body or "(No email generated)", height=350, key="preview_body")
    errs = res.get("errors", [])
    if errs:
        for e in errs:
            st.warning(e)
    st.caption(f"Words: {len((edited or '').split())}  |  Tone: {res.get('selected_tone', '')}  |  Intent: {res.get('detected_intent', '')}  |  Model: {res.get('model_used', '')}")
    if res.get("fallback_triggered"):
        st.caption("Fallback model was used.")
    # Download TXT
    st.download_button("Download .txt", data=edited or "", file_name="email.txt", mime="text/plain")
    # PDF via fpdf2
    try:
        from fpdf import FPDF
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Helvetica", size=11)
        text = (subject + "\n\n" + (edited or ""))[:4000]
        pdf.multi_cell(0, 8, text)
        out = pdf.output()
        st.download_button("Download .pdf", data=out if isinstance(out, bytes) else out.encode("latin-1", errors="replace"), file_name="email.pdf", mime="application/pdf")
    except Exception:
        pass
    with st.expander("Validation report"):
        rep = res.get("review_report", {})
        if rep:
            st.write("Tone score:", rep.get("tone_score"), "/ 10")
            st.write("Coherence:", rep.get("coherence_score"), "/ 10")
            st.write("Word count:", rep.get("word_count"))
            if rep.get("grammar_issues"):
                st.write("Issues:", rep.get("grammar_issues"))
        st.json(res.get("routing_log", []))
