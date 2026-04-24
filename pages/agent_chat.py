"""Page 3 — Conversational SQL + Vector Agent."""

import streamlit as st


EXAMPLE_QUESTIONS = [
    "What is the upset rate at each Grand Slam?",
    "Which top-10 player lost most often as a favourite?",
    "Show the biggest rank-difference upsets in the dataset",
    "What did Djokovic say about fatigue before his upset losses?",
    "Which round has the highest upset rate?",
    "Find matches where 'cramping' was mentioned before an upset",
    "Compare upset rates on grass vs clay",
    "How many matches are in the dataset?",
]


def _format_table(text: str) -> str:
    """Detect a DataFrame string and wrap in a code block."""
    if "\n" in text and any(c.isdigit() for c in text):
        lines = text.strip().split("\n")
        if len(lines) > 2:
            return f"```\n{text}\n```"
    return text


def render(groq_key: str, db_exists: bool):
    st.title("💬 Ask the Model")
    st.markdown(
        "Ask natural language questions about Grand Slam upsets. "
        "The agent routes to **SQL** (structured stats) or "
        "**vector search** (transcript patterns) as appropriate."
    )

    if not db_exists:
        st.info(
            "ℹ️ Database not found — answering from demo statistics. "
            "Run the full pipeline for real query results."
        )

    if not groq_key:
        st.warning(
            "💡 Add a **Groq API key** in the sidebar to unlock the full LangChain agent "
            "(SQL + vector tool-use). Without it, a rule-based router is used instead."
        )

    # ── Conversation history ─────────────────────────────────────────────────
    if "messages" not in st.session_state:
        st.session_state.messages = [
            {
                "role": "assistant",
                "content": (
                    "👋 Hi! I can answer questions about Grand Slam upsets — "
                    "statistics, player patterns, and what players said in press conferences. "
                    "Try one of the example questions below, or ask your own."
                ),
                "snippets": [],
            }
        ]

    # ── Example buttons ──────────────────────────────────────────────────────
    st.markdown("**Example questions:**")
    cols = st.columns(4)
    for i, q in enumerate(EXAMPLE_QUESTIONS):
        if cols[i % 4].button(q[:40] + ("…" if len(q) > 40 else ""), key=f"ex_{i}"):
            st.session_state.pending_question = q

    st.markdown("---")

    # ── Chat display ─────────────────────────────────────────────────────────
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            content = msg["content"]
            # Detect table-like content
            if "```" not in content and "\n" in content:
                content = _format_table(content)
            st.markdown(content)

            # Show snippets if any
            if msg.get("snippets"):
                with st.expander("📑 Retrieved transcript excerpts"):
                    for s in msg["snippets"][:3]:
                        outcome = "🔴 UPSET" if s.get("upset") else "🟢 Win"
                        st.markdown(
                            f"**{s.get('player','?')} — {s.get('tournament','?')} "
                            f"{s.get('round','')} {outcome}**\n\n{s['text'][:400]}…"
                        )

    # ── Input ────────────────────────────────────────────────────────────────
    # Consume pending question from example buttons
    pending = st.session_state.pop("pending_question", None)
    user_input = st.chat_input("Ask a question about tennis upsets…")
    question   = pending or user_input

    if question:
        # Add user message
        st.session_state.messages.append(
            {"role": "user", "content": question, "snippets": []}
        )
        with st.chat_message("user"):
            st.markdown(question)

        # Get answer
        with st.chat_message("assistant"):
            with st.spinner("Thinking…"):
                from agent_service import answer_question
                answer, snippets, used_agent = answer_question(question, groq_key)

            # Format
            display = _format_table(answer)
            st.markdown(display)

            tag = ""
            if used_agent:
                tag = " *(LangChain agent)*"
            elif "sql" in answer.lower() or any(c.isdigit() for c in answer[:20]):
                tag = " *(SQL query)*"
            else:
                tag = " *(transcript search)*"
            if tag:
                st.caption(f"Answered via{tag}")

            if snippets:
                with st.expander("📑 Retrieved transcript excerpts"):
                    for s in snippets[:3]:
                        outcome = "🔴 UPSET" if s.get("upset") else "🟢 Win"
                        st.markdown(
                            f"**{s.get('player','?')} — {s.get('tournament','?')} "
                            f"{s.get('round','')} {outcome}**\n\n{s['text'][:400]}…"
                        )

        st.session_state.messages.append(
            {"role": "assistant", "content": answer, "snippets": snippets}
        )

    # ── Controls ─────────────────────────────────────────────────────────────
    st.markdown("---")
    col1, col2 = st.columns([1, 4])
    with col1:
        if st.button("🗑️ Clear chat"):
            st.session_state.messages = []
            st.rerun()

    with col2:
        st.caption(
            "The agent routes structured questions to SQL and "
            "transcript/language questions to semantic vector search."
        )
