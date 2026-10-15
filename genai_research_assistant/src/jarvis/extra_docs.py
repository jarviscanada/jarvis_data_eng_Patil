"""Add plain text documents (the pilot's planted documents, internal memos) to the chunks and to every index.

    python -m jarvis.extra_docs DOCS_DIR [--models minilm bge-small]

Each .txt file becomes paragraph aligned chunks with the same metadata as the filings. A file whose name starts with
JARVIS-INTERNAL-MEMO is tagged access "memo" (readable by regulatory_affairs only); every other file is "public".
The institution and fiscal year come from the file's first line ("Northwind Trust - ...", "fiscal 2025") or its name.
Re-running replaces the earlier copy of every document from the same folder.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from .index import Embedder, client, metadata
from .ingest import OUT, risk_category, tokens

EXTRA = OUT / "extra_chunks.jsonl"
BANK_CODES = {"Northwind Trust": "NWT", "Harbourline Bank": "HBL", "Jarvis Compliance Analytics": "JCA"}


def chunks_of(path: Path, max_tokens: int = 700) -> list[dict]:
    text = path.read_text(encoding="utf-8")
    first = text.splitlines()[0] if text else path.stem
    memo = path.name.startswith("JARVIS-INTERNAL-MEMO")
    # A memo is indexed under the institution it is about (named in its body), not under its author, so a question
    # about that institution finds it; a filing is indexed under the institution in its title.
    about = [n for n in BANK_CODES if n != "Jarvis Compliance Analytics" and n in text]
    bank_name = (about[0] if memo and about else
                 next((n for n in BANK_CODES if n in first or n.split()[0].upper() in path.stem), "Unknown"))
    years = re.findall(r"\b(20\d\d)\b", first + " " + path.stem)
    meta = {"filing_id": path.stem, "bank": BANK_CODES.get(bank_name, "OTHER"), "bank_name": bank_name,
            "document_type": "Internal Memo" if memo else "Pilot Document", "fiscal_year": int(years[-1]) if years else 0,
            "quarter": "Q3" if "Q3" in path.stem else "annual", "source_file": path.name, "source_url": "",
            "filed": "", "access": "memo" if memo else "public", "page": 1, "page_end": 1, "chunk_type": "text"}
    paras = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    out, cur = [], []
    for p in paras:
        if cur and tokens("\n".join(cur + [p])) > max_tokens:
            out.append(cur)
            cur = []
        cur.append(p)
    if cur:
        out.append(cur)
    res = []
    for i, part in enumerate(out):
        body = "\n".join(part)
        res.append({**meta, "chunk_id": f"{path.stem}#{i:02d}", "section": first[:80], "subsection": "",
                    "risk_category": risk_category(first, body), "text": f"[{first[:80]}]\n{body}", "tokens": tokens(body)})
    return res


def add(folder: Path, models: list[str]) -> dict:
    new = [c for p in sorted(folder.glob("*.txt")) if p.name.lower() != "readme.txt" for c in chunks_of(p)]
    names = {c["source_file"] for c in new}
    old = [json.loads(x) for x in EXTRA.read_text(encoding="utf-8").splitlines()] if EXTRA.exists() else []
    keep = [c for c in old if c["source_file"] not in names]
    EXTRA.write_text("".join(json.dumps(c, ensure_ascii=False) + "\n" for c in keep + new), encoding="utf-8")
    db = client()
    for m in models:
        col = db.get_collection(f"filings_{m}")
        stale = [c["chunk_id"] for c in old if c["source_file"] in names]
        if stale:
            col.delete(ids=stale)
        emb = Embedder(m)
        col.add(ids=[c["chunk_id"] for c in new], documents=[c["text"] for c in new],
                embeddings=emb.documents([c["text"] for c in new]), metadatas=[metadata(c) for c in new])
    return {"documents": len(names), "chunks": len(new), "memo_chunks": sum(c["access"] == "memo" for c in new)}


def load_extra() -> list[dict]:
    return [json.loads(x) for x in EXTRA.read_text(encoding="utf-8").splitlines()] if EXTRA.exists() else []


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("folder", type=Path)
    ap.add_argument("--models", nargs="+", default=["minilm", "bge-small"])
    a = ap.parse_args(argv)
    print(add(a.folder, a.models))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
