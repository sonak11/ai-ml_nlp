"""Page 2 — RAG-enhanced Player Scouting Report."""

import streamlit as st


def _groq_report(player, query, snippets, groq_key):
    try:
        from groq import Groq
        client  = Groq(api_key=groq_key)
        context = "\n\n---\n\n".join(
            f"[{s.get('tournament','?')} {s.get('round','')} – "
            f"{'UPSET' if s.get('upset') else 'win'}] {s['text'][:500]}"
            for s in snippets[:5]
        )
        prompt = (
            f"You are a professional tennis scout. Based on the transcript excerpts below "
            f"from {player}'s matches, answer the following question and produce a "
            f"concise scouting report:\n\nQUESTION: {query}\n\nTRANSCRIPTS:\n{context}\n\n"
            f"Scouting report (bullet points, 150-200 words max):"
        )
        resp = client.chat.completions.create(
            model="llama3-70b-8192",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.25,
            max_tokens=300,
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        return f"(LLM unavailable: {e})"


def _rule_report(player, query, snippets):
    if not snippets:
        return f"No transcript data found for **{player}** matching your query."

    # Count fatigue words across snippets
    import re
    FATIGUE_CATS = {
        "Physical fatigue": ["tired","exhausted","heavy legs","cramping","drained","sore"],
        "Mental fatigue":   ["mentally","focus","distracted","lost focus"],
        "Schedule burden":  ["back-to-back","five sets","long match","tough schedule"],
        "Injury concern":   ["injury","pain","knee","shoulder","back","ankle","blister"],
        "Motivation doubt": ["doubt","question mark","uncertain","not sure"],
    }
    combined = " ".join(s["text"] for s in snippets).lower()
    findings = []
    for cat, words in FATIGUE_CATS.items():
        hits = sum(len(re.findall(r"\b" + re.escape(w) + r"\b", combined)) for w in words)
        if hits:
            findings.append(f"- **{cat}**: {hits} mentions across {len(snippets)} excerpts")

    n_upsets = sum(1 for s in snippets if s.get("upset"))
    header   = (f"### Scouting report: {player}\n"
                f"*Based on {len(snippets)} retrieved transcript excerpts, "
                f"{n_upsets} from upset matches.*\n\n")
    body     = "\n".join(findings) if findings else "- No strong fatigue signals detected."
    note     = "\n\n> 💡 Add a Groq API key for a full LLM-generated report."
    return header + body + note


def render(groq_key: str, db_exists: bool):
    st.title("📋 Player Scouting Report")
    st.markdown(
        "Ask about a player's historical fatigue signals before upsets. "
        "Retrieves relevant transcript chunks via RAG and synthesises a scouting report."
    )

    if not db_exists:
        st.info(
            "ℹ️ No match database found — using demo transcripts. "
            "Run the full pipeline to scout from real data."
        )

    from rag_service import get_all_players

    known_players = get_all_players()
    col1, col2 = st.columns([2, 3])

    with col1:
        player = st.selectbox("Select player", known_players) if known_players else \
                 st.text_input("Player name", "Carlos Alcaraz")

    with col2:
        query = st.text_input(
            "What do you want to know?",
            "What are this player's fatigue signals before an upset?",
        )

    adv = st.expander("🔧 Advanced options")
    with adv:
        n_results  = st.slider("Number of transcript chunks to retrieve", 2, 10, 5)
        upset_only = st.checkbox("Only retrieve from upset matches", value=True)
        show_raw   = st.checkbox("Show retrieved transcript snippets", value=True)

    if st.button("📋 Generate Scouting Report", type="primary", use_container_width=True):
        from rag_service import search_transcripts

        with st.spinner("Retrieving relevant transcripts…"):
            snippets = search_transcripts(
                query        = query,
                player_filter = player,
                n_results    = n_results,
                upset_only   = upset_only,
            )

        if not snippets:
            st.warning(f"No relevant transcripts found for **{player}**. "
                       "Try a different player or broaden your query.")
            return

        st.markdown(f"✅ Retrieved **{len(snippets)}** relevant excerpts.")

        # Generate report
        with st.spinner("Generating scouting report…"):
            if groq_key:
                report = _groq_report(player, query, snippets, groq_key)
            else:
                report = _rule_report(player, query, snippets)

        st.markdown("---")
        st.subheader("📄 Scouting Report")
        st.markdown(report)

        # Visual summary
        st.markdown("---")
        st.subheader("📊 Fatigue signal breakdown")
        import re, pandas as pd

        FATIGUE_CATS = {
            "Physical":   ["tired","exhausted","heavy legs","cramping","drained","sore","not 100"],
            "Mental":     ["mentally","focus","distracted","lost focus","concentration"],
            "Schedule":   ["back-to-back","five sets","long match","tough schedule","no rest"],
            "Injury":     ["injury","pain","knee","shoulder","back","ankle","blister","trainer"],
            "Motivation": ["doubt","question mark","uncertain","not sure","hard to believe"],
        }
        combined = " ".join(s["text"] for s in snippets).lower()
        cat_counts = {}
        for cat, words in FATIGUE_CATS.items():
            cat_counts[cat] = sum(
                len(re.findall(r"\b" + re.escape(w) + r"\b", combined))
                for w in words
            )

        df_cats = pd.DataFrame(
            {"Category": list(cat_counts.keys()), "Mentions": list(cat_counts.values())}
        ).sort_values("Mentions", ascending=False)

        max_val = max(df_cats["Mentions"].max(), 1)
        for _, row in df_cats.iterrows():
            pct = int(row["Mentions"] / max_val * 100)
            color = "#ef4444" if pct > 60 else "#f59e0b" if pct > 30 else "#22c55e"
            st.markdown(
                f"<div style='display:flex;align-items:center;gap:10px;margin:6px 0'>"
                f"<span style='width:100px;color:#aaa'>{row['Category']}</span>"
                f"<div style='flex:1;background:#1e1e2e;border-radius:4px;height:18px'>"
                f"<div style='width:{pct}%;background:{color};height:18px;"
                f"border-radius:4px'></div></div>"
                f"<span style='color:{color};font-weight:600;width:30px'>{row['Mentions']}</span>"
                f"</div>",
                unsafe_allow_html=True,
            )

        # Match outcomes
        n_upsets = sum(1 for s in snippets if s.get("upset"))
        mc1, mc2, mc3 = st.columns(3)
        mc1.metric("Excerpts retrieved", len(snippets))
        mc2.metric("From upset matches", n_upsets)
        mc3.metric("Avg rank diff", f"{sum(s.get('rank_diff',0) for s in snippets)/len(snippets):.1f}")

        # Raw snippets
        if show_raw:
            st.markdown("---")
            st.subheader("📑 Retrieved transcript excerpts")
            for i, s in enumerate(snippets, 1):
                outcome = "🔴 UPSET" if s.get("upset") else "🟢 Win"
                with st.expander(
                    f"{i}. {s.get('player','?')} — {s.get('tournament','?')} "
                    f"{s.get('round','')} {outcome}"
                ):
                    st.markdown(s["text"])
                    if s.get("rank_diff"):
                        st.caption(f"Rank diff: {s['rank_diff']:.0f} | CTFI: {s.get('ctfi',0):.0f}")
