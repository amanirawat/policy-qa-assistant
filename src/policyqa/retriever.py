"""BM25 keyword retrieval, implemented from scratch (no external search library).

Why BM25 instead of embeddings? It runs offline with zero API cost, it is fully
explainable (you can see exactly which words matched), and for policy text full
of specific terms ("MFA", "sanitization", "PII") it performs well.

Each hit also reports *coverage*: the share of the question's meaningful words
that appear in the chunk. Coverage is what the answerer uses to decide whether a
question is actually covered by the approved documents.
"""

from __future__ import annotations

import math
import re
from collections import Counter
from dataclasses import dataclass

from .ingest import Chunk

STOPWORDS = set("""
a an and are as at be been but by can could do does did for from has have how i
if in into is it its me my of on or our should so that the their them then there
these they this to us was we were what when where which who why will with would
you your yours about any also am being both each few more most other some such
than too very just only own same s t don isn aren need needs
had get got make sure company companies policy policies difference between okay ok
""".split())

# Light synonym map so common employee phrasing hits the policy vocabulary.
SYNONYMS = {
    "2fa": ["mfa", "multi", "factor"],
    "two": ["multi"],
    "passcode": ["password"],
    "passphrase": ["password"],
    "hack": ["incident", "compromise"],
    "hacked": ["incident", "compromised"],
    "breach": ["incident", "compromise"],
    "scam": ["phishing"],
    "suspicious": ["phishing", "suspicious"],
    "wipe": ["sanitization", "purge"],
    "erase": ["sanitization", "clear"],
    "dispose": ["disposal", "destroy"],
    "throw": ["disposal", "trash"],
    "personal": ["pii", "personal"],
    "ssn": ["social", "security", "number", "pii"],
    "patch": ["update"],
    "patching": ["update"],
    "long": ["length"],
    "rid": ["disposal", "destroy"],
    "sms": ["sms", "restricted"],
    "text": ["sms"],
}

_TOKEN = re.compile(r"[a-z0-9]+")


def stem(word: str) -> str:
    """Tiny suffix stripper so 'passwords'/'password', 'reporting'/'report' match."""
    for suffix in ("ations", "ation", "ings", "ing", "ions", "ion", "edly", "ed", "es", "s"):
        if word.endswith(suffix) and len(word) - len(suffix) >= 4:
            return word[: -len(suffix)]
    return word


def tokenize(text: str, expand: bool = False) -> list[str]:
    tokens = []
    for raw in _TOKEN.findall(text.lower()):
        if raw in STOPWORDS:
            continue
        tokens.append(stem(raw))
        if expand:
            tokens.extend(stem(s) for s in SYNONYMS.get(raw, []))
    return tokens


@dataclass
class Hit:
    chunk: Chunk
    score: float
    coverage: float
    matched_terms: list[str]


class BM25Retriever:
    def __init__(self, chunks: list[Chunk], k1: float = 1.5, b: float = 0.75):
        self.chunks = chunks
        self.k1, self.b = k1, b
        # Section headings are included (twice) so a chunk under
        # "Password expiration" ranks well for expiration questions.
        self.doc_tokens = [
            tokenize(f"{c.section} {c.section} {c.title} {c.text}") for c in chunks
        ]
        self.term_freqs = [Counter(toks) for toks in self.doc_tokens]
        self.doc_lens = [len(toks) for toks in self.doc_tokens]
        self.avg_len = sum(self.doc_lens) / max(len(self.doc_lens), 1)
        df = Counter()
        for toks in self.doc_tokens:
            df.update(set(toks))
        n = len(chunks)
        self.idf = {t: math.log(1 + (n - f + 0.5) / (f + 0.5)) for t, f in df.items()}
        self.max_idf = max(self.idf.values(), default=1.0)

    def term_weight(self, term: str) -> float:
        """IDF weight of a term. Words that never appear in the approved documents
        get the maximum weight: an unknown word like 'deposit' is strong evidence
        the question is about something the documents don't cover."""
        return self.idf.get(term, self.max_idf)

    def _score(self, query_terms: list[str], i: int) -> float:
        tf, dl = self.term_freqs[i], self.doc_lens[i]
        score = 0.0
        for term in query_terms:
            if term not in tf:
                continue
            freq = tf[term]
            denom = freq + self.k1 * (1 - self.b + self.b * dl / self.avg_len)
            score += self.idf.get(term, 0.0) * freq * (self.k1 + 1) / denom
        return score

    def search(self, query: str, k: int = 4) -> list[Hit]:
        original = set(tokenize(query))
        expanded = tokenize(query, expand=True)
        if not original:
            return []
        hits = []
        for i, chunk in enumerate(self.chunks):
            score = self._score(expanded, i)
            if score <= 0:
                continue
            present = self.term_freqs[i]
            # Coverage counts a question word as matched if it, or one of its
            # synonyms, appears in the chunk.
            matched = [
                t for t in original
                if t in present or any(stem(s) in present for s in SYNONYMS.get(t, []))
            ]
            hits.append(Hit(chunk, score, len(matched) / len(original), sorted(matched)))
        hits.sort(key=lambda h: h.score, reverse=True)
        return hits[:k]
