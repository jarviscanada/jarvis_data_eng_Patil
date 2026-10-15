"""Jarvis research assistant: the live demo (Module 4, Day 10).

    streamlit run app.py

Ask about the Big Five banks' fiscal 2024 and 2025 filings. Every answer cites bank, document, year and page; every
figure is checked against its cited passage; agent mode shows each tool call (the audit trail E-23 asks for).
"""

from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).parent / "src"))

from jarvis import llm  # noqa: E402
from jarvis.agent import Agent  # noqa: E402
from jarvis.rag import RAG  # noqa: E402

st.set_page_config(page_title="Jarvis Research Assistant", page_icon="📑", layout="wide")


@st.cache_resource
def rag(strategy: str, prompt: str) -> RAG:
    return RAG(strategy=strategy, prompt=prompt)


@st.cache_resource
def agent() -> Agent:
    return Agent()


def md(text: str) -> str:
    """Streamlit reads text between two $ signs as math; filings are full of dollar amounts."""
    return str(text).replace("$", "\\$")


def figures(checks: list[dict]) -> str:
    """✅ found in a cited passage, 🧮 computed from cited figures (the calculation shown), ⚠️ not verified."""
    return "**Figure check:** " + md("  ".join(
        (f"🧮 {c['figure']} ({c['computed']})" if c.get("computed") else f"✅ {c['figure']}") if c["supported"]
        else f"⚠️ {c['figure']}" for c in checks))


with st.sidebar:
    st.header("Settings")
    role = st.selectbox("Signed in as", ["analyst", "regulatory_affairs"],
                        help="Analysts read public filings only; regulatory affairs also reads internal memos.")
    mode = st.radio("Mode", ["Answer (RAG)", "Research (agent)"])
    strategy = st.selectbox("Retrieval", ["rerank", "hybrid", "mmr", "topk"],
                            help="rerank: hybrid search reordered by a cross encoder (the evaluation's winner)")
    prompt = st.selectbox("Prompt", ["cot", "fewshot", "basic"])
    try:
        m = llm.models()
        st.caption(f"Answers: {m['gen'].split('.')[-1]}  \nJudge: {m['judge'].split('.')[-1]}")
    except Exception as exc:  # noqa: BLE001  most often an expired AWS sign in
        st.error("Cannot reach the models on AWS Bedrock. Sign in again in a terminal:\n\n"
                 f"`{llm.login_hint()}`\n\nthen refresh this page.")
        st.caption(type(exc).__name__)
        st.stop()
    st.divider()
    st.caption("Examples")
    for ex in ["What was RBC's CET1 ratio at the end of fiscal 2025?",
               "How did TD's provision for credit losses change from fiscal 2024 to 2025?",
               "What was BMO's net income in Q2 2025 compared with Q1 2025?",
               "Which banks discuss model risk management or OSFI E-23 in their 2025 filings?",
               "How did BMO's description of climate risk change between 2024 and 2025?"]:
        if st.button(ex, use_container_width=True):
            st.session_state["q"] = ex

st.title("Jarvis Research Assistant")
st.caption("Big Five Canadian bank filings, fiscal 2024 and 2025: Annual Information Forms, MD&A and financial "
           "statements (SEC EDGAR copies), and the Q1 to Q3 Reports to Shareholders (PDF, from each bank's site). Name a "
           "quarter to search its report. A first pass review tool: every answer needs analyst review.")
q = st.text_input("Question", value=st.session_state.get("q", ""), placeholder="Ask about a bank, a risk and a year")

if q:
    with st.spinner("Researching..."):
        if mode.startswith("Answer"):
            out = rag(strategy, prompt).answer(q, role=role)
            conf = {"high": "🟢", "medium": "🟡", "low": "🔴"}.get(out["confidence"], "⚪")
            st.subheader(f"{conf} Answer ({out['confidence']} confidence)")
            st.markdown(md(out["answer"]))
            if out["figure_check"]:
                st.markdown(figures(out["figure_check"]))
            for c in out["caveats"]:
                st.warning(md(c))
            if out["sources"]:
                st.write("**Sources**")
                st.dataframe([{k: s.get(k, s["year"]) for k in ("id", "bank", "document", "period", "section", "page")}
                              for s in out["sources"]], hide_index=True, use_container_width=True)
            st.caption(md(f"Scope applied: {out['scope']} | {out.get('ms', 0)} ms | ${out.get('usd', 0):.4f}"))
        else:
            out = agent().run(q, role=role)
            st.subheader("Answer")
            st.markdown(md(out["answer"]))
            if out["figure_check"]:
                st.markdown(figures(out["figure_check"]))
            if out["sources"]:
                st.write("**Sources:** " + "; ".join(out["sources"]))
            with st.expander(f"Audit trail: {out['iterations']} steps, {len(out['tool_calls'])} tool calls"):
                for t in out["trace"]:
                    if "tool" in t:
                        st.markdown(f"**Step {t['step']}** `{t['tool']}` {t['args']} -> {t['results']} passages")
                    else:
                        st.markdown(f"**Step {t['step']}** final answer")
            st.caption(md(f"{out['seconds']} s | ${out['usd']:.4f}"))
