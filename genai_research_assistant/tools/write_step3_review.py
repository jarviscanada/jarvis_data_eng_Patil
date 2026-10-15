"""Write reports/step3_review.json: the manual verdicts for the Step 3 answers.

Each answer was read against its hand located truth (reports/step3_questions.json) and against the text of the chunks
it cites. Verdicts: correct, partly correct, wrong. citations_accurate: the cited passage supports what the answer
says. The verdicts are written here as data with a note for every answer that is not plainly correct, so the review
itself can be checked. Re-run after a new configuration is reviewed.
"""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CORRECT = {
    "Q01": "$4,362 million, cited to the PCL table on p223 (the same table also appears on p13)",
    "Q02": "129%, average for the quarter ended July 31, 2025, p38",
    "Q03": "integration into risk management, scenario analysis, enterprise stress testing, transition and physical "
           "risk; grounded in pp177 to 183",
    "Q04": "$1,341 million with the Stage 3 and Stage 1 and 2 split, p15",
    "Q05": "130% for the quarter ended October 31, 2025, p92",
    "Q06": "technology and cyber risk governance (Platforms and Technology Risk Oversight Committee, enterprise "
           "programs) from p84; a valid passage, different from the risk trend passage on p60 recorded as truth",
    "Q07": "$1,054 million ($765 million impaired, $289 million performing); the chunk starting on p14 holds the figure",
    "Q08": "13.5% as at July 31, 2025; the cited chunk runs from p17 to p18 where the sentence is",
    "Q09": "physical and transition risk, channels into credit, market, operational and liquidity risk, risk appetite "
           "and sector reviews; pp189 to 193",
    "Q10": "13.2% as at April 30, 2025 (after the date fix), cited to the CET1 sentence on p53",
    "Q11": "131% for the quarter ended October 31, 2024 (136% a year earlier), p171",
    "Q12": "Model Risk Management Framework over internal and vendor models, policies and standards, Enterprise Model "
           "Risk Score; pp133 and 197",
    "Q13": "$559 million, up $76 million year over year, p8",
    "Q15": "Board committees (CGC, RMC, Audit), Group ELT, CAO as sustainability lead; p159",
}
SPECIAL = {
    "Q10": ("wrong", False, "declined: the question names the quarter by its end date (April 30, 2025); the scope "
                            "rule did not read dates, so only annual filings were searched. Fixed (dates map to "
                            "quarters) and measured in the +datefix run."),
    "Q14v4": "$11.4 million (and +$0.4 million from $11.0 million), cited to the VaR table chunk on pp133 to 135, "
             "which the neighbouring chunk rule brought in",
    "Q14": ("partly correct", True, "states the +$0.4 million change correctly but says the level is not disclosed: the "
                                    "retrieved chunk holds the explanation, not the VaR table ($11.4 million) in the "
                                    "neighbouring chunk. A retrieval miss, not a fabrication."),
}
LC_STORE = ("wrong", False, "declined: the LangChain chain searches by vector only (no BM25 keyword search, no query "
                            "rewrite, no retry) and missed the passage the native build finds; repeated on a healthy "
                            "store in the +datefix run (first suspected to be store damage; that was ruled out).")
LC_Q10 = ("wrong", False, "declined although the date now selects Q2 2025: it retrieved the paragraph after the CET1 "
                          "sentence (p53 to 54), not the sentence itself; vector only retrieval")
RAW_JSON = "; the model wrote its JSON with unquoted passage ids, so the raw JSON was shown (parser made tolerant after)"


# Configurations whose answers have been read; any other stays "needs review" until it is read and added here.
REVIEWED = {"native:basic", "native:fewshot", "native:cot", "langchain:cot", "native:cot+datefix",
            "langchain:cot+datefix", "native:cot+openai", "native:cot+v4", "langchain:cot+v4", "native:cot+v5"}


def verdicts(config: str, results: list[dict]) -> list[dict]:
    out = []
    for r in results:
        if r["config"] != config:
            continue
        q = r["id"]
        if config not in REVIEWED:
            v, cit, note = "needs review", None, "not yet read"
        elif config == "langchain:cot+v4" and q == "Q01":
            v, cit, note = ("wrong", False, "quoted PCL on loans ($4,356 million, credit risk note p325) as the total "
                                            "PCL ($4,362 million): a real figure from the right table family but the "
                                            "wrong line; the figure check cannot catch this (the number is in the "
                                            "passage)")
        elif config == "langchain:cot+v4" and q == "Q13":
            v, cit, note = "correct", True, CORRECT[q] + "; the citation [S13] was flagged as a figure (checker fixed)"
        elif config in ("langchain:cot", "langchain:cot+datefix") and q in ("Q11", "Q12", "Q13", "Q14"):
            v, cit, note = LC_STORE
        elif config == "langchain:cot+datefix" and q == "Q10":
            v, cit, note = LC_Q10
        elif config == "native:cot+openai" and q == "Q09":
            v, cit, note = ("correct", False, "content matches the truth (physical and transition risk, effects on "
                                              "operations and counterparties) but no passage id could be read" + RAW_JSON)
        elif q == "Q14" and r["key_found"]:
            v, cit, note = "correct", True, SPECIAL["Q14v4"]
        elif q in SPECIAL and (q != "Q10" or r["abstained"]) and (q != "Q14" or not r["key_found"]):
            v, cit, note = SPECIAL[q]
        elif r["abstained"]:
            v, cit, note = "wrong", False, "declined although the filings hold the answer"
        elif q in CORRECT and (r["key_found"] in (True, None)):
            raw = r["answer"].lstrip().startswith("{")
            v, cit, note = "correct", True, CORRECT[q] + (RAW_JSON if raw else "")
        else:
            v, cit, note = "needs review", None, "not yet reviewed"
        out.append({"id": q, "config": config, "verdict": v, "citations_accurate": cit, "note": note})
    return out


def main() -> None:
    results = json.loads((ROOT / "reports" / "step3_results.json").read_text(encoding="utf-8"))
    reviews = [v for cfg in dict.fromkeys(r["config"] for r in results) for v in verdicts(cfg, results)]
    doc = {"method": __doc__.split("\n\n")[1].replace("\n", " "), "reviews": reviews}
    (ROOT / "reports" / "step3_review.json").write_text(json.dumps(doc, indent=1), encoding="utf-8")
    pending = [f"{v['config']} {v['id']}" for v in reviews if v["verdict"] == "needs review"]
    print(len(reviews), "verdicts;", "to review by hand:", pending or "none")


if __name__ == "__main__":
    main()
