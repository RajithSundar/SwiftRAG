import streamlit as st
import uuid
from query import run_visa_consultation

st.set_page_config(page_title="SwiftVisa AI", page_icon="🌎", layout="wide")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
}
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
.stTextInput > div > div > input {
    border-radius: 8px;
}
.stChatInput > div {
    border-radius: 12px;
    border: 1px solid #1a5f7a;
}
[data-testid="stSidebar"] {
    border-right: 1px solid #2e3b4e;
}
h1, h2, h3 {
    color: #38bdf8 !important;
}
.stMetric {
    background: #1e293b;
    padding: 10px;
    border-radius: 8px;
    border-left: 4px solid #38bdf8;
}
</style>
""", unsafe_allow_html=True)

if "thread_id" not in st.session_state:
    st.session_state.thread_id = str(uuid.uuid4())[:8]
if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": "Hi! I'm SwiftVisa AI. I'm here to help evaluate your US/UK visa eligibility. To get started, what kind of visa are you applying for, and what is your nationality?"}]
if "info" not in st.session_state:
    st.session_state.info = {}
if "end_session" not in st.session_state:
    st.session_state.end_session = False  

st.title("SwiftVisa AI")
st.caption("AI-powered pre-screening. Not official legal advice.")

with st.sidebar:
    st.header("Profile")
    has_info = False
    for key, value in st.session_state.info.items():
        if value and str(value).lower() not in ["", "unknown", "none"]:
            has_info = True
            st.markdown(f"**{key.replace('_', ' ').title()}:**\n<div style='color: #38bdf8; font-weight: 600; font-size: 1.1em; padding-bottom: 8px;'>{value}</div>", unsafe_allow_html=True)
    if not has_info:
        st.info("Your visa profile parameters (Age, Nationality, Financials, etc.) will dynamically populate here as we chat.")

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg.get("relevance") or msg.get("confidence"):
            cols = st.columns(2)
            cols[0].metric("Relevance", f"{msg.get('relevance', 0)}%")
            cols[1].metric("Confidence", f"{msg.get('confidence', 0)}%")
        if msg.get("sources"):
            with st.expander("Sources"):
                for s in set(msg["sources"]):
                    st.caption(s)
        if msg.get("end_session"):
            st.divider()
            st.subheader("📋 Final Visa Assessment")
            score = msg.get("confidence", 0)
            col1, col2 = st.columns([1, 2])
            with col1:
                if score >= 80:
                    delta_color = "normal"
                    status = "High Probability"
                elif score >= 50:
                    delta_color = "off"
                    status = "Moderate Risk"
                else:
                    delta_color = "inverse"
                    status = "High Risk (214b)"
                st.metric(label="Visa Approval Confidence", value=f"{score}%", delta=status, delta_color=delta_color)
            with col2:
                st.progress(score / 100.0)
                st.caption("This score is calculated based on alignment with US Immigration policy, financial verifiability, and intent indicators.")
            st.info("This consultation has concluded. Please refresh the page to start a new profile audit.")

if not st.session_state.end_session:
    prompt = st.chat_input("Message...")
    if prompt:
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
        with st.spinner("Analyzing..."):
            res = run_visa_consultation(prompt, st.session_state.thread_id)
        st.session_state.info = res.get("info", {})
        st.session_state.end_session = res.get("end_session", False)
        st.session_state.messages.append({
            "role": "assistant",
            "content": res.get("answer", ""),
            "relevance": res.get("relevance", 0),
            "confidence": res.get("confidence", 0),
            "sources": res.get("sources", []),
            "end_session": res.get("end_session", False)
        })
        st.rerun()