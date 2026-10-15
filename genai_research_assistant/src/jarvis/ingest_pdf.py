"""Step 1b (quarterly): parse the quarterly Reports to Shareholders (PDF) into the same chunks as the annual filings.

    python -m jarvis.ingest_pdf

Reads data/raw/quarterly/manifest.json and writes data/processed/chunks_quarterly.jsonl, filing_index_quarterly.csv
and text/<id>.txt. The PDF reader yields the same ("page",) / ("heading", text, top) / ("para", text) / ("table", text)
items as the HTML reader, so cleaning and chunking are shared (ingest.clean, ingest.chunk).

PDF choices:
* Page numbers are the PDF's own pages (what a reader's viewer shows), so a citation opens on the right page.
* Running headers and footers sit in the top and bottom margins and are dropped by position.
* Headings: short blocks set larger than the body text or in bold; clearly larger ones, or known MD&A section names,
  start a top level section.
* Tables in these reports have no ruling lines, so rows are rebuilt from positions: lines at the same height with two
  or more figures form a row; neighbouring rows form a table, which also takes in its column headers and wrapped
  labels; cells are joined with " | " like the HTML tables.
"""

from __future__ import annotations

import csv
import json
import re
from collections import Counter
from pathlib import Path

import pymupdf

from .ingest import OUT, chunk, clean, top_section

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data" / "raw" / "quarterly"
MARGIN = 0.055                                            # share of the page height holding running headers/footers
FIGURE = re.compile(r"^\(?[-–]?\$?\s*\(?[\d,]*\d(\.\d+)?\)?\s*(%|bps|x)?\)?$|^(n\.?m\.?|n/a|–|—|-|nil)$", re.I)
SPAN_GAP = 6.0                                            # points between spans that make two cells


def _bold(span: dict) -> bool:
    return bool(span["flags"] & 16) or "bold" in span["font"].lower() or "black" in span["font"].lower()


def segments(page: pymupdf.Page) -> list[dict]:
    """Every horizontal text run on the page outside the margins, split into cells where spans are far apart."""
    h = page.rect.height
    out = []
    for bi, b in enumerate(page.get_text("dict")["blocks"]):
        for li, line in enumerate(b.get("lines", [])):
            if abs(line["dir"][0] - 1) > 0.01:            # rotated text: side labels
                continue
            y0, y1 = line["bbox"][1], line["bbox"][3]
            if y1 < h * MARGIN or y0 > h * (1 - MARGIN):
                continue
            cell = None
            for s in line["spans"]:
                if not s["text"].strip():
                    continue
                if cell and s["bbox"][0] - cell["x1"] <= SPAN_GAP:
                    cell["text"] += s["text"]
                    cell["x1"] = s["bbox"][2]
                    cell["bold"] = cell["bold"] and _bold(s)
                    cell["size"] = max(cell["size"], s["size"])
                    continue
                if cell:
                    out.append(cell)
                cell = {"text": s["text"], "x0": s["bbox"][0], "x1": s["bbox"][2], "y0": y0, "y1": y1,
                        "size": s["size"], "bold": _bold(s), "block": bi, "line": li}
            if cell:
                out.append(cell)
    for c in out:
        c["text"] = re.sub(r"\s+", " ", c["text"].replace("�", "•")).strip()
        c["figure"] = bool(FIGURE.match(c["text"])) and c["text"] not in ("$", "%")
    return [c for c in out if c["text"]]


def rows(segs: list[dict]) -> list[list[dict]]:
    """Group cells whose vertical centres are within 2.5 points into rows, top to bottom, cells left to right."""
    out: list[list[dict]] = []
    for c in sorted(segs, key=lambda c: (c["y0"] + c["y1"]) / 2):
        mid = (c["y0"] + c["y1"]) / 2
        if out and abs(mid - out[-1][0]["_mid"]) <= 2.5:
            out[-1].append(c)
        else:
            out.append([c])
        c["_mid"] = out[-1][0]["_mid"] if len(out[-1]) > 1 else mid
    return [sorted(r, key=lambda c: c["x0"]) for r in out]


def _header_row(row: list[dict], x0: float, x1: float, right: float) -> bool:
    """Column headings and short row group labels inside the table's width (a long line of text ends the table)."""
    inside = all(c["x0"] >= x0 - 1 and c["x1"] <= x1 + 1 for c in row)
    short = all(len(c["text"].split()) <= 8 for c in row)
    return inside and short and (len(row) >= 2 or row[0]["x0"] > right or len(row[0]["text"]) <= 60)


def tables(segs: list[dict]) -> list[dict]:
    """Find tables: runs of rows with two or more figures, grown to take in headers and wrapped labels nearby."""
    rs = rows(segs)
    numeric = [sum(c["figure"] for c in r) >= 2 and len(r) >= 3 for r in rs]
    found, i = [], 0
    while i < len(rs):
        if not numeric[i]:
            i += 1
            continue
        j, last = i, i
        while j + 1 < len(rs):                            # extend while rows keep coming close together
            gap = rs[j + 1][0]["y0"] - rs[j][0]["y1"]
            if gap > 14:
                break
            j += 1
            if numeric[j]:
                last = j
        body = rs[i:last + 1]
        if sum(numeric[i:last + 1]) < 2:                  # one figure row alone: a line of text with numbers
            i = last + 1
            continue
        x0 = min(c["x0"] for r in body for c in r if c["figure"]) - 5
        x0 = min(x0, min(r[0]["x0"] for r in body))
        x1 = max(c["x1"] for r in body for c in r) + 5
        top = i
        right = x0 + (x1 - x0) * 0.3
        while top > 0 and i - top < 5 and rs[i][0]["y0"] - rs[top - 1][0]["y1"] < 12 * (i - top + 1) \
                and _header_row(rs[top - 1], x0, x1, right):  # column headers above the first figure row
            top -= 1
        y0, y1 = rs[top][0]["y0"] - 0.5, body[-1][0]["y1"] + 0.5
        found.append({"x0": x0, "x1": x1, "y0": y0, "y1": y1})
        i = last + 1
    for t in found:
        t["cells"] = [c for c in segs if c["x0"] >= t["x0"] - 1 and c["x1"] <= t["x1"] + 1
                      and c["y0"] >= t["y0"] - 1 and c["y1"] <= t["y1"] + 1]
    return [t for t in found if t["cells"]]


def page_items(page: pymupdf.Page, body: float):
    segs = segments(page)
    tabs = tables(segs)
    in_table = {id(c): k for k, t in enumerate(tabs) for c in t["cells"]}
    units: list[tuple[float, tuple]] = []                 # (block order, item)
    for k, t in enumerate(tabs):
        text = "\n".join(" | ".join(c["text"] for c in r) for r in rows(t["cells"]))
        units.append((min(c["block"] for c in t["cells"]) + 0.5, ("table", text)))
    blocks: dict[int, list[dict]] = {}
    for c in segs:
        if id(c) not in in_table:
            blocks.setdefault(c["block"], []).append(c)
    for bi, cells in blocks.items():
        lines: dict[int, list[dict]] = {}
        for c in cells:
            lines.setdefault(c["line"], []).append(c)
        order = [sorted(lines[li], key=lambda c: c["x0"]) for li in sorted(lines)]
        lead = 0                                          # a run in heading: whole bold lines before plain ones
        while lead < len(order) and all(c["bold"] for c in order[lead]):
            lead += 1
        parts = [order[:lead], order[lead:]] if 0 < lead < len(order) else [order]
        for k, part in enumerate(parts):
            text = ""
            for line in part:
                t = " ".join(c["text"] for c in line)
                text = text[:-1] + t if text.endswith("-") and t[:1].islower() else (text + " " + t if text else t)
            flat = [c for line in part for c in line]
            size = max(c["size"] for c in flat)
            bold = all(c["bold"] for c in flat)
            heading = (len(text.split()) <= 14 and not text.rstrip().endswith((".", ",", ";"))
                       and not FIGURE.match(text) and re.search(r"[A-Za-z]{3}", text) and (size >= body + 1.2 or bold))
            item = ("heading", text, size >= body * 1.35 or top_section(text)) if heading else ("para", text)
            units.append((bi + k * 0.01, item))
    for _, item in sorted(units, key=lambda u: u[0]):
        yield item


def read_pdf(path: Path):
    doc = pymupdf.open(path)
    sizes: Counter = Counter()
    for p in doc:
        for b in p.get_text("dict")["blocks"]:
            for line in b.get("lines", []):
                for s in line["spans"]:
                    sizes[round(s["size"] * 2) / 2] += len(s["text"])
    body = sizes.most_common(1)[0][0]
    for n, p in enumerate(doc):
        if n:
            yield ("page",)
        yield from page_items(p, body)


def ingest() -> dict:
    manifest = json.loads((RAW / "manifest.json").read_text(encoding="utf-8"))
    (OUT / "text").mkdir(parents=True, exist_ok=True)
    all_chunks, index = [], []
    for m in manifest:
        paras = clean(list(read_pdf(ROOT / m["file"])))
        fid = f"{m['bank']}_{m['fiscal_year']}_{m['quarter']}"
        meta = {"filing_id": fid, "bank": m["bank"], "bank_name": m["bank_name"], "document_type": "Quarterly Report",
                "fiscal_year": m["fiscal_year"], "quarter": m["quarter"], "source_file": Path(m["file"]).name,
                "source_url": m["url"], "filed": ""}
        chunks = chunk(paras, meta)
        for i, c in enumerate(chunks):
            c["chunk_id"] = f"{fid}#{i:04d}"
        all_chunks += chunks
        (OUT / "text" / f"{fid}.txt").write_text(
            "\n".join(f"[p{p['page']}] {'## ' if p['kind'] == 'table' else ''}{p['text']}" for p in paras),
            encoding="utf-8")
        pages = max((p["page"] for p in paras), default=0)
        index.append({"filing_id": fid, "bank": m["bank"], "document_type": "Quarterly Report",
                      "fiscal_year": m["fiscal_year"], "quarter": m["quarter"], "pages": pages, "chunks": len(chunks),
                      "tokens": sum(c["tokens"] for c in chunks), "source_url": m["url"]})
        print(f"{fid}: {pages} pages, {len(chunks)} chunks, {index[-1]['tokens']:,} tokens")
    with (OUT / "chunks_quarterly.jsonl").open("w", encoding="utf-8") as f:
        for c in all_chunks:
            f.write(json.dumps(c, ensure_ascii=False) + "\n")
    with (OUT / "filing_index_quarterly.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(index[0]))
        w.writeheader()
        w.writerows(index)
    return {"filings": len(index), "chunks": len(all_chunks), "tokens": sum(c["tokens"] for c in all_chunks)}


if __name__ == "__main__":
    print(ingest())
