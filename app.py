"""Streamlit web UI.  Run with:  streamlit run app.py"""

import os
import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).parent / "src"))

from policyqa.answer import answer_question  # noqa: E402
from policyqa.cli import LOG_PATH, get_retriever  # noqa: E402

st.set_page_config(page_title="Cybersecurity Policy Q&A", page_icon="🔐", layout="centered")


@st.cache_resource
def retriever():
    return get_retriever()


st.title("🔐 Cybersecurity Policy Q&A")
st.caption("Answers come only from approved NIST and CISA guidance, with a citation for every answer.")

has_key = bool(os.environ.get("ANTHROPIC_API_KEY"))
mode = st.radio(
    "Answer mode",
    ["extractive", "llm"],
    index=1 if has_key else 0,
    horizontal=True,
    help="Extractive quotes the documents directly (free, offline). "
         "LLM writes a summary from the retrieved passages (needs ANTHROPIC_API_KEY).",
    disabled=not has_key,
)

examples = [
    "How often do I need to change my password?",
    "What should I do if I clicked a link in a phishing email?",
    "How do I get rid of an old laptop that had customer data on it?",
    "What is the company's vacation policy?",
]
st.write("Try one:")
cols = st.columns(2)
for i, ex in enumerate(examples):
    if cols[i % 2].button(ex, use_container_width=True):
        st.session_state["q"] = ex

question = st.text_input("Ask a security policy question", key="q")

if question:
    ans = answer_question(question, retriever(), mode=mode, log_path=LOG_PATH)
    if ans.covered:
        st.success(ans.text)
        st.subheader("Sources")
        for c in ans.citations:
            where = f"p. {c.page}" if c.page else c.section
            with st.expander(f"[{c.number}] {c.title} - {where}   (score {c.score})"):
                st.write(c.excerpt)
                if c.url:
                    st.markdown(f"[Official source]({c.url})")
    else:
        st.warning(ans.text)
        st.caption(f"Why: {ans.reason}")
