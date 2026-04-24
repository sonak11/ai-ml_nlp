"""Page 1 — Real-time Upset Alert with LLM explanation."""

import streamlit as st
import numpy as np


ROUND_MAP = {"R1": 1, "R2": 2, "R3": 3, "R4": 4, "QF": 5, "SF": 6, "F": 7}
ROUND_LABELS = list(ROUND_MAP.keys())

FATIGUE_WORDS = [
    "tired", "exhausted", "heavy legs", "cramping", "drained",
    "back pain", "mentally tough", "back-to-back", "five sets",
    "physically tough", "injury", "tight schedule",
]


# ─── LLM explanation ─────────────────────────────────────────────────────────

def _groq_explain(prob, shap_dict, player, opponent, groq_key):
    try:
        from groq import Groq
        client = Groq(api_key=groq_key)
        top    = sorted(shap_dict.items(), key=lambda x: abs(x[1]), reverse=True)[:5]
        lines  = [f"  • {f.replace('_',' ')}: {v:+.3f}" for f, v in top if abs(v) > 0.005]
        prompt = (
            f"You are a tennis analyst. The model predicts a {prob*100:.1f}% upset probability "
            f"for {player} (underdog) vs {opponent} (favourite) at a Grand Slam.\n"
            f"Top contributing factors (SHAP values — positive = increases upset chance):\n"
            + "\n".join(lines)
            + "\n\nWrite a 2-sentence natural language explanation for a coach. "
              "Be specific about which factors matter most and why."
        )
        resp = client.chat.completions.create(
            model="llama3-70b-8192",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=120,
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        return f"(LLM unavailable: {e})"


def _rule_explain(prob, shap_dict, player, opponent):
    top = sorted(shap_dict.items(), key=lambda x: abs(x[1]), reverse=True)[:3]
    parts = []
    for feat, val in top:
        label = feat.replace("_", " ")
        direction = "increases" if val > 0 else "decreases"
        parts.append(f"{label} ({direction} risk by {abs(val):.2f})")
    drivers = ", ".join(parts) if parts else "rank gap and fatigue"
    level = "high" if prob > 0.6 else "moderate" if prob > 0.4 else "low"
    return (
        f"The model assigns a **{level}** upset risk of {prob*100:.1f}% for {player} vs {opponent}. "
        f"Key drivers: {drivers}."
    )


# ─── NLP transcript analyser ─────────────────────────────────────────────────

def _analyse_transcript(text: str) -> dict:
    """Quick rule-based NLP (mirrors nlp.py logic)."""
    import re
    text_l = text.lower()
    LEXICON = {
        "physical":  ["tired","exhausted","heavy legs","cramping","drained",
                       "sore","worn out","stiff","not 100","my body"],
        "mental":    ["mentally drained","mentally tired","mentally exhausting",
                       "lost focus","couldn't focus","distracted"],
        "schedule":  ["back to back","back-to-back","five sets","long match",
                       "played a lot","tough schedule","no rest","tight schedule"],
        "injury":    ["injury","pain","hurts","my knee","my shoulder",
                       "my back","my ankle","pulled my","blister","trainer"],
        "motivation":["doubt","not sure","hard to believe","question mark",
                       "uncertain","lacking confidence"],
    }
    counts = {k: 0 for k in LEXICON}
    total  = 0
    for cat, phrases in LEXICON.items():
        for ph in phrases:
            hits = len(re.findall(r"\b" + re.escape(ph) + r"\b", text_l))
            counts[cat] += hits
            total += hits

    words       = text.split()
    n_words     = max(len(words), 1)
    density     = round(total / n_words * 100, 2)

    # Sentiment: count positive vs negative words (simplified)
    pos = sum(text_l.count(w) for w in
              ["confident","great","good","ready","strong","sharp","relaxed","well"])
    neg = sum(text_l.count(w) for w in
              ["not","never","tired","exhausted","pain","doubt","worried","sore"])
    polarity    = round((pos - neg) / max(pos + neg, 1), 3)
    word_count  = len(words)

    return {
        "fatigue_total":    total,
        "fatigue_density":  density,
        "fatigue_physical": counts["physical"],
        "fatigue_mental":   counts["mental"],
        "fatigue_schedule": counts["schedule"],
        "fatigue_injury":   counts["injury"],
        "fatigue_motivation": counts["motivation"],
        "sentiment_polarity": polarity,
        "word_count":       word_count,
    }


# ─── SHAP waterfall visual ────────────────────────────────────────────────────

def _shap_bars(shap_dict):
    top    = sorted(shap_dict.items(), key=lambda x: abs(x[1]), reverse=True)[:8]
    mx     = max(abs(v) for _, v in top) if top else 1
    html   = "<div style='font-size:0.85rem;'>"
    for feat, val in top:
        width = int(abs(val) / mx * 100)
        color = "#ef4444" if val > 0 else "#22c55e"
        label = feat.replace("_", " ")
        sign  = "+" if val > 0 else "−"
        html += (
            f"<div style='margin:4px 0;display:flex;align-items:center;gap:8px;'>"
            f"<span style='width:160px;text-align:right;color:#aaa;font-size:0.8rem'>{label}</span>"
            f"<div style='width:{width}%;height:16px;background:{color};"
            f"border-radius:3px;transition:width 0.3s;'></div>"
            f"<span style='color:{color};font-weight:600'>{sign}{abs(val):.3f}</span>"
            f"</div>"
        )
    html += "</div>"
    return html


# ─── Render ───────────────────────────────────────────────────────────────────

def render(groq_key: str, model_exists: bool, features_exist: bool):
    st.title("🚨 Real-time Upset Alert")
    st.markdown(
        "Enter match details and an optional post-match transcript to get "
        "an upset probability with a natural language explanation."
    )

    if not model_exists:
        st.warning("⚠️ No trained model found — running with demo synthetic model. "
                   "Run `data_ingestion.py` → `model.py` to train on real data.")

    # ── Input form ──────────────────────────────────────────────────────────
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("🟦 Underdog Player")
        player      = st.text_input("Player name", "Carlos Alcaraz", key="p_name")
        player_rank = st.number_input("ATP Ranking", 1, 500, 45, key="p_rank")
        ctfi        = st.slider("Cumulative Tournament Fatigue Index (CTFI)",
                                0, 30, 8, help="Sets played so far this tournament")

    with col2:
        st.subheader("🟥 Favourite")
        opponent  = st.text_input("Opponent name", "Novak Djokovic", key="o_name")
        opp_rank  = st.number_input("ATP Ranking", 1, 500, 3, key="o_rank")
        round_sel = st.selectbox("Round", ROUND_LABELS, index=4)

    best_of = st.radio("Best of", [3, 5], index=1, horizontal=True)

    # ── Optional transcript ──────────────────────────────────────────────────
    st.markdown("---")
    st.subheader("📝 Post-match transcript (optional)")
    st.markdown("Paste the press conference transcript to extract NLP features automatically.")

    use_transcript = st.toggle("Include transcript NLP features", value=True)
    transcript_text = ""
    nlp_feats       = {}

    if use_transcript:
        quick_add = st.multiselect(
            "Quick-add fatigue signals (or type transcript below):",
            FATIGUE_WORDS,
        )
        transcript_text = st.text_area(
            "Transcript text",
            placeholder="Paste the press conference transcript here…",
            height=160,
        )
        # Merge quick-add words into text
        if quick_add:
            transcript_text = " ".join(quick_add) + " " + transcript_text

        if transcript_text.strip():
            nlp_feats = _analyse_transcript(transcript_text)
            with st.expander("📊 Extracted NLP features", expanded=False):
                ncol1, ncol2, ncol3 = st.columns(3)
                ncol1.metric("Fatigue total",    nlp_feats["fatigue_total"])
                ncol2.metric("Density per 100w", f"{nlp_feats['fatigue_density']:.2f}")
                ncol3.metric("Sentiment",        f"{nlp_feats['sentiment_polarity']:+.2f}")
                ncol1.metric("Physical",  nlp_feats["fatigue_physical"])
                ncol2.metric("Mental",    nlp_feats["fatigue_mental"])
                ncol3.metric("Schedule",  nlp_feats["fatigue_schedule"])
                ncol1.metric("Injury",    nlp_feats["fatigue_injury"])
                ncol2.metric("Motivation",nlp_feats["fatigue_motivation"])
                ncol3.metric("Word count",nlp_feats["word_count"])

    # ── Prediction ───────────────────────────────────────────────────────────
    st.markdown("---")
    if st.button("⚡ Predict Upset Probability", type="primary", use_container_width=True):
        from prediction_service import predict_with_explanation

        sentiment = nlp_feats.get("sentiment_polarity", 0.0)
        fatigue   = nlp_feats.get("fatigue_total", 0)

        with st.spinner("Running model…"):
            prob, shap_dict = predict_with_explanation(
                player_rank  = player_rank,
                opp_rank     = opp_rank,
                ctfi         = ctfi,
                sentiment_polarity = sentiment,
                fatigue_total      = fatigue,
                round_num    = ROUND_MAP[round_sel],
                best_of      = best_of,
            )

        # Colour band
        if prob >= 0.65:
            risk_class, emoji, label = "high-risk", "🔴", "HIGH RISK"
        elif prob >= 0.40:
            risk_class, emoji, label = "mid-risk",  "🟡", "MODERATE RISK"
        else:
            risk_class, emoji, label = "low-risk",  "🟢", "LOW RISK"

        st.markdown(f"""
        <div class="metric-card {risk_class}">
          <h2 style="margin:0">{emoji} {prob*100:.1f}% upset probability</h2>
          <p style="margin:4px 0 0;color:#888;">{label} — {player} vs {opponent} ({round_sel})</p>
        </div>
        """, unsafe_allow_html=True)

        # Progress bar
        st.progress(prob)

        # Explanation
        st.subheader("🧠 Explanation")
        if groq_key:
            with st.spinner("Generating LLM explanation…"):
                explanation = _groq_explain(prob, shap_dict, player, opponent, groq_key)
        else:
            explanation = _rule_explain(prob, shap_dict, player, opponent)
            st.caption("💡 Add a Groq API key in the sidebar for richer LLM explanations.")

        st.info(explanation)

        # SHAP chart
        if shap_dict:
            st.subheader("📊 Feature importance (SHAP)")
            st.markdown(
                "<small style='color:#888'>Red = increases upset chance | "
                "Green = decreases upset chance</small>",
                unsafe_allow_html=True,
            )
            st.markdown(_shap_bars(shap_dict), unsafe_allow_html=True)

        # Context table
        with st.expander("🔢 Input summary"):
            import pandas as pd
            df = pd.DataFrame({
                "Feature": ["Player rank", "Opponent rank", "CTFI", "Round",
                             "Sentiment", "Fatigue total", "Best of"],
                "Value":   [player_rank, opp_rank, ctfi, round_sel,
                             f"{sentiment:.2f}", fatigue, best_of],
            })
            st.dataframe(df, use_container_width=True, hide_index=True)
