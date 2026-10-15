"""Step 1a: download the Big Five banks' filings from SEC EDGAR (the regulator's official copies).

    python -m jarvis.download --years 2024 2025 [--quarterly]

Each bank files its annual report on Form 40-F (exhibits: the Annual Information Form, the MD&A and the audited
financial statements) and its quarterly reports to shareholders on Form 6-K. SEC fair access policy: requests declare
a contact in the User-Agent (SEC_USER_AGENT in .env.local, never committed) and stay under 10 a second; we use 2.
Files land in data/raw/edgar/<bank>/<fiscal year>/ with a manifest.json of source URL, size and sha256.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data" / "raw" / "edgar"
BANKS = {"RBC": ("Royal Bank of Canada", 1000275), "TD": ("Toronto-Dominion Bank", 947263),
         "BMO": ("Bank of Montreal", 927971), "BNS": ("Bank of Nova Scotia", 9631),
         "CIBC": ("Canadian Imperial Bank of Commerce", 1045520)}
MIN_EXHIBIT = 300_000          # the AIF, MD&A and statements are all larger; certifications and consents are smaller
_last = [0.0]


def user_agent() -> str:
    env = ROOT / ".env.local"
    for line in env.read_text(encoding="utf-8").splitlines() if env.exists() else []:
        if line.startswith("SEC_USER_AGENT="):
            return line.split("=", 1)[1].strip()
    raise SystemExit("set SEC_USER_AGENT=<name> <contact email> in .env.local (SEC fair access policy)")


def get(url: str) -> bytes:
    wait = 0.5 - (time.monotonic() - _last[0])
    if wait > 0:
        time.sleep(wait)
    req = urllib.request.Request(url, headers={"User-Agent": user_agent(), "Accept-Encoding": "identity"})
    with urllib.request.urlopen(req, timeout=60) as r:  # noqa: S310  fixed sec.gov hosts only
        data = r.read()
    _last[0] = time.monotonic()
    return data


def _rows(block: dict) -> list[dict]:
    n = len(block["form"])
    return [{"form": block["form"][i], "date": block["filingDate"][i], "acc": block["accessionNumber"][i],
             "doc": block["primaryDocument"][i]} for i in range(n)]


def filing_pages(cik: int):
    """The issuer's filings, newest first: the recent block, then each older page only when asked for."""
    sub = json.loads(get(f"https://data.sec.gov/submissions/CIK{cik:010d}.json"))
    yield _rows(sub["filings"]["recent"])
    for f in sub["filings"].get("files", []):
        yield _rows(json.loads(get(f"https://data.sec.gov/submissions/{f['name']}")))


def find(cik: int, form: str, date_prefix: str) -> list[dict]:
    """Filings of `form` whose filing date starts with `date_prefix`, reading older pages until past that date."""
    found = []
    for page in filing_pages(cik):
        found += [f for f in page if f["form"] == form and f["date"].startswith(date_prefix)]
        if page and min(f["date"] for f in page) < date_prefix:
            break
    return found


def annual(cik: int, fiscal_year: int) -> dict | None:
    """The 40-F for a fiscal year ending October 31 is filed in late November or December of that year."""
    hits = find(cik, "40-F", f"{fiscal_year}-1")
    return hits[0] if hits else None


def exhibits(cik: int, acc: str) -> list[tuple[str, int]]:
    idx = json.loads(get(f"https://www.sec.gov/Archives/edgar/data/{cik}/{acc.replace('-', '')}/index.json"))
    return [(i["name"], int(i.get("size") or 0)) for i in idx["directory"]["item"]
            if re.search(r"ex", i["name"], re.I) and i["name"].lower().endswith((".htm", ".pdf"))
            and not re.match(r"R\d+\.htm", i["name"]) and int(i.get("size") or 0) >= MIN_EXHIBIT]


def download(fiscal_years: list[int], dry: bool = False) -> list[dict]:
    rows = []
    for code, (name, cik) in BANKS.items():
        for fy in fiscal_years:
            f = annual(cik, fy)
            if not f:
                print(f"{code} {fy}: no 40-F found")
                continue
            folder = RAW / code / str(fy)
            for ex, size in exhibits(cik, f["acc"]):
                url = f"https://www.sec.gov/Archives/edgar/data/{cik}/{f['acc'].replace('-', '')}/{ex}"
                row = {"bank": code, "bank_name": name, "fiscal_year": fy, "form": "40-F", "filed": f["date"],
                       "accession": f["acc"], "file": ex, "url": url, "size": size}
                if not dry:
                    folder.mkdir(parents=True, exist_ok=True)
                    path = folder / ex
                    if not path.exists():
                        path.write_bytes(get(url))
                    row["sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
                rows.append(row)
                print(f"{code} {fy} {ex} {size / 1e6:.1f} MB{'' if dry else ' ok'}")
    if not dry:
        RAW.mkdir(parents=True, exist_ok=True)
        (RAW / "manifest.json").write_text(json.dumps(rows, indent=1), encoding="utf-8")
    return rows


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--years", nargs="+", type=int, default=[2024, 2025])
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args(argv)
    rows = download(a.years, a.dry_run)
    print(f"{len(rows)} files, {sum(r['size'] for r in rows) / 1e6:.0f} MB")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
