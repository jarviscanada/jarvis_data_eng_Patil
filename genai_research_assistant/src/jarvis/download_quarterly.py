"""Step 1a (quarterly): download the Big Five banks' quarterly Reports to Shareholders as PDF, from each bank's own
investor relations site, as the brief describes (Q1 to Q3; Q4 is the annual report).

    python -m jarvis.download_quarterly [--years 2024 2025]

Files land in data/raw/quarterly/<bank>/<fiscal year>/Q<n>.pdf, with manifest.json (URL, size, sha256). Scotiabank
names its full report "Shareholders Report" (its "Press Release" is a short summary); BMO serves files from prod.bmo.com.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data" / "raw" / "quarterly"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) jarvis-capstone research"
TD = "https://www.td.com/content/dam/tdcom/canada/about-td/pdf/quarterly-results"
TD_FILES = {(2024, 1): "2024/q1/2024-q1-reports-shareholders-en.pdf", (2024, 2): "2024/q2/2024-q2-reports-shareholders-en.pdf",
            (2024, 3): "2024/q3/2024-q3-reports-shareholders-en.pdf", (2025, 1): "2025/q1/2025-q1-reports-shareholders-en.pdf",
            (2025, 2): "2025/q2/2025-q2-reports-shareholders-en.pdf", (2025, 3): "2025/q3/q3-2025-report-to-shareholders-en.pdf"}
NAMES = {"RBC": "Royal Bank of Canada", "TD": "Toronto-Dominion Bank", "BMO": "Bank of Montreal",
         "BNS": "Bank of Nova Scotia", "CIBC": "Canadian Imperial Bank of Commerce"}


def url(bank: str, y: int, q: int) -> str:
    yy = str(y)[2:]
    return {"RBC": f"https://www.rbc.com/investor-relations/_assets-custom/pdf/{y}q{q}_report.pdf",
            "TD": f"{TD}/{TD_FILES[(y, q)]}",
            "BMO": f"https://www.prod.bmo.com/ir/qtrinfo/1/{y}-q{q}/Q{q}{yy}_ReportToShareholders.pdf",
            "BNS": f"https://www.scotiabank.com/content/dam/scotiabank/corporate/quarterly-reports/{y}/q{q}/"
                   f"Q{q}{yy}_Shareholders_Report-EN.pdf",
            "CIBC": f"https://www.cibc.com/content/dam/cibc-public-assets/about-cibc/investor-relations/pdfs/"
                    f"quarterly-results/{y}/q{q}{yy}report-en.pdf"}[bank]


def fetch(u: str) -> bytes:
    req = urllib.request.Request(u, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=120) as r:  # noqa: S310  fixed bank hosts only
        data = r.read()
    if not data.startswith(b"%PDF"):
        raise ValueError(f"not a PDF: {u}")
    return data


def download(years: list[int]) -> list[dict]:
    rows = []
    for bank in NAMES:
        for y in years:
            for q in (1, 2, 3):
                u, path = url(bank, y, q), RAW / bank / str(y) / f"Q{q}.pdf"
                if not path.exists():
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_bytes(fetch(u))
                    time.sleep(1.0)
                data = path.read_bytes()
                rows.append({"bank": bank, "bank_name": NAMES[bank], "fiscal_year": y, "quarter": f"Q{q}", "url": u,
                             "file": str(path.relative_to(ROOT)).replace("\\", "/"), "size": len(data),
                             "sha256": hashlib.sha256(data).hexdigest()})
                print(f"{bank} {y} Q{q} {len(data) / 1e6:.1f} MB")
    (RAW / "manifest.json").write_text(json.dumps(rows, indent=1), encoding="utf-8")
    return rows


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--years", nargs="+", type=int, default=[2024, 2025])
    rows = download(ap.parse_args(argv).years)
    print(f"{len(rows)} reports, {sum(r['size'] for r in rows) / 1e6:.0f} MB")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
