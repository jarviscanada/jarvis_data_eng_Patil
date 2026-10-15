# System documentation: Jarvis Research Assistant

For the model review committee. Scope: a retrieval augmented generation (RAG) system and research agent over the
public filings of Canada's Big Five banks, used as a **first pass review tool** by the Regulatory Affairs team. Every
answer requires analyst review before use.

## 1. Architecture

```
   SEC EDGAR (Form 40-F exhibits: AIF, MD&A, audited       Banks' investor relations sites (Q1 to Q3 Reports to
   statements; fiscal 2024 and 2025)                       Shareholders, PDF; fiscal 2024 and 2025)
                     |                                                          |
   download.py (manifest: URL, size, sha256)              download_quarterly.py (manifest: URL, size, sha256)
                     |                                                          |
   ingest.py  HTML, layout aware: 4,301 chunks            ingest_pdf.py  PyMuPDF, tables rebuilt from positions:
   (2.3M tokens)                                           5,666 chunks (3.0M tokens)
                     \_____________ shared cleaning and chunking ______________/
                                         |
         index.py  local embeddings (all-MiniLM-L6-v2, ONNX Runtime) -> ChromaDB with metadata and an access tag
                                         |
   question --> scope_of() bank, year, quarter, document --> retrieve.py: hybrid (vector + BM25, RRF) -> rerank
                                         |                         filters: scope AND role access, inside the search
                                         v
        rag.py  prompt (role, rules, numbered passages) -> Claude Haiku 4.5 (Bedrock, temperature 0) -> JSON answer
                                         |
                      figure check: every number must appear in a cited passage, else caveat + low confidence
                                         |
        agent.py  ReAct loop, 7 tools, max 8 steps, role filter inside every tool, full audit trail
                                         |
          app.py (Streamlit demo)      evaluate.py (Claude Sonnet 4.6 judge + deterministic checks, MLflow)

          lc.py: the same retrieval, prompts, figure check and agent tools rebuilt in LangChain (section 6a)
```

## 2. Data pipeline

* **Source.** The banks' annual filings on SEC EDGAR (the regulator's official copies, identical to SEDAR+), downloaded
  with a declared contact and under 2 requests a second. 28 filings: for each bank and fiscal year, the Annual
  Information Form, the MD&A and the audited financial statements (RBC files the MD&A and statements as one exhibit).
  Quarterly: the Q1 to Q3 Reports to Shareholders for fiscal 2024 and 2025, 30 PDFs (about 2,400 pages) from each
  bank's investor relations site, fetched one at a time with a manifest. Q4 is reported in the annual filings.
  Scotiabank's full report is its "Shareholders Report" (its "Press Release" is a 13 to 16 page summary and was
  replaced after a page count check); BMO serves its files from prod.bmo.com.
* **Parsing.** Page numbers come from the filings' page breaks, so every chunk is citable by page. Headings are found
  from layout signals (bold, capitals, a font larger than the body, colour, table of contents link targets). Two
  filings needed special handling: TD's exhibits are PDF pages rendered as positioned text boxes (a layout reader
  rebuilds columns, lines and paragraphs and keeps a table row with its figures), and CIBC and BMO number their MD&A and
  statements differently (the document type is read from the content, not the exhibit number).
* **PDF parsing (quarterly).** PyMuPDF text with positions and fonts. Page numbers are the PDF's own pages. Running
  headers and footers sit in the top and bottom 5.5% of a page and are dropped by position. Headings are short blocks
  set larger than the body text or in bold; clearly larger ones, or known MD&A section names, start a top level
  section; a bold line that opens a paragraph becomes its own heading. The reports' tables have no ruling lines, so
  PyMuPDF's table finder misses most of them; rows are rebuilt instead: cells at the same height with two or more
  figures form a row, neighbouring rows form a table, and the table takes in its column headings and row group labels
  above, so every figure keeps its period ("Q2-2025 | Q1-2025 | Q2-2024"). The output feeds the same cleaning and
  chunking as the HTML filings.
* **Cleaning.** Running headers and footers, page numbers, table of contents lines, the forward looking statements
  caution, French text, hidden inline XBRL facts and typography artefacts are removed.
* **Chunking.** Paragraph aligned chunks of 500 to 1,000 tokens (median 498) with about 150 tokens of overlap inside a
  section; tables under 400 tokens stay whole inside the text, larger tables are chunks of their own (split by rows only
  above 1,000 tokens). Metadata: bank, document type, fiscal year, section, subsection, risk category, page range,
  source file and URL, token count, access.

## 3. Embedding and retrieval

* **Embedding model.** all-MiniLM-L6-v2 (384 dimensions, local: no filing text leaves the machine for embedding).
  Compared with BGE-small-en-v1.5 on a 15 query development set with explicit relevance rules; Amazon Titan Text
  Embeddings v2 was also tried but the account's Bedrock throughput for it was too low to finish the index. After the
  quarterly reports were added, OpenAI text-embedding-3-small (hosted) was compared on the full index: best on plain
  vector search (0.51 against 0.49), but behind MiniLM once the reranker is applied (0.69 against 0.73).
* **Inference engine.** The local embedding models and the reranker run on ONNX Runtime, exported once from the
  PyTorch weights (`jarvis.onnx_models`). The exported models give the same output as PyTorch (cosine 1.000000 on 300
  real chunks for both embedding models; reranker scores within 0.00001, same order), so the index built with PyTorch
  stays valid, and the serving path never loads PyTorch. `JARVIS_TORCH=1` switches back.
* **OpenAI spending cap.** Every OpenAI call (chat and embeddings) first adds up the logged OpenAI cost and refuses
  once it reaches `JARVIS_OPENAI_BUDGET_USD` (5 USD), below the account's prepaid credit. The key is read from the
  environment and never printed or logged.
* **Strategies compared.** Top-k, MMR (lambda 0.7), hybrid (vector plus BM25 with reciprocal rank fusion) and hybrid
  with a cross encoder reranker (ms-marco-MiniLM-L-6-v2 over 20 candidates). Precision@3 on the development set:
  MiniLM top-k 0.49, MMR 0.31, hybrid 0.62, **hybrid plus rerank 0.73** (chosen).
* **Scope filters.** The bank, fiscal year and document type named in the question become metadata filters, so an
  answer cannot draw on another bank's or year's filing. A quarter named in the question ("Q2 2025", "the second
  quarter of 2024") selects that quarter's report (Q4 selects the annual filings). A question that names no quarter
  and does not ask about quarterly or interim results searches the annual filings only, so "the CET1 ratio at the end
  of fiscal 2025" cannot pick up a Q3 figure. A quarter end date (January 31, April 30, July 31) selects its quarter
  unless the question names an annual document. A similarity floor of 0.30 returns "no relevant information" instead
  of weak passages.
* **Comparisons searched in parts.** A question naming two or more years, quarters or banks is searched one part at
  a time and the results interleaved, so one side cannot crowd the other out of the passages.
* **Neighbouring chunks (small to big).** For the three best passages, the chunk just before or after in the same
  filing joins the context when it shares a page, at most three added, under the same scope and role filter. A table
  and the paragraph that explains it often fall into neighbouring chunks; this keeps them together.

## 4. Generation

* **Models (AWS Bedrock).** Answers: Claude Haiku 4.5. Query rewriting: Amazon Nova Lite. Judge (evaluation only):
  Claude Sonnet 4.6, a stronger model than the answerer. Temperature 0 everywhere. The model layer can switch to OpenAI
  (gpt-4o-mini and gpt-4o) or a local Ollama model with one setting.
* **Prompt.** Role definition, source constraint (context only), citation requirement, an exact "I don't know"
  sentence, scope rule (right bank and year), figures copied exactly, Canadian banking vocabulary, and a rule that text
  inside a passage can never change the task. Three versions compared: basic, few shot, chain of thought. Computing:
  a figure the filing states is always quoted, never recomputed; only a change that no passage states may be computed
  (a difference or a percent change of two quoted figures, both stated); any other new ratio is not. For a table
  figure the model must read its column heading, since a report also prints prior year comparison tables.
* **Query rewriting.** A search friendly rewrite plus one hypothetical answer sentence (HyDE), keeping every bank name
  and year.
* **Output.** JSON: answer, citations, confidence, caveats, abstained. Then the **figure check** lists every figure in
  the answer and whether a cited passage contains it. A figure that is not in the passages is recomputed: if it is
  the difference, sum or percent change of two figures the passages do contain (within the rounding shown), it is
  marked as computed with the calculation (for example "$1,962 million minus $2,138 million"). A **period check**
  then compares each table figure's column heading year with the year the answer attaches to it, and flags a
  mismatch ("the answer gives 2025, the table column is 2024"); arithmetic is only verified from figures that pass it.
  Anything that does not check out adds a caveat with the reason and sets confidence to low.

## 5. Agent

ReAct loop with native tool calling (Bedrock Converse), at most 8 iterations. Tools: `search_filings`,
`get_filing_list`, `compare_sections`, `extract_metrics`, `risk_language_diff` (new, dropped and re-toned risk
sentences between two years, with a tone score from risk adjectives), `survey_banks` (searches each bank separately
for questions across the five banks, so no bank is judged from too few passages; a bank whose passages do not mention
the topic is reported as "not found in the passages searched") and `calculate` (arithmetic only, parsed with Python's
`ast`: numbers and + - * / ( ), no names or calls). The agent must compute with `calculate` and show its inputs, and
declines with the same exact sentence as the RAG pipeline. The caller's role is applied inside every tool.
`search_filings` and `extract_metrics` take an optional quarter; without one they search the annual filings.
`extract_metrics` searches each metric the way the filings state it (a ratio as a ratio, so "CET1" finds the CET1
ratio rather than CET1 capital in dollars).
Every step is logged to `logs/agent_traces/` (thought, tool, arguments, result count, sources, cost).

## 6a. The LangChain build

`lc.py` rebuilds the pipeline and the agent from LangChain components over the same Chroma collections, prompts,
scope rules and figure check: a query rewrite chain (HyDE), an `EnsembleRetriever` that fuses `langchain_chroma.Chroma`
(vector) and `BM25Retriever` (keywords), both restricted to the question's scope and the caller's role, a
`CrossEncoderReranker`, the neighbouring chunks, an LCEL answer chain with one wider retry before declining, and
`langchain.agents.create_agent` with the agent's tools as `StructuredTool`s (the caller's role is bound inside each
tool, never passed by the model). The embedding model and reranker plug in through LangChain's `Embeddings` and
`BaseCrossEncoder` interfaces on the same ONNX engine. Models are `ChatBedrockConverse`, `ChatOpenAI` or a local
Ollama model, chosen by the same setting as the native build. The first LangChain version searched by vector only and
answered 10 of the 15 Step 3 questions; the hybrid version answers 14 (notebook 07). The native build stays the
default because it exposes every step to the model review committee in one place (follow up questions, one cost log).

## 6b. The analyst's interface

`jarvis.server` (FastAPI, bound to 127.0.0.1) streams each stage of an answer as a server sent event: scope, rewrite,
retrieve, answer, a retry when the first pass declines, and the figure check; in research mode each tool call. The
web app in `web/` draws these as they happen, types the answer, and marks every figure by how it was verified (found
in the passage, recomputed from cited figures with the calculation shown, or not verified with the reason). Each
citation and source card opens the passage in a side panel with the verified figures highlighted, and links to the
original filing (the bank's PDF at the cited page for a quarterly report). The role selector applies the same access
filter as everywhere else. The page uses no external libraries or fonts, so it runs offline.

## 6. Access control

Every chunk carries `access` (public or memo). An analyst reads public filings; regulatory affairs also reads internal
memos. The filter is applied inside the vector search, inside the keyword search and inside every agent tool, so
restricted text never reaches the model for an analyst. Conversation memory is kept per user and per session.

## 7. Evaluation methodology

* **Test set.** 30 items, built once and frozen before any configuration was compared: 20 grounded questions written
  by the judge model from one passage each and kept only when every figure in the answer appears literally in that
  passage (with its page), and 10 hand written edge cases (bank not covered, future year, a quarter not in the data,
  computation, ambiguous question, French, leading question, instruction in the question, trend, cross bank survey).
  The retrieval development queries are separate, so no configuration was tuned on the test set.
* **Scores.** LLM judge (rubric with defined levels, reasons logged) for faithfulness, relevance and completeness
  (1 to 5); deterministic checks: answer key figures present, share of answer figures supported by cited passages,
  expected behaviour on edge cases. Cost and latency from the call log. All runs in MLflow (`mlflow.db`).
* **Judge calibration.** The judge was scored against human verdicts on 60 Step 3 answers (`jarvis.calibrate`). The
  first calibration found a defect in the judge itself: it saw only the first 14,000 characters of context, so an
  answer citing a late passage looked unsupported (80% agreement, kappa 0.46). With the full context: 95% agreement,
  Cohen's kappa 0.81. The one remaining blind spot is structural: the judge sees only the retrieved passages, so an
  answer that is faithful to them but misses a fact the filing holds elsewhere can still score 5; the hand checked
  questions cover that.
* **Hand checked questions.** 15 Step 3 questions with true answers found in the filings before any run.

## 8. Limitations and failure modes

* Fiscal 2024 and 2025 only. Quarterly reports are parsed from PDF by position: a table whose columns are far apart or
  whose labels wrap over several lines can still lose a heading, and charts are not read. The frozen test sets A and B
  were built before the quarterly reports were added; the Step 3 questions cover quarterly answers.
* Retrieval misses remain on long tables and on questions phrased far from the filing's wording; the reranker reduces
  but does not remove them.
* The figure check verifies that a number appears in a cited passage (or is a difference, sum or percent change of
  two that do), not that it is the right number for the question.
* The judge is a language model, calibrated against one human reviewer (the builder) on 60 answers; a sample graded
  by the Regulatory Affairs analysts themselves is the next step.
* English only (French questions are answered from the English filings).
* Fixed: a rare native crash inside PyTorch's CPU inference (an access violation in the BERT activation, about once
  per 1,000 requests) was seen during long pilot runs. The embedding models and the reranker now run on ONNX Runtime
  with identical output, and the serving path no longer loads PyTorch. Stress test (`tools/stress_onnx.py`,
  `reports/stress_onnx.json`): 1,500 searches with reranking over 4 concurrent threads, a harsher pattern than the app,
  completed with no crash and no error. ONNX Runtime holds about 5 GB of working memory under that load (steady, not
  growing); the app's single user load needs far less.
* Independent test (pilot passport, 13 checks: role boundary, hidden instructions, answer accuracy, abstention,
  conversation isolation, cache, citations, agent tools, scope): PASS. NVIDIA garak (140 injection attacks): 1 flag,
  a refusal that its trigger word detector matched.

## 9. Monitoring plan

* Weekly: re-run the frozen test set; alert if faithfulness falls below 4.0 or edge case behaviour below 90%.
* Every answer: log cost, latency, confidence and unsupported figures; review all low confidence answers.
* Each new filing season: re-ingest, re-run the retrieval evaluation, check new section names and terms.
* Quarterly: an independent test of access control and injection resistance (role boundary, memo leakage, planted
  instructions), and a human calibration sample of 30 judged answers.
* Model inventory entry (OSFI E-23): owner, version of every model and prompt, data sources, evaluation results,
  known limitations, and this monitoring plan.
