"""Step 2 evaluation: precision@3 and recall of the right filing, for every embedding model and retrieval strategy.

    python -m jarvis.retrieval_eval [--models minilm bge-small titan] [--out reports/retrieval_eval.json]

Each test query carries an explicit relevance rule instead of a hand label: a retrieved chunk is relevant when it comes
from the named bank and fiscal year and its text matches the rule's pattern (the metric the question asks about).
The rules are printed with the results, so anyone can check them. The scope filter (bank and year read from the
question) is part of the system, so it is on; `--no-scope` measures the raw embedding quality without it.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from .retrieve import Retriever, Scope, scope_of

ROOT = Path(__file__).resolve().parents[2]
QUERIES = [
    ("What was RBC's provision for credit losses in fiscal 2025?", "RBC", 2025, r"provision for credit losses|\bpcl\b"),
    ("How much did TD set aside for credit losses in 2024?", "TD", 2024, r"provision for credit losses|\bpcl\b"),
    ("What was BMO's Common Equity Tier 1 ratio at the end of fiscal 2025?", "BMO", 2025, r"common equity tier 1|cet1"),
    ("What was Scotiabank's liquidity coverage ratio in 2025?", "BNS", 2025, r"liquidity coverage ratio|\blcr\b"),
    ("How does CIBC describe climate-related risk in its 2025 MD&A?", "CIBC", 2025, r"climate"),
    ("What market risk measures, such as VaR, did RBC report for 2024?", "RBC", 2024, r"value at risk|\bvar\b"),
    ("What are TD's top and emerging risks in fiscal 2025?", "TD", 2025, r"top and emerging|emerging risk"),
    ("How did BMO describe cyber and information security risk in 2024?", "BMO", 2024, r"cyber|information security"),
    ("What was Scotiabank's gross impaired loans figure in 2024?", "BNS", 2024, r"impaired loans|\bgil\b"),
    ("What is CIBC's net stable funding ratio for 2024?", "CIBC", 2024, r"net stable funding|\bnsfr\b"),
    ("Describe RBC's operational risk management framework in 2025.", "RBC", 2025, r"operational risk"),
    ("What does TD's 2025 AIF say about its dividend policy?", "TD", 2025, r"dividend"),
    ("How does BMO manage model risk in fiscal 2025?", "BMO", 2025, r"model risk"),
    ("What allowance for credit losses did Scotiabank hold at the end of 2025?", "BNS", 2025, r"allowance for credit losses|\bacl\b"),
    ("What was CIBC's leverage ratio in fiscal 2025?", "CIBC", 2025, r"leverage ratio"),
]


def relevant(hit: dict, bank: str, year: int, pattern: str) -> bool:
    return hit["bank"] == bank and int(hit["fiscal_year"]) == year and re.search(pattern, hit["text"], re.I) is not None


def evaluate(models: list[str], strategies=("topk", "mmr", "hybrid", "rerank"), k: int = 3, use_scope: bool = True) -> dict:
    out = {"k": k, "scope_filter": use_scope, "queries": len(QUERIES), "results": {}, "rules": QUERIES}
    for m in models:
        r = Retriever(m)
        for s in strategies:
            per = []
            for q, bank, year, pat in QUERIES:
                hits = r.search(q, strategy=s, k=k, scope=None if use_scope else Scope(), floor=0.0)
                rel = [relevant(h, bank, year, pat) for h in hits]
                per.append({"query": q, "precision": sum(rel) / k, "hit_at_1": bool(rel and rel[0]),
                            "right_filing": any(h["bank"] == bank and int(h["fiscal_year"]) == year for h in hits),
                            "top": [f"{h['bank']} {h['fiscal_year']} p{h['page']} {h['section'][:40]}" for h in hits]})
            out["results"][f"{m}/{s}"] = {
                "precision_at_k": round(sum(p["precision"] for p in per) / len(per), 3),
                "hit_at_1": round(sum(p["hit_at_1"] for p in per) / len(per), 3),
                "right_filing": round(sum(p["right_filing"] for p in per) / len(per), 3), "per_query": per}
            print(f"{m:10s} {s:7s} precision@{k} {out['results'][f'{m}/{s}']['precision_at_k']:.3f}  "
                  f"hit@1 {out['results'][f'{m}/{s}']['hit_at_1']:.3f}")
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--models", nargs="+", default=["minilm", "bge-small"])
    ap.add_argument("--no-scope", action="store_true")
    ap.add_argument("--out", type=Path, default=ROOT / "reports" / "retrieval_eval.json")
    a = ap.parse_args(argv)
    res = evaluate(a.models, use_scope=not a.no_scope)
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(res, indent=1), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
