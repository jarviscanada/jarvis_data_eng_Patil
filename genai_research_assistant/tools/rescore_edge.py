"""Re-score the edge case behaviour of every saved evaluation run with the corrected check, from the stored answers.

    python tools/rescore_edge.py

No model is called. Each result file keeps the first check's score as `edge_behaviour_ok_strict` beside the corrected
`edge_behaviour_ok`, and each row keeps `behaviour_ok_strict`, so the change is visible. The corrected check reads a
refusal in the system's own words as a refusal and "I cannot confirm" as not agreeing (see evaluate.DECLINE).
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from jarvis.evaluate import behaviour_ok, behaviour_ok_strict  # noqa: E402


def main() -> None:
    items = {}
    for f in ("testset.json", "testset_b.json"):
        for i in json.loads((ROOT / "reports" / f).read_text(encoding="utf-8"))["items"]:
            items[(f, i["id"])] = i
    for path in sorted((ROOT / "reports").glob("evaluation_results*.json")):
        ts = "testset.json" if path.name in ("evaluation_results.json",) or "_a_" in path.name else "testset_b.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        for name, res in data.items():
            edge = [r for r in res["rows"] if r.get("type") == "edge"]
            for r in edge:
                it = items[(ts, r["id"])]
                r["behaviour_ok_strict"] = behaviour_ok_strict(it, r["answer"], r["abstained"])
                r["behaviour_ok"] = behaviour_ok(it, r["answer"], r["abstained"])
            scored = [r for r in edge if r["behaviour_ok"] is not None]
            strict = [r for r in edge if r["behaviour_ok_strict"] is not None]
            res["edge_behaviour_ok_strict"] = round(sum(r["behaviour_ok_strict"] for r in strict) / len(strict), 3)
            res["edge_behaviour_ok"] = round(sum(r["behaviour_ok"] for r in scored) / len(scored), 3)
            print(f"{path.name:42s} {name:15s} strict {res['edge_behaviour_ok_strict']:.3f} -> {res['edge_behaviour_ok']:.3f}")
        path.write_text(json.dumps(data, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
