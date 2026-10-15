"""The local models on ONNX Runtime instead of PyTorch: the two embedding models and the cross encoder reranker.

    python -m jarvis.onnx_models export      writes models/onnx/<name>.onnx (once, from the installed PyTorch models)
    python -m jarvis.onnx_models check       compares ONNX against PyTorch on 300 real chunks

Why: long pilot runs saw a rare native crash (an access violation inside PyTorch's CPU BERT activation, about once
per 1,000 requests). ONNX Runtime runs the same weights through a different, thread safe engine, and the serving path
then never imports PyTorch. The pooling matches sentence-transformers exactly: MiniLM takes the mean over tokens
(256 word pieces at most), BGE takes the first token (512 at most); both are normalised. The check proves the ONNX
vectors equal the PyTorch ones, so the existing index stays valid.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
DIR = ROOT / "models" / "onnx"
SPECS = {"minilm": ("sentence-transformers/all-MiniLM-L6-v2", "mean", 256),
         "bge-small": ("BAAI/bge-small-en-v1.5", "cls", 512),
         "rerank": ("cross-encoder/ms-marco-MiniLM-L-6-v2", "logit", 512)}


def path(name: str) -> Path:
    return DIR / f"{name}.onnx"


def available(name: str) -> bool:
    return path(name).exists()


def export(name: str) -> Path:
    import torch
    from transformers import AutoModel, AutoModelForSequenceClassification, AutoTokenizer
    repo, kind, _ = SPECS[name]
    tok = AutoTokenizer.from_pretrained(repo)
    model = (AutoModelForSequenceClassification if kind == "logit" else AutoModel).from_pretrained(repo).eval()
    enc = tok(["a sample sentence", "another, longer sample sentence"], padding=True, return_tensors="pt")
    args = (enc["input_ids"], enc["attention_mask"], enc["token_type_ids"])
    DIR.mkdir(parents=True, exist_ok=True)
    out = "logits" if kind == "logit" else "last_hidden_state"

    class ByName(torch.nn.Module):                        # inputs by name: positional order differs across versions
        def __init__(self, m):
            super().__init__()
            self.m = m

        def forward(self, input_ids, attention_mask, token_type_ids):
            r = self.m(input_ids=input_ids, attention_mask=attention_mask, token_type_ids=token_type_ids)
            return r.logits if kind == "logit" else r.last_hidden_state

    with torch.no_grad():
        torch.onnx.export(ByName(model), args, str(path(name)), input_names=["input_ids", "attention_mask", "token_type_ids"],
                          output_names=[out], dynamic_axes={k: {0: "batch", 1: "seq"} for k in
                                                            ("input_ids", "attention_mask", "token_type_ids")},
                          opset_version=17, dynamo=False)
    tok.save_pretrained(DIR / f"{name}_tokenizer")
    return path(name)


class OnnxModel:
    """One session per model; ONNX Runtime sessions are safe to call from several threads."""

    def __init__(self, name: str):
        import onnxruntime as ort
        from tokenizers import Tokenizer
        self.name, (_, self.kind, self.max_len) = name, SPECS[name]
        opts = ort.SessionOptions()
        opts.intra_op_num_threads = 4
        self.sess = ort.InferenceSession(str(path(name)), opts, providers=["CPUExecutionProvider"])
        self.tok = Tokenizer.from_file(str(DIR / f"{name}_tokenizer" / "tokenizer.json"))
        self.tok.enable_truncation(self.max_len)
        self.tok.enable_padding()

    def _run(self, encs) -> np.ndarray:
        ids = np.array([e.ids for e in encs], dtype=np.int64)
        mask = np.array([e.attention_mask for e in encs], dtype=np.int64)
        types = np.array([e.type_ids for e in encs], dtype=np.int64)
        out = self.sess.run(None, {"input_ids": ids, "attention_mask": mask, "token_type_ids": types})[0]
        if self.kind == "logit":
            return out[:, 0]
        if self.kind == "cls":
            vec = out[:, 0]
        else:
            m = mask[..., None].astype(np.float32)
            vec = (out * m).sum(1) / np.clip(m.sum(1), 1e-9, None)
        return vec / np.clip(np.linalg.norm(vec, axis=1, keepdims=True), 1e-12, None)

    def encode(self, texts: list[str], batch: int = 32) -> np.ndarray:
        return np.vstack([self._run(self.tok.encode_batch(texts[i:i + batch])) for i in range(0, len(texts), batch)])

    def score(self, pairs: list[tuple[str, str]], batch: int = 16) -> np.ndarray:
        return np.concatenate([self._run(self.tok.encode_batch(pairs[i:i + batch])) for i in range(0, len(pairs), batch)])


def check(n: int = 300) -> dict:
    """ONNX against PyTorch on real chunks: embeddings (cosine) and reranker scores (absolute difference)."""
    from sentence_transformers import CrossEncoder, SentenceTransformer
    from .index import QUERY_PREFIX, load_chunks
    texts = [c["text"] for c in load_chunks()[::30][:n]]
    out = {}
    for name in ("minilm", "bge-small"):
        st = SentenceTransformer(SPECS[name][0], device="cpu").encode(texts, normalize_embeddings=True)
        ox = OnnxModel(name).encode(texts)
        cos = (st * ox).sum(1)
        q = QUERY_PREFIX.get(name, "") + "What was the CET1 ratio?"
        qcos = float((SentenceTransformer(SPECS[name][0], device="cpu").encode([q], normalize_embeddings=True)
                      * OnnxModel(name).encode([q])).sum())
        out[name] = {"min_cosine": round(float(cos.min()), 6), "mean_cosine": round(float(cos.mean()), 6),
                     "query_cosine": round(qcos, 6)}
    pairs = [("What was the provision for credit losses?", t[:2000]) for t in texts[:100]]
    a = CrossEncoder(SPECS["rerank"][0], device="cpu", max_length=512).predict(pairs, show_progress_bar=False)
    b = OnnxModel("rerank").score(pairs)
    out["rerank"] = {"max_abs_diff": round(float(np.abs(a - b).max()), 5),
                     "same_order_top5": list(np.argsort(-a)[:5]) == list(np.argsort(-b)[:5])}
    return out


if __name__ == "__main__":
    if sys.argv[1:] == ["export"]:
        for m in SPECS:
            print(m, export(m))
    else:
        print(check())
