# Credit Scoring — turning a 0.774 AUROC model into a $578M decision

> **Full project, with notebooks, trained pipelines and reports:**
> **[kaustubhspatil/credit-scoring-decision-system](https://github.com/kaustubhspatil/credit-scoring-decision-system)**

**Can we predict, at application time, which consumer loans will go bad — and what is
that prediction worth in dollars?**

| | Result |
|---|---|
| **Model** | Tuned gradient boosting — **0.774 test AUROC** (logistic baseline 0.757) |
| **Generalization** | CV 0.768 ± 0.005 · validation 0.773 · sealed test 0.774 |
| **Decision rule** | Decline at PD ≥ 7% → 63.2% of applicants approved, **74.5% of defaults caught** |
| **Business value** | **+$578.7M net** on the 46,127-application test book |
| **Fairness** | Audit found **gender was a model input** — prohibited in credit decisions. Removed for **0.0006 AUROC** |
| **Verdict** | **DEPLOY**, gender-free pipeline, with monitoring and manual review for thin-file applicants |

**Data:** Home Credit — 307,511 applications × 122 columns (8.07% default rate), plus
1,716,428 credit-bureau records from other lenders.

## What makes this more than a modeling exercise

1. **The threshold is a business dial.** A profit curve prices *every* possible approval
   rate. Leadership picks the risk appetite; the model reports what it costs. That is the
   step that turns an AUROC into a decision.
2. **Class weighting was refused on purpose.** The usual rare-event trick inflates
   predicted probabilities, and both the dollar math and the decline reasons need honest
   ones. Calibration is verified decile by decile instead.
3. **Adverse-action reasons are production-grade.** All 279 model features map to consumer
   language, with a lawful generic fallback — never a raw column name.
4. **The monitoring alarm was test-fired.** A simulated severe recession (incomes −25%,
   scores −20%) drives PSI to **0.337** and trips the threshold. A tested control, not a
   promise.

## Stack

Python, pandas, NumPy, scikit-learn, SHAP, matplotlib, Jupyter, joblib.

## Try it

```bash
git clone https://github.com/kaustubhspatil/credit-scoring-decision-system
cd credit-scoring-decision-system
python score_applicant.py --riskiest --waterfall
```

Scores an applicant end to end and issues the decision plus its legally-required reasons.
The riskiest applicant in the test set: 23 years old, 12 bureau records, **PD 72.6%**,
declined — and did default.
