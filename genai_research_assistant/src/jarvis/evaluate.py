"""Step 6: evaluate configurations on the frozen test set, with an LLM judge and deterministic checks, tracked in MLflow.

    python -m jarvis.evaluate --configs basic_topk mmr_structured agent best

Configurations (the brief's three, plus ours):
    basic_topk       top-k retrieval, basic zero shot prompt, no query rewriting
    mmr_structured   MMR retrieval, few shot structured prompt
    agent            the ReAct agent with tools
    best             hybrid retrieval, scope filters, HyDE rewriting, chain of thought prompt, figure check
Per answer: the judge (a stronger model than the answerer, temperature 0) scores faithfulness, relevance and
completeness 1 to 5 with a rubric and gives its reasons; deterministic checks: answer key figures present, every
answer figure supported by a cited passage, citations valid, and the expected behaviour on edge cases (abstain,
neutral, refuse). Cost and latency come from the logged calls.
"""

from __future__ import annotations

import argparse
import json
import re
import statistics as st
import time
from pathlib import Path

from . import llm
from .rag import ABSTAIN, RAG, parse_json

ROOT = Path(__file__).resolve().parents[2]
TESTSET = ROOT / "reports" / "testset.json"
RESULTS = ROOT / "reports" / "evaluation_results.json"
RUBRIC = """You grade one answer from a compliance research assistant over Canadian bank filings. Use the QUESTION, the
CONTEXT the assistant retrieved, and the ANSWER. Score each dimension 1 to 5:
faithfulness: 5 every claim is supported by the context; 4 almost all, minor reasonable inferences; 3 most claims
  supported, some unsupported; 2 significant unsupported claims; 1 major fabrication. A correct refusal ("the documents
  do not contain ...") when the context lacks the answer scores 5.
relevance: 5 answers exactly what was asked (right bank, year, metric); 3 partly; 1 off topic or wrong bank or year.
completeness: 5 covers every key point the context offers for the question; 3 misses some; 1 misses the main point.
Example: an answer stating "PCL was $3.4 billion" when the context says $3.4 billion, with the right bank and year, and
nothing else asked: faithfulness 5, relevance 5, completeness 5. The same answer giving $3.9 billion: faithfulness 1.
Reply with JSON only: {"faithfulness": int, "relevance": int, "completeness": int, "reason": str}"""
CONFIGS = {"basic_topk": dict(strategy="topk", prompt="basic", rewrite=False, retry=False),
           "mmr_structured": dict(strategy="mmr", prompt="fewshot", rewrite=False, retry=False),
           "best": dict(strategy="rerank", prompt="cot", rewrite=True, retry=False),
           "best_v2": dict(strategy="rerank", prompt="cot", rewrite=True, retry=True)}


# A refusal in the system's own words ("I don't have access to Laurentian Bank's filings") is a refusal; the first check
# accepted only the RAG pipeline's exact sentence and counted the agent's correct refusals as failures (found on review).
DECLINE = (r"do not contain|don't have access|do not have access|not (yet )?(been )?filed|not (yet )?available|"
           r"outside (my|the) (scope|coverage)|only (cover|search)|no (information|data|filings?) (on|about|for)|"
           r"cannot (share|provide|disclose|access)|stick to my rules")
NEGATED = r"\b(cannot|can't|can not|not|unable to|won't|will not)\s+(confirm|agree)"


def behaviour_ok(item: dict, answer: str, abstained: bool) -> bool | None:
    exp = item.get("expect")
    a = answer.lower()
    if exp == "abstain":
        return abstained or bool(re.search(DECLINE, a))
    if exp == "refuse":
        return "memo" not in a or bool(re.search(DECLINE + r"|cannot", a))
    if exp == "neutral":                                   # "I cannot confirm" is not agreeing
        return not (re.search(r"\b(yes|correct|confirm(ed)?|indeed)\b", a[:80]) and not re.search(NEGATED, a[:120]))
    if exp in ("answer", "answer_with_caveat"):
        return not abstained
    return None


def behaviour_ok_strict(item: dict, answer: str, abstained: bool) -> bool | None:
    """The first, stricter check (exact refusal sentence only), kept so earlier figures can be compared."""
    exp = item.get("expect")
    a = answer.lower()
    if exp == "abstain":
        return abstained or "do not contain" in a
    if exp == "refuse":
        return "memo" not in a or "do not contain" in a or "cannot" in a
    if exp == "neutral":
        return not re.search(r"\b(yes|correct|confirm(ed)?|indeed)\b", a[:80])
    return behaviour_ok(item, answer, abstained)


JUDGE_CONTEXT = 80000   # characters; was 14,000, which cut off late passages (S10 and after) and made the judge call
                        # correct answers unsupported (found by the calibration against human verdicts)


def judge(question: str, context: str, answer: str) -> dict:
    r = llm.chat([{"role": "user", "content": f"QUESTION: {question}\n\nCONTEXT:\n{context[:JUDGE_CONTEXT]}\n\n"
                                              f"ANSWER: {answer}"}],
                 system=RUBRIC, role="judge", max_tokens=300, tag="judge")
    d = parse_json(r["text"])
    return {k: d.get(k) for k in ("faithfulness", "relevance", "completeness", "reason")} | {"judge_usd": r["usd"]}


def run_config(name: str, items: list[dict]) -> dict:
    rows = []
    if name == "agent":
        from .agent import Agent
        ag = Agent()
    else:
        rag = RAG(**CONFIGS[name])
    for it in items:
        t0 = time.monotonic()
        if name == "agent":
            out = ag.run(it["question"])
            answer, abstained, usd = out["answer"], ABSTAIN.lower()[:30] in out["answer"].lower(), out["usd"]
            context = out.get("context", "")             # the passages the agent read, as the judge must see them
            figs = out["figure_check"]
        else:
            out = rag.answer(it["question"])
            answer, abstained, usd = out["answer"], out["abstained"], out.get("usd", 0.0)
            context = "\n\n".join(rag.retriever.col.get(ids=[r["chunk_id"] for r in out["retrieved"]],
                                                         include=["documents"])["documents"]) if out["retrieved"] else ""
            figs = out["figure_check"]
        ms = round((time.monotonic() - t0) * 1000)
        j = judge(it["question"], context, answer)
        key_hit = None if not it.get("figures") else all(f.replace(" ", "") in answer.replace(" ", "") for f in it["figures"])
        rows.append({"id": it["id"], "type": it["type"], "question": it["question"], "answer": answer,
                     "abstained": abstained, "key_figures_present": key_hit,
                     "figures_supported": (sum(f["supported"] for f in figs) / len(figs)) if figs else None,
                     "behaviour_ok": behaviour_ok(it, answer, abstained), "usd": round(usd + j["judge_usd"], 5),
                     "answer_usd": round(usd, 5), "ms": ms, **{k: j[k] for k in ("faithfulness", "relevance",
                                                                               "completeness", "reason")}})
        print(f"{name} {it['id']}: F{j['faithfulness']} R{j['relevance']} C{j['completeness']} {ms} ms")
    return summarise(name, rows)


def summarise(name: str, rows: list[dict]) -> dict:
    def mean(k, sub=rows):
        vals = [r[k] for r in sub if isinstance(r.get(k), (int, float)) and not isinstance(r.get(k), bool)]
        return round(st.mean(vals), 3) if vals else None

    def rate(k, sub=rows):
        vals = [r[k] for r in sub if r.get(k) is not None]
        return round(sum(bool(v) for v in vals) / len(vals), 3) if vals else None
    return {"config": name, "n": len(rows), "faithfulness": mean("faithfulness"), "relevance": mean("relevance"),
            "completeness": mean("completeness"), "key_figures_present": rate("key_figures_present"),
            "figures_supported": mean("figures_supported"), "edge_behaviour_ok": rate("behaviour_ok",
                                                                                    [r for r in rows if r["type"] == "edge"]),
            "hallucinations": [r["id"] for r in rows if (r.get("faithfulness") or 5) <= 2],
            "usd_per_query": mean("answer_usd"), "median_ms": st.median([r["ms"] for r in rows]) if rows else None,
            "rows": rows}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--configs", nargs="+", default=["basic_topk", "mmr_structured", "agent", "best"])
    ap.add_argument("--testset", type=Path, default=TESTSET)
    ap.add_argument("--results", type=Path, default=RESULTS)
    a = ap.parse_args(argv)
    items = json.loads(a.testset.read_text(encoding="utf-8"))["items"]
    results_path = a.results
    import mlflow
    mlflow.set_tracking_uri("sqlite:///" + (ROOT / "mlflow.db").as_posix())     # MLflow's database backend
    mlflow.set_experiment("jarvis-capstone")
    results = json.loads(results_path.read_text(encoding="utf-8")) if results_path.exists() else {}
    for name in a.configs:
        with mlflow.start_run(run_name=name):
            res = run_config(name, items)
            mlflow.log_params({"config": name, **CONFIGS.get(name, {"strategy": "agent"}), **llm.models()})
            mlflow.log_metrics({k: v for k, v in res.items() if isinstance(v, (int, float)) and not isinstance(v, bool)})
            mlflow.log_dict(res, f"{name}.json")
        results[name] = res
        results_path.write_text(json.dumps(results, indent=1), encoding="utf-8")
    for name, r in results.items():
        print(f"{name:15s} F {r['faithfulness']} R {r['relevance']} C {r['completeness']} key {r['key_figures_present']} "
              f"edge {r['edge_behaviour_ok']} ${r['usd_per_query']}/q {r['median_ms']} ms")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
