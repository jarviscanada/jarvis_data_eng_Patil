"""Write notebooks/01 to 07 (the brief's six deliverables and the LangChain build). Each explains its step and calls the project code in src/jarvis,
so the notebooks and the application never diverge. Execute them with:

    python tools/make_notebooks.py && jupyter nbconvert --to notebook --execute --inplace notebooks/*.ipynb
"""

from pathlib import Path

import nbformat as nbf

ROOT = Path(__file__).resolve().parents[1]
SETUP = ("import sys, json, pandas as pd\nsys.path.insert(0, '../src')\n"
         "pd.set_option('display.max_colwidth', 120)")
BOOKS = {
    "01_data_ingestion": [
        ("md", "# Step 1: Data ingestion and chunking\nThe Big Five banks file their annual report (MD&A and audited "
               "statements) and Annual Information Form with the SEC on Form 40-F. We download the fiscal 2024 and "
               "2025 filings from SEC EDGAR (`jarvis.download`), then parse them (`jarvis.ingest`): page numbers from the "
               "filings' own page breaks, headings from layout signals, tables kept whole, boilerplate removed, "
               "chunks of 500 to 1,000 tokens with about 150 tokens of overlap inside a section."),
        ("code", SETUP),
        ("code", "index = pd.read_csv('../data/processed/filing_index.csv')\nindex"),
        ("code", "chunks = pd.read_json('../data/processed/chunks.jsonl', lines=True)\n"
                 "print(len(chunks), 'chunks,', chunks.tokens.sum(), 'tokens')\n"
                 "chunks.groupby(['bank', 'document_type']).agg(chunks=('chunk_id', 'count'), tokens=('tokens', 'sum'))"),
        ("md", "## Token analysis and estimated embedding cost\nTitan Text Embeddings v2 costs about $0.02 per million "
               "tokens; the local models are free."),
        ("code", "tok = chunks.tokens.sum()\nprint(f'{tok:,} tokens -> Titan v2 about ${tok / 1e6 * 0.02:.2f}; OpenAI "
                 "text-embedding-3-small about ${tok / 1e6 * 0.02:.2f}')"),
        ("code", "import matplotlib.pyplot as plt\nfig, ax = plt.subplots(1, 2, figsize=(13, 4))\n"
                 "chunks[chunks.chunk_type == 'text'].tokens.hist(bins=40, ax=ax[0]); ax[0].set_title('Text chunk tokens')\n"
                 "chunks.groupby(['bank', 'document_type']).size().unstack().plot.bar(stacked=True, ax=ax[1])\n"
                 "ax[1].set_title('Chunks per bank and document'); plt.tight_layout()"),
        ("code", "chunks[['chunk_id', 'section', 'risk_category', 'page', 'tokens']].sample(8, random_state=1)"),
        ("md", "Two filings needed special handling: TD's exhibits are PDF pages converted to positioned HTML boxes "
               "(a layout reader rebuilds columns, lines and paragraphs), and CIBC and BMO number their MD&A and "
               "statements the other way round (the document type is read from the content, not the exhibit number)."),
        ("md", "## Quarterly Reports to Shareholders (PDF)\nThe brief also asks for the quarterly reports. "
               "`jarvis.download_quarterly` fetches the Q1 to Q3 reports for fiscal 2024 and 2025 from each bank's "
               "investor relations site (30 PDFs; Q4 is covered by the annual report), with a manifest of URL, size "
               "and sha256. `jarvis.ingest_pdf` reads them with PyMuPDF and feeds the same cleaning and chunking: "
               "running headers and footers are dropped by position, headings come from font size and weight, and "
               "tables (which have no ruling lines in these reports) are rebuilt from positions: lines at the same "
               "height with two or more figures form a row, and neighbouring rows, column headers and wrapped labels "
               "form one table."),
        ("code", "qman = pd.read_json('../data/raw/quarterly/manifest.json')\n"
                 "qman[['bank', 'fiscal_year', 'quarter', 'size', 'url']].head(6)"),
        ("code", "qindex = pd.read_csv('../data/processed/filing_index_quarterly.csv')\n"
                 "qindex.pivot_table(index='bank', columns=['fiscal_year', 'quarter'], values='chunks')"),
        ("code", "qchunks = pd.read_json('../data/processed/chunks_quarterly.jsonl', lines=True)\n"
                 "print(len(qchunks), 'quarterly chunks,', qchunks.tokens.sum(), 'tokens;', len(chunks) + len(qchunks), "
                 "'chunks in all')\nqchunks.chunk_type.value_counts()"),
        ("md", "A table rebuilt from a PDF page (BMO, Q2 2025, page 6): the column headings stay with their figures."),
        ("code", "t = qchunks[(qchunks.filing_id == 'BMO_2025_Q2') & (qchunks.text.str.contains('Q2-2025'))].iloc[0]\n"
                 "print(t.section, '| page', t.page)\nprint(t.text[:900])"),
    ],
    "02_embedding_vectordb": [
        ("md", "# Step 2: Embeddings and the vector store\nThree embedding models over the same 4,300 chunks in ChromaDB, "
               "with metadata (bank, document type, fiscal year, section, risk category, page, access). Retrieval "
               "strategies: top-k, MMR, hybrid (vector plus BM25, reciprocal rank fusion) and hybrid with a cross "
               "encoder reranker. The bank and fiscal year are read from the question and applied as filters."),
        ("code", SETUP),
        ("code", "res = json.load(open('../reports/retrieval_eval.json'))\n"
                 "pd.DataFrame([{'config': k, **{m: v[m] for m in ('precision_at_k', 'hit_at_1', 'right_filing')}} "
                 "for k, v in res['results'].items()]).sort_values('precision_at_k', ascending=False)"),
        ("md", "Relevance is decided by an explicit rule per query (right bank, right year, the metric named in the "
               "passage), printed below, so the precision figures can be checked by anyone."),
        ("code", "pd.DataFrame(res['rules'], columns=['query', 'bank', 'year', 'relevant if passage matches'])"),
        ("code", "from jarvis.retrieve import Retriever, scope_of\nr = Retriever('minilm')\n"
                 "q = \"What was RBC's CET1 ratio at the end of fiscal 2025?\"\nprint(scope_of(q))\n"
                 "pd.DataFrame(r.search(q, strategy='hybrid', k=5))[['bank', 'fiscal_year', 'document_type', 'section', "
                 "'page', 'similarity']]"),
        ("md", "## Local against hosted embeddings, after the quarterly reports were added\nThe same 15 queries over "
               "the full index (annual and quarterly), with OpenAI text-embedding-3-small beside the two local models. "
               "OpenAI is a little better on plain vector search, but with the cross encoder reranker the free local "
               "MiniLM still leads, so it stays the default (and no filing text leaves the machine for indexing). "
               "Indexing the 5.4M tokens with OpenAI cost about $0.11."),
        ("code", "v2 = json.load(open('../reports/retrieval_eval_v2.json'))\n"
                 "t = pd.DataFrame([{'model': k.split('/')[0], 'strategy': k.split('/')[1], 'precision_at_3': "
                 "v['precision_at_k'], 'hit_at_1': v['hit_at_1']} for k, v in v2['results'].items()])\n"
                 "t.pivot(index='strategy', columns='model', values='precision_at_3').round(2)"),
        ("md", "Metadata filtering: the same question with and without the scope filter."),
        ("code", "from jarvis.retrieve import Scope\npd.DataFrame(r.search('credit risk exposure commercial real estate', "
                 "strategy='topk', k=5, scope=Scope(['RBC'], [], [])))[['bank', 'fiscal_year', 'section', 'page']]"),
    ],
    "03_rag_pipeline": [
        ("md", "# Step 3: The RAG pipeline\nQuestion, scope from the question, query rewriting, hybrid retrieval, a "
               "prompt with numbered passages, a JSON answer with citations, then a figure check: every number in the "
               "answer must appear in a cited passage."),
        ("code", SETUP),
        ("code", "from jarvis.rag import RAG\nrag = RAG()\nout = rag.answer(\"What was RBC's CET1 ratio at the end of "
                 "fiscal 2025?\")\n{k: out[k] for k in ('answer', 'confidence', 'caveats', 'figure_check', 'sources')}"),
        ("code", "out = rag.answer(\"What was Laurentian Bank's provision for credit losses in fiscal 2025?\")\nout['answer']"),
        ("code", "out = rag.answer(\"What was BMO's net income in Q2 2025 compared with Q1 2025?\")\n"
                 "print(out['scope'])\n{k: out[k] for k in ('answer', 'figure_check', 'sources')}"),
        ("md", "## The 15 compliance questions (Step 3)\nAll five banks, three questions each, across credit, market, "
               "liquidity, operational, climate and capital risk, annual and quarterly. The true answer to each was "
               "located in the filing by hand **before** any run, with its pages (`reports/step3_questions.json`). "
               "For each answer we record the retrieved chunks, the answer, the cited pages, whether the key figure "
               "is present and whether a citation lands on a page holding the truth; then each answer was read "
               "against its truth and cited passages and given a manual verdict (`reports/step3_review.json`)."),
        ("code", "qs = pd.DataFrame(json.load(open('../reports/step3_questions.json')))\n"
                 "qs[['id', 'bank', 'risk', 'period', 'question', 'truth', 'where']]"),
        ("code", "res = pd.DataFrame(json.load(open('../reports/step3_results.json')))\n"
                 "rev = pd.DataFrame(json.load(open('../reports/step3_review.json'))['reviews'])\n"
                 "CFG = 'native:cot+v5'   # the final configuration; earlier runs are compared below\n"
                 "best = res[res.config == CFG].merge(rev[rev.config == CFG], on=['id', 'config'])\n"
                 "best['retrieved'] = best.retrieved.map(lambda ids: ', '.join(i.split('#')[0] + '#' + i.split('#')[1] "
                 "for i in ids[:3]) + ' ...')\n"
                 "best[['id', 'answer', 'retrieved', 'key_found', 'cites_truth_page', 'verdict', 'citations_accurate', "
                 "'note']]"),
        ("code", "acc = (best.verdict == 'correct').mean()\npart = (best.verdict == 'partly correct').mean()\n"
                 "cit = best.citations_accurate.mean()\n"
                 "print(f'Accuracy (manual): {acc:.0%} correct, {part:.0%} partly correct; citations accurate: {cit:.0%}')"),
        ("md", "### Failure analysis\nThe final configuration answers all 15 correctly. Each earlier run's failures led "
               "to one logged mechanism fix: a quarter named by its end date (scope rule), and a table separated from "
               "the paragraph that explains it (neighbouring chunks)."),
        ("code", "progress = rev.groupby('config', sort=False).verdict.apply(lambda v: f\"{(v == 'correct').sum()} of "
                 "{len(v)} correct\")\nprogress[[c for c in ('native:cot', 'native:cot+datefix', 'native:cot+v4', 'native:cot+v5') "
                 "if c in progress.index]]"),
        ("code", "first = rev[rev.config.isin(['native:cot', 'native:cot+datefix'])]\n"
                 "first[first.verdict != 'correct'][['config', 'id', 'verdict', 'note']]"),
    ],
    "04_prompt_optimization": [
        ("md", "# Step 4: Prompt optimization and structured output\nThree prompts (basic, few shot, chain of thought "
               "with citation enforcement) on the same questions, JSON output, query rewriting with HyDE, edge cases."),
        ("code", SETUP),
        ("code", "from jarvis.rag import PROMPTS\nfor k, v in PROMPTS.items():\n    print('=' * 20, k, len(v), "
                 "'characters')\nprint(PROMPTS['cot'])"),
        ("code", "ev = json.load(open('../reports/evaluation_results.json'))\npd.DataFrame([{k: v[k] for k in ('config', "
                 "'faithfulness', 'relevance', 'completeness', 'key_figures_present', 'edge_behaviour_ok', "
                 "'usd_per_query')} for v in ev.values()])"),
        ("code", "edge = pd.DataFrame(ev['best']['rows'])\nedge[edge.type == 'edge'][['id', 'question', 'answer', "
                 "'behaviour_ok']]"),
        ("md", "## The three prompts on the same 15 questions from Step 3\nAccuracy and citation quality per prompt, "
               "from the manual review."),
        ("code", "res = pd.DataFrame(json.load(open('../reports/step3_results.json')))\n"
                 "rev = pd.DataFrame(json.load(open('../reports/step3_review.json'))['reviews'])\n"
                 "m = res.merge(rev, on=['id', 'config'])\n"
                 "m.groupby('config').agg(correct=('verdict', lambda v: (v == 'correct').sum()), "
                 "partly=('verdict', lambda v: (v == 'partly correct').sum()), "
                 "citations_accurate=('citations_accurate', 'sum'), cites_truth_page=('cites_truth_page', 'sum'), "
                 "answered=('abstained', lambda a: (~a).sum()))"),
    ],
    "05_agentic_workflow": [
        ("md", "# Step 5: The agent\nA ReAct loop with native tool calling and seven tools: search_filings, "
               "get_filing_list, compare_sections, extract_metrics, risk_language_diff (new, dropped and re-toned "
               "risk sentences between two years), survey_banks (each bank searched separately for questions across "
               "banks) and calculate (safe arithmetic, so computed figures show their inputs). The user's role is applied inside every tool; every step is "
               "logged."),
        ("code", SETUP),
        ("code", "from jarvis.agent import Agent\nag = Agent()\nQS = [\"What new risks did RBC add in 2025 that were not "
                 "in 2024?\", \"How does TD's credit risk language compare to BMO's in their most recent annual reports?\","
                 " \"Which of the Big Five banks has the most detailed climate risk disclosure?\", \"How did Scotiabank's "
                 "provision for credit losses change from fiscal 2024 to fiscal 2025?\", \"Which banks mention AI risk or "
                 "OSFI E-23 in their most recent filings?\"]\nruns = [ag.run(q) for q in QS]"),
        ("code", "pd.DataFrame([{'question': r['question'], 'iterations': r['iterations'], 'tools': [t['tool'] for t in "
                 "r['tool_calls']], 'usd': r['usd'], 'seconds': r['seconds']} for r in runs])"),
        ("code", "for r in runs:\n    print('#', r['question'])\n    print(r['answer'][:1500], '\\n')"),
    ],
    "06_evaluation": [
        ("md", "# Step 6: Evaluation\nA frozen 30 question test set (20 grounded questions whose answers were checked "
               "against their source passage, 10 edge cases). The judge is a stronger model than the answerer, at "
               "temperature 0, with a rubric. Deterministic checks sit beside it. All runs are tracked in MLflow."),
        ("code", SETUP),
        ("code", "ts = json.load(open('../reports/testset.json'))\npd.DataFrame(ts['items'])[['id', 'type', 'question', "
                 "'expect']]"),
        ("code", "ev = json.load(open('../reports/evaluation_results.json'))\ntable = pd.DataFrame([{k: v[k] for k in "
                 "('config', 'faithfulness', 'relevance', 'completeness', 'key_figures_present', 'figures_supported', "
                 "'edge_behaviour_ok', 'usd_per_query', 'median_ms')} for v in ev.values()])\ntable"),
        ("code", "for name, v in ev.items():\n    print(name, 'hallucinations (faithfulness <= 2):', v['hallucinations'])"),
        ("code", "cost = table.set_index('config').usd_per_query\n(cost * 1000 * 365).rename('USD per year at 1,000 "
                 "queries a day')"),
        ("md", "## Set B after the quarterly reports were added, and on OpenAI\nThe first run after the change found a "
               "scope regression (one question sent to the Q1 reports by a date); after the fix two identical runs "
               "differ by about one item in twenty, which is the run to run spread. The OpenAI run (gpt-4o-mini, "
               "judged by gpt-4o) uses a different judge, so it compares only roughly."),
        ("code", "runs = {'set B, original': 'evaluation_results_b.json', 'after change, first run': "
                 "'evaluation_results_b_v3.json', 'after fix, run 1': 'evaluation_results_b_v3_run1.json', "
                 "'after fix, run 2': 'evaluation_results_b_v3_run2.json', 'OpenAI': 'evaluation_results_b_openai.json'}\n"
                 "pd.DataFrame([{'run': n, **{k: json.load(open('../reports/' + f))['best_v2'][k] for k in "
                 "('faithfulness', 'relevance', 'completeness', 'key_figures_present', 'edge_behaviour_ok', "
                 "'usd_per_query')}} for n, f in runs.items()])"),
        ("code", "rows = {n: {r['id']: r['key_figures_present'] for r in json.load(open('../reports/' + f))['best_v2']"
                 "['rows'] if r['id'].startswith('G')} for n, f in runs.items() if n != 'OpenAI'}\n"
                 "k = pd.DataFrame(rows)\nk[k.nunique(axis=1) > 1]"),
        ("md", "## The final design (v4, v5)\nv4: neighbouring chunks, verified computations, the agent's survey and "
               "calculator tools, and the judge with its full context (see calibration below). v5 adds comparison "
               "searches in parts, the period check on table figures and the quote rule. Set A, on which none of "
               "these changes were made, is the cleanest test of v5."),
        ("code", "v4 = {'v1 best, set A': ('evaluation_results.json', 'best'), 'v5, set A': "
                 "('evaluation_results_a_v5.json', 'best_v2'), 'v4 run 1, set B': ('evaluation_results_b_v4_run1.json', "
                 "'best_v2'), 'v4 run 2, set B': ('evaluation_results_b_v4_run2.json', 'best_v2'), 'v5, set B': "
                 "('evaluation_results_b_v5.json', 'best_v2'), 'agent v4, set B': ('evaluation_results_b_v4_agent.json', "
                 "'agent')}\npd.DataFrame([{'run': n, **{k: json.load(open('../reports/' + f))[c][k] for k in "
                 "('faithfulness', 'relevance', 'completeness', 'key_figures_present', 'edge_behaviour_ok', "
                 "'usd_per_query', 'median_ms')}} for n, (f, c) in v4.items()])"),
        ("md", "## Judge calibration against human verdicts\nThe judge scored 60 Step 3 answers that a person had "
               "already graded against the hand located truth. The first calibration exposed a defect in the judge: "
               "it saw only the first 14,000 characters of context, so answers citing late passages looked "
               "unsupported. With the full context it agrees with the person on 95% of answers (Cohen's kappa 0.81)."),
        ("code", "cal = json.load(open('../reports/judge_calibration.json'))['summary']\n"
                 "old = json.load(open('../reports/judge_calibration_14k.json'))\n"
                 "print('before the fix (14,000 characters): agreement', round(sum(r['human_pass'] == r['judge_pass'] "
                 "for r in old['rows']) / len(old['rows']), 2))\n"
                 "print('after: agreement', cal['agreement'], 'kappa', cal['kappa'])\npd.Series(cal['table'])"),
        ("code", "pd.DataFrame(cal['disagreements'])[['id', 'config', 'human', 'faithfulness', 'relevance', "
                 "'completeness', 'reason']]"),
    ],
    "07_langchain": [
        ("md", "# The same system in LangChain\nThe module builds with LangChain. `rag.py` and `agent.py` are written "
               "without a framework so every step is visible; `jarvis.lc` rebuilds both from LangChain components over "
               "the same Chroma collections, prompts, scope rules and figure check:\n\n"
               "* retrieval: an `EnsembleRetriever` fusing `langchain_chroma.Chroma` (vector) and `BM25Retriever` "
               "(keywords), both inside the question's scope and the caller's role, then `CrossEncoderReranker` and "
               "the neighbouring chunks\n* chain (LCEL): rewrite | retrieve | prompt | chat model | retry once if "
               "declined | JSON | figure check\n* engines: the embedding model and reranker on ONNX Runtime through "
               "LangChain's `Embeddings` and `BaseCrossEncoder` interfaces\n"
               "* agent: `langchain.agents.create_agent` with the agent's tools as `StructuredTool`s, the role bound inside "
               "each tool\n* models: `ChatBedrockConverse`, `ChatOpenAI` or local Ollama, chosen by `JARVIS_PROVIDER`"),
        ("code", SETUP),
        ("code", "from jarvis.lc import LCRAG, lc_agent\nlc = LCRAG()\n"
                 "out = lc.answer(\"What was TD's provision for credit losses in Q2 2025?\")\n"
                 "{k: out[k] for k in ('answer', 'confidence', 'figure_check', 'sources', 'ms')}"),
        ("md", "## LangChain against the native build on the Step 3 questions\nSame 15 questions, same prompt "
               "(chain of thought), manual verdicts. The first LangChain chain searched by vector only and missed table "
               "rows (10 of 15); with BM25 keywords fused in an EnsembleRetriever, the rewrite, the neighbouring chunks "
               "and the retry, it reaches 14 of 15."),
        ("code", "res = pd.DataFrame(json.load(open('../reports/step3_results.json')))\n"
                 "rev = pd.DataFrame(json.load(open('../reports/step3_review.json'))['reviews'])\n"
                 "m = res.merge(rev, on=['id', 'config'])\n"
                 "m = m[m.config.isin(['native:cot+v5', 'langchain:cot', 'langchain:cot+v4'])]\n"
                 "m.pivot(index='id', columns='config', values='verdict')"),
        ("code", "m.groupby('config').agg(correct=('verdict', lambda v: (v == 'correct').sum()), "
                 "citations_accurate=('citations_accurate', 'sum'))"),
        ("md", "## The LangChain agent\nThe same question through both agents; the audit trail lists every tool call."),
        ("code", "q = 'Compare the CET1 ratios of RBC and TD at the end of fiscal 2025.'\na = lc_agent(q)\n"
                 "print(a['answer'][:1200])\npd.DataFrame(a['tool_calls'])"),
        ("md", "Why the native build stays the default: on the same questions it scores 15 of 15 against 14 (the "
               "LangChain chain once quoted PCL on loans as total PCL), and it exposes every step to the model review "
               "committee in one place (follow up questions, one cost log). The LangChain build shows the same design "
               "in the framework the module teaches and switches provider with one setting."),
    ],
}


def main() -> None:
    out = ROOT / "notebooks"
    out.mkdir(exist_ok=True)
    for name, cells in BOOKS.items():
        nb = nbf.v4.new_notebook()
        nb.cells = [nbf.v4.new_markdown_cell(c) if k == "md" else nbf.v4.new_code_cell(c) for k, c in cells]
        nbf.write(nb, out / f"{name}.ipynb")
    print(f"{len(BOOKS)} notebooks in {out}")


if __name__ == "__main__":
    main()
