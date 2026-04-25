"""
🎾 GrandSlam IQ — Tennis Upset Intelligence Platform
"""

import streamlit as st
import os

st.set_page_config(
    page_title="GrandSlam IQ",
    page_icon="🎾",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Global CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Syne:wght@400;600;700;800&family=DM+Mono:wght@300;400;500&family=DM+Sans:wght@300;400;500&display=swap');

/* ── Base ── */
html, body, [class*="css"] {
    font-family: 'DM Sans', sans-serif;
    background-color: #080810;
    color: #e8e8f0;
}
.stApp { background: #080810; }

/* ── Sidebar ── */
[data-testid="stSidebar"] {
    background: #0d0d1a !important;
    border-right: 1px solid #1e1e3a;
}
[data-testid="stSidebar"] * { color: #c8c8e0 !important; }
[data-testid="stSidebar"] .stTextInput input {
    background: #1a1a2e !important;
    border: 1px solid #2e2e5a !important;
    border-radius: 8px !important;
    color: #e8e8f0 !important;
    font-family: 'DM Mono', monospace !important;
    font-size: 0.78rem !important;
}

/* ── Typography ── */
h1, h2, h3 { font-family: 'Syne', sans-serif !important; letter-spacing: -0.02em; }

/* ── Cards ── */
.gs-card {
    background: #0d0d1a;
    border: 1px solid #1e1e3a;
    border-radius: 16px;
    padding: 1.5rem 2rem;
    margin-bottom: 1.2rem;
    transition: border-color 0.2s;
}
.gs-card:hover { border-color: #3d3d7a; }

.gs-card-accent {
    background: linear-gradient(135deg, #0d0d1a 0%, #12122a 100%);
    border: 1px solid #c8f23d33;
    border-radius: 16px;
    padding: 1.5rem 2rem;
    margin-bottom: 1.2rem;
}

/* ── Accent colour: electric lime ── */
.accent  { color: #c8f23d; }
.accent2 { color: #5ee7df; }
.accent3 { color: #ff6b6b; }
.muted   { color: #6868a0; font-size: 0.85rem; }

/* ── Hero ── */
.hero-title {
    font-family: 'Syne', sans-serif;
    font-size: clamp(2.4rem, 5vw, 4rem);
    font-weight: 800;
    letter-spacing: -0.04em;
    line-height: 1.05;
    margin: 0;
}
.hero-sub {
    font-family: 'DM Sans', sans-serif;
    font-size: 1.1rem;
    color: #8888b0;
    margin-top: 0.75rem;
    font-weight: 300;
    line-height: 1.6;
}

/* ── Metrics ── */
.metric-row { display: flex; gap: 1rem; margin: 1rem 0; }
.metric-box {
    flex: 1;
    background: #0d0d1a;
    border: 1px solid #1e1e3a;
    border-radius: 12px;
    padding: 1.2rem 1.4rem;
    text-align: center;
}
.metric-val {
    font-family: 'Syne', sans-serif;
    font-size: 2rem;
    font-weight: 700;
    color: #c8f23d;
    line-height: 1;
}
.metric-lbl {
    font-size: 0.75rem;
    color: #6868a0;
    margin-top: 4px;
    text-transform: uppercase;
    letter-spacing: 0.08em;
}

/* ── Probability ring ── */
.prob-ring-wrap {
    display: flex;
    flex-direction: column;
    align-items: center;
    padding: 2rem 0;
}
.prob-number {
    font-family: 'Syne', sans-serif;
    font-size: 5rem;
    font-weight: 800;
    letter-spacing: -0.05em;
    line-height: 1;
}
.prob-label {
    font-size: 0.8rem;
    letter-spacing: 0.15em;
    text-transform: uppercase;
    color: #6868a0;
    margin-top: 0.4rem;
}

/* ── SHAP bars ── */
.shap-row {
    display: flex;
    align-items: center;
    gap: 10px;
    margin: 5px 0;
}
.shap-label {
    width: 170px;
    text-align: right;
    font-family: 'DM Mono', monospace;
    font-size: 0.75rem;
    color: #8888b0;
    flex-shrink: 0;
}
.shap-track {
    flex: 1;
    background: #1a1a2e;
    border-radius: 4px;
    height: 14px;
    overflow: hidden;
}
.shap-fill-pos { height: 100%; background: #ff6b6b; border-radius: 4px; }
.shap-fill-neg { height: 100%; background: #5ee7df; border-radius: 4px; }
.shap-val {
    font-family: 'DM Mono', monospace;
    font-size: 0.72rem;
    width: 55px;
    flex-shrink: 0;
}

/* ── Snippet cards ── */
.snippet-card {
    background: #0d0d1a;
    border-left: 3px solid #c8f23d;
    border-radius: 0 10px 10px 0;
    padding: 0.9rem 1.2rem;
    margin: 0.6rem 0;
    font-size: 0.88rem;
    line-height: 1.6;
    color: #b0b0cc;
}
.snippet-meta {
    font-family: 'DM Mono', monospace;
    font-size: 0.7rem;
    color: #5050a0;
    margin-bottom: 0.4rem;
    text-transform: uppercase;
    letter-spacing: 0.06em;
}

/* ── Chat bubbles ── */
.chat-user {
    background: #1a1a2e;
    border: 1px solid #2e2e5a;
    border-radius: 14px 14px 4px 14px;
    padding: 0.8rem 1.2rem;
    margin: 0.5rem 0 0.5rem auto;
    max-width: 78%;
    font-size: 0.9rem;
}
.chat-bot {
    background: #0d0d1a;
    border: 1px solid #1e1e3a;
    border-radius: 4px 14px 14px 14px;
    padding: 0.8rem 1.2rem;
    margin: 0.5rem 0;
    max-width: 85%;
    font-size: 0.9rem;
    line-height: 1.65;
}

/* ── Feature pills ── */
.pill {
    display: inline-block;
    background: #1a1a2e;
    border: 1px solid #2e2e5a;
    border-radius: 100px;
    padding: 4px 14px;
    font-size: 0.75rem;
    font-family: 'DM Mono', monospace;
    color: #8888b0;
    margin: 3px;
}

/* ── Buttons ── */
.stButton > button {
    background: #c8f23d !important;
    color: #080810 !important;
    font-family: 'Syne', sans-serif !important;
    font-weight: 700 !important;
    border: none !important;
    border-radius: 10px !important;
    font-size: 0.92rem !important;
    letter-spacing: 0.02em !important;
    transition: all 0.15s !important;
}
.stButton > button:hover {
    background: #d8ff4d !important;
    transform: translateY(-1px) !important;
}
.stButton > button[kind="secondary"] {
    background: #1a1a2e !important;
    color: #c8c8e0 !important;
    border: 1px solid #2e2e5a !important;
}
.stButton > button[kind="secondary"]:hover {
    border-color: #c8f23d !important;
    color: #c8f23d !important;
}

/* ── Inputs ── */
.stTextInput input, .stTextArea textarea, .stNumberInput input {
    background: #0d0d1a !important;
    border: 1px solid #1e1e3a !important;
    border-radius: 10px !important;
    color: #e8e8f0 !important;
    font-family: 'DM Sans', sans-serif !important;
}
.stTextInput input:focus, .stTextArea textarea:focus {
    border-color: #c8f23d !important;
    box-shadow: 0 0 0 2px #c8f23d22 !important;
}
.stSelectbox div[data-baseweb] {
    background: #0d0d1a !important;
    border-color: #1e1e3a !important;
}
.stSlider [data-baseweb="slider"] { }
[data-testid="stSlider"] [data-baseweb="slider"] div {
    background: #c8f23d !important;
}

/* ── Progress / misc ── */
.stProgress > div > div { background: #c8f23d !important; }
.stAlert { border-radius: 10px !important; }
[data-testid="stExpander"] {
    background: #0d0d1a !important;
    border: 1px solid #1e1e3a !important;
    border-radius: 10px !important;
}
.stTabs [data-baseweb="tab-list"] { background: #0d0d1a; border-radius: 10px; }
.stTabs [data-baseweb="tab"] { color: #6868a0 !important; }
.stTabs [aria-selected="true"] { color: #c8f23d !important; }
div[data-testid="stMetricValue"] {
    font-family: 'Syne', sans-serif !important;
    font-size: 1.8rem !important;
    color: #c8f23d !important;
}
div[data-testid="stMetricLabel"] { color: #6868a0 !important; font-size: 0.75rem !important; }

/* ── Divider ── */
hr { border-color: #1e1e3a !important; }

/* ── Radio / toggle ── */
.stRadio label { color: #c8c8e0 !important; }
[data-testid="stToggle"] { }

/* ── Scrollbar ── */
::-webkit-scrollbar { width: 6px; }
::-webkit-scrollbar-track { background: #0d0d1a; }
::-webkit-scrollbar-thumb { background: #2e2e5a; border-radius: 3px; }
</style>
""", unsafe_allow_html=True)


# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div style='padding: 0.5rem 0 1.5rem'>
      <p style='font-family:Syne,sans-serif; font-size:1.3rem; font-weight:800;
                color:#c8f23d; margin:0; letter-spacing:-0.02em'>GrandSlam IQ</p>
      <p style='font-size:0.72rem; color:#4040a0; margin:2px 0 0;
                font-family:DM Mono,monospace; text-transform:uppercase;
                letter-spacing:0.1em'>Tennis Upset Intelligence</p>
    </div>
    """, unsafe_allow_html=True)

    page = st.radio(
        "Navigate",
        ["🏠  Home", "🚨  Upset Alert", "📋  Scouting Report", "💬  Ask the Model"],
        label_visibility="collapsed",
    )

    st.markdown("<hr>", unsafe_allow_html=True)
    st.markdown("<p class='muted' style='margin-bottom:6px'>🔑 API KEY</p>",
                unsafe_allow_html=True)
    groq_key = st.text_input("Groq API Key",
                              placeholder="gsk_...",
                              type="password",
                              label_visibility="collapsed",
                              help="Free at console.groq.com — powers all AI explanations")

    st.markdown("<hr>", unsafe_allow_html=True)
    st.markdown("<p class='muted' style='margin-bottom:6px'>📊 DATA STATUS</p>",
                unsafe_allow_html=True)

    db_ok      = os.path.exists("tennis_upsets.db") and os.path.getsize("tennis_upsets.db") > 10_000
    model_ok   = os.path.exists("upset_model.pkl")
    feats_ok   = os.path.exists("features.csv")

    for label, ok in [("Database", db_ok), ("Trained model", model_ok), ("Features", feats_ok)]:
        icon  = "🟢" if ok else "🔴"
        state = "Live" if ok else "Demo mode"
        st.markdown(f"<p style='font-size:0.8rem;margin:3px 0'>{icon} {label} <span class='muted'>· {state}</span></p>",
                    unsafe_allow_html=True)

    if not db_ok:
        st.markdown("""
        <div style='background:#1a1a0d;border:1px solid #c8f23d33;border-radius:8px;
                    padding:0.7rem;margin-top:0.8rem;font-size:0.75rem;color:#a0a060;
                    line-height:1.5'>
        ⚡ Run the pipeline scripts to load real data. App works in demo mode until then.
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<hr>", unsafe_allow_html=True)
    st.markdown("""
    <p class='muted'>Built with scikit-learn · ChromaDB · LangChain · Groq</p>
    """, unsafe_allow_html=True)


# ── Page routing ─────────────────────────────────────────────────────────────
p = page.split("  ")[-1].strip()

if p == "Home":
    import pages.home as ph
    ph.render(db_ok, model_ok, groq_key)
elif p == "Upset Alert":
    import pages.upset_alert as pa
    pa.render(groq_key, model_ok, feats_ok)
elif p == "Scouting Report":
    import pages.scouting_report as ps
    ps.render(groq_key, db_ok)
elif p == "Ask the Model":
    import pages.agent_chat as pc
    pc.render(groq_key, db_ok)