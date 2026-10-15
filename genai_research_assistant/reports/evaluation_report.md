# Evaluation report: Jarvis Research Assistant

All figures below come from `reports/evaluation_results.json` (test set A), `reports/evaluation_results_b*.json`
(test set B), `reports/step3_*.json` (the 15 hand checked questions) and `reports/retrieval_eval*.json`, produced by
`python -m jarvis.evaluate`, `jarvis.step3` and `jarvis.retrieval_eval`, and are tracked in MLflow (`mlflow.db`).

## 1. Method

* **Test sets.** Set A (30 items) was built and frozen before any configuration was compared. After v1 was diagnosed on
  set A, a second set B (30 items, new seed, no source passage shared with set A) was built and **only then** used to
  measure v2, so the v2 improvement is measured on questions no change was made for. Each set has 20 grounded
  questions (written by the judge model from one passage, kept only when every figure of the answer appears literally
  in that passage, with its page) and 10 hand written edge cases: a bank that is not covered, a future year, a quarter
  that is not in the data, a computation, an ambiguous question, a question in French, a leading question, an
  instruction hidden in the question, a trend across two years, and a cross bank survey.
* **Judge.** Claude Sonnet 4.6 (stronger than the answering model, Claude Haiku 4.5), temperature 0, a rubric with
  defined levels, reasons logged. Faithfulness, relevance and completeness from 1 to 5. A correct refusal when the
  context lacks the answer scores 5 for faithfulness, so faithfulness must be read together with how often the system
  answered.
* **Deterministic checks.** Answer key figures present in the answer; share of answer figures found in a cited passage
  (the figure check); expected behaviour on each edge case.

## 2. Results

### Test set A (configuration comparison, v1)

| Configuration | Faithfulness | Relevance | Completeness | Answer key found | Answered (of 20) | Edge cases | $ per query | Median latency |
|---|---|---|---|---|---|---|---|---|
| Basic top-k, zero shot | 4.50 | 4.63 | 4.43 | 50% | 11 | 78% | 0.004 | 1.9 s |
| MMR, few shot, JSON | 4.57 | 4.57 | 4.54 | 55% | 13 | 89% | 0.004 | 2.0 s |
| Hybrid + rerank, CoT, HyDE (v1 best) | **4.90** | 4.73 | 4.63 | 60% | 14 | 89% | 0.004 | 8.6 s |
| Agent (5 tools) | 4.70 | **4.87** | 4.67 | **80%** | 18 | 100% (56% under the first check) | 0.009 | 9.4 s |

### Test set B (fresh questions; v2 measured here)

| Configuration | Faithfulness | Relevance | Completeness | Answer key found | Answered (of 20) | Edge cases | $ per query | Median latency |
|---|---|---|---|---|---|---|---|---|
| v1 best | 4.71 | 4.64 | 4.61 | 65% | 17 | 78% | 0.004 | 8.8 s |
| **v2 best (retry before declining)** | **4.93** | **4.83** | **4.83** | 80% | 19 | **89%** | 0.005 | 9.8 s |
| Agent | 4.83 | 4.72 | 4.72 | **85%** | 20 | 100% (56% under the first check) | 0.007 | 10.3 s |

Minimum targets in the brief: faithfulness at least 3.5 and relevance at least 4.0. Every configuration meets both.

### Test set B again, after the quarterly reports were added (October 14)

The index grew from 4,301 to 9,967 chunks and the scope rules learned quarters. Set B (annual questions only) was run
again to check that nothing regressed (`evaluation_results_b_v3*.json`):

| Run | Faithfulness | Relevance | Completeness | Answer key found | Answered (of 20) | Edge cases | $ per query |
|---|---|---|---|---|---|---|---|
| v2 best, first run after the change | 5.00 | 4.89 | 4.89 | 65% | 17 | 89% | 0.004 |
| v2 best, after the scope fix, run 1 | 4.93 | 4.86 | 4.86 | 80% | 19 | 89% | 0.005 |
| v2 best, after the scope fix, run 2 | 4.93 | 4.86 | 4.86 | 75% | 18 | 78% | 0.005 |
| Agent (first run after the change) | 4.86 | 4.79 | 4.83 | 85% | 20 | 100% (56% first check) | 0.008 |
| v2 best on **OpenAI** (gpt-4o-mini, judged by gpt-4o) | 4.73 | 4.87 | 4.73 | 75% | 18 | 78% | 0.001 |

* The first run fell to 65%. Item by item: one question (G7, asked of CIBC's fiscal 2025 annual report) mentioned "the
  quarter ending January 31, 2026", and the new date rule sent it to the Q1 reports. The rule now applies dates only
  when the question names no annual document; G7 was correct in both later runs.
* Three other items (G2, G4, G6) changed between two identical runs: the query rewrite and the answer model vary a
  little even at temperature 0. Run to run spread is about one item in twenty (5 points of answer key found), so the
  original 80% and the 75% to 80% after the change are the same result. A single run should not be read more
  precisely than that.
* The OpenAI row uses a different judge (gpt-4o) from the Bedrock rows (Claude Sonnet 4.6), so the scores compare
  only roughly; it ran before the scope fix. It is the cheapest option (0.001 USD a query) but not equal: two of its
  answers were scored unfaithful (G14 contradicted the passage on OCC heightened standards; E10 said no bank mentions
  E-23 when Scotiabank does), against none for the Bedrock design in either run. Its answers also sometimes wrote JSON
  with unquoted passage ids, which the parser now accepts. Bedrock stays the default.
* The agent's one low score is the known survey weakness (E10, faithfulness 2): it found Scotiabank's E-23 mention
  but generalised about the other banks from too few passages per bank.

## 2a. The 15 hand checked questions (Step 3)

`reports/step3_questions.json`: three questions per bank across credit, market, liquidity, operational, climate and
capital risk, nine annual and six quarterly. The true answer to each, with its pages, was found in the filing before
any run. Every answer was then read against that truth and against the chunks it cites; verdicts and reasons are in
`reports/step3_review.json`.

| Configuration | Correct | Partly correct | Wrong | Citations accurate |
|---|---|---|---|---|
| Basic, few shot and chain of thought prompts (first run, each) | 13 | 1 | 1 | 14 of 15 |
| **Chain of thought, after the date fix** | **14** | 1 | **0** | **15 of 15** |
| Chain of thought on OpenAI gpt-4o-mini | 14 | 1 | 0 | 14 of 15 |
| LangChain build (vector only), before and after the fix | 10 | 0 | 5 | 10 of 15 |
| Chain of thought, final (v4 and v5) | **15** | 0 | **0** | **15 of 15** |
| LangChain build, hybrid (v4) | 14 | 0 | 1 | 14 of 15 |

* The three prompts tie on these questions; chain of thought stays the default for its edge case behaviour on the
  test sets.
* The one wrong answer in the first run asked for Scotiabank's CET1 ratio "as at April 30, 2025": a quarter named by
  its end date, which the scope rule did not read, so only annual filings were searched and the system declined. The
  rule was extended to quarter end dates (and then guarded, see set B above).
* The partly correct answer (CIBC average VaR, fiscal 2025) stated the change (+$0.4 million) correctly and said the
  level was not disclosed: the $11.4 million sits in the neighbouring table chunk, which was not retrieved.
* The LangChain build declines five that the native build answers. It searches by vector only; the native build adds
  BM25 keyword search, a query rewrite and a retry, which find table rows such as Scotiabank's LCR. This is the
  measured reason the native build is the default.

## 2c. Closing the documented limitations (v4 and v5, October 15)

Each limitation in the system documentation was addressed with a mechanism, then measured. v4: the embedding models
and reranker on ONNX Runtime, neighbouring chunks (a table with its explanation), computed figures verified, a per
bank survey tool and a calculator for the agent, the LangChain build made hybrid, the judge given its full context.
v5 adds: comparisons searched one year, quarter or bank at a time, a period check on every table figure, and the
rule that a figure the filing states is quoted, never recomputed.

| Configuration | Set | Faithfulness | Relevance | Completeness | Answer key found | Answered (of 20) | Edge cases | $ per query |
|---|---|---|---|---|---|---|---|---|
| v1 best (for reference) | A | 4.90 | 4.73 | 4.63 | 60% | 14 | 89% | 0.004 |
| **v5** | **A** | **5.00** | **4.93** | **4.86** | **75%** | **17** | 89% | 0.007 |
| v4, run 1 | B | 4.86 | 4.76 | 4.79 | 70% | 18 | 89% | 0.006 |
| v4, run 2 | B | 5.00 | 4.85 | 4.89 | 65% | 18 | 89% | 0.007 |
| **v5** | **B** | **5.00** | 4.86 | 4.76 | **80%** | **19** | 89% | 0.006 |
| Agent v4 | B | 4.93 | 4.79 | 4.79 | 85% | 20 | 100% | 0.009 |
| v5 on OpenAI (gpt-4o-mini, judged by gpt-4o) | B | 4.60 | 4.73 | 4.53 | 70% | 19 | 89% | 0.001 |

* **Set A is the cleanest test:** none of these changes were made on its questions. v5 answers 17 of 20 against 14
  for v1, finds 4 more answer keys and loses 1, and no answer was scored unfaithful.
* **v4 on set B looked lower (65 to 70%) for two reasons found item by item:** the run to run spread (G2, G4, G6 change
  between identical runs), and G8, where the newly allowed arithmetic let the model compute TD's CET1 ratio (14.70%)
  instead of quoting the reported 14.7%. v5's rule (quote what the filing states; compute only a change no passage
  states) removed that, and v5 found 80%.
* **The one edge case still failing is the computation (E3, both sets):** BMO's fiscal 2025 headline net income sits in
  a summary table the retriever does not rank in the top passages. In v4 a split search found the 2024 against 2023
  table instead, and the model read its columns as 2025 and 2024. That wrong answer led to the period check, which
  now flags a figure attributed to a year other than its column heading; v5 declines this question rather than answer
  it wrongly. The agent answers it correctly (19.08%, from $7,327 million to $8,725 million, with the calculator), so
  computations across years belong to research mode.
* **Edge case scoring was corrected.** The first automatic check accepted only the RAG pipeline's exact refusal
  sentence and read "I cannot confirm" as agreeing, so the agent's correct refusals counted as failures (56%); the
  hand review had always found 9 of 9. The corrected check reads refusals in the system's own words and negation;
  every saved run was re-scored from its stored answers (`tools/rescore_edge.py`), and each file keeps the first
  check's score as `edge_behaviour_ok_strict`.
* **OpenAI on the final design** stays behind Bedrock (faithfulness 4.60 against 5.00, answer key 70% against 80%) at a
  sixth of the cost per query, so Bedrock stays the default. The whole OpenAI comparison cost 1.65 USD.
* **Step 3, final:** v5 answers all 15 correctly with accurate citations; the hybrid LangChain build answers 14 (it
  quoted PCL on loans as total PCL once).
* **Judge calibration** (`reports/judge_calibration.json`): against the human verdicts on 60 Step 3 answers, the judge
  agreed on 95% (Cohen's kappa 0.81) once it saw the full context. With the earlier 14,000 character limit it agreed
  on 80% (kappa 0.46): it called correct answers that cite a late passage unsupported. So the faithfulness scores
  reported before this fix were, if anything, too low.
* **A second, independent judge** (OpenAI gpt-4o, `reports/judge_calibration_gpt4o.json`) graded the same 60 answers:
  it agrees with the human verdicts on 98% (kappa 0.93) and with the Claude Sonnet judge on 97% (kappa 0.87), and the
  two judges' faithfulness scores are within one point on 98% of answers. Two judges from different providers agreeing
  this closely means the scores are not one model's bias. Cost: 0.68 USD.
* **Stability:** 1,500 concurrent searches with reranking on ONNX Runtime, no crash (`reports/stress_onnx.json`).

## 2b. Changes made after seeing results (no overfitting log)

Each change fixes a class of failure, not a single question, and each was measured on questions it was not tuned on
or on a repeat run.

| Date | Seen on | Change | Measured on |
|---|---|---|---|
| Oct 14 | an ad hoc agent question (CET1 ratios) | `extract_metrics` searches a ratio as a ratio ("CET1 ratio"), keeps 3 passages | the same question; agent on set B (85%) |
| Oct 14 | Step 3 Q10 | quarter end dates select their quarter | Step 3 rerun (14 of 15) |
| Oct 14 | set B G7 | dates select a quarter only when no annual document is named | set B, two runs |
| Oct 14 | Step 3, OpenAI answers | JSON with unquoted passage ids is accepted | parser test |
| Oct 15 | Step 3 Q14 | neighbouring chunks on the same page join the context | set A and set B (v4, v5) |
| Oct 15 | the brief's computation rule | computed figures verified from cited figures; agent calculator | unit tests; set B agent |
| Oct 15 | set B E10 | agent `survey_banks` searches each bank separately | set B agent (E10 faithfulness 2 to 3) |
| Oct 15 | Step 3 LangChain | LangChain made hybrid (BM25 in an EnsembleRetriever), rewrite, retry | Step 3 (10 to 14 of 15) |
| Oct 15 | calibration | judge context raised from 14,000 to 80,000 characters | calibration (80% to 95% agreement) |
| Oct 15 | set B E3 | comparisons searched per year or bank; period check on table figures | set A (v5) |
| Oct 15 | set B G8 | quote a figure the filing states, compute only an unstated change | set A and set B (v5) |
| Oct 15 | set B edge review | edge check reads own words refusals and negation | every saved run re-scored |
| Oct 15 | Step 3 LangChain Q13 | citation markers are not read as figures | unit test |
| Oct 15 | live demo | a figure such as $2,046 million was skipped as the year 2046; the app showed $ amounts as math | unit test; live app |

## 3. Hallucination analysis (faithfulness 2 or lower)

* **v2 best on set B: none.** On set A, v1 best had one: the leading question ("TD's credit quality collapsed, right?"),
  where the answer refused and then added commentary the judge found unsupported.
* **Basic top-k on set A: four** (two grounded questions, the computation and the leading question): weak retrieval
  hands the model passages from the wrong section, and the zero shot prompt does not stop it from filling gaps.
* **Agent: one on each set.** On set B the cross bank survey (E10) stated that no bank mentions OSFI E-23 explicitly,
  although one filing does: a search that returned too few passages per bank, then a confident summary. Fix: survey
  questions should search each bank separately.
* The figure check supports these numbers: 96 to 97% of the figures in RAG answers were found in a cited passage, and
  every figure that was not (computed differences and percentages) was flagged to the reader.

## 4. Failure analysis and the v2 change

* **The main v1 failure was over-caution, not invention.** On set A, v1 best declined 6 of 20 answerable questions.
  In each case the retriever had not returned the passage that held the figure (long tables, or the question phrased
  far from the filing's wording). Mechanism fix (v2): when the first pass declines, search again with the analyst's own
  words and twice the passages, and answer only if the wider context supports it. Measured on fresh set B: answered
  17 to 19 of 20, answer key found 65% to 80%, with no loss of faithfulness (4.71 to 4.93) and one extra model call
  only when the first pass declines (cost per query 0.004 to 0.005 USD).
* **Remaining v2 failures (set B):** a segment figure where the question asked for the bank (TD ROE); a total that
  sits in a large table (TD Ontario real estate lending); a figure stated pre tax where the key states after tax; and
  the computation case, which v2 declines because its prompt forbids computing new ratios. That rule is deliberate
  (the brief: do not trust computed ratios); a v3 could compute with a calculator tool and show the arithmetic.
* **Agent edge cases.** The first automatic check counted 4 of 9 as failures, but each was a correct refusal in the
  agent's own words ("I don't have access to Laurentian Bank's filings"). The check now reads refusals in the
  system's own words and negation (section 2c), and scores 9 of 9, as the hand review always did.
* **Test set limitation.** One grounded item (TD ROE) may be ambiguous between a segment and the whole bank: the
  question was written from a segment passage. Questions are machine written and figure checked, not human reviewed.

## 5. Retrieval (development set, separate from both test sets)

Precision@3 on 15 queries with explicit relevance rules (`reports/retrieval_eval.json`):

| Embedding | Top-k | MMR | Hybrid | Hybrid + rerank |
|---|---|---|---|---|
| all-MiniLM-L6-v2 | 0.49 | 0.31 | 0.62 | **0.73** |
| BGE-small-en-v1.5 | 0.42 | 0.31 | 0.56 | 0.62 |

MMR trades precision for diversity, which suits broad questions, not the specific figures these queries ask for.
Amazon Titan Text Embeddings v2 was also tried, but Bedrock throughput for it on this account was too low to finish
the index (throttled after about 2,500 of 4,301 passages).

After the quarterly reports were added, the comparison was repeated over the full index with a hosted model, OpenAI
text-embedding-3-small (`reports/retrieval_eval_v2.json`):

| Embedding | Top-k | MMR | Hybrid | Hybrid + rerank |
|---|---|---|---|---|
| all-MiniLM-L6-v2 (local) | 0.49 | 0.31 | 0.60 | **0.73** |
| BGE-small-en-v1.5 (local) | 0.42 | 0.31 | 0.51 | 0.67 |
| OpenAI text-embedding-3-small (hosted) | **0.51** | 0.47 | 0.62 | 0.69 |

The hosted model is best on plain vector search and much better under MMR, but the cross encoder reranker closes the
gap and the free local MiniLM still leads, so it stays the default (no filing text leaves the machine for indexing).
Indexing all 5.4M tokens with OpenAI cost about 0.11 USD.

## 6. Cost and latency

* Per query: about 0.006 USD for v5 RAG (the neighbouring chunks add context) and 0.005 USD for v2 RAG (Nova Lite rewrite, Haiku answer, Haiku second pass when needed) and 0.007 to
  0.009 USD for the agent. At 1,000 queries a day: about 1,800 USD a year for v2 RAG and 2,600 to 3,300 USD for the
  agent, against 1.8 million USD a year for the review team.
* Latency: median 9.8 s for v2 RAG and 10.3 s for the agent on this machine, dominated by the reranker running on a
  shared laptop CPU and by the rewrite call; the basic configuration answers in 1.9 s. A GPU or a hosted reranker
  would cut most of the difference.
* The whole evaluation (both test sets, all configurations, the judge) cost 4.26 USD of Bedrock calls. The OpenAI
  comparison (embeddings, the Step 3 questions, set B twice and a second judge) cost 1.65 USD, under a hard 5 USD cap
  enforced in code before every OpenAI call.

## 7. Recommendation from the evaluation

Use v5 RAG for factual lookups and the agent for comparisons and computations across years and banks, both with the
figure check visible and an analyst review step. Every limitation listed at the start of this work has a measured fix
(section 2c). What remains: headline figures in large summary tables are still sometimes not retrieved (the system
then declines rather than guesses), the judge is calibrated against one reviewer, and the next calibration sample
should come from the Regulatory Affairs analysts themselves during the pilot.
