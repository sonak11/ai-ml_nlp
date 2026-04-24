"""
🎾 Tennis Upset Predictor — Streamlit App
==========================================
Three features:
  Page 1 — Real-time Upset Alert + LLM Explanation
  Page 2 — RAG-enhanced Player Scouting Report
  Page 3 — Conversational SQL + Vector Agent
"""

import streamlit as st

st.set_page_config(
    page_title="Tennis Upset Predictor",
    page_icon="🎾",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── Shared CSS ───────────────────────────────────────────────────────────────
st.markdown("""
<style>
  .metric-card {
    background: #1e1e2e;
    border-radius: 12px;
    padding: 1.2rem 1.5rem;
    margin-bottom: 1rem;
    border-left: 4px solid #6366f1;
  }
  .high-risk  { border-left-color: #ef4444; }
  .mid-risk   { border-left-color: #f59e0b; }
  .low-risk   { border-left-color: #22c55e; }
  .shap-bar   { height: 18px; border-radius: 4px; background: #6366f1; }
  .shap-neg   { background: #22c55e; }
  .snippet    { background: #1e1e2e; border-radius: 8px; padding: 0.8rem;
                font-size: 0.85rem; margin-bottom: 0.5rem; border-left: 3px solid #6366f1; }
  .stButton>button { border-radius: 8px; }
</style>
""", unsafe_allow_html=True)

# ─── Sidebar navigation ───────────────────────────────────────────────────────
page = st.sidebar.radio(
    "Navigate",
    ["🚨 Upset Alert", "📋 Scouting Report", "💬 Ask the Model"],
    index=0,
)

st.sidebar.markdown("---")
st.sidebar.markdown("### ⚙️ API Keys")
groq_key = st.sidebar.text_input("Groq API Key", type="password",
                                  help="Free at console.groq.com")
hf_key   = st.sidebar.text_input("HuggingFace Token (optional)", type="password",
                                  help="For Mistral LLM labels")

st.sidebar.markdown("---")
st.sidebar.markdown("**Data status**")
import os
db_exists = os.path.exists("tennis_upsets.db") and os.path.getsize("tennis_upsets.db") > 10_000
model_exists = os.path.exists("upset_model.pkl")
features_exist = os.path.exists("features.csv")

st.sidebar.markdown(f"{'✅' if db_exists else '⚠️'} Database")
st.sidebar.markdown(f"{'✅' if model_exists else '⚠️'} Trained model")
st.sidebar.markdown(f"{'✅' if features_exist else '⚠️'} Feature matrix")

if not (db_exists and model_exists):
    st.sidebar.info("Run `data_ingestion.py` → `model.py` to populate data. "
                    "Demo mode is active until then.")

# ─── Route to pages ───────────────────────────────────────────────────────────
if page == "🚨 Upset Alert":
    import pages.upset_alert as pa
    pa.render(groq_key, model_exists, features_exist)

elif page == "📋 Scouting Report":
    import pages.scouting_report as ps
    ps.render(groq_key, db_exists)

elif page == "💬 Ask the Model":
    import pages.agent_chat as pc
    pc.render(groq_key, db_exists)
