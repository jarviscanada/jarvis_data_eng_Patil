"""Step 3 and Step 4.2: the 15 compliance questions (all five banks; credit, market, liquidity, operational, climate
and capital risk; annual and quarterly), answered by each prompt version and by the LangChain build.

    python -m jarvis.step3            writes reports/step3_results.json

reports/step3_questions.json holds each question's true answer, located in the filing by hand before any run, with
its pages. For each answer this records the retrieved chunks, the answer, the cited pages, whether the key figure is
present and whether a citation lands on a page that holds the truth. The manual verdict (correct, partly correct,
wrong; citations accurate or not) is recorded separately in reports/step3_review.json after reading each answer
against its truth and cited passages.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
QUESTIONS = ROOT / "reports" / "step3_questions.json"
RESULTS = ROOT / "reports" / "step3_results.json"


def truth_pages(where: str) -> set[tuple[str, int]]:
    """"RBC_2025_AR p13 and p15" -> {("RBC_2025_AR", 13), ("RBC_2025_AR", 15)}."""
    fid = where.split()[0]
    return {(fid, int(p)) for p in re.findall(r"p(\d+)", where)}


def record(q: dict, out: dict, config: str) -> dict:
    ids = out.get("retrieved", [])
    ids = [i["chunk_id"] if isinstance(i, dict) else i for i in ids]
    cited = []
    for s in out.get("sources", []):
        n = int(s["id"][1:]) - 1
        fid = ids[n].split("#")[0] if 0 <= n < len(ids) else ""
        cited.append({"filing": fid, "page": s["page"], "period": s.get("period", "")})
    want = truth_pages(q["where"])
    on_truth = any(c["filing"] == f and abs(int(c["page"]) - p) <= 1 for c in cited for f, p in want)
    text = out.get("answer", "")
    return {"id": q["id"], "config": config, "answer": text, "abstained": out.get("abstained", False),
            "confidence": out.get("confidence"), "retrieved": ids, "cited": cited,
            "key_found": all(k.replace(",", "") in text.replace(",", "") for k in q["key"]) if q["key"] else None,
            "cites_truth_page": on_truth, "unsupported_figures": [c["figure"] for c in out.get("figure_check", [])
                                                                 if not c["supported"]]}


def run(prompts=("basic", "fewshot", "cot"), langchain: bool = True, suffix: str = "") -> list[dict]:
    """`suffix` labels a rerun after a logged change (for example "+datefix"), kept beside the first run."""
    from .rag import RAG
    qs = json.loads(QUESTIONS.read_text(encoding="utf-8"))
    done = json.loads(RESULTS.read_text(encoding="utf-8")) if RESULTS.exists() else []
    have = {(r["id"], r["config"]) for r in done}
    configs = [(f"native:{p}{suffix}", lambda p=p: RAG(prompt=p)) for p in prompts]
    if langchain:
        from .lc import LCRAG
        configs.append((f"langchain:cot{suffix}", lambda: LCRAG(prompt="cot")))
    for name, make in configs:
        todo = [q for q in qs if (q["id"], name) not in have]
        if not todo:
            continue
        system = make()
        for q in todo:
            done.append(record(q, system.answer(q["question"]), name))
            RESULTS.write_text(json.dumps(done, indent=1), encoding="utf-8")       # resumable after any stop
            print(name, q["id"], done[-1]["key_found"], done[-1]["cites_truth_page"], flush=True)
    return done


def summary(rows: list[dict]) -> list[dict]:
    out = []
    for cfg in dict.fromkeys(r["config"] for r in rows):
        rs = [r for r in rows if r["config"] == cfg]
        keyed = [r for r in rs if r["key_found"] is not None]
        out.append({"config": cfg, "answered": sum(not r["abstained"] for r in rs), "of": len(rs),
                    "key_figure_found": f"{sum(r['key_found'] for r in keyed)}/{len(keyed)}",
                    "cites_truth_page": f"{sum(r['cites_truth_page'] for r in rs)}/{len(rs)}"})
    return out


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--prompts", nargs="+", default=["basic", "fewshot", "cot"])
    ap.add_argument("--no-langchain", action="store_true")
    ap.add_argument("--suffix", default="")
    a = ap.parse_args()
    for row in summary(run(a.prompts, not a.no_langchain, a.suffix)):
        print(row)
