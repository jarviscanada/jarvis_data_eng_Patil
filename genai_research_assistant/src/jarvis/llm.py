"""The model layer: one call shape for every provider, with cost and latency logged for each call.

Providers (JARVIS_PROVIDER, default bedrock):
    bedrock   AWS Bedrock Converse API, profile JARVIS_AWS_PROFILE (environment or .env.local; else AWS's default credentials), region us-east-1. The answer
              model and the judge are the first models of each preference list that this account can use, unless
              JARVIS_GEN_MODEL or JARVIS_JUDGE_MODEL name one. The judge is always a stronger model than the answerer.
    openai    the OpenAI API (OPENAI_API_KEY), gpt-4o-mini answers and gpt-4o judges, as the module's examples do.
    ollama    a local Ollama server (no key, no cost).
Temperature is 0 everywhere (Module 4: compliance answers must be reproducible). Every call is appended to
logs/llm_calls.jsonl with the model, tokens, estimated cost and latency (Module 4: log every API call).
"""

from __future__ import annotations

import json
import os
import time
import urllib.request
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LOG = ROOT / "logs" / "llm_calls.jsonl"
REGION = os.environ.get("JARVIS_AWS_REGION", "us-east-1")
GEN_PREFERENCE = ["claude-haiku-5-5", "claude-haiku-4-5", "claude-3-5-haiku", "nova-lite"]
REWRITE_PREFERENCE = ["nova-lite", "nova-micro", "claude-haiku-4-5"]   # cheap, and its own quota beside the answerer
JUDGE_PREFERENCE = ["claude-sonnet-5-5", "claude-sonnet-4-6", "claude-sonnet-4-5", "claude-sonnet-4", "nova-pro"]
# USD per million input and output tokens, for the cost estimate only (check current prices before quoting them).
PRICES = {"haiku-4-5": (1.0, 5.0), "haiku": (1.0, 5.0), "sonnet": (3.0, 15.0), "opus": (15.0, 75.0), "nova-lite": (0.06, 0.24),
          "nova-pro": (0.8, 3.2), "gpt-4o-mini": (0.15, 0.6), "gpt-4o": (2.5, 10.0)}


def aws_profile() -> str | None:
    """The AWS profile to use: JARVIS_AWS_PROFILE from the environment or .env.local (not committed); None means AWS's
    default credential chain."""
    if os.environ.get("JARVIS_AWS_PROFILE"):
        return os.environ["JARVIS_AWS_PROFILE"]
    env = ROOT / ".env.local"
    if env.exists():
        for line in env.read_text(encoding="utf-8").splitlines():
            if line.startswith("JARVIS_AWS_PROFILE="):
                return line.split("=", 1)[1].strip() or None
    return None


def login_hint() -> str:
    p = aws_profile()
    return f"aws login{' --profile ' + p if p else ''} --region {REGION}"


@lru_cache(maxsize=1)
def bedrock_client(service: str = "bedrock-runtime"):
    import boto3
    return boto3.Session(profile_name=aws_profile(),
                         region_name=REGION).client(service)


@lru_cache(maxsize=1)
def bedrock_models() -> list[str]:
    """The inference profiles and on demand models this account can call."""
    b = bedrock_client("bedrock")
    ids = [p["inferenceProfileId"] for p in b.list_inference_profiles(maxResults=1000).get("inferenceProfileSummaries", [])]
    ids += [m["modelId"] for m in b.list_foundation_models(byOutputModality="TEXT")["modelSummaries"]
            if "ON_DEMAND" in m.get("inferenceTypesSupported", [])]
    return ids


ACCESS = ROOT / "models" / "bedrock_access.json"


def callable_model(model: str) -> bool:
    """Listed is not enabled: one 5 token call, remembered in models/bedrock_access.json."""
    seen = json.loads(ACCESS.read_text(encoding="utf-8")) if ACCESS.exists() else {}
    if model not in seen:
        try:
            bedrock_client().converse(modelId=model, messages=[{"role": "user", "content": [{"text": "ok"}]}],
                                      inferenceConfig={"maxTokens": 5, "temperature": 0})
            seen[model] = True
        except Exception as exc:  # noqa: BLE001
            seen[model] = "AccessDenied" not in type(exc).__name__ and "not available" not in str(exc)
        ACCESS.parent.mkdir(parents=True, exist_ok=True)
        ACCESS.write_text(json.dumps(seen, indent=1), encoding="utf-8")
    return bool(seen[model])


def pick(preference: list[str], override: str | None) -> str:
    if override:
        return override
    ids = bedrock_models()
    for want in preference:
        hits = [i for i in ids if want in i]
        us = sorted(i for i in hits if i.startswith("us."))          # a US cross region profile, the newest version
        for cand in reversed(us or sorted(hits)):
            if callable_model(cand):
                return cand
    raise RuntimeError(f"none of {preference} is callable on this Bedrock account")


@lru_cache(maxsize=1)
def models() -> dict:
    p = os.environ.get("JARVIS_PROVIDER", "bedrock")
    if p == "openai":
        return {"provider": p, "gen": "gpt-4o-mini", "judge": "gpt-4o", "rewrite": "gpt-4o-mini"}
    if p == "ollama":
        return {"provider": p, "gen": os.environ.get("JARVIS_OLLAMA_MODEL", "qwen2.5:7b"),
                "judge": os.environ.get("JARVIS_OLLAMA_MODEL", "qwen2.5:7b")}
    return {"provider": p, "gen": pick(GEN_PREFERENCE, os.environ.get("JARVIS_GEN_MODEL")),
            "judge": pick(JUDGE_PREFERENCE, os.environ.get("JARVIS_JUDGE_MODEL")),
            "rewrite": pick(REWRITE_PREFERENCE, os.environ.get("JARVIS_REWRITE_MODEL"))}


def _price(model: str) -> tuple[float, float]:
    for k, v in PRICES.items():
        if k in model:
            return v
    return (0.0, 0.0)


def _log(rec: dict) -> None:
    LOG.parent.mkdir(parents=True, exist_ok=True)
    with LOG.open("a", encoding="utf-8") as f:
        f.write(json.dumps(rec) + "\n")


def chat(messages: list[dict], system: str = "", role: str = "gen", max_tokens: int = 800,
         tools: list[dict] | None = None, tag: str = "") -> dict:
    """messages: [{"role": "user"|"assistant", "content": str}]. Returns {"text", "tool_calls", "usage", "model"}.
    `tools` (optional) are JSON schema tool specs {"name", "description", "parameters"}."""
    m = models()
    model = m.get(role, m["gen"])
    t0 = time.monotonic()
    for attempt in range(6):
        try:
            out = {"bedrock": _bedrock, "openai": _openai, "ollama": _ollama}[m["provider"]](
                model, messages, system, max_tokens, tools)
            break
        except Exception as exc:  # noqa: BLE001  throttling is retried with backoff, anything else is raised
            if attempt == 5 or "Throttl" not in type(exc).__name__ + str(exc):
                raise
            time.sleep(min(60, 4 * 2 ** attempt))
    ms = round((time.monotonic() - t0) * 1000)
    pin, pout = _price(model)
    cost = (out["usage"]["input"] * pin + out["usage"]["output"] * pout) / 1e6
    _log({"t": time.time(), "tag": tag, "role": role, "provider": m["provider"], "model": model, "ms": ms,
          "input_tokens": out["usage"]["input"], "output_tokens": out["usage"]["output"], "usd": round(cost, 6)})
    return {**out, "model": model, "ms": ms, "usd": cost}


def _bedrock(model, messages, system, max_tokens, tools):
    kwargs = {"modelId": model, "messages": [{"role": x["role"], "content": x["content"] if isinstance(x["content"], list)
                                              else [{"text": x["content"]}]} for x in messages],
              "inferenceConfig": {"maxTokens": max_tokens, "temperature": 0.0}}
    if system:
        kwargs["system"] = [{"text": system}]
    if tools:
        kwargs["toolConfig"] = {"tools": [{"toolSpec": {"name": t["name"], "description": t["description"],
                                                         "inputSchema": {"json": t["parameters"]}}} for t in tools]}
    r = bedrock_client().converse(**kwargs)
    content = r["output"]["message"]["content"]
    text = "".join(c.get("text", "") for c in content)
    calls = [{"id": c["toolUse"]["toolUseId"], "name": c["toolUse"]["name"], "args": c["toolUse"]["input"]}
             for c in content if "toolUse" in c]
    return {"text": text, "tool_calls": calls, "raw": r["output"]["message"],
            "usage": {"input": r["usage"]["inputTokens"], "output": r["usage"]["outputTokens"]},
            "stop": r.get("stopReason")}


# A hard cap on OpenAI spend, from the call log, checked before every OpenAI call (chat and embeddings). The account
# holds a small prepaid credit; the cap stays below it so an estimate error can never reach the card.
OPENAI_BUDGET_USD = float(os.environ.get("JARVIS_OPENAI_BUDGET_USD", "5.0"))


def openai_spent() -> float:
    if not LOG.exists():
        return 0.0
    total = 0.0
    for line in LOG.read_text(encoding="utf-8").splitlines():
        rec = json.loads(line) if line.strip() else {}
        if rec.get("provider") == "openai":
            total += rec.get("usd", 0.0)
    return total


def openai_client():
    """The OpenAI client, under the budget cap. The key is read from the environment, or on Windows from the user's
    saved environment (set after this process started); it is never printed or logged."""
    spent = openai_spent()
    if spent >= OPENAI_BUDGET_USD:
        raise RuntimeError(f"OpenAI budget reached: ${spent:.2f} of ${OPENAI_BUDGET_USD:.2f} (JARVIS_OPENAI_BUDGET_USD)")
    if not os.environ.get("OPENAI_API_KEY") and os.name == "nt":
        import winreg
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as k:
                os.environ["OPENAI_API_KEY"] = winreg.QueryValueEx(k, "OPENAI_API_KEY")[0]
        except OSError:
            pass
    from openai import OpenAI
    return OpenAI()


def _openai(model, messages, system, max_tokens, tools):
    msgs = ([{"role": "system", "content": system}] if system else []) + messages
    kw = {"model": model, "messages": msgs, "temperature": 0, "max_tokens": max_tokens}
    if tools:
        kw["tools"] = [{"type": "function", "function": t} for t in tools]
    r = openai_client().chat.completions.create(**kw)
    msg = r.choices[0].message
    calls = [{"id": c.id, "name": c.function.name, "args": json.loads(c.function.arguments or "{}")}
             for c in (msg.tool_calls or [])]
    return {"text": msg.content or "", "tool_calls": calls, "raw": msg.model_dump(),
            "usage": {"input": r.usage.prompt_tokens, "output": r.usage.completion_tokens},
            "stop": r.choices[0].finish_reason}


def _ollama(model, messages, system, max_tokens, tools):
    msgs = ([{"role": "system", "content": system}] if system else []) + messages
    body = json.dumps({"model": model, "messages": msgs, "stream": False,
                       "options": {"temperature": 0, "num_predict": max_tokens}}).encode()
    req = urllib.request.Request("http://127.0.0.1:11434/api/chat", data=body, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=300) as r:  # noqa: S310  local server
        d = json.loads(r.read())
    return {"text": d["message"]["content"], "tool_calls": [], "raw": d["message"],
            "usage": {"input": d.get("prompt_eval_count", 0), "output": d.get("eval_count", 0)}, "stop": "stop"}
