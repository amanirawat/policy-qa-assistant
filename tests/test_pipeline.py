from pathlib import Path

import pytest

from policyqa.answer import NOT_COVERED_MSG, answer_question
from policyqa.ingest import Document, Section, build_chunks, chunk_document, load_markdown
from policyqa.retriever import BM25Retriever, tokenize

DOCS = Path(__file__).resolve().parents[1] / "data" / "docs"


@pytest.fixture(scope="module")
def retriever():
    return BM25Retriever(build_chunks(DOCS))


def test_markdown_front_matter_and_sections():
    doc = load_markdown(DOCS / "nist-sp-800-63b-passwords.md")
    assert doc.publisher == "NIST"
    assert doc.url.startswith("https://")
    assert any("expiration" in s.heading.lower() for s in doc.sections)


def test_long_sections_are_windowed_with_overlap():
    words = [f"w{i}" for i in range(300)]
    doc = Document("T", "t.md", None, None, [Section("S", " ".join(words))])
    chunks = chunk_document(doc, max_words=100, overlap=20)
    assert len(chunks) == 4
    assert chunks[0].text.split()[-20:] == chunks[1].text.split()[:20]
    assert all(c.section == "S" for c in chunks)


def test_tokenize_drops_stopwords_and_stems():
    assert tokenize("How do I change my passwords?") == ["change", "password"]


def test_retrieval_finds_right_document(retriever):
    hits = retriever.search("How do I recognize a phishing email?")
    assert hits[0].chunk.file == "cisa-secure-our-world.md"


def test_answer_has_citations(retriever):
    ans = answer_question("How often should passwords be changed?", retriever, mode="extractive")
    assert ans.covered
    assert ans.citations
    assert "[1]" in ans.text or "[2]" in ans.text


def test_out_of_scope_is_refused(retriever):
    ans = answer_question("What is the company's vacation policy?", retriever, mode="extractive")
    assert not ans.covered
    assert ans.text == NOT_COVERED_MSG
    assert ans.citations == []


def test_audit_log_written(retriever, tmp_path):
    log = tmp_path / "answers.jsonl"
    answer_question("Should PII be encrypted?", retriever, mode="extractive", log_path=log)
    line = log.read_text().strip()
    assert '"retrieved"' in line and '"cited_chunks"' in line


def test_llm_answer_without_citation_is_rejected(retriever, monkeypatch):
    import policyqa.answer as answer_mod

    monkeypatch.setattr(answer_mod, "llm_answer", lambda q, hits: ("Change it every 90 days.", []))
    ans = answer_question("How often should passwords be changed?", retriever, mode="llm")
    assert not ans.covered
    assert ans.reason == "model answer had no valid citation"


def test_llm_answer_with_citation_is_accepted(retriever, monkeypatch):
    import policyqa.answer as answer_mod

    monkeypatch.setattr(
        answer_mod, "llm_answer",
        lambda q, hits: ("Only change it when there is evidence of compromise [1].", [1]),
    )
    ans = answer_question("How often should passwords be changed?", retriever, mode="llm")
    assert ans.covered
    assert [c.number for c in ans.citations] == [1]
