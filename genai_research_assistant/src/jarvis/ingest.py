"""Step 1b: parse the downloaded filings into clean text and semantically coherent chunks with full metadata.

    python -m jarvis.ingest

Reads data/raw/edgar/manifest.json and writes:
    data/processed/chunks.jsonl        one chunk a line: text and metadata (bank, document type, fiscal year,
                                       quarter, section, subsection, risk category, page, source file, tokens)
    data/processed/filing_index.csv    one filing a line: bank, type, fiscal year, filed date, pages, chunks, tokens
    data/processed/text/<id>.txt       the cleaned text of each filing, with page and heading markers

Choices (Module 4, Step 1 best practices):
* Pages come from the filings' own page breaks, so every chunk can be cited by page.
* Headings are detected from the layout (short, bold or capitalised blocks) and kept on every chunk.
* Chunks follow paragraph boundaries, 500 to 1,000 tokens with about 150 tokens of overlap; a table is kept whole as
  its own chunk (split by rows only when one table is larger than 1,000 tokens).
* Boilerplate is removed: the table of contents, running headers and footers, page numbers, the forward looking
  statements caution, and any French text.
"""

from __future__ import annotations

import csv
import json
import re
from collections import Counter
from pathlib import Path

import tiktoken
from bs4 import BeautifulSoup, NavigableString, Tag

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data" / "raw" / "edgar"
OUT = ROOT / "data" / "processed"
ENC = tiktoken.get_encoding("cl100k_base")
TARGET, MAX, OVERLAP = 700, 1000, 150
INLINE_TABLE = 400

BLOCKS = {"p", "div", "li", "h1", "h2", "h3", "h4", "h5", "h6", "td"}
RISK_CATEGORIES = {
    "credit": r"credit risk|provision for credit losses|allowance for credit losses|impaired loans|\bpcl\b|counterparty",
    "market": r"market risk|value at risk|\bvar\b|interest rate risk|foreign exchange risk|trading",
    "liquidity": r"liquidity|funding risk|\blcr\b|\bnsfr\b|liquidity coverage|net stable funding",
    "operational": r"operational risk|cyber|technology risk|third.party risk|fraud|model risk|outsourcing",
    "climate": r"climate|environmental|net.zero|transition risk|physical risk|sustainab|b-15",
    "capital": r"capital management|cet1|common equity tier 1|capital ratio|leverage ratio|tlac|risk.weighted",
    "regulatory": r"regulatory|compliance risk|legal and regulatory|osfi|aml|anti.money",
    "strategic": r"strategic risk|reputation|business risk|top and emerging risks|emerging risk",
}
FRENCH = re.compile(r"\b(le|la|les|des|du|est|sont|pour|avec|dans|une|nous|leurs|aux)\b", re.I)
PAGE_NUMBER = re.compile(r"^\s*(page\s*)?\d{1,3}\s*$", re.I)


def tokens(text: str) -> int:
    return len(ENC.encode(text, disallowed_special=()))


def read_html(path: Path) -> str:
    raw = path.read_bytes()
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        return raw.decode("cp1252", errors="replace")


_C1 = {chr(c): bytes([c]).decode("cp1252", errors="replace") for c in range(0x80, 0xA0)}


def fix_text(t: str) -> str:
    """Typography the filings mix up: C1 control characters that are really cp1252 punctuation, a replacement character
    standing for an apostrophe between letters, and curly quotes and dashes made plain for matching."""
    t = "".join(_C1.get(ch, ch) for ch in t)
    t = re.sub(r"(?<=[A-Za-z])\ufffd(?=[A-Za-z])", "'", t).replace("\ufffd", " ")
    for a, b in (("\u2019", "'"), ("\u2018", "'"), ("\u201c", '"'), ("\u201d", '"'), ("\u2013", "-"),
                 ("\u2014", "-"), ("\xa0", " ")):
        t = t.replace(a, b)
    return re.sub(r"[ \t]+", " ", t)


def doc_type_by_content(head: str, bank: str, file: str) -> str:
    """Which document this is. Exhibit 1 is the AIF for every bank and RBC's exhibit 2 is its whole annual report; the
    MD&A and the financial statements are told apart by the markers in their opening text, since banks number those
    two exhibits differently (CIBC and BMO put the statements first)."""
    h = head.lower().replace("\u2019", "'")[:8000]
    by_number = doc_type(bank, file)
    if by_number in ("Annual Information Form", "Annual Report"):
        return by_number
    fs = len(re.findall(r"responsib\w* for the preparation|management's responsibility|independent auditor|"
                        r"independent registered public accounting|consolidated balance sheet", h))
    md = len(re.findall(r"forward.looking|enhanced disclosure task force|\bedtf\b|financial highlights|outlook|"
                        r"who we are|our strategy|non-gaap", h))
    if fs != md:
        return "Financial Statements" if fs > md else "Annual Report (MD&A)"
    return by_number


def doc_type(bank: str, file: str) -> str:
    """By exhibit number, which every bank uses the same way in its 40-F: 99.1 the Annual Information Form, 99.2 the
    annual MD&A, 99.3 the audited financial statements. RBC files its whole annual report as exhibit 2 (MD&A and
    statements together) and its AIF as exhibit 1; CIBC numbers them 99(b)(3)(a), (b) and (c)."""
    f = file.lower()
    if re.search(r"ex(99)?1\.htm$|ex99b3a\.htm$|dex1\.htm$", f):
        return "Annual Information Form"
    if bank == "RBC" and re.search(r"dex2\.htm$", f):
        return "Annual Report"
    if re.search(r"ex(99)?2\.htm$|ex99b3b\.htm$", f):
        return "Annual Report (MD&A)"
    if re.search(r"ex(99)?3\.htm$|ex99b3c\.htm$", f):
        return "Financial Statements"
    return "Annual Report"


def _is_page_break(el: Tag) -> bool:
    style = (el.get("style") or "").replace(" ", "").lower()
    return el.name == "hr" or "page-break-before:always" in style or "page-break-after:always" in style


def _bold(el: Tag) -> bool:
    if el.find(["b", "strong"]):
        return True
    styles = " ".join((x.get("style") or "") for x in [el, *el.find_all(True)]).replace(" ", "").lower()
    return "font-weight:bold" in styles or "font-weight:700" in styles or "font-weight:600" in styles


JUNK_HEADING = re.compile(r"intentionally left blank|^\(?continued\)?$|^\(.{1,8}\)$|^page \d+|^\d+$", re.I)


_SIZE = re.compile(r"font-size:\s*([\d.]+)\s*(pt|px)", re.I)
_COLOR = re.compile(r"(?<![-\w])color:\s*(#[0-9a-f]{3,6}|rgb\([^)]*\))", re.I)
CTX = {"body_pt": 10.0, "targets": set()}


def _pt(style: str) -> float | None:
    m = _SIZE.search(style or "")
    if not m:
        return None
    v = float(m.group(1))
    return v * 0.75 if m.group(2).lower() == "px" else v


def _emphasis(el: Tag) -> bool:
    """Larger than the body text, coloured (not black), or the target of a table of contents link."""
    nodes = [el, *el.find_all(True)]
    sizes = [x for x in (_pt(n.get("style")) for n in nodes) if x]
    if sizes and max(sizes) >= CTX["body_pt"] + 1.5:
        return True
    for n in nodes:
        m = _COLOR.search(n.get("style") or "")
        if m and m.group(1).replace(" ", "").lower() not in ("#000", "#000000", "rgb(0,0,0)", "#231f20", "#222", "#333333"):
            return True
        if (n.get("id") or n.get("name")) in CTX["targets"]:
            return True
    return False


def _heading(text: str, el: Tag) -> bool:
    t = text.strip()
    if JUNK_HEADING.search(t):
        return False
    if not (3 <= len(t) <= 90) or t.endswith((".", ",", ";", ":")) or PAGE_NUMBER.match(t):
        return False
    if re.fullmatch(r"[\d\s.,$%()\-–—]+", t):
        return False
    words = t.split()
    return ((_bold(el) or _emphasis(el)) and len(words) <= 12) or (t.isupper() and len(words) <= 10)


NUMERIC = re.compile(r"[\s$%()\-.,\d]+(bps|million|billion)?\s*")
GUTTER_GAP, COLUMN_SPLIT = 260, 400    # TD pages: two columns, the right one starting near 419px
_POS = re.compile(r"left:\s*([\d.]+)px.*?top:\s*([\d.]+)px|top:\s*([\d.]+)px.*?left:\s*([\d.]+)px", re.I | re.S)


def layout_blocks(body: Tag):
    """For filings converted from PDF pages (TD): every line is an absolutely positioned box. Rebuild each page:
    boxes on the same line are merged, lines are split into columns by their left edge, and lines join into paragraphs
    across small vertical gaps; a line that is bold throughout is a heading."""
    def flush(lines):
        if not lines:
            return
        rows: dict = {}
        for left, top, text, bold in lines:
            key = round(top / 3)
            rows.setdefault(key, []).append((left, top, text, bold))
        merged = []
        for _key, segs in rows.items():
            segs.sort()
            parts = [[segs[0]]]
            for seg in segs[1:]:
                if seg[0] - parts[-1][-1][0] < GUTTER_GAP or NUMERIC.fullmatch(seg[2]):
                    parts[-1].append(seg)              # the same line, split into several boxes
                else:
                    parts.append([seg])                # a wide jump on one row: the other column
            for part in parts:
                merged.append((part[0][0], part[0][1], " ".join(x[2] for x in part).strip(), all(x[3] for x in part)))

        def column(left: float) -> int:
            return 1 if left >= COLUMN_SPLIT else 0

        for col in sorted({column(x[0]) for x in merged}):
            col_lines = sorted((x for x in merged if column(x[0]) == col), key=lambda x: x[1])
            para, last_top = [], None
            for left, top, text, bold in col_lines:
                if not text:
                    continue
                gap = None if last_top is None else top - last_top
                if bold and len(text) <= 90:
                    if para:
                        yield ("para", " ".join(para))
                        para = []
                    yield ("heading", text)
                elif gap is not None and gap > 20 and para:
                    yield ("para", " ".join(para))
                    para = [text]
                else:
                    para.append(text)
                last_top = top
            if para:
                yield ("para", " ".join(para))

    lines: list = []
    for el in body.descendants:
        if not isinstance(el, Tag):
            continue
        style = (el.get("style") or "")
        if _is_page_break(el):
            yield from flush(lines)
            lines = []
            yield ("page",)
            continue
        if "position:absolute" not in style.replace(" ", ""):
            continue
        if el.find(style=re.compile(r"position:\s*absolute")):
            continue                                     # a container of line boxes, not a line
        m = _POS.search(style)
        if not m:
            continue
        left, top = (float(m.group(1)), float(m.group(2))) if m.group(1) else (float(m.group(4)), float(m.group(3)))
        text = re.sub(r"\s+", " ", el.get_text(" ", strip=True).replace(" ", " ")).strip()
        if text:
            lines.append((left, top, text, "font-weight:bold" in style.replace(" ", "").lower()))
    yield from flush(lines)


def blocks(html: str):
    """Yield ("page",), ("heading", text), ("para", text) and ("table", text) in document order."""
    soup = BeautifulSoup(html, "lxml")
    for bad in soup(["script", "style", "head", "ix:header"]):
        bad.decompose()
    for hidden in soup.find_all(style=re.compile(r"display:\s*none", re.I)):
        hidden.decompose()                                # inline XBRL facts the viewer never shows
    body = soup.body or soup
    sizes = Counter(round(x * 2) / 2 for x in (_pt(t.get("style")) for t in body.find_all(style=True)) if x)
    CTX["body_pt"] = sizes.most_common(1)[0][0] if sizes else 10.0
    CTX["targets"] = {a["href"][1:] for a in body.find_all("a", href=True) if a["href"].startswith("#")}
    if html.count("position:absolute") > 2000:
        yield from layout_blocks(body)
        return
    for el in body.descendants:
        if not isinstance(el, Tag):
            continue
        if _is_page_break(el):
            yield ("page",)
        if el.name == "table":
            rows, width = [], 0
            for tr in el.find_all("tr"):
                cells = [re.sub(r"\s+", " ", c.get_text(" ", strip=True)) for c in tr.find_all(["td", "th"])]
                cells = [c for c in cells if c and c not in ("$", "%")]
                if cells:
                    rows.append(" | ".join(cells))
                    width = max(width, len(cells))
            if not rows:
                continue
            text = "\n".join(rows)
            if len(rows) >= 3 and width >= 2:
                yield ("table", text)                     # a real table: kept whole
            else:                                         # a layout box around a heading or a line of text
                flat = " ".join(rows)
                yield ("heading" if _heading(flat, el) else "para", flat)
            continue
        if el.name in BLOCKS and not el.find(list(BLOCKS) + ["table"]) and not el.find_parent("table"):
            text = re.sub(r"\s+", " ", el.get_text(" ", strip=True)).strip()
            if not text:
                continue
            yield ("heading" if _heading(text, el) else "para", text)


TOP_SECTIONS = re.compile(
    r"^(overview|risk management|credit risk|market risk|liquidity( and funding)? risk|operational risk|"
    r"capital management|climate|environmental|regulatory|financial (performance|condition|results)|"
    r"business segment|accounting|controls and procedures|description of (the )?business|"
    r"risk factors|top and emerging risks|selected financial|quarterly financial|glossary|"
    r"consolidated (financial )?statements|notes to|independent auditor|dividends|capital structure|"
    r"general development|directors and|legal proceedings|insurance risk|model risk|strategic risk)", re.I)


def top_section(text: str) -> bool:
    """A top level section: a known MD&A or AIF heading, or a capitalised heading of two to eight words that is not
    an acronym or a code."""
    t = text.strip()
    if TOP_SECTIONS.search(t):
        return True
    words = re.findall(r"[A-Za-z]{2,}", t)
    return t.isupper() and 2 <= len(words) <= 8 and not re.search(r"\d|[-(]", t)


def clean(items: list[tuple]) -> list[dict]:
    """Drop the contents pages, running headers and footers, page numbers, the forward looking statements caution
    and French text; number the pages; carry the heading path."""
    lines = Counter(i[1] for i in items if i[0] in ("para", "heading") and len(i[1]) < 120)
    running = {t for t, n in lines.items() if n >= 8}             # repeated on many pages: a header or footer
    out, page, section, subsection, skip = [], 1, "", "", False
    for it in items:
        if it[0] == "page":
            page += 1
            continue
        kind, text = it[0], fix_text(it[1]).strip()
        if not text:
            continue
        if text in running or PAGE_NUMBER.match(text):
            continue
        if kind == "para" and len(FRENCH.findall(text)) > max(3, len(text.split()) * 0.15):
            continue
        low = text.lower()
        if kind == "heading":
            skip = "forward-looking" in low or "forward looking" in low or low in ("table of contents", "contents")
            if not skip:
                if it[2] if len(it) > 2 else top_section(text):   # the PDF reader marks top headings by size
                    title = re.sub(r"'S\b", "'s", text.title()) if text.isupper() else text
                    section, subsection = title, ""
                else:
                    subsection = text
            continue
        if skip or (kind == "para" and re.search(r"\.{4,}\s*\d+\s*$", text)):   # dotted contents lines
            continue
        out.append({"kind": kind, "text": text, "page": page, "section": section, "subsection": subsection})
    return out


def risk_category(*texts: str) -> str:
    joined = " ".join(texts).lower()
    scores = {c: len(re.findall(p, joined)) for c, p in RISK_CATEGORIES.items()}
    best = max(scores, key=scores.get)
    return best if scores[best] else "general"


def chunk(paras: list[dict], meta: dict) -> list[dict]:
    """Paragraph aligned chunks of about TARGET tokens with about OVERLAP tokens carried over; tables alone."""
    out, cur, cur_tok = [], [], 0

    def emit(parts: list[dict], kind: str = "text") -> None:
        if not parts:
            return
        text = "\n".join(p["text"] for p in parts)
        first = parts[0]
        heading = " > ".join(x for x in (first["section"], first["subsection"]) if x)
        out.append({**meta, "chunk_type": kind, "section": first["section"] or "(front matter)",
                    "subsection": first["subsection"], "page": first["page"], "page_end": parts[-1]["page"],
                    "risk_category": risk_category(heading, heading, text),
                    "text": (f"[{heading}]\n" if heading else "") + text, "tokens": tokens(text)})

    for p in paras:
        n = tokens(p["text"])
        if p["kind"] == "table" and n <= INLINE_TABLE:
            p = {**p, "kind": "para"}                     # whole, inside the text chunk (never split)
        if p["kind"] == "table":
            emit(cur)
            cur, cur_tok = [], 0
            if n <= MAX:
                emit([p], "table")
            else:                                         # an oversized table: split by rows, headers repeated
                rows = p["text"].split("\n")
                head, part, part_tok = rows[:1], [], 0
                for row in rows[1:]:
                    t = tokens(row)
                    if part and part_tok + t > MAX:
                        emit([{**p, "text": "\n".join(head + part)}], "table")
                        part, part_tok = [], 0
                    part.append(row)
                    part_tok += t
                emit([{**p, "text": "\n".join(head + part)}], "table")
            continue
        new_heading = cur and (p["section"], p["subsection"]) != (cur[-1]["section"], cur[-1]["subsection"])
        if cur and (cur_tok + n > MAX or (new_heading and cur_tok >= TARGET * 0.5)):
            emit(cur)
            keep, kt = [], 0
            if not new_heading:                           # overlap only inside one section
                for q in reversed(cur):
                    qt = tokens(q["text"])
                    if kt + qt > OVERLAP:
                        break
                    keep.insert(0, q)
                    kt += qt
            cur, cur_tok = keep, kt
        cur.append(p)
        cur_tok += n
        if cur_tok >= TARGET and p["text"].rstrip().endswith((".", ":", ";")):
            emit(cur)
            keep, kt = [], 0
            for q in reversed(cur):
                qt = tokens(q["text"])
                if kt + qt > OVERLAP:
                    break
                keep.insert(0, q)
                kt += qt
            cur, cur_tok = keep, kt
    emit(cur)
    return out


def ingest() -> dict:
    manifest = json.loads((RAW / "manifest.json").read_text(encoding="utf-8"))
    (OUT / "text").mkdir(parents=True, exist_ok=True)
    all_chunks, index = [], []
    for m in manifest:
        path = RAW / m["bank"] / str(m["fiscal_year"]) / m["file"]
        html = read_html(path)
        items = list(blocks(html))
        head = " ".join(i[1] for i in items[:300] if len(i) > 1)
        dtype = doc_type_by_content(fix_text(head), m["bank"], m["file"])
        paras = clean(items)
        short = {"Annual Information Form": "AIF", "Annual Report": "AR", "Annual Report (MD&A)": "MDA",
                 "Financial Statements": "FS"}[dtype]
        fid = f"{m['bank']}_{m['fiscal_year']}_{short}"
        meta = {"filing_id": fid, "bank": m["bank"], "bank_name": m["bank_name"], "document_type": dtype,
                "fiscal_year": m["fiscal_year"], "quarter": "annual", "source_file": m["file"], "source_url": m["url"],
                "filed": m["filed"]}
        chunks = chunk(paras, meta)
        for i, c in enumerate(chunks):
            c["chunk_id"] = f"{fid}#{i:04d}"
        all_chunks += chunks
        (OUT / "text" / f"{fid}.txt").write_text(
            "\n".join(f"[p{p['page']}] {'## ' if p['kind'] == 'table' else ''}{p['text']}" for p in paras),
            encoding="utf-8")
        pages = max((p["page"] for p in paras), default=0)
        index.append({"filing_id": fid, "bank": m["bank"], "document_type": dtype, "fiscal_year": m["fiscal_year"],
                      "filed": m["filed"], "pages": pages, "chunks": len(chunks),
                      "tokens": sum(c["tokens"] for c in chunks), "source_url": m["url"]})
        print(f"{fid}: {pages} pages, {len(chunks)} chunks, {index[-1]['tokens']:,} tokens")
    with (OUT / "chunks.jsonl").open("w", encoding="utf-8") as f:
        for c in all_chunks:
            f.write(json.dumps(c, ensure_ascii=False) + "\n")
    with (OUT / "filing_index.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(index[0]))
        w.writeheader()
        w.writerows(index)
    return {"filings": len(index), "chunks": len(all_chunks), "tokens": sum(c["tokens"] for c in all_chunks)}


if __name__ == "__main__":
    print(ingest())
