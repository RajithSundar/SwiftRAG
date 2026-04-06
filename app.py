import streamlit as st
import uuid
from query import run_visa_consultation

st.set_page_config(page_title="SwiftVisa AI", layout="wide")

# init session state 
if "thread_id" not in st.session_state: st.session_state.thread_id = str(uuid.uuid4())[:8]
if "messages" not in st.session_state: st.session_state.messages = []
if "info" not in st.session_state: st.session_state.info = {}
if "end_session" not in st.session_state: st.session_state.end_session = False  

st.title("SwiftVisa AI")

# render sidebar profile
with st.sidebar:
    st.header("Profile")
    for key, value in st.session_state.info.items():
        if value and str(value).lower() not in ["", "unknown", "none"]:
            st.write(f"**{key.replace('_', ' ').title()}:** {value}")

# re-render chat history
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg.get("relevance") or msg.get("confidence") or msg.get("faithfulness"):
            cols = st.columns(3)
            cols[0].metric("Relevance", f"{msg.get('relevance', 0)}%")
            cols[1].metric("Confidence", f"{msg.get('confidence', 0)}%")
            cols[2].metric("Faithfulness", f"{msg.get('faithfulness', 0)}/5")
        if msg.get("sources"):
            with st.expander("Sources"):
                for s in set(msg["sources"]): st.caption(s)
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

# handle new chat input
if not st.session_state.end_session:
    prompt = st.chat_input("Message...")
    if prompt:
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"): st.markdown(prompt)
        with st.spinner("Analyzing..."):
            res = run_visa_consultation(prompt, st.session_state.thread_id)
        st.session_state.info = res.get("info", {})
        st.session_state.end_session = res.get("end_session", False)
        st.session_state.messages.append({
            "role": "assistant",
            "content": res.get("answer", ""),
            "relevance": res.get("relevance", 0),
            "confidence": res.get("confidence", 0),
            "faithfulness": res.get("faithfulness", 0),
            "sources": res.get("sources", []),
            "end_session": res.get("end_session", False)
        })
        st.rerun()