"""Step 2 and 3: retrieval over the filings. Top-k, MMR, hybrid (vector plus BM25), metadata filters inferred from the
question, a similarity floor, and role based access.

    from jarvis.retrieve import Retriever
    r = Retriever("bge-small")
    r.search("What was RBC's provision for credit losses in 2025?", strategy="hybrid", k=5)

Scope from the question (Module 4: "always filter by bank, document type and period"): a question that names a bank
or a fiscal year is searched only in that bank's or year's filings, so an answer cannot borrow another bank's or
another year's figure. A question that names several banks or years searches all of them.
Quarters: a question that names a quarter ("Q2 2025", "the second quarter of 2024", or its end date "as at April 30,
2025") searches that quarter's Report to Shareholders; Q4 is reported in the annual filings. A question that names no quarter and does not ask about quarterly
or interim results searches the annual filings only, so "the CET1 ratio at the end of fiscal 2025" cannot pick up a Q3
figure.
Access: every chunk carries `access` ("public" or "memo"); a role reads only what ROLE_ACCESS allows, and the filter is
applied inside the vector search, before anything reaches the model.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, field

from .index import Embedder, client, load_chunks

BANK_NAMES = {
    "RBC": [r"\brbc\b", r"royal bank"], "TD": [r"\btd\b", r"toronto[- ]dominion"],
    "BMO": [r"\bbmo\b", r"bank of montreal"], "BNS": [r"scotia", r"\bbns\b", r"bank of nova scotia"],
    "CIBC": [r"\bcibc\b", r"canadian imperial"], "NWT": [r"northwind"], "HBL": [r"harbourline"]}
DOC_TYPES = {"Annual Information Form": r"\baif\b|annual information form",
             "Financial Statements": r"financial statements|balance sheet|notes? to the",
             "Annual Report (MD&A)": r"\bmd&a\b|management'?s discussion"}
ROLE_ACCESS = {"analyst": ["public"], "regulatory_affairs": ["public", "memo"]}
QUARTERLY = "Quarterly Report"
ORDINAL = {"first": 1, "second": 2, "third": 3, "fourth": 4}
QUARTER_END = {"january": 1, "april": 2, "july": 3, "october": 4}
QUARTER_WORDS = r"\bquarter(ly|s)?\b|\binterim\b|three months ended|six months ended|nine months ended|\bytd\b|year.to.date"
MIN_SIMILARITY = 0.30


@dataclass
class Scope:
    banks: list[str] = field(default_factory=list)
    years: list[int] = field(default_factory=list)
    doc_types: list[str] = field(default_factory=list)
    quarters: list[str] = field(default_factory=list)     # "Q1" to "Q3", or "annual" for Q4
    quarterly: bool = True                                # False: the quarterly reports are left out

    def where(self, role: str = "analyst") -> dict | None:
        clauses = [{"access": {"$in": ROLE_ACCESS.get(role, ["public"])}}]
        if self.banks:
            clauses.append({"bank": {"$in": self.banks}})
        if self.years:
            clauses.append({"fiscal_year": {"$in": self.years}})
        if self.quarters:
            clauses.append({"quarter": {"$in": self.quarters}})
        elif not self.quarterly:
            clauses.append({"document_type": {"$ne": QUARTERLY}})
        if self.doc_types:
            dts = list(self.doc_types)
            if "Annual Report (MD&A)" in dts:
                dts.append("Annual Report")             # RBC's single exhibit holds its MD&A
            if set(self.quarters) - {"annual"}:
                dts.append(QUARTERLY)                   # a quarterly report holds its own MD&A and statements
            clauses.append({"document_type": {"$in": dts}})
        return clauses[0] if len(clauses) == 1 else {"$and": clauses}


def scope_of(question: str) -> Scope:
    q = question.lower().replace("’", "'")
    banks = [b for b, pats in BANK_NAMES.items() if any(re.search(p, q) for p in pats)]
    years = sorted({int(y) for y in re.findall(r"\b(20\d\d)\b", q)})
    if re.search(r"\b(last|previous|prior) year\b", q) and years:
        years = sorted(set(years) | {min(years) - 1})
    docs = [d for d, p in DOC_TYPES.items() if re.search(p, q)]
    named = {int(n) for n in re.findall(r"\bq([1-4])\b", q)}
    named |= {ORDINAL[w] for w in re.findall(r"\b(first|second|third|fourth)[- ]quarter", q)}
    # A quarter end date names its quarter: all five banks close their fiscal quarters on January 31, April 30,
    # July 31 and October 31 (the year end), and that calendar year is the fiscal year. Not when the question names
    # an annual document: there a date only says when something happened ("the dividend approved for the quarter
    # ending January 31, 2026", asked of the fiscal 2025 annual report).
    if not docs and not re.search(r"\bannual\b", q):
        named |= {QUARTER_END[m] for m, _ in re.findall(r"\b(january|april|july|october)\s+3[01],?\s+(20\d\d)\b", q)}
    quarters = sorted({f"Q{n}" if n < 4 else "annual" for n in named})
    return Scope(banks, years, docs, quarters, quarterly=bool(quarters) or bool(re.search(QUARTER_WORDS, q)))


def _tok(text: str) -> list[str]:
    return re.findall(r"[a-z0-9$%.]+", text.lower())


class BM25:
    """Okapi BM25 over the chunks, for exact terms (bank names, guideline numbers, metric names)."""

    def __init__(self, chunks: list[dict], k1: float = 1.5, b: float = 0.75):
        from rank_bm25 import BM25Okapi
        self.ids = [c["chunk_id"] for c in chunks]
        self.meta = {c["chunk_id"]: c for c in chunks}
        self.bm = BM25Okapi([_tok(c["text"]) for c in chunks], k1=k1, b=b)

    def search(self, query: str, allowed: set[str] | None, n: int) -> list[tuple[str, float]]:
        scores = self.bm.get_scores(_tok(query))
        ranked = sorted(((s, i) for i, s in zip(self.ids, scores) if allowed is None or i in allowed), reverse=True)
        return [(i, s) for s, i in ranked[:n]]


def _matches(meta: dict, where: dict | None) -> bool:
    if not where:
        return True
    if "$and" in where:
        return all(_matches(meta, w) for w in where["$and"])
    (k, cond), = where.items()
    if "$ne" in cond:
        return meta.get(k) != cond["$ne"]
    return meta.get(k) in cond["$in"]


class Retriever:
    def __init__(self, model: str = "minilm", extra_chunks: list[dict] | None = None):
        self.model = model
        self.emb = Embedder(model)
        self.col = client().get_collection(f"filings_{model}")
        self._bm25 = None
        self._extra = extra_chunks or []

    @property
    def bm25(self) -> BM25:
        if self._bm25 is None:
            from .extra_docs import load_extra
            self._bm25 = BM25(load_chunks() + load_extra() + self._extra)
        return self._bm25

    def _vector(self, query: str, where: dict | None, n: int) -> list[dict]:
        r = self.col.query(query_embeddings=[self.emb.query(query)], n_results=n, where=where,
                           include=["documents", "metadatas", "distances", "embeddings"])
        out = []
        for i, d, m, dist, e in zip(r["ids"][0], r["documents"][0], r["metadatas"][0], r["distances"][0],
                                    r["embeddings"][0]):
            out.append({"chunk_id": i, "text": d, **m, "similarity": round(1 - dist, 4), "embedding": list(e)})
        return out

    def search(self, query: str, strategy: str = "hybrid", k: int = 5, role: str = "analyst",
               scope: Scope | None = None, lam: float = 0.7, floor: float = MIN_SIMILARITY) -> list[dict]:
        """strategy: topk, mmr, hybrid or rerank (hybrid candidates reordered by a cross encoder). Returns at most k
        chunks above the similarity floor, best first."""
        scope = scope if scope is not None else scope_of(query)
        where = scope.where(role)
        if strategy == "topk":
            hits = self._vector(query, where, k)
        elif strategy == "mmr":
            hits = mmr(self._vector(query, where, max(20, 4 * k)), k, lam)
        elif strategy == "rerank":
            hits = rerank(query, self._hybrid(query, where, max(20, 4 * k)), k)
        else:
            hits = self._hybrid(query, where, k)
        hits = [h for h in hits if h["similarity"] >= floor]
        for h in hits:
            h.pop("embedding", None)
        return hits

    def neighbours(self, hits: list[dict], role: str = "analyst", scope: Scope | None = None, top: int = 3,
                   extra: int = 3) -> list[dict]:
        """Small to big: for the best `top` hits, add the chunk just before or after in the same filing when it
        shares a page, so a table travels with the paragraph that explains it (and the reverse). At most `extra`
        chunks are added, each under the same scope and role filter as the search, after the retrieved ones."""
        where = (scope or Scope()).where(role)
        have, added = {h["chunk_id"] for h in hits}, []
        for h in hits[:top]:
            fid, _, num = h["chunk_id"].rpartition("#")
            if not num.isdigit():
                continue
            for step in (-1, 1):
                cid = f"{fid}#{int(num) + step:0{len(num)}d}"
                c = self.bm25.meta.get(cid)
                if not c or cid in have or len(added) >= extra:
                    continue
                if not _matches(c | {"access": c.get("access", "public")}, where):
                    continue
                lo, hi = int(c.get("page") or 0), int(c.get("page_end") or c.get("page") or 0)
                if lo <= int(h.get("page_end") or h["page"]) and hi >= int(h["page"]):
                    added.append({**c, "similarity": h["similarity"], "neighbour_of": h["chunk_id"]})
                    have.add(cid)
        return hits + added

    def _hybrid(self, query: str, where: dict | None, k: int, n: int = 40, rrf: int = 60) -> list[dict]:
        """Reciprocal rank fusion of the vector ranking and the BM25 ranking, both inside the same filter."""
        vec = self._vector(query, where, n)
        allowed = {cid for cid, meta in self.bm25.meta.items() if _matches(meta | {"access": meta.get("access", "public")}, where)}
        kw = self.bm25.search(query, allowed, n)
        score: dict[str, float] = {}
        for rank, h in enumerate(vec):
            score[h["chunk_id"]] = score.get(h["chunk_id"], 0) + 1 / (rrf + rank + 1)
        for rank, (cid, _s) in enumerate(kw):
            score[cid] = score.get(cid, 0) + 1 / (rrf + rank + 1)
        by_id = {h["chunk_id"]: h for h in vec}
        missing = [cid for cid in score if cid not in by_id]
        if missing:                                       # keyword only hits: fetch them to give a similarity
            r = self.col.get(ids=missing, include=["documents", "metadatas", "embeddings"])
            q = self.emb.query(query)
            for cid, d, m, e in zip(r["ids"], r["documents"], r["metadatas"], r["embeddings"]):
                by_id[cid] = {"chunk_id": cid, "text": d, **m, "similarity": round(sum(a * b for a, b in zip(q, e)), 4),
                              "embedding": list(e)}
        ranked = sorted(score, key=score.get, reverse=True)[:k]
        return [{**by_id[c], "fusion": round(score[c], 5)} for c in ranked if c in by_id]


def mmr(cands: list[dict], k: int, lam: float = 0.7) -> list[dict]:
    """Maximal marginal relevance: relevant to the query, unlike what is already picked."""
    def cos(a, b):
        return sum(x * y for x, y in zip(a, b)) / (math.sqrt(sum(x * x for x in a)) * math.sqrt(sum(y * y for y in b)) or 1)
    picked, rest = [], list(cands)
    while rest and len(picked) < k:
        best = max(rest, key=lambda c: lam * c["similarity"]
                   - (1 - lam) * max((cos(c["embedding"], p["embedding"]) for p in picked), default=0))
        picked.append(best)
        rest.remove(best)
    return picked


_CROSS = []


def rerank(query: str, cands: list[dict], k: int) -> list[dict]:
    """Reorder candidates with a cross encoder that reads the query and each passage together (more precise than
    comparing two separate embeddings), keeping the first k."""
    if not cands:
        return cands
    from .index import MODEL_LOCK, use_onnx
    pairs = [(query, c["text"][:2000]) for c in cands]
    if not _CROSS:
        if use_onnx("rerank"):
            from .onnx_models import OnnxModel        # same scores as PyTorch (checked), thread safe
            _CROSS.append(OnnxModel("rerank"))
        else:
            from sentence_transformers import CrossEncoder
            _CROSS.append(CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2", device="cpu", max_length=512))
    if hasattr(_CROSS[0], "score"):
        scores = _CROSS[0].score(pairs)
    else:
        with MODEL_LOCK:
            scores = _CROSS[0].predict(pairs, show_progress_bar=False)
    ranked = sorted(zip(scores, range(len(cands))), reverse=True)[:k]
    return [{**cands[i], "rerank": round(float(sc), 3)} for sc, i in ranked]
