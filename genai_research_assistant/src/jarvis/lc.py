"""Steps 4 and 5 in LangChain: the same RAG pipeline and agent, built from LangChain components.

    from jarvis.lc import LCRAG, lc_agent
    LCRAG().answer("What was TD's net income in Q2 2025?")
    lc_agent("How did RBC's description of credit risk change between fiscal 2024 and 2025?")

The module teaches LangChain; rag.py and agent.py are written without a framework so every step is visible and
testable. This module rebuilds both with LangChain over the same Chroma collections, prompts, scope rules and figure
check, so the two can be compared on the same test set (notebook 07):
    retrieval  EnsembleRetriever: langchain_chroma.Chroma (vector) and BM25Retriever (keywords), both inside the
               question's scope and the caller's role, fused by reciprocal rank -> CrossEncoderReranker -> the chunks
               next to the best hits (a table with its explanation)
    chain      LCEL: rewrite (HyDE) | retrieve | prompt | chat model | retry once wider if declined | JSON | figure check
    agent      langchain.agents.create_agent with the agent's tools as StructuredTools (role applied inside each tool)
    engines    the embedding model and the reranker run on ONNX Runtime through LangChain's Embeddings and
               BaseCrossEncoder interfaces, the same engine as the native build
    models     ChatBedrockConverse, ChatOpenAI or a local Ollama model, chosen by JARVIS_PROVIDER like llm.py
"""

from __future__ import annotations

import json
import os
import re
import time

from langchain_community.cross_encoders.base import BaseCrossEncoder
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from langchain_core.messages import AIMessage, SystemMessage, ToolMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableLambda, RunnablePassthrough
from langchain_core.tools import StructuredTool

from . import llm
from .index import client
from .rag import ABSTAIN, PROMPTS, context_block, figure_caveat, figure_check, parse_json, period
from .retrieve import MIN_SIMILARITY, scope_of

RERANKER = "cross-encoder/ms-marco-MiniLM-L-6-v2"
REWRITE = ("Rewrite the analyst's question as a search query for Canadian bank filings, then add one sentence that a "
           "filing passage answering it might contain (no invented numbers). Keep every bank name and fiscal year. "
           "Reply with the query and the sentence only.")
META = ("filing_id", "bank", "bank_name", "document_type", "fiscal_year", "quarter", "section", "subsection",
        "risk_category", "page", "page_end", "chunk_type", "source_file", "source_url", "tokens", "access")


def chat_model(role: str = "gen", max_tokens: int = 900):
    """The provider's chat model for a role (gen, judge, rewrite), temperature 0."""
    m = llm.models()
    if m["provider"] == "openai":
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(model=m.get(role, m["gen"]), temperature=0, max_tokens=max_tokens)
    if m["provider"] == "ollama":                         # Ollama speaks the OpenAI API locally
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(model=m["gen"], temperature=0, max_tokens=max_tokens, api_key="ollama",
                          base_url=os.environ.get("JARVIS_OLLAMA_URL", "http://127.0.0.1:11434/v1"))
    from langchain_aws import ChatBedrockConverse
    return ChatBedrockConverse(model=m.get(role, m["gen"]), region_name=llm.REGION, temperature=0, max_tokens=max_tokens,
                               credentials_profile_name=llm.aws_profile())


class IndexEmbeddings(Embeddings):
    """index.py's Embedder behind LangChain's Embeddings interface: the same model, query prefix and engine (ONNX
    Runtime once exported) that built the collection."""

    def __init__(self, model: str):
        from .index import Embedder
        self.emb = Embedder(model)

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return self.emb.documents(texts)

    def embed_query(self, text: str) -> list[float]:
        return self.emb.query(text)


def vectorstore(model: str = "minilm"):
    """The index.py collection, opened through LangChain with the same embedding model and query prefix."""
    from langchain_chroma import Chroma
    return Chroma(client=client(), collection_name=f"filings_{model}", embedding_function=IndexEmbeddings(model))


def _hit(doc: Document, sim: float) -> dict:
    return {**doc.metadata, "chunk_id": doc.id or doc.metadata.get("chunk_id", ""), "text": doc.page_content,
            "similarity": round(sim, 4)}


class OnnxCrossEncoder(BaseCrossEncoder):
    """The reranker on ONNX Runtime behind LangChain's cross encoder interface (same scores as PyTorch, checked)."""

    def score(self, text_pairs: list[tuple[str, str]]) -> list[float]:
        from .onnx_models import OnnxModel
        if not _ONNX:
            _ONNX.append(OnnxModel("rerank"))
        return [float(s) for s in _ONNX[0].score([(q, d[:2000]) for q, d in text_pairs])]


_ONNX: list = []


class LCRAG:
    """rewrite (HyDE) -> hybrid retrieval: EnsembleRetriever of Chroma (vector) and BM25Retriever (keywords), both
    inside the question's scope and the caller's role -> CrossEncoderReranker -> neighbouring chunks -> prompt ->
    model -> JSON -> figure check, with one wider retry before declining: the native pipeline's design, in LangChain."""

    def __init__(self, model: str = "minilm", k: int = 6, prompt: str = "cot", rerank: bool = True,
                 hybrid: bool = True, rewrite: bool = True, retry: bool = True):
        from langchain_classic.retrievers.document_compressors import CrossEncoderReranker
        from .retrieve import Retriever
        self.k, self.store, self.hybrid, self.retry = k, vectorstore(model), hybrid, retry
        self.native = Retriever(model)                     # passage metadata for BM25 and the neighbouring chunks
        self.reranker = CrossEncoderReranker(model=self._cross(), top_n=k) if rerank else None
        self._bm25: dict = {}
        template = ChatPromptTemplate.from_messages([SystemMessage(content=PROMPTS[prompt]),
                                                     ("human", "CONTEXT:\n{context}\n\nQUESTION: {question}")])
        self.answer_chain = template | chat_model("gen") | StrOutputParser()
        rewrite_chain = (ChatPromptTemplate.from_messages([SystemMessage(content=REWRITE), ("human", "{question}")])
                         | chat_model("rewrite", max_tokens=150) | StrOutputParser())
        self.chain = (RunnablePassthrough.assign(query=(lambda x: x["question"] + "\n" + rewrite_chain.invoke(x))
                                                 if rewrite else (lambda x: x["question"]))
                      | RunnablePassthrough.assign(hits=RunnableLambda(lambda x: self._retrieve(x, x["query"], self.k)))
                      | RunnablePassthrough.assign(context=lambda x: context_block(x["hits"]))
                      | RunnablePassthrough.assign(raw=self.answer_chain)
                      | RunnableLambda(self._maybe_retry)
                      | RunnableLambda(self._finish))

    @staticmethod
    def _cross():
        from .index import use_onnx
        if use_onnx("rerank"):
            return OnnxCrossEncoder()
        from langchain_community.cross_encoders import HuggingFaceCrossEncoder
        return HuggingFaceCrossEncoder(model_name=RERANKER)

    def _keyword(self, where: dict, role: str):
        """A BM25Retriever over the passages this scope and role allow (cached per filter)."""
        from langchain_community.retrievers import BM25Retriever
        from .retrieve import _matches, _tok
        key = json.dumps(where, sort_keys=True)
        if key not in self._bm25:
            docs = [Document(page_content=c["text"], id=cid, metadata={**{k: c.get(k) for k in META}, "chunk_id": cid})
                    for cid, c in self.native.bm25.meta.items()
                    if _matches(c | {"access": c.get("access", "public")}, where)]
            self._bm25[key] = BM25Retriever.from_documents(docs, k=40, preprocess_func=_tok) if docs else None
        return self._bm25[key]

    def _retrieve(self, x: dict, query: str, k: int) -> list[dict]:
        from langchain_classic.retrievers import EnsembleRetriever
        role = x.get("role", "analyst")
        scope = scope_of(x["question"])
        where = scope.where(role)
        vector = self.store.as_retriever(search_kwargs={"k": 40, "filter": where})
        keyword = self._keyword(where, role) if self.hybrid else None
        retriever = EnsembleRetriever(retrievers=[vector, keyword], weights=[0.5, 0.5]) if keyword else vector
        docs = retriever.invoke(query)[:max(20, 4 * k)]
        if not docs:
            return []
        ids = [d.id or d.metadata.get("chunk_id") for d in docs]
        got = self.store._collection.get(ids=ids, include=["embeddings"])   # similarity for the floor, every passage
        q = self.store.embeddings.embed_query(query)
        sim = {i: float(sum(a * b for a, b in zip(q, e))) for i, e in zip(got["ids"], got["embeddings"])}
        for d, i in zip(docs, ids):
            d.id = i
        if self.reranker:
            self.reranker.top_n = k
            docs = list(self.reranker.compress_documents(docs, x["question"]))
        hits = [_hit(d, sim.get(d.id, 0.0)) for d in docs if sim.get(d.id, 0.0) >= MIN_SIMILARITY][:k]
        return self.native.neighbours(hits, role=role, scope=scope) if hits else hits

    def _maybe_retry(self, x: dict) -> dict:
        """Declined? Search again with the analyst's own words and twice the passages before giving up."""
        out = parse_json(x["raw"])
        if not (self.retry and out.get("abstained")):
            return x
        seen = {h["chunk_id"] for h in x["hits"]}
        wider = x["hits"] + [h for h in self._retrieve(x, x["question"], 2 * self.k) if h["chunk_id"] not in seen]
        if len(wider) == len(x["hits"]):
            return x
        raw = self.answer_chain.invoke({"question": x["question"], "context": context_block(wider)})
        return {**x, "hits": wider, "raw": raw} if not parse_json(raw).get("abstained") else x

    @staticmethod
    def _finish(x: dict) -> dict:
        hits = x["hits"]
        if not hits:
            return {"answer": ABSTAIN, "abstained": True, "confidence": "high", "caveats": ["No passage passed the "
                    "relevance threshold."], "figure_check": [], "sources": []}
        out = parse_json(x["raw"]) or {"answer": x["raw"].strip(), "citations": [], "confidence": "low",
                                       "caveats": ["The model did not return JSON."], "abstained": False}
        ids = [c.strip("[] ") for c in out.get("citations", [])] or re.findall(r"\[(S\d+)\]", out.get("answer", ""))
        cited = [hits[int(i[1:]) - 1] for i in ids if re.fullmatch(r"S\d+", i) and 0 < int(i[1:]) <= len(hits)]
        checks = [] if out.get("abstained") else figure_check(out.get("answer", ""), cited)
        caveats = list(out.get("caveats") or [])
        if any(not c["supported"] for c in checks):
            caveats.append(figure_caveat(checks))
            out["confidence"] = "low"
        return {"answer": out.get("answer", ""), "abstained": bool(out.get("abstained")),
                "confidence": out.get("confidence", "low"), "caveats": caveats, "figure_check": checks,
                "sources": [{"id": f"S{hits.index(h) + 1}", "bank": h["bank"], "document": h["document_type"],
                             "period": period(h), "section": h["section"], "page": h["page"]} for h in cited],
                "retrieved": [h["chunk_id"] for h in hits],
                "context": context_block(hits)}

    def answer(self, question: str, role: str = "analyst") -> dict:
        t0 = time.monotonic()
        out = self.chain.invoke({"question": question, "role": role})
        return {**out, "ms": round((time.monotonic() - t0) * 1000), "framework": "langchain"}


def lc_tools(role: str, native=None) -> list[StructuredTool]:
    """The agent's tools as LangChain StructuredTools. The caller's role is bound here, inside each tool, so the
    model can never widen it."""
    from .agent import TOOLS, Agent
    native = native or Agent()
    calls = [0]

    def make(spec: dict) -> StructuredTool:
        def run(**kwargs) -> str:
            res = native.tool(spec["name"], kwargs, role)
            calls[0] += 1
            items = res if isinstance(res, list) else res.get("passages", [])
            shown = context_block(items).replace("[S", f"[T{calls[0]}:S") if items else ""   # unique ids across calls
            extra = {k: v for k, v in res.items() if k != "passages"} if isinstance(res, dict) else {}
            return (shown + ("\n" + json.dumps(extra) if extra else ""))[:12000] or "no results"
        return StructuredTool.from_function(func=run, name=spec["name"], description=spec["description"],
                                            args_schema=spec["parameters"])
    return [make(s) for s in TOOLS]


def lc_agent(question: str, role: str = "analyst", max_iterations: int = 8, native=None) -> dict:
    """A LangChain agent (create_agent, a tool calling loop) with the same system prompt and tools as agent.py."""
    from langchain.agents import create_agent
    from .agent import SYSTEM
    t0 = time.monotonic()
    graph = create_agent(chat_model("gen"), tools=lc_tools(role, native), system_prompt=SYSTEM)
    try:
        state = graph.invoke({"messages": [{"role": "user", "content": question}]},
                             config={"recursion_limit": 2 * max_iterations + 1})
        msgs = state["messages"]
    except Exception as exc:  # noqa: BLE001  LangGraph raises at the step limit; report it like agent.py does
        if "Recursion" not in type(exc).__name__:
            raise
        msgs = []
    trace, by_id = [], {}
    for m in msgs:
        if isinstance(m, AIMessage):
            for call in m.tool_calls:
                by_id[call["id"]] = {"tool": call["name"], "args": call["args"]}
                trace.append(by_id[call["id"]])
        elif isinstance(m, ToolMessage) and m.tool_call_id in by_id:
            by_id[m.tool_call_id]["result_chars"] = len(str(m.content))
    final = next((m for m in reversed(msgs) if isinstance(m, AIMessage) and not m.tool_calls), None)
    answer = final.text if final else "Stopped at the iteration limit before an answer; see the trace."
    context = "\n\n".join(str(m.content) for m in msgs if isinstance(m, ToolMessage))
    return {"question": question, "role": role, "answer": answer, "tool_calls": trace, "framework": "langchain",
            "seconds": round(time.monotonic() - t0, 1), "context": context[:30000]}
