"""Step 2: embed every chunk and load it into ChromaDB with its metadata, one collection per embedding model.

    python -m jarvis.index --model minilm bge-small [titan]

Models (Module 4, Topic 2: compare a local model with a hosted one on our own data):
    minilm      sentence-transformers/all-MiniLM-L6-v2, 384 dimensions, local and free. It reads only the first 256
                word pieces of a text, shorter than our chunks, which the comparison makes visible.
    bge-small   BAAI/bge-small-en-v1.5, 384 dimensions, local and free, reads 512 tokens.
    titan       amazon.titan-embed-text-v2:0 on Bedrock, 1024 dimensions, reads up to 8,000 tokens.
    openai      text-embedding-3-small on the OpenAI API, 1,536 dimensions, reads up to 8,191 tokens, about $0.02 per
                million tokens (under the OpenAI budget cap in llm.py).
Embeddings are normalised, so cosine similarity is the inner product. The same model embeds the chunks and the queries.
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CHUNKS = ROOT / "data" / "processed" / "chunks.jsonl"
QUARTERLY_CHUNKS = ROOT / "data" / "processed" / "chunks_quarterly.jsonl"
STORE = ROOT / "models" / "chroma"
META_KEYS = ("filing_id", "bank", "bank_name", "document_type", "fiscal_year", "quarter", "section", "subsection",
             "risk_category", "page", "page_end", "chunk_type", "source_file", "source_url", "tokens", "access")
MODELS = {"minilm": "sentence-transformers/all-MiniLM-L6-v2", "bge-small": "BAAI/bge-small-en-v1.5",
          "titan": "amazon.titan-embed-text-v2:0", "openai": "text-embedding-3-small"}
OPENAI_EMBED_PRICE = 0.02          # USD per million tokens, text-embedding-3-small (for the budget cap's log)
# One model call at a time in this process: PyTorch BERT inference is not safe from several threads at once (a pilot
# run crashed with an access violation inside the model when two requests overlapped; the Streamlit app is threaded).
MODEL_LOCK = __import__("threading").RLock()
QUERY_PREFIX = {"bge-small": "Represent this sentence for searching relevant passages: "}


def use_onnx(name: str) -> bool:
    """The local models run on ONNX Runtime once exported (`python -m jarvis.onnx_models export`); JARVIS_TORCH=1
    goes back to PyTorch."""
    import os
    from .onnx_models import available
    return os.environ.get("JARVIS_TORCH") != "1" and available(name)


class Embedder:
    def __init__(self, name: str):
        self.name = name
        self.dim = None
        if name == "titan":
            from .llm import bedrock_client
            self._client = bedrock_client()
        elif name == "openai":
            pass                                           # a client per call, so the budget cap is checked each time
        elif use_onnx(name):
            from .onnx_models import OnnxModel             # same vectors as PyTorch (checked), no PyTorch loaded
            self._onnx = OnnxModel(name)
        else:
            from sentence_transformers import SentenceTransformer
            self._model = SentenceTransformer(MODELS[name], device="cpu")

    def _titan_one(self, t: str) -> list[float]:
        body = json.dumps({"inputText": t[:30000], "dimensions": 1024, "normalize": True})
        r = self._client.invoke_model(modelId=MODELS["titan"], body=body)
        return json.loads(r["body"].read())["embedding"]

    def _titan(self, texts: list[str]) -> list[list[float]]:
        """One call per text (Titan takes one input), eight at a time."""
        from concurrent.futures import ThreadPoolExecutor
        with ThreadPoolExecutor(8) as pool:
            return list(pool.map(self._titan_one, texts))

    def _openai(self, texts: list[str]) -> list[list[float]]:
        """OpenAI embeddings (1,536 dimensions, normalised), logged with tokens and cost like every model call."""
        from .llm import _log, openai_client
        t0 = time.monotonic()
        for attempt in range(8):                           # the tokens per minute limit: wait and retry
            try:
                r = openai_client().embeddings.create(model=MODELS["openai"], input=[t[:24000] for t in texts])
                break
            except Exception as exc:  # noqa: BLE001
                if attempt == 7 or "RateLimit" not in type(exc).__name__:
                    raise
                time.sleep(min(60, 5 * 2 ** attempt))
        tok = r.usage.total_tokens
        _log({"t": time.time(), "tag": "embed", "role": "embed", "provider": "openai", "model": MODELS["openai"],
              "ms": round((time.monotonic() - t0) * 1000), "input_tokens": tok, "output_tokens": 0,
              "usd": round(tok * OPENAI_EMBED_PRICE / 1e6, 6)})
        return [d.embedding for d in r.data]

    def documents(self, texts: list[str]) -> list[list[float]]:
        if self.name == "titan":
            return self._titan(texts)
        if self.name == "openai":
            return self._openai(texts)
        if hasattr(self, "_onnx"):
            return self._onnx.encode(texts).tolist()
        with MODEL_LOCK:
            return self._model.encode(texts, batch_size=32, normalize_embeddings=True, show_progress_bar=False).tolist()

    def query(self, text: str) -> list[float]:
        if self.name == "titan":
            return self._titan([text])[0]
        if self.name == "openai":
            return self._openai([text])[0]
        if hasattr(self, "_onnx"):
            return self._onnx.encode([QUERY_PREFIX.get(self.name, "") + text])[0].tolist()
        with MODEL_LOCK:
            return self._model.encode([QUERY_PREFIX.get(self.name, "") + text], normalize_embeddings=True).tolist()[0]


def load_chunks(path: Path | None = None) -> list[dict]:
    """The annual filings' chunks and, when parsed, the quarterly reports' chunks (or one file, when named)."""
    paths = [path] if path else [p for p in (CHUNKS, QUARTERLY_CHUNKS) if p.exists()]
    return [json.loads(x) for p in paths for x in p.read_text(encoding="utf-8").splitlines() if x.strip()]


def metadata(c: dict) -> dict:
    """Chroma takes str, int, float and bool values only."""
    out = {}
    for k in META_KEYS:
        v = c.get(k, "public" if k == "access" else "")
        out[k] = v if isinstance(v, (int, float, bool)) else str(v)
    return out


def client():
    import chromadb
    STORE.mkdir(parents=True, exist_ok=True)
    return chromadb.PersistentClient(path=str(STORE))


def build(name: str, chunks: list[dict] | None = None, batch: int = 64, resume: bool = False) -> dict:
    """Embed every chunk into the model's collection. `resume` keeps what an interrupted build already stored."""
    chunks = chunks if chunks is not None else load_chunks()
    emb = Embedder(name)
    db = client()
    if not resume:
        try:
            db.delete_collection(f"filings_{name}")
        except Exception:  # noqa: BLE001  not there yet
            pass
    col = db.get_or_create_collection(f"filings_{name}", metadata={"hnsw:space": "cosine", "model": MODELS[name]})
    if resume:
        have = set(col.get(include=[])["ids"])
        chunks = [c for c in chunks if c["chunk_id"] not in have]
    t0 = time.monotonic()
    for i in range(0, len(chunks), batch):
        part = chunks[i:i + batch]
        col.add(ids=[c["chunk_id"] for c in part], documents=[c["text"] for c in part],
                embeddings=emb.documents([c["text"] for c in part]), metadatas=[metadata(c) for c in part])
    secs = round(time.monotonic() - t0, 1)
    stats = {"model": name, "chunks": col.count(), "seconds": secs}
    (STORE / f"build_{name}.json").write_text(json.dumps(stats, indent=1), encoding="utf-8")
    return stats


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--model", nargs="+", default=["minilm", "bge-small"], choices=list(MODELS))
    a = ap.parse_args(argv)
    for m in a.model:
        print(build(m))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
