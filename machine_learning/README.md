# Machine Learning

Two capstones that take a model all the way to a decision someone can act on — and, in one
case, to the recommendation *not* to deploy. Both are about the part that comes after the
model works: calibration, leakage, cost, fairness and drift.

| | [Credit Scoring Decision System](credit_scoring/) | [Deep Learning Equity Signal](equity_signal/) |
|---|---|---|
| **Question** | Which loan applications will go bad, and what is that worth in dollars? | Can deep learning beat a systematic desk's existing trading signal? |
| **Data** | 307,511 Home Credit applications + 1.7M credit-bureau records | 48 S&P 500 stocks, 259,073 rows, 2005–2025 |
| **Stack** | Python, scikit-learn, SHAP, pandas | PyTorch, pandas, scikit-learn, SHAP |
| **Headline** | 0.774 test AUROC → **+$578.7M net** on the sealed test book | Charging 10bps costs **inverted the ranking** and retired the incumbent |
| **Verdict** | **Deploy** — gender-free pipeline, with monitoring | **Iterate, not deploy** — it still loses to buy-and-hold |

## 1. Credit Scoring — a 0.774 AUROC turned into a $578M decision

A profit curve prices *every* possible approval rate, so leadership picks the risk appetite
and the model reports what it costs. Declining at PD ≥ 7% approves 63.2% of applicants and
catches 74.5% of defaults.

Three things make it more than a modelling exercise: class weighting was **refused on
purpose** (it inflates predicted probabilities, and both the dollar math and the decline
reasons need honest ones — calibration is verified decile by decile instead); all 279
features map to **lawful adverse-action reasons**; and the PSI drift alarm was **test-fired**
under a simulated recession, tripping at 0.337. A fairness audit caught **gender among the
model inputs** — prohibited in credit decisions — and removing it cost 0.0006 AUROC.

→ [Full write-up](credit_scoring/) · [complete repo](https://github.com/kaustubhspatil/credit-scoring-decision-system)

## 2. Equity Signal — the result that inverted after costs

The desk's incumbent signal looks profitable **gross** (+0.50 Sharpe), but it trades **159×
its capital per year**. Charging realistic 10bps costs turns that into **−0.30 net Sharpe**
and −$271,380. Retiring it is worth roughly **$118k/year in fees alone**, before any
question of alpha.

The honest conclusion is that the best network does **not** get capital: it clears the
firm's 0.6 target and beats the S&P 500, but loses to equal-weight buy-and-hold (0.85 vs
0.88) and holds 47.7 of 48 stocks on an average day — a learned long bias a bullish test
period rewarded, not alpha. The accuracy ceiling was fixed **before** modelling from return
autocorrelation (−0.105), leak-freedom is **proven by recomputation** rather than asserted,
and the chart-reading ResNet-18 that failed is reported as a failure.

→ [Full write-up](equity_signal/) · [complete repo](https://github.com/kaustubhspatil/sp500-quantitative-deep-learning)

---

Each folder holds the results write-up. The linked repositories carry the notebooks,
trained models, reports and a runnable demo script (`score_applicant.py` and `predict.py`).
