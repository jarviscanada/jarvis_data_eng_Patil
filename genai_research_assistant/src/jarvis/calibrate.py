"""Judge calibration: the LLM judge against human verdicts on the same answers.

    python -m jarvis.calibrate          writes reports/judge_calibration.json

The Step 3 answers were each read by a person against the hand located truth (reports/step3_review.json). Here the
evaluation judge (Claude Sonnet 4.6, the rubric in evaluate.py) scores the same answers from the same retrieved
passages. The judge passes an answer when it answered and faithfulness, relevance and completeness are all at least 4;
the person passes it when the verdict is "correct". Agreement and Cohen's kappa say how far the judge's scores in the
evaluation report can be trusted, and the disagreements say where it cannot.
"""

from __future__ import annotations

import json
from pathlib import Path

from .evaluate import judge
from .rag import context_block

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "reports" / "judge_calibration.json"
CONFIGS = ("native:cot", "native:cot+datefix", "langchain:cot", "native:cot+openai")


def kappa(pairs: list[tuple[bool, bool]]) -> float:
    n = len(pairs)
    agree = sum(a == b for a, b in pairs) / n
    pa, pb = sum(a for a, _ in pairs) / n, sum(b for _, b in pairs) / n
    chance = pa * pb + (1 - pa) * (1 - pb)
    return round((agree - chance) / (1 - chance), 3) if chance < 1 else 1.0


def main(out_path: Path | None = None) -> dict:
    """`out_path` keeps a second judge's calibration apart (JARVIS_PROVIDER=openai judges with gpt-4o)."""
    global OUT
    OUT = out_path or OUT
    from .index import load_chunks
    from .extra_docs import load_extra
    by_id = {c["chunk_id"]: c for c in load_chunks() + load_extra()}
    qs = {q["id"]: q for q in json.loads((ROOT / "reports" / "step3_questions.json").read_text(encoding="utf-8"))}
    results = json.loads((ROOT / "reports" / "step3_results.json").read_text(encoding="utf-8"))
    review = {(v["id"], v["config"]): v for v in
              json.loads((ROOT / "reports" / "step3_review.json").read_text(encoding="utf-8"))["reviews"]}
    done = json.loads(OUT.read_text(encoding="utf-8"))["rows"] if OUT.exists() else []
    have = {(r["id"], r["config"]) for r in done}
    for r in results:
        key = (r["id"], r["config"])
        if r["config"] not in CONFIGS or key in have or key not in review:
            continue
        hits = [by_id[i] for i in r["retrieved"] if i in by_id]
        j = judge(qs[r["id"]]["question"], context_block(hits), r["answer"])
        scores = [j.get(k) or 0 for k in ("faithfulness", "relevance", "completeness")]
        done.append({"id": r["id"], "config": r["config"], "human": review[key]["verdict"],
                     "human_pass": review[key]["verdict"] == "correct",
                     "judge_pass": (not r["abstained"]) and min(scores) >= 4, **j})
        OUT.write_text(json.dumps({"rows": done}, indent=1), encoding="utf-8")       # resumable
    pairs = [(d["human_pass"], d["judge_pass"]) for d in done]
    tab = {"both pass": sum(a and b for a, b in pairs), "both fail": sum(not a and not b for a, b in pairs),
           "judge passes, human fails": sum(b and not a for a, b in pairs),
           "judge fails, human passes": sum(a and not b for a, b in pairs)}
    summary = {"answers": len(pairs), "agreement": round(sum(a == b for a, b in pairs) / len(pairs), 3),
               "kappa": kappa(pairs), "table": tab,
               "disagreements": [{k: d[k] for k in ("id", "config", "human", "faithfulness", "relevance",
                                                    "completeness", "reason")} for d in done
                                 if d["human_pass"] != d["judge_pass"]],
               "usd": round(sum(d.get("judge_usd") or 0 for d in done), 4)}
    OUT.write_text(json.dumps({"summary": summary, "rows": done}, indent=1), encoding="utf-8")
    return summary


def cross(a: Path, b: Path) -> dict:
    """Two judges on the same answers: how often they agree with each other, and each with the person."""
    ra = {(r["id"], r["config"]): r for r in json.loads(a.read_text(encoding="utf-8"))["rows"]}
    rb = {(r["id"], r["config"]): r for r in json.loads(b.read_text(encoding="utf-8"))["rows"]}
    keys = sorted(set(ra) & set(rb))
    pairs = [(ra[k]["judge_pass"], rb[k]["judge_pass"]) for k in keys]
    gaps = [abs((ra[k].get("faithfulness") or 0) - (rb[k].get("faithfulness") or 0)) for k in keys]
    return {"answers": len(keys), "judges_agree": round(sum(x == y for x, y in pairs) / len(pairs), 3),
            "kappa_between_judges": kappa(pairs), "faithfulness_within_1": round(sum(g <= 1 for g in gaps) / len(gaps), 3),
            "disagreements": [{"id": k[0], "config": k[1], "human": ra[k]["human"], "judge_a": ra[k]["judge_pass"],
                               "judge_b": rb[k]["judge_pass"]} for k in keys if ra[k]["judge_pass"] != rb[k]["judge_pass"]]}


if __name__ == "__main__":
    import sys
    if sys.argv[1:2] == ["--cross"]:
        print(json.dumps(cross(Path(sys.argv[2]), Path(sys.argv[3])), indent=1))
        raise SystemExit(0)
    s = main(Path(sys.argv[1]) if sys.argv[1:] else None)
    print({k: v for k, v in s.items() if k != "disagreements"})
    for d in s["disagreements"]:
        print(d["id"], d["config"], d["human"], d["faithfulness"], d["relevance"], d["completeness"], d["reason"][:120])
