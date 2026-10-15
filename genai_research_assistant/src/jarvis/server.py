"""The Jarvis web app: a small local API around the RAG pipeline and the agent, and the single page front end in web/.

    python -m jarvis.server            then open http://127.0.0.1:8600

POST /api/ask streams server sent events while the system works: one `step` event per stage (scope, rewrite, retrieve,
answer, retry, verify; or think, tool and verify for the agent), then one `result` event with the answer, its figure
check, sources with their passages and cost; or one `error` event. The front end draws the pipeline from these events.
The server listens on 127.0.0.1 only. One question is answered at a time (the models and the vector store are shared).
"""

from __future__ import annotations

import json
import queue
import threading
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

ROOT = Path(__file__).resolve().parents[2]
WEB = ROOT / "web"
app = FastAPI(title="Jarvis Research Assistant", docs_url=None, redoc_url=None)
app.mount("/static", StaticFiles(directory=WEB), name="static")
_LOCK = threading.Lock()
_CACHE: dict = {}


class Ask(BaseModel):
    question: str
    mode: str = "answer"                                  # answer (RAG) or research (agent)
    role: str = "analyst"
    history: list[dict] = []                               # earlier turns of this conversation, for follow ups


def _rag():
    if "rag" not in _CACHE:
        from .rag import RAG
        _CACHE["rag"] = RAG()
    return _CACHE["rag"]


def _agent():
    if "agent" not in _CACHE:
        from .agent import Agent
        _CACHE["agent"] = Agent(model="minilm")
    return _CACHE["agent"]


def _friendly(exc: Exception) -> str:
    text = f"{type(exc).__name__}: {exc}"
    if any(k in text for k in ("Token", "Credential", "ExpiredToken", "UnauthorizedSSO", "SSO", "credentials")):
        from . import llm
        return f"The AWS sign in has expired. In a terminal run: {llm.login_hint()}, then ask again."
    return f"Something went wrong: {text[:300]}"


@app.get("/")
def index() -> FileResponse:
    return FileResponse(WEB / "index.html")


@app.get("/api/meta")
def meta() -> JSONResponse:
    """What the front end shows before the first question: the corpus and the models."""
    import csv
    files = [ROOT / "data" / "processed" / f for f in ("filing_index.csv", "filing_index_quarterly.csv")]
    rows = [r for f in files if f.exists() for r in csv.DictReader(f.open(encoding="utf-8"))]
    try:
        from . import llm
        m = llm.models()
        models = {"answers": m["gen"].split(".")[-1].split(":")[0], "judge": m["judge"].split(".")[-1].split(":")[0],
                  "provider": m["provider"]}
    except Exception as exc:  # noqa: BLE001  shown in the app, not raised
        models = {"error": _friendly(exc)}
    return JSONResponse({"filings": len(rows), "chunks": sum(int(r["chunks"]) for r in rows),
                         "tokens": sum(int(r["tokens"]) for r in rows),
                         "banks": sorted({r["bank"] for r in rows}), "models": models})


def _clean(out: dict) -> dict:
    """Only what the page needs (no embeddings, no internal context)."""
    keep = ("answer", "abstained", "confidence", "caveats", "figure_check", "sources", "passages", "scope", "model",
            "usd", "ms", "seconds", "retried", "tool_calls", "iterations")
    res = {k: out[k] for k in keep if k in out}
    for t in res.get("tool_calls", []):
        t.pop("thought", None)
    return res


@app.post("/api/ask")
def ask(req: Ask) -> StreamingResponse:
    events: queue.Queue = queue.Queue()

    def step(name: str, data: dict) -> None:
        events.put(("step", {"name": name, **data}))

    def work() -> None:
        try:
            with _LOCK:
                if req.mode == "research":
                    out = _agent().run(req.question, role=req.role, on_step=step)
                else:
                    history = [{"role": h["role"], "content": str(h["content"])[:4000]} for h in req.history[-6:]
                               if h.get("role") in ("user", "assistant")]
                    out = _rag().answer(req.question, role=req.role, history=history or None, on_step=step)
            events.put(("result", _clean(out)))
        except Exception as exc:  # noqa: BLE001  reported to the page
            events.put(("error", {"message": _friendly(exc)}))
        events.put(None)

    threading.Thread(target=work, daemon=True).start()

    def stream():
        while (item := events.get()) is not None:
            kind, data = item
            yield f"event: {kind}\ndata: {json.dumps(data, default=str)}\n\n"

    return StreamingResponse(stream(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


def main() -> None:
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8600, log_level="warning")


if __name__ == "__main__":
    main()
