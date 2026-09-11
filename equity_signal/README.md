# Deep Learning Equity Signal — the result that inverted after costs

> **Full project, with notebooks, trained models and reports:**
> **[kaustubhspatil/sp500-quantitative-deep-learning](https://github.com/kaustubhspatil/sp500-quantitative-deep-learning)**

**Can deep learning beat a systematic fund's existing trading signal?**

**$1,000,000 traded over a sealed 2022–2025 test period, net of 10 bps costs:**

| Strategy | Net Sharpe | P&L | Max drawdown | Turnover/yr |
|---|---|---|---|---|
| **Feedforward NN** | **0.85** | **+$627,692** | −21.3% | 4.3× |
| Equal-weight buy & hold | 0.88 | +$660,768 | −20.9% | ~0 |
| Buy & hold SPY | 0.69 | +$531,026 | −24.5% | ~0 |
| LSTM (60-day) | 0.35 | +$185,475 | −20.5% | 43× |
| **Linear model (incumbent)** | **−0.30** | **−$271,380** | −41.2% | 159× |
| 1D CNN (60-day) | −0.37 | −$324,557 | −38.9% | 246× |

## The headline: charging realistic costs reversed the ranking

The desk's incumbent signal looks profitable **gross** (+0.50 Sharpe) — but it trades
**159× its capital per year**, paying **$473,796** in fees over four years, which turns it
into a **−0.30 net Sharpe, value-destroying** strategy. Retiring it is worth roughly
**$118k/year in fees alone**, before any question of alpha. The selected network trades
4.3×/yr, so its Sharpe moves only 0.87 → 0.81 across a 0–25 bps cost sweep.

## The honest conclusion: ITERATE, not deploy

The best network clears the firm's 0.6 target and beats the S&P 500 — but **not**
equal-weight buy-and-hold (0.85 vs 0.88), and it holds 47.7 of 48 stocks on an average
day. Most of its edge is a learned long bias that a bullish test period rewarded. That
isn't alpha, so it doesn't get capital yet.

## Methodology worth reading

- **The honest ceiling was set before any modeling.** Next-day return autocorrelation is
  **−0.105** — essentially noise — so 52–55% directional accuracy is the realistic maximum.
  Anything higher would indicate a bug.
- **Leak-freedom is proven, not asserted:** delete all data after a cutoff, recompute every
  feature, confirm the surviving rows are byte-identical.
- **Walk-forward validation across four market regimes** (COVID crash, 2022 bear, AI
  recovery, melt-up): **52.3% ± 0.5%**, gross Sharpe 0.59 ± 0.07.
- **Gradient attribution** shows the LSTM's last 10 days carry **99% of its input
  influence** — effective memory is ~2 weeks regardless of the 60-day window.
- **The chart-reading ResNet-18 failed, and is reported as such:** 55.1% accuracy / AUC
  0.516 frozen, against a 55.6% majority-class bar.

**Data:** 48 S&P 500 stocks, 2005–2025 (259,073 rows) plus VIX and the 10-year Treasury
yield. SPY and QQQ are reserved as benchmarks and never used as model inputs.

## Stack

Python, PyTorch, pandas, NumPy, scikit-learn, SHAP, matplotlib, Jupyter.

## Try it

```bash
git clone https://github.com/kaustubhspatil/sp500-quantitative-deep-learning
cd sp500-quantitative-deep-learning
python predict.py --top 10     # today's signal, straight from raw prices
```
