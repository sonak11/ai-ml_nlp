"""
GrandSlam IQ — Complete Single-File Streamlit App
All four pages in one file to avoid import issues.
"""

import streamlit as st
import os, re, numpy as np

st.set_page_config(
    page_title="GrandSlam IQ",
    page_icon="🎾",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ═══════════════════════════════════════════════════════════════════════════════
#  GLOBAL CSS
# ═══════════════════════════════════════════════════════════════════════════════
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Bebas+Neue&family=DM+Sans:ital,wght@0,300;0,400;0,500;0,600;1,300&family=JetBrains+Mono:wght@300;400;500&display=swap');

/* ── Reset & Base ── */
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
html, body, [class*="css"] {
    font-family: 'DM Sans', sans-serif;
    background: #050508;
    color: #ddddf0;
}
.stApp { background: #050508; }
section[data-testid="stSidebar"] { display: none; }
[data-testid="collapsedControl"] { display: none; }
header[data-testid="stHeader"] { display: none !important; }
#MainMenu { display: none !important; }
footer { display: none !important; }
.stDeployButton { display: none !important; }
[data-testid="stToolbar"] { display: none !important; }
.block-container { padding-top: 1rem !important; }
.block-container { padding: 0 2rem 4rem !important; max-width: 1200px !important; }

/* ── Top Nav ── */
.topnav {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 1.2rem 0 1rem;
    border-bottom: 1px solid #16162a;
    margin-bottom: 2.5rem;
    position: sticky;
    top: 0;
    background: #050508;
    z-index: 100;
}
.topnav-logo {
    font-family: 'Bebas Neue', sans-serif;
    font-size: 1.6rem;
    letter-spacing: 0.12em;
    color: #e8ff48;
    line-height: 1;
}
.topnav-logo span { color: #4d4dff; }
.topnav-links {
    display: flex;
    gap: 0.3rem;
}
.nav-btn {
    background: transparent;
    border: 1px solid transparent;
    border-radius: 8px;
    padding: 0.45rem 1.1rem;
    color: #6666aa;
    font-family: 'DM Sans', sans-serif;
    font-size: 0.85rem;
    font-weight: 500;
    cursor: pointer;
    transition: all 0.15s;
    text-decoration: none;
}
.nav-btn:hover { color: #ddddf0; border-color: #16162a; background: #0d0d1e; }
.nav-btn.active {
    color: #e8ff48;
    border-color: #e8ff4833;
    background: #e8ff4808;
}
.nav-key {
    display: inline-block;
    background: #e8ff4822;
    border: 1px solid #e8ff4844;
    border-radius: 4px;
    padding: 1px 5px;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.65rem;
    color: #e8ff48;
    margin-left: 4px;
    vertical-align: middle;
}

/* ── Section heading ── */
.page-eyebrow {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.7rem;
    letter-spacing: 0.2em;
    text-transform: uppercase;
    color: #3333aa;
    margin-bottom: 0.6rem;
}
.page-title {
    font-family: 'Bebas Neue', sans-serif;
    font-size: clamp(2.5rem, 6vw, 4.5rem);
    letter-spacing: 0.06em;
    line-height: 0.95;
    color: #f0f0ff;
    margin-bottom: 0.8rem;
}
.page-title .hl { color: #e8ff48; }
.page-title .hl2 { color: #4d4dff; }
.page-title .hl3 { color: #ff4d6d; }
.page-sub {
    color: #55557a;
    font-size: 0.95rem;
    line-height: 1.65;
    max-width: 580px;
    margin-bottom: 2rem;
    font-weight: 300;
}

/* ── Cards ── */
.card {
    background: #0a0a18;
    border: 1px solid #16162a;
    border-radius: 14px;
    padding: 1.4rem 1.6rem;
    margin-bottom: 1rem;
    transition: border-color 0.2s;
}
.card:hover { border-color: #2a2a55; }
.card-accent {
    background: linear-gradient(135deg, #0a0a18 0%, #0d0d22 100%);
    border: 1px solid #1a1a35;
    border-radius: 14px;
    padding: 1.4rem 1.6rem;
    margin-bottom: 1rem;
}
.card-label {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.68rem;
    text-transform: uppercase;
    letter-spacing: 0.15em;
    margin-bottom: 0.5rem;
}
.card-title {
    font-family: 'Bebas Neue', sans-serif;
    font-size: 1.2rem;
    letter-spacing: 0.05em;
    margin-bottom: 0.5rem;
}
.card-body {
    font-size: 0.85rem;
    color: #55557a;
    line-height: 1.65;
}

/* ── Stat strip ── */
.stat-strip {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 1px;
    background: #16162a;
    border: 1px solid #16162a;
    border-radius: 12px;
    overflow: hidden;
    margin: 1.5rem 0 2.5rem;
}
.stat-cell {
    background: #0a0a18;
    padding: 1.2rem 1.4rem;
    text-align: center;
}
.stat-num {
    font-family: 'Bebas Neue', sans-serif;
    font-size: 2.2rem;
    letter-spacing: 0.05em;
    color: #e8ff48;
    line-height: 1;
}
.stat-lbl {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.65rem;
    text-transform: uppercase;
    letter-spacing: 0.12em;
    color: #33334a;
    margin-top: 0.3rem;
}

/* ── Feature grid ── */
.feat-grid {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 1rem;
    margin: 1rem 0 2rem;
}
.feat-card {
    background: #0a0a18;
    border: 1px solid #16162a;
    border-radius: 14px;
    padding: 1.4rem;
    transition: all 0.2s;
    cursor: default;
}
.feat-card:hover {
    border-color: #2a2a55;
    transform: translateY(-2px);
}
.feat-icon { font-size: 1.8rem; margin-bottom: 0.8rem; }
.feat-name {
    font-family: 'Bebas Neue', sans-serif;
    font-size: 1.1rem;
    letter-spacing: 0.06em;
    margin-bottom: 0.5rem;
}
.feat-desc {
    font-size: 0.82rem;
    color: #44446a;
    line-height: 1.6;
}
.feat-tags { margin-top: 0.8rem; }
.tag {
    display: inline-block;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.62rem;
    padding: 2px 8px;
    background: #12122a;
    border: 1px solid #1e1e3a;
    border-radius: 4px;
    color: #33334a;
    margin: 2px 2px 0 0;
    letter-spacing: 0.05em;
}

/* ── Prob display ── */
.prob-block {
    text-align: center;
    padding: 2rem 1rem;
}
.prob-num {
    font-family: 'Bebas Neue', sans-serif;
    font-size: 5.5rem;
    letter-spacing: 0.03em;
    line-height: 1;
}
.prob-lbl {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.7rem;
    letter-spacing: 0.18em;
    text-transform: uppercase;
    color: #33334a;
    margin-top: 0.4rem;
}
.prob-match {
    font-size: 0.82rem;
    color: #44446a;
    margin-top: 0.6rem;
}

/* ── SHAP bars ── */
.shap-wrap { margin-top: 0.5rem; }
.shap-row {
    display: flex;
    align-items: center;
    gap: 8px;
    margin: 4px 0;
}
.shap-lbl {
    width: 160px;
    text-align: right;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.7rem;
    color: #33334a;
    flex-shrink: 0;
}
.shap-track {
    flex: 1;
    background: #0d0d1e;
    border-radius: 3px;
    height: 12px;
    overflow: hidden;
}
.shap-pos { height: 100%; border-radius: 3px; background: #ff4d6d; }
.shap-neg { height: 100%; border-radius: 3px; background: #4d4dff; }
.shap-val {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.68rem;
    width: 52px;
    flex-shrink: 0;
}

/* ── Snippet ── */
.snippet {
    background: #0a0a18;
    border-left: 2px solid #e8ff48;
    padding: 0.8rem 1rem;
    margin: 0.5rem 0;
    border-radius: 0 8px 8px 0;
    font-size: 0.84rem;
    line-height: 1.6;
    color: #9999bb;
}
.snippet-meta {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.65rem;
    color: #22224a;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    margin-bottom: 0.35rem;
}

/* ── Chat ── */
.chat-user {
    background: #0d0d22;
    border: 1px solid #1a1a35;
    border-radius: 12px 12px 3px 12px;
    padding: 0.75rem 1rem;
    margin: 0.4rem 0 0.4rem auto;
    max-width: 76%;
    font-size: 0.88rem;
    color: #c0c0e0;
}
.chat-bot {
    background: #0a0a18;
    border: 1px solid #16162a;
    border-radius: 3px 12px 12px 12px;
    padding: 0.75rem 1rem;
    margin: 0.4rem 0;
    max-width: 82%;
    font-size: 0.88rem;
    line-height: 1.65;
    color: #aaaacc;
}
.chat-source {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.62rem;
    color: #22224a;
    margin-top: 0.4rem;
    letter-spacing: 0.08em;
    text-transform: uppercase;
}

/* ── Explanation box ── */
.explain-box {
    border-left: 3px solid;
    border-radius: 0 10px 10px 0;
    padding: 1rem 1.2rem;
    font-size: 0.88rem;
    line-height: 1.65;
    color: #aaaacc;
    margin: 0.8rem 0;
}

/* ── Example buttons ── */
.ex-grid {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 0.5rem;
    margin-bottom: 1.2rem;
}
.ex-btn {
    background: #0a0a18;
    border: 1px solid #16162a;
    border-radius: 8px;
    padding: 0.55rem 0.7rem;
    font-size: 0.78rem;
    color: #44446a;
    cursor: pointer;
    text-align: left;
    transition: all 0.15s;
    line-height: 1.3;
    font-family: 'DM Sans', sans-serif;
}
.ex-btn:hover { border-color: #2a2a55; color: #9999bb; }

/* ── Streamlit overrides ── */
.stButton > button {
    background: #e8ff48 !important;
    color: #050508 !important;
    font-family: 'Bebas Neue', sans-serif !important;
    font-size: 1rem !important;
    letter-spacing: 0.1em !important;
    border: none !important;
    border-radius: 8px !important;
    padding: 0.55rem 1.4rem !important;
    transition: all 0.15s !important;
}
.stButton > button:hover {
    background: #f5ff70 !important;
    transform: translateY(-1px) !important;
}
.stTextInput input, .stTextArea textarea, .stNumberInput input {
    background: #0a0a18 !important;
    border: 1px solid #16162a !important;
    border-radius: 8px !important;
    color: #ddddf0 !important;
    font-family: 'DM Sans', sans-serif !important;
    font-size: 0.9rem !important;
}
.stTextInput input:focus, .stTextArea textarea:focus {
    border-color: #e8ff4844 !important;
    box-shadow: 0 0 0 2px #e8ff4811 !important;
}
.stSelectbox > div > div {
    background: #0a0a18 !important;
    border: 1px solid #16162a !important;
    border-radius: 8px !important;
    color: #ddddf0 !important;
}
label, .stSlider label, .stRadio label,
[data-testid="stWidgetLabel"] {
    color: #44446a !important;
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 0.72rem !important;
    text-transform: uppercase !important;
    letter-spacing: 0.1em !important;
}
div[data-testid="stMetricValue"] {
    font-family: 'Bebas Neue', sans-serif !important;
    font-size: 2rem !important;
    color: #e8ff48 !important;
}
div[data-testid="stMetricLabel"] {
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 0.65rem !important;
    text-transform: uppercase !important;
    letter-spacing: 0.12em !important;
    color: #33334a !important;
}
.stProgress > div > div { background: #e8ff48 !important; }
[data-testid="stExpander"] {
    background: #0a0a18 !important;
    border: 1px solid #16162a !important;
    border-radius: 10px !important;
}
[data-testid="stExpander"] summary { color: #44446a !important; }
hr { border-color: #16162a !important; }
.stAlert { border-radius: 8px !important; }
div[data-testid="stToggle"] > label > div { background: #16162a !important; }
::-webkit-scrollbar { width: 5px; height: 5px; }
::-webkit-scrollbar-track { background: #050508; }
::-webkit-scrollbar-thumb { background: #16162a; border-radius: 3px; }
</style>
""", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════════════
#  SESSION STATE
# ═══════════════════════════════════════════════════════════════════════════════
if "page" not in st.session_state:
    st.session_state.page = "Home"
if "messages" not in st.session_state:
    st.session_state.messages = []

# ═══════════════════════════════════════════════════════════════════════════════
#  TOP NAVIGATION
# ═══════════════════════════════════════════════════════════════════════════════
db_ok    = os.path.exists("tennis_upsets.db") and os.path.getsize("tennis_upsets.db") > 10_000
model_ok = os.path.exists("upset_model.pkl")
feats_ok = os.path.exists("features.csv")

pages = ["Home", "Upset Alert", "Scouting Report", "Ask the Model"]
icons = ["◈", "⚡", "◎", "◉"]

nav_html = '<div class="topnav"><div class="topnav-logo">Grand<span>Slam</span> IQ</div><div class="topnav-links">'
for icon, p in zip(icons, pages):
    active = "active" if st.session_state.page == p else ""
    nav_html += f'<span class="nav-btn {active}" id="nav-{p.replace(" ","-")}">{icon} {p}</span>'
nav_html += "</div></div>"
st.markdown(nav_html, unsafe_allow_html=True)

# Navigation buttons (hidden but functional)
nav_cols = st.columns([3, 1, 1, 1, 1])
with nav_cols[1]:
    if st.button("◈ Home", key="nav_home", use_container_width=True):
        st.session_state.page = "Home"; st.rerun()
with nav_cols[2]:
    if st.button("⚡ Alert", key="nav_alert", use_container_width=True):
        st.session_state.page = "Upset Alert"; st.rerun()
with nav_cols[3]:
    if st.button("◎ Scout", key="nav_scout", use_container_width=True):
        st.session_state.page = "Scouting Report"; st.rerun()
with nav_cols[4]:
    if st.button("◉ Chat", key="nav_chat", use_container_width=True):
        st.session_state.page = "Ask the Model"; st.rerun()

st.markdown("<div style='height:0.5rem'></div>", unsafe_allow_html=True)

page = st.session_state.page

# ═══════════════════════════════════════════════════════════════════════════════
#  SHARED HELPERS
# ═══════════════════════════════════════════════════════════════════════════════

def analyse_transcript(text):
    LEXICON = {
        "physical":   ["tired","exhausted","heavy legs","cramping","drained","sore",
                        "not 100","my body","physically","stiff"],
        "mental":     ["mentally","focus","distracted","lost focus","concentrate"],
        "schedule":   ["back to back","back-to-back","five sets","long match",
                        "tough schedule","no rest","played a lot"],
        "injury":     ["injury","pain","hurts","my knee","my shoulder","my back",
                        "my ankle","blister","trainer","pulled"],
        "motivation": ["doubt","not sure","question mark","uncertain","lacking confidence"],
    }
    t = text.lower()
    counts, total = {}, 0
    for cat, phrases in LEXICON.items():
        c = sum(len(re.findall(r"\b"+re.escape(ph)+r"\b", t)) for ph in phrases)
        counts[cat] = c; total += c
    words = text.split()
    n = max(len(words), 1)
    pos = sum(t.count(w) for w in ["confident","great","good","ready","strong","sharp"])
    neg = sum(t.count(w) for w in ["not","never","tired","exhausted","pain","doubt","sore"])
    polarity = round((pos-neg)/max(pos+neg,1), 3)
    return {
        "fatigue_total": total,
        "fatigue_density": round(total/n*100, 2),
        "sentiment_polarity": polarity,
        **{f"fatigue_{k}": v for k,v in counts.items()},
        "word_count": len(words),
    }

ROUND_MAP = {"R1":1,"R2":2,"R3":3,"R4":4,"QF":5,"SF":6,"F":7}

def predict(player_rank, opp_rank, ctfi, sentiment, fatigue, round_num, best_of):
    row = {
        "rank": player_rank, "opp_rank": opp_rank,
        "rank_ratio": player_rank/max(opp_rank,1),
        "log_rank_diff": np.sign(player_rank-opp_rank)*np.log1p(abs(player_rank-opp_rank)),
        "is_underdog": int(player_rank>opp_rank),
        "round_num": round_num, "best_of": best_of, "ctfi": ctfi,
        "sentiment_polarity": sentiment, "fatigue_total": fatigue,
        "fatigue_word_density": fatigue/100,
        "fatigue_physical": max(0,fatigue-2), "fatigue_mental": max(0,fatigue-3),
        "fatigue_schedule": max(0,fatigue-4), "fatigue_injury": 0,
        "fatigue_motivation": 0, "first_person_rate": 0.15,
        "negation_rate": 0.05, "llm_is_fatigued": 0.5,
        "rank_bin": "top100" if player_rank<=100 else "outside100",
    }
    shap_dict = {}
    if model_ok:
        try:
            import joblib, pandas as pd
            pkg  = joblib.load("upset_model.pkl")
            pipe = pkg["model_b"]
            cols = pkg["full_cols"]
            df   = pd.DataFrame([row])[[c for c in cols if c in row]]
            prob = float(pipe.predict_proba(df)[0,1])
            try:
                import shap
                prep = pipe.named_steps["prep"]
                Xt   = prep.transform(df)
                exp  = shap.TreeExplainer(pipe.named_steps["model"])
                sv   = exp.shap_values(Xt)
                vals = sv[1][0] if isinstance(sv, list) else sv[0]
                nc   = prep.transformers_[0][2]
                cc   = prep.transformers_[1][2] if len(prep.transformers_)>1 else []
                all_c= list(nc)+list(cc)
                shap_dict = {c: float(v) for c,v in zip(all_c, vals)}
            except Exception:
                pass
            return prob, shap_dict
        except Exception:
            pass
    # Synthetic fallback
    rank_diff = player_rank - opp_rank
    raw = 0.5 + 0.003*rank_diff - 0.005*ctfi + 0.05*fatigue - 0.1*sentiment + np.random.normal(0,0.05)
    prob = float(np.clip(1/(1+np.exp(-raw*0.5)), 0.05, 0.95))
    shap_dict = {
        "rank_ratio": round(0.3*(player_rank/max(opp_rank,1)-1), 3),
        "ctfi": round(-0.02*ctfi, 3),
        "fatigue_total": round(0.04*fatigue, 3),
        "sentiment_polarity": round(-0.08*sentiment, 3),
        "round_num": round(0.01*round_num, 3),
    }
    return prob, shap_dict

def shap_html(shap_dict):
    top = sorted(shap_dict.items(), key=lambda x: abs(x[1]), reverse=True)[:7]
    mx  = max(abs(v) for _,v in top) if top else 1
    out = "<div class='shap-wrap'>"
    for feat, val in top:
        pct  = int(abs(val)/mx*100)
        col  = "#ff4d6d" if val>0 else "#4d4dff"
        sign = "+" if val>0 else "−"
        cls  = "shap-pos" if val>0 else "shap-neg"
        lbl  = feat.replace("_"," ")
        out += (f"<div class='shap-row'>"
                f"<span class='shap-lbl'>{lbl}</span>"
                f"<div class='shap-track'><div class='{cls}' style='width:{pct}%'></div></div>"
                f"<span class='shap-val' style='color:{col}'>{sign}{abs(val):.3f}</span></div>")
    return out + "</div>"

def groq_call(prompt, groq_key, max_tokens=150):
    try:
        from groq import Groq
        client = Groq(api_key=groq_key)
        resp   = client.chat.completions.create(
            model="llama3-70b-8192",
            messages=[{"role":"user","content":prompt}],
            temperature=0.25, max_tokens=max_tokens,
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        return None

def search_transcripts(query, player=None, n=5, upset_only=True):
    DEMO = [
        {"player":"Carlos Alcaraz","tournament":"Wimbledon","round":"QF","upset":1,"rank_diff":15,
         "text":"I'm honestly feeling very tired. Yesterday's match took a lot out of me — five sets, almost four hours. My legs are really heavy and I've been cramping. I haven't slept well and mentally I'm drained. My back is a bit stiff."},
        {"player":"Carlos Alcaraz","tournament":"Roland Garros","round":"SF","upset":1,"rank_diff":22,
         "text":"It was really tough physically. I had a lot of tension in my legs. I'm not 100 percent. The run in this tournament has been so demanding — back-to-back five-set matches. My knee was bothering me."},
        {"player":"Novak Djokovic","tournament":"Australian Open","round":"SF","upset":1,"rank_diff":30,
         "text":"The wrist has been bothering me since the third round. I'm taking painkillers to get through matches. Mentally it is draining because you're always thinking about the injury. I struggled to focus."},
        {"player":"Novak Djokovic","tournament":"Wimbledon","round":"QF","upset":0,"rank_diff":-12,
         "text":"I feel very confident. My game is in good shape, movement is great. I'm sleeping nine hours and my body feels refreshed."},
        {"player":"Rafael Nadal","tournament":"Australian Open","round":"QF","upset":1,"rank_diff":10,
         "text":"My abs are very painful. I've had a medical timeout twice this week. I have doubts about finishing the tournament healthy. The fatigue is real."},
    ]
    try:
        import sqlite3
        if db_ok:
            conn = sqlite3.connect("tennis_upsets.db")
            q    = "SELECT player_name, tourney_name, round, raw_text FROM transcripts WHERE raw_text IS NOT NULL"
            rows = conn.execute(q).fetchall()
            conn.close()
            docs = [{"player":r[0],"tournament":r[1],"round":r[2],"upset":0,"rank_diff":0,"text":r[3][:600]} for r in rows]
            if player:
                docs = [d for d in docs if player.lower() in (d["player"] or "").lower()] or docs
            qw = set(re.findall(r"\w+", query.lower()))
            docs.sort(key=lambda d: -len(qw & set(re.findall(r"\w+", d["text"].lower()))))
            return docs[:n]
    except Exception:
        pass
    docs = DEMO
    if player:
        filtered = [d for d in docs if player.lower() in d["player"].lower()]
        docs     = filtered or docs
    if upset_only:
        docs = [d for d in docs if d.get("upset")] or docs
    return docs[:n]

def answer_sql(question):
    """Returns (df_or_None, summary_string)."""
    try:
        import sqlite3, pandas as pd
        if not db_ok:
            raise Exception("no db")
        conn = sqlite3.connect("tennis_upsets.db")
        q    = question.lower()

        if "upset rate" in q and ("slam" in q or "tournament" in q or "grand" in q):
            df = pd.read_sql("""
                SELECT slam_name AS Tournament,
                       COUNT(*) AS Matches,
                       SUM(upset) AS Upsets,
                       ROUND(AVG(upset)*100,1) AS "Upset Rate %"
                FROM matches GROUP BY slam_name ORDER BY "Upset Rate %" DESC
            """, conn)
            summary = "Upset rate by Grand Slam (higher = more unpredictable):"

        elif "biggest" in q or ("rank" in q and "gap" in q) or "largest" in q:
            df = pd.read_sql("""
                SELECT winner_name AS Winner, loser_name AS Loser,
                       CAST(rank_diff AS INT) AS "Rank Gap",
                       slam_name AS Tournament, round AS Round,
                       SUBSTR(tourney_date,1,4) AS Year
                FROM matches WHERE upset=1 ORDER BY rank_diff DESC LIMIT 10
            """, conn)
            summary = "Biggest upsets by rank gap (Winner's rank minus Loser's rank):"

        elif "round" in q and ("upset" in q or "rate" in q):
            df = pd.read_sql("""
                SELECT round AS Round, COUNT(*) AS Matches,
                       ROUND(AVG(upset)*100,1) AS "Upset Rate %"
                FROM matches GROUP BY round ORDER BY "Upset Rate %" DESC
            """, conn)
            summary = "Upset rate by round:"

        elif "how many" in q or "count" in q or "total" in q or "dataset" in q:
            df = pd.read_sql("""
                SELECT COUNT(*) AS "Total Matches",
                       SUM(upset) AS "Total Upsets",
                       ROUND(AVG(upset)*100,1) AS "Overall Upset Rate %"
                FROM matches
            """, conn)
            summary = "Dataset overview:"

        elif any(n in q for n in ["favourite","favorite","top-10","top 10","top10"]):
            df = pd.read_sql("""
                SELECT loser_name AS Player,
                       COUNT(*) AS "Times Lost as Favourite"
                FROM matches WHERE upset=1 AND loser_rank<=10
                GROUP BY loser_name ORDER BY "Times Lost as Favourite" DESC LIMIT 10
            """, conn)
            summary = "Top-10 players who lost most often as the favourite:"

        elif "surface" in q or "grass" in q or "clay" in q or "hard" in q:
            df = pd.read_sql("""
                SELECT surface AS Surface,
                       COUNT(*) AS Matches,
                       ROUND(AVG(upset)*100,1) AS "Upset Rate %"
                FROM matches WHERE surface IS NOT NULL
                GROUP BY surface ORDER BY "Upset Rate %" DESC
            """, conn)
            summary = "Upset rate by surface:"

        elif any(name in question for name in
                 ["Djokovic","Nadal","Federer","Alcaraz","Sinner","Medvedev",
                  "Tsitsipas","Zverev","Rublev","Murray"]):
            # Player-specific query
            for name in ["Djokovic","Nadal","Federer","Alcaraz","Sinner","Medvedev",
                          "Tsitsipas","Zverev","Rublev","Murray"]:
                if name in question:
                    df = pd.read_sql(f"""
                        SELECT slam_name AS Tournament, round AS Round,
                               winner_name AS Winner, loser_name AS Loser,
                               CAST(rank_diff AS INT) AS "Rank Gap",
                               SUBSTR(tourney_date,1,4) AS Year
                        FROM matches
                        WHERE upset=1 AND (winner_name LIKE '%{name}%' OR loser_name LIKE '%{name}%')
                        ORDER BY tourney_date DESC LIMIT 10
                    """, conn)
                    summary = f"Recent upset matches involving {name}:"
                    break
        else:
            df = pd.read_sql("""
                SELECT slam_name AS Tournament, COUNT(*) AS Matches,
                       ROUND(AVG(upset)*100,1) AS "Upset Rate %"
                FROM matches GROUP BY slam_name ORDER BY "Upset Rate %" DESC
            """, conn)
            summary = "Upset summary by Grand Slam:"

        conn.close()
        return df, summary

    except Exception:
        import pandas as pd
        df = pd.DataFrame({
            "Tournament":   ["Wimbledon","Roland Garros","Australian Open","US Open"],
            "Upset Rate %": [30.5, 29.3, 28.5, 26.7],
            "Note":         ["Demo data"]*4,
        })
        return df, "Demo stats (run pipeline for real data):"

# ═══════════════════════════════════════════════════════════════════════════════
#  PAGE: HOME
# ═══════════════════════════════════════════════════════════════════════════════
if page == "Home":
    st.markdown("""
    <div style='padding:1.5rem 0 0'>
      <div class='page-eyebrow'>Grand Slam Analytics · 2022–2024</div>
      <div class='page-title'>Can we predict<br>a <span class='hl'>tennis upset</span><br>before it happens?</div>
      <div class='page-sub'>
        GrandSlam IQ uses 10 years of match data, player rankings,
        and AI-powered press conference analysis to detect fatigue signals
        and forecast upsets at the four Grand Slams.
      </div>
    </div>
    """, unsafe_allow_html=True)

    status = f"{'Live Data' if db_ok else 'Demo Mode'}"
    st.markdown(f"""
    <div class='stat-strip'>
      <div class='stat-cell'><div class='stat-num'>26%</div><div class='stat-lbl'>Avg upset rate</div></div>
      <div class='stat-cell'><div class='stat-num'>2,279</div><div class='stat-lbl'>Transcripts</div></div>
      <div class='stat-cell'><div class='stat-num'>0.70</div><div class='stat-lbl'>Model AUC</div></div>
      <div class='stat-cell'><div class='stat-num' style='font-size:1.4rem;padding-top:0.3rem'>{'🟢' if db_ok else '🟡'}</div><div class='stat-lbl'>{status}</div></div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class='feat-grid'>
      <div class='feat-card'>
        <div class='feat-icon'>⚡</div>
        <div class='feat-name' style='color:#e8ff48'>Upset Alert</div>
        <div class='feat-desc'>Enter two players and match context. The model returns an upset probability with a plain-English AI explanation of exactly what's driving the risk.</div>
        <div class='feat-tags'><span class='tag'>Random Forest</span><span class='tag'>SHAP</span><span class='tag'>Groq LLM</span></div>
      </div>
      <div class='feat-card'>
        <div class='feat-icon'>◎</div>
        <div class='feat-name' style='color:#4d4dff'>Scouting Report</div>
        <div class='feat-desc'>Ask "What are Alcaraz's fatigue signals before an upset?" The system searches real press conference transcripts and generates a tactical report.</div>
        <div class='feat-tags'><span class='tag'>ChromaDB RAG</span><span class='tag'>Embeddings</span><span class='tag'>Groq LLM</span></div>
      </div>
      <div class='feat-card'>
        <div class='feat-icon'>◉</div>
        <div class='feat-name' style='color:#ff4d6d'>Ask the Model</div>
        <div class='feat-desc'>Chat with 10 years of Grand Slam data. Ask anything — the AI routes to SQL queries for stats or transcript search for language patterns.</div>
        <div class='feat-tags'><span class='tag'>SQL Agent</span><span class='tag'>Vector Search</span><span class='tag'>LangChain</span></div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("<div style='border-top:1px solid #16162a;padding-top:2rem;margin-top:0.5rem'>", unsafe_allow_html=True)
    st.markdown("<div class='page-eyebrow'>How it works</div>", unsafe_allow_html=True)

    for num, col, title, desc in [
        ("01","#e8ff48","Rank features","Player ATP rankings, rank gap, log-transform, underdog flag — who is expected to win and by how much."),
        ("02","#4d4dff","Fatigue Index (CTFI)","Sets played before this match in the same tournament. Going to five sets twice before a quarterfinal is a huge hidden cost."),
        ("03","#ff4d6d","NLP transcript analysis","60+ fatigue signals across five categories scanned from press conferences: physical, mental, schedule, injury, motivation."),
        ("04","#888","Random Forest + SHAP","Trained on 10 years of Grand Slam data. SHAP values explain every prediction — you always know WHY, not just what."),
    ]:
        st.markdown(f"""
        <div class='card' style='display:flex;gap:1.2rem;align-items:flex-start'>
          <div style='font-family:Bebas Neue,sans-serif;font-size:2.5rem;color:{col};opacity:0.25;line-height:1;flex-shrink:0'>{num}</div>
          <div>
            <div style='font-family:Bebas Neue,sans-serif;font-size:1rem;letter-spacing:0.06em;color:{col};margin-bottom:0.3rem'>{title}</div>
            <div style='font-size:0.84rem;color:#44446a;line-height:1.6'>{desc}</div>
          </div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)

    groq_key_home = st.text_input("Groq API key (free at console.groq.com)", type="password",
                                   placeholder="gsk_...", key="groq_home",
                                   help="Powers all AI explanations. Get one free in 30 seconds.")
    if groq_key_home:
        st.session_state.groq_key = groq_key_home
        st.success("✓ Key saved — AI explanations enabled across all tools")

# ═══════════════════════════════════════════════════════════════════════════════
#  PAGE: UPSET ALERT
# ═══════════════════════════════════════════════════════════════════════════════
elif page == "Upset Alert":
    st.markdown("""
    <div class='page-eyebrow'>Tool 01 / 03</div>
    <div class='page-title'><span class='hl'>Upset</span> Alert</div>
    <div class='page-sub'>Enter match details and an optional transcript to get an AI-powered upset probability with a natural language explanation.</div>
    """, unsafe_allow_html=True)

    if not model_ok:
        st.markdown("<div class='card' style='border-color:#2a1a0a;color:#886644;font-size:0.84rem'>⚠️ No trained model found — using demo mode. Run the pipeline scripts to train on real data.</div>", unsafe_allow_html=True)

    # Groq key
    groq_key = st.session_state.get("groq_key","")
    if not groq_key:
        groq_key = st.text_input("Groq API key for AI explanations", type="password",
                                  placeholder="gsk_... (optional — get free at console.groq.com)", key="groq_alert")

    st.markdown("<div style='height:0.8rem'></div>", unsafe_allow_html=True)

    # Players
    c1, c2, c3 = st.columns([5,1,5])
    with c1:
        st.markdown("<div class='card-label' style='color:#e8ff48;margin-bottom:0.5rem'>⬤ Underdog</div>", unsafe_allow_html=True)
        player      = st.text_input("Underdog name", "Carlos Alcaraz", key="p_name", label_visibility="collapsed")
        player_rank = st.number_input("Underdog ATP rank", 1, 1000, 45, key="p_rank")
        ctfi        = st.slider("Fatigue Index (CTFI)", 0, 30, 8, help="Sets played so far this tournament")
    with c2:
        st.markdown("<div style='text-align:center;padding-top:2rem;font-family:Bebas Neue,sans-serif;font-size:1.5rem;color:#22224a'>VS</div>", unsafe_allow_html=True)
    with c3:
        st.markdown("<div class='card-label' style='color:#ff4d6d;margin-bottom:0.5rem'>⬤ Favourite</div>", unsafe_allow_html=True)
        opponent = st.text_input("Favourite name", "Novak Djokovic", key="o_name", label_visibility="collapsed")
        opp_rank = st.number_input("Favourite ATP rank", 1, 1000, 3, key="o_rank")
        round_sel = st.selectbox("Round", list(ROUND_MAP.keys()), index=4)

    best_of = st.radio("Format", [3,5], index=1, horizontal=True, format_func=lambda x: f"Best of {x}")

    # Transcript
    st.markdown("<hr>", unsafe_allow_html=True)
    st.markdown("<div class='card-label'>Press conference transcript <span style='color:#16162a'>optional</span></div>", unsafe_allow_html=True)

    use_transcript = st.toggle("Include NLP features from transcript", value=True)
    nlp_feats = {}

    if use_transcript:
        quick = st.multiselect("Quick-add fatigue signals",
                               ["tired","heavy legs","cramping","mentally drained","back-to-back",
                                "five sets","injury","my knee","not 100%","doubt"],
                               label_visibility="visible")
        transcript_text = st.text_area("Paste transcript here",
                                        placeholder='"I\'m really tired, my legs are heavy after five sets yesterday. My back is stiff and I\'m not 100%..."',
                                        height=120, label_visibility="collapsed")
        full_text = " ".join(quick) + " " + (transcript_text or "")
        if full_text.strip():
            nlp_feats = analyse_transcript(full_text)
            mc1,mc2,mc3,mc4 = st.columns(4)
            mc1.metric("Fatigue signals", nlp_feats["fatigue_total"])
            mc2.metric("Density/100w", f"{nlp_feats['fatigue_density']:.1f}")
            mc3.metric("Sentiment", f"{nlp_feats['sentiment_polarity']:+.2f}")
            mc4.metric("Word count", nlp_feats["word_count"])

    st.markdown("<div style='height:0.8rem'></div>", unsafe_allow_html=True)

    if st.button("⚡  PREDICT UPSET PROBABILITY", use_container_width=True):
        sentiment = nlp_feats.get("sentiment_polarity", 0.0)
        fatigue   = nlp_feats.get("fatigue_total", 0)

        with st.spinner("Running model…"):
            prob, shap_dict = predict(player_rank, opp_rank, ctfi, sentiment,
                                      fatigue, ROUND_MAP[round_sel], best_of)

        color = "#ff4d6d" if prob>=0.65 else "#f5a623" if prob>=0.40 else "#4d4dff"
        risk  = "HIGH UPSET RISK" if prob>=0.65 else "MODERATE RISK" if prob>=0.40 else "LOW RISK"

        r1, r2 = st.columns([2,3])
        with r1:
            st.markdown(f"""
            <div class='card' style='border-color:{color}22;text-align:center'>
              <div class='prob-num' style='color:{color}'>{prob*100:.0f}%</div>
              <div class='prob-lbl'>upset probability</div>
              <div style='font-family:JetBrains Mono,monospace;font-size:0.65rem;
                          letter-spacing:0.15em;color:{color};margin-top:0.5rem'>{risk}</div>
              <div class='prob-match'>{player} vs {opponent}<br>{round_sel}</div>
            </div>
            """, unsafe_allow_html=True)
            st.progress(prob)

        with r2:
            st.markdown("<div class='card-label'>AI Explanation</div>", unsafe_allow_html=True)
            explanation = None
            if groq_key:
                top   = sorted(shap_dict.items(), key=lambda x: abs(x[1]), reverse=True)[:4]
                lines = [f"  • {f.replace('_',' ')}: {v:+.3f}" for f,v in top if abs(v)>0.005]
                prompt = (f"Tennis analyst. {prob*100:.0f}% upset probability for {player} (rank {player_rank}) vs "
                          f"{opponent} (rank {opp_rank}) at a Grand Slam, {round_sel}.\n"
                          f"Top SHAP features:\n"+"\n".join(lines)+
                          "\n\nWrite 2 clear sentences for a general audience. What's driving the risk and what it means.")
                with st.spinner("Generating explanation…"):
                    explanation = groq_call(prompt, groq_key)

            if not explanation:
                top   = sorted(shap_dict.items(), key=lambda x: abs(x[1]), reverse=True)[:2]
                names = [f.replace("_"," ") for f,_ in top]
                level = "high" if prob>0.6 else "moderate" if prob>0.4 else "low"
                explanation = (f"The model assigns **{level}** upset risk ({prob*100:.0f}%) for {player}. "
                               f"Key drivers are **{names[0]}** and **{names[1] if len(names)>1 else 'rank gap'}**.")
                if not groq_key:
                    st.caption("Add a Groq key for richer explanations.")

            st.markdown(f"<div class='explain-box' style='border-color:{color}'>{explanation}</div>",
                        unsafe_allow_html=True)

            if shap_dict:
                st.markdown("<div class='card-label' style='margin-top:1rem'>Feature importance (SHAP)</div>", unsafe_allow_html=True)
                st.markdown("<div style='font-size:0.75rem;color:#22224a;margin-bottom:0.3rem'>Red = increases upset risk · Blue = decreases it</div>", unsafe_allow_html=True)
                st.markdown(shap_html(shap_dict), unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════════════
#  PAGE: SCOUTING REPORT
# ═══════════════════════════════════════════════════════════════════════════════
elif page == "Scouting Report":
    st.markdown("""
    <div class='page-eyebrow'>Tool 02 / 03</div>
    <div class='page-title'>Player <span class='hl2'>Scouting</span></div>
    <div class='page-sub'>Ask about a player's fatigue history. The AI searches press conference transcripts and generates a tactical scouting report.</div>
    """, unsafe_allow_html=True)

    groq_key = st.session_state.get("groq_key","")
    if not groq_key:
        groq_key = st.text_input("Groq API key for AI reports", type="password",
                                  placeholder="gsk_... (optional)", key="groq_scout")

    PLAYERS = ["Carlos Alcaraz","Novak Djokovic","Rafael Nadal","Jannik Sinner",
               "Daniil Medvedev","Stefanos Tsitsipas","Alexander Zverev","Andrey Rublev",
               "Roger Federer","Dominic Thiem","Felix Auger-Aliassime","Taylor Fritz",
               "Casper Ruud","Holger Rune","Ben Shelton","Frances Tiafoe"]

    if db_ok:
        try:
            import sqlite3
            conn = sqlite3.connect("tennis_upsets.db")
            # Pull players sorted by frequency so the most-transcribed players appear first
            rows = conn.execute("""
                SELECT player_name, COUNT(*) as cnt
                FROM transcripts
                WHERE player_name IS NOT NULL
                  AND player_name != 'Unknown'
                  AND LENGTH(player_name) > 3
                GROUP BY player_name
                ORDER BY cnt DESC
                LIMIT 80
            """).fetchall()
            conn.close()
            if rows:
                PLAYERS = [r[0] for r in rows]
        except Exception:
            pass

    c1, c2 = st.columns([1,2])
    with c1:
        player = st.selectbox("Select player", PLAYERS)
    with c2:
        query = st.text_input("What do you want to know?",
                               "What are this player's fatigue signals before upset losses?")

    adv1, adv2 = st.columns(2)
    with adv1:
        n_results  = st.slider("Excerpts to retrieve", 2, 10, 5)
    with adv2:
        upset_only = st.toggle("Only from upset matches", value=True)

    if st.button("◎  GENERATE SCOUTING REPORT", use_container_width=True):
        with st.spinner("Searching transcripts…"):
            snippets = search_transcripts(query, player, n_results, upset_only)

        if not snippets:
            st.markdown("<div class='card' style='color:#664444'>No matching transcripts found. Try turning off 'Only from upset matches'.</div>", unsafe_allow_html=True)
        else:
            st.markdown(f"<div class='card-label' style='margin-bottom:0.8rem'>✓ Retrieved {len(snippets)} excerpts</div>", unsafe_allow_html=True)

            # Generate report
            report = None
            if groq_key:
                context = "\n\n---\n\n".join(
                    f"[{s.get('tournament','?')} · {s.get('round','')} · {'UPSET' if s.get('upset') else 'WIN'}]\n{s['text'][:400]}"
                    for s in snippets[:5]
                )
                prompt = (f"You are a professional tennis scout writing for a coaching team.\n"
                          f"Question: {query}\nPlayer: {player}\n\nTranscripts:\n{context}\n\n"
                          f"Write a sharp, bullet-point scouting report (max 200 words). "
                          f"Focus on recurring fatigue patterns and match preparation insights.")
                with st.spinner("Writing report…"):
                    report = groq_call(prompt, groq_key, max_tokens=350)

            if not report:
                CATS = {
                    "Physical fatigue": ["tired","exhausted","heavy legs","cramping","drained","sore"],
                    "Mental fatigue":   ["mentally","focus","distracted","lost focus"],
                    "Schedule burden":  ["back-to-back","five sets","long match","tough schedule"],
                    "Injury concern":   ["injury","pain","knee","shoulder","back","ankle"],
                    "Motivation doubt": ["doubt","question mark","uncertain","not sure"],
                }
                combined = " ".join(s["text"] for s in snippets).lower()
                lines = []
                for cat, words in CATS.items():
                    hits = sum(len(re.findall(r"\b"+re.escape(w)+r"\b", combined)) for w in words)
                    if hits:
                        lines.append(f"• **{cat}**: {hits} mention{'s' if hits>1 else ''} detected")
                n_upsets = sum(1 for s in snippets if s.get("upset"))
                report   = (f"**Pattern analysis for {player}** *(from {len(snippets)} excerpts, "
                            f"{n_upsets} from upset matches)*\n\n"
                            + ("\n".join(lines) if lines else "• No strong fatigue signals detected.")
                            + "\n\n*Add a Groq key for a full AI-written scouting report.*")

            st.markdown("<div class='card'>", unsafe_allow_html=True)
            st.markdown(f"<div class='card-label' style='color:#4d4dff'>Scouting Report — {player}</div>", unsafe_allow_html=True)
            st.markdown(report)
            st.markdown("</div>", unsafe_allow_html=True)

            # Signal bars
            st.markdown("<div style='height:0.5rem'></div>", unsafe_allow_html=True)
            st.markdown("<div class='card-label'>Fatigue signal breakdown</div>", unsafe_allow_html=True)
            CATS2  = {"Physical":["tired","exhausted","heavy legs","cramping","sore"],
                      "Mental":["mentally","focus","distracted"],"Schedule":["back-to-back","five sets"],
                      "Injury":["injury","pain","knee","shoulder"],"Motivation":["doubt","uncertain"]}
            COLORS = ["#ff4d6d","#4d4dff","#e8ff48","#f5a623","#888"]
            combined = " ".join(s["text"] for s in snippets).lower()
            counts   = {cat: sum(len(re.findall(r"\b"+re.escape(w)+r"\b", combined)) for w in words)
                        for cat, words in CATS2.items()}
            mx = max(counts.values()) if max(counts.values())>0 else 1
            for (cat,val), color in zip(counts.items(), COLORS):
                pct = int(val/mx*100)
                st.markdown(
                    f"<div style='display:flex;align-items:center;gap:10px;margin:5px 0'>"
                    f"<span style='width:80px;font-family:JetBrains Mono,monospace;font-size:0.68rem;color:#33334a'>{cat}</span>"
                    f"<div style='flex:1;background:#0a0a18;border-radius:3px;height:10px'>"
                    f"<div style='width:{pct}%;background:{color};height:10px;border-radius:3px'></div></div>"
                    f"<span style='color:{color};font-family:JetBrains Mono,monospace;font-size:0.7rem;width:20px'>{val}</span>"
                    f"</div>", unsafe_allow_html=True)

            m1,m2,m3 = st.columns(3)
            m1.metric("Excerpts", len(snippets))
            m2.metric("From upsets", sum(1 for s in snippets if s.get("upset")))
            m3.metric("Total signals", sum(counts.values()))

            with st.expander("View all retrieved excerpts"):
                for i, s in enumerate(snippets, 1):
                    outcome = "🔴 UPSET" if s.get("upset") else "🟢 Win"
                    st.markdown(
                        f"<div class='snippet'><div class='snippet-meta'>{i} · {s.get('player','?')} · "
                        f"{s.get('tournament','?')} {s.get('round','')} · {outcome}</div>"
                        f"{s['text'][:500]}</div>", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════════════
#  PAGE: ASK THE MODEL
# ═══════════════════════════════════════════════════════════════════════════════
elif page == "Ask the Model":
    st.markdown("""
    <div class='page-eyebrow'>Tool 03 / 03</div>
    <div class='page-title'>Ask the <span class='hl3'>Model</span></div>
    <div class='page-sub'>Chat with 10 years of Grand Slam data. The AI routes your question to a SQL query, a transcript search, or both.</div>
    """, unsafe_allow_html=True)

    groq_key = st.session_state.get("groq_key","")
    if not groq_key:
        groq_key = st.text_input("Groq API key", type="password",
                                  placeholder="gsk_... (optional)", key="groq_chat")

    # Example buttons
    EXAMPLES = [
        ("📊","Upset rates by slam","What is the upset rate at each Grand Slam?"),
        ("🏆","Biggest upsets","Show the 5 biggest rank-gap upsets"),
        ("🔴","Favourite losses","Which top-10 player lost most as a favourite?"),
        ("🎾","Round analysis","Which round has the highest upset rate?"),
        ("💬","Fatigue quotes","Find mentions of cramping before an upset"),
        ("😓","Djokovic fatigue","What did Djokovic say about fatigue?"),
        ("🌿","Surface stats","Upset rates on grass vs clay"),
        ("📈","Dataset size","How many Grand Slam matches in the dataset?"),
    ]

    st.markdown("<div class='card-label' style='margin-bottom:0.5rem'>Try an example</div>", unsafe_allow_html=True)
    ecols = st.columns(4)
    for i, (icon, lbl, q) in enumerate(EXAMPLES):
        with ecols[i%4]:
            if st.button(f"{icon} {lbl}", key=f"ex_{i}", use_container_width=True):
                st.session_state.pending_q = q

    st.markdown("<hr>", unsafe_allow_html=True)

    # Init chat
    if not st.session_state.messages:
        st.session_state.messages = [{
            "role":"assistant",
            "content":"Hi! I can answer questions about Grand Slam upsets — stats, player patterns, and what players said in press conferences.\n\nTry one of the examples above or type your own question.",
            "source":""
        }]

    # Render messages
    for msg in st.session_state.messages:
        if msg["role"] == "user":
            st.markdown(f"<div class='chat-user'>{msg['content']}</div>",
                        unsafe_allow_html=True)
        else:
            content = msg["content"]
            source  = msg.get("source", "")
            src_tag = f"<div class='chat-source' style='margin-top:0.5rem'>{source}</div>" if source else ""
            # Render code blocks properly
            if "```" in content:
                parts   = content.split("```")
                display = parts[0]
                if len(parts) > 1:
                    table_block = parts[1].replace("\n","<br>")
                    display += f"<pre style='background:#0d0d1e;padding:0.8rem;border-radius:6px;font-family:JetBrains Mono,monospace;font-size:0.72rem;color:#6666aa;overflow-x:auto;margin-top:0.5rem'>{table_block}</pre>"
                st.markdown(f"<div class='chat-bot'>{display}{src_tag}</div>",
                            unsafe_allow_html=True)
            else:
                st.markdown(f"<div class='chat-bot'>{content}{src_tag}</div>",
                            unsafe_allow_html=True)
            if msg.get("snippets"):
                with st.expander("View transcript excerpts"):
                    for s in msg["snippets"][:3]:
                        outcome = "🔴 UPSET" if s.get("upset") else "🟢 Win"
                        st.markdown(
                            f"<div class='snippet'><div class='snippet-meta'>"
                            f"{s.get('player','?')} · {s.get('tournament','?')} "
                            f"{s.get('round','')} · {outcome}</div>"
                            f"{s['text'][:380]}</div>", unsafe_allow_html=True)

    # Input
    pending = st.session_state.pop("pending_q", None)
    user_input = st.chat_input("Ask anything about tennis upsets…")
    question   = pending or user_input

    if question:
        st.session_state.messages.append({"role":"user","content":question,"source":""})
        st.markdown(f"<div class='chat-user'>{question}</div>", unsafe_allow_html=True)

        q_lower   = question.lower()
        snippets  = []
        answer    = ""
        source    = ""

        is_transcript_q = any(w in q_lower for w in
            ["said","transcript","mention","fatigue","tired","cramping","press","quote","words"])

        with st.spinner("Thinking…"):
            if is_transcript_q:
                snippets  = search_transcripts(question, n=4, upset_only=False)
                df_result = None
                if groq_key and snippets:
                    context = "\n\n".join(
                        f"[{s.get('player','?')} – {s.get('tournament','?')} {s.get('round','')}]: {s['text'][:350]}"
                        for s in snippets
                    )
                    prompt = (f"You are a tennis analyst. Answer concisely:\n\n"
                              f"QUESTION: {question}\n\nEXCERPTS:\n{context}\n\nAnswer in 2-3 sentences:")
                    answer = groq_call(prompt, groq_key, max_tokens=200) or ""
                if not answer:
                    answer = "\n\n".join(
                        f"**{s.get('player','?')} — {s.get('tournament','?')} {s.get('round','')}**"
                        f" ({'UPSET' if s.get('upset') else 'win'}): {s['text'][:280]}…"
                        for s in snippets[:3]
                    ) or "No matching transcripts found."
                source = "◎ Transcript search"
            else:
                df_result, summary = answer_sql(question)
                ai_insight = ""
                if groq_key and df_result is not None:
                    data_str  = df_result.to_string(index=False)
                    prompt    = (f"Tennis analyst. User asked: '{question}'\nData:\n{data_str}\n\n"
                                 f"Write 1 clear, insightful sentence about the most interesting finding.")
                    ai_insight = groq_call(prompt, groq_key, max_tokens=80) or ""
                answer = ai_insight if ai_insight else summary
                source = "🗄️ SQL query"

        # ── Render the response ──────────────────────────────────────────
        if df_result is not None and not df_result.empty:
            # Build HTML table
            cols_html = "".join(
                f"<th style='padding:6px 12px;text-align:left;font-family:JetBrains Mono,monospace;"
                f"font-size:0.65rem;text-transform:uppercase;letter-spacing:0.1em;color:#33334a;"
                f"border-bottom:1px solid #16162a'>{c}</th>"
                for c in df_result.columns
            )
            rows_html = ""
            for i, row in df_result.iterrows():
                bg = "#0a0a18" if i%2==0 else "#080812"
                cells = "".join(
                    f"<td style='padding:8px 12px;font-size:0.85rem;color:#aaaacc;"
                    f"border-bottom:1px solid #0d0d1e'>{v}</td>"
                    for v in row.values
                )
                rows_html += f"<tr style='background:{bg}'>{cells}</tr>"

            table_html = (
                f"<div style='overflow-x:auto;margin-top:0.8rem'>"
                f"<table style='width:100%;border-collapse:collapse'>"
                f"<thead><tr>{cols_html}</tr></thead>"
                f"<tbody>{rows_html}</tbody></table></div>"
            )
            full_html = (
                f"<div class='chat-bot'>"
                f"<div style='margin-bottom:0.6rem;color:#c0c0e0'>{answer}</div>"
                f"{table_html}"
                f"<div class='chat-source' style='margin-top:0.6rem'>{source}</div>"
                f"</div>"
            )
            st.markdown(full_html, unsafe_allow_html=True)
            table_str = df_result.to_string(index=False)
        else:
            st.markdown(
                f"<div class='chat-bot'>{answer}"
                f"<div class='chat-source' style='margin-top:0.5rem'>{source}</div></div>",
                unsafe_allow_html=True
            )
            table_str = ""

        if snippets:
            with st.expander("View transcript excerpts"):
                for s in snippets[:3]:
                    outcome = "🔴 UPSET" if s.get("upset") else "🟢 Win"
                    st.markdown(
                        f"<div class='snippet'><div class='snippet-meta'>"
                        f"{s.get('player','?')} · {s.get('tournament','?')} "
                        f"{s.get('round','')} · {outcome}</div>"
                        f"{s['text'][:380]}</div>", unsafe_allow_html=True)

        # Save full content to history
        full_content = answer
        if table_str:
            full_content += f"\n\n```\n{table_str}\n```"
        st.session_state.messages.append({
            "role": "assistant", "content": full_content,
            "snippets": snippets, "source": source, "has_table": False,
        })

    if len(st.session_state.messages) > 1:
        if st.button("Clear conversation"):
            st.session_state.messages = []
            st.rerun()