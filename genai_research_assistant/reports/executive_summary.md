# Executive summary: can a GenAI assistant speed up filing review?

**For:** Chief Compliance Officer. **Recommendation: deploy as a first pass review tool for a supervised pilot with the
Regulatory Affairs team, then iterate.** It is accurate when it answers, it says so when it cannot, and every figure
is checked against its source, but it does not yet find every answer and must not replace analyst review.

## What we built

An assistant that answers analysts' questions about the Big Five banks' fiscal 2024 and 2025 filings (Annual
Information Forms, MD&A, financial statements, and the first to third quarter Reports to Shareholders), citing the
bank, document, period and page for every claim. A research mode compares filings across years and banks, including
what changed in their risk language.

## How well it works (30 question tests, scored by an independent AI grader and automatic checks)

* **Does not make things up:** faithfulness 5.0 out of 5 on both test sets with the final design, and no fabricated
  answer. Every figure is checked against its cited page, against the year of its table column, and, if computed,
  recomputed from the cited figures; anything that does not check out is flagged to the analyst with the reason. The
  AI grader itself was checked against a person's grading and agreed on 95% of answers.
* **Finds the answer 75 to 80% of the time** for specific factual questions on both test sets (85% in research mode),
  up from 50% for a basic design. When it cannot find an answer it says "the documents do not contain this" rather than guessing.
* **Checked by hand:** of 15 compliance questions across all five banks and six risk types, each with the true answer
  found in the filing beforehand, all 15 were answered correctly, each cited to a page that supports it.
* **Handles tricky questions:** it declines questions about banks or periods it does not cover, ignores instructions
  slipped into a question, and does not simply agree with a leading question.

## Can I trust it not to miss a material risk?

Not on its own. In about 1 of 5 factual questions it cannot find the passage (most often a headline figure in a large
summary table) or picks a related figure (for example a business segment instead of the whole bank); when it cannot
find the figure it says so rather than guessing. It is therefore a first pass tool: it saves the analyst the search, shows
exactly where each answer came from, and flags anything it could not verify; the analyst confirms.

## Cost and time

About half a cent per question (0.6 cents): roughly 2,200 dollars a year at 1,000 questions a day, against 1.8 million dollars a
year for the review team. Answers take about 8 seconds. If it halves the 4 to 6 hours spent per annual report, the
time saved is worth far more than the running cost.

## Risks and controls

* **Wrong or missing answers:** every answer cites its page; unverified figures are flagged; analyst review required.
* **Confidential data:** the filings are public; internal memos are restricted by role inside the search itself, so
  an analyst's question can never reach them. Embeddings run on our own machine; answers use AWS Bedrock (OpenAI was
  compared: a fifth of the cost, but two of its 30 answers were judged unfaithful against none for Bedrock).
* **Tested independently:** 13 of 13 outside checks passed (access, hidden instructions, accuracy, isolation), and
  140 automated injection attacks produced no real failure.
* **Model risk (OSFI E-23):** every model call and research step is logged; the system has an evaluation set,
  a monitoring plan and an inventory entry.

## Next steps

Supervised pilot with 3 analysts for one quarter, with the analysts grading a sample of answers to recalibrate the AI
grader; improve retrieval of headline figures in summary tables; measure review time saved and missed findings against analysts' own reviews before any
wider rollout.
