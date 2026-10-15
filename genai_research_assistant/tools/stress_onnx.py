"""Stress test for the native crash fix: many concurrent searches (embedding plus reranker) on ONNX Runtime.

    python tools/stress_onnx.py [requests] [threads]

The PyTorch build crashed about once per 1,000 requests in long pilot runs (an access violation inside the BERT
activation), and crashed fastest when requests overlapped. This runs 1,500 requests over 4 threads at once, a
harsher pattern than the app, and writes
reports/stress_onnx.json. A native crash would kill the process, so finishing is itself the result.
"""

import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from jarvis.retrieve import Retriever  # noqa: E402

BANKS = ["RBC", "TD", "BMO", "Scotiabank", "CIBC"]
TOPICS = ["CET1 ratio", "provision for credit losses", "liquidity coverage ratio", "climate risk", "cyber risk",
          "value at risk", "net income", "model risk management"]
PERIODS = ["fiscal 2024", "fiscal 2025", "Q2 2025", "Q3 2024"]


def main(n: int = 1500, threads: int = 4) -> dict:
    r = Retriever("minilm")
    qs = [f"What did {BANKS[i % 5]} report on {TOPICS[i % 8]} in {PERIODS[i % 4]}?" for i in range(n)]
    t0, done, errors = time.monotonic(), [0], []

    def one(q):
        try:
            r.search(q, strategy="rerank", k=5)
            done[0] += 1
            if done[0] % 100 == 0:                        # progress, and a partial result if the process dies
                print(f"{done[0]} done, {round(time.monotonic() - t0)} s", flush=True)
                (ROOT / "reports" / "stress_onnx.json").write_text(json.dumps(
                    {"requests": n, "threads": threads, "completed": done[0], "running": True}), encoding="utf-8")
        except Exception as exc:  # noqa: BLE001  a Python error is recorded; a native crash would end the run
            errors.append(f"{type(exc).__name__}: {exc}"[:200])

    r.bm25                                                # build the keyword index once, before the threads start
    with ThreadPoolExecutor(threads) as pool:
        list(pool.map(one, qs))
    out = {"requests": n, "threads": threads, "completed": done[0], "python_errors": errors[:5],
           "seconds": round(time.monotonic() - t0), "engine": "onnxruntime", "torch_loaded": "torch" in sys.modules}
    (ROOT / "reports" / "stress_onnx.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    return out


if __name__ == "__main__":
    print(main(*(int(a) for a in sys.argv[1:3])))
