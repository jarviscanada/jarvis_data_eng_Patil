# Jarvis Research Assistant: Canadian Bank Annual Report Research Agent

A RAG and agent system over the Big Five Canadian banks' fiscal 2024 and 2025 filings (Annual Information Forms,
MD&A, audited financial statements) and their Q1 to Q3 quarterly Reports to Shareholders, built to the Module 4
capstone brief (GenAI module, Jarvis Consulting).

Built with AI pair programming (Claude Code): the design, the evaluation and every result in `reports/` were directed
and reviewed by the author; the 15 Step 3 answers were checked by hand against the filings.

## What it does

* Answers analyst questions with citations to bank, document, period (fiscal year or quarter) and **page**.
* Reads the bank, fiscal year and quarter out of the question and searches only those filings, so an answer cannot
  borrow another bank's, year's or quarter's figure. A question that names no quarter searches the annual filings.
* Checks every figure in an answer against the passage it cites: a figure must be in the passage, in the column of
  the year the answer gives it, or be a difference or percent change of two cited figures (the calculation shown);
  anything else lowers the confidence and adds a caveat with the reason.
* Compares filings across years and banks with an agent (search, list, compare, extract metrics, a per bank survey,
  a safe calculator, and a **risk language diff** that finds new, dropped and re-toned risk sentences).
* Applies role based access inside the retriever and inside every agent tool (analysts: public filings; regulatory
  affairs: also internal memos).
* Logs every model call (tokens, cost, latency) and every agent step (the audit trail E-23 asks for).
* Ships twice: a framework free build (`rag.py`, `agent.py`) where every step is visible, and the same design in
  **LangChain** (`lc.py`: an EnsembleRetriever of Chroma and BM25, a cross encoder reranker, an LCEL chain and
  `create_agent`).

## Reproduce end to end

```bash
python -m venv .venv
.venv/Scripts/python -m pip install torch --index-url https://download.pytorch.org/whl/cpu
.venv/Scripts/python -m pip install beautifulsoup4 lxml pymupdf onnx chromadb sentence-transformers rank-bm25 tiktoken pandas matplotlib seaborn mlflow "boto3" "botocore[crt]" streamlit jupyter nbformat nbconvert langchain langchain-aws langchain-openai langchain-chroma langchain-huggingface langchain-community
```

1. **Data.** Put `SEC_USER_AGENT=<name> <contact email>` in `.env.local` (SEC fair access policy), then
   `python -m jarvis.download` (28 annual filings, about 160 MB, into `data/raw/edgar`) and
   `python -m jarvis.download_quarterly` (30 quarterly PDFs, about 67 MB, from the banks' own sites, into
   `data/raw/quarterly`).
2. **Parse and chunk.** `python -m jarvis.ingest` (annual, HTML) and `python -m jarvis.ingest_pdf` (quarterly, PDF)
   write `data/processed/chunks*.jsonl`, the filing indexes and the cleaned text.
3. **Index.** `python -m jarvis.index --model minilm bge-small` (add `titan` or `openai` for the hosted comparison),
   then `python -m jarvis.onnx_models export` and `check`: the local models run on ONNX Runtime from then on
   (identical output, no PyTorch at serving time; `tools/stress_onnx.py` is the concurrency test).
4. **Retrieval evaluation.** `python -m jarvis.retrieval_eval --models minilm bge-small`.
5. **Step 3 questions.** `python -m jarvis.step3` (15 questions with hand located truths, every prompt and the
   LangChain build; manual verdicts in `reports/step3_review.json`).
6. **Test set (once).** `python -m jarvis.testset` (frozen in `reports/testset.json`).
7. **Evaluation.** `python -m jarvis.evaluate` (results in `reports/evaluation_results*.json`, runs in `mlflow.db`),
   and `python -m jarvis.calibrate` (the judge against the human verdicts on the Step 3 answers).
8. **Notebooks.** `python tools/make_notebooks.py` then `jupyter nbconvert --to notebook --execute --inplace notebooks/*.ipynb`.
9. **Demo.** `python -m jarvis.server`, then open http://127.0.0.1:8600: the Jarvis web app (the pipeline drawn live
   as it runs, figures marked by how they were verified, every citation opening its passage). The Streamlit version
   is `streamlit run app.py --server.address 127.0.0.1`.

All commands run from the repository root with `PYTHONPATH=src`. Models come from AWS Bedrock (the profile named
by `JARVIS_AWS_PROFILE` in the environment or `.env.local`, else AWS's default credentials; `us-east-1`): set `JARVIS_PROVIDER=openai` (needs `OPENAI_API_KEY`) or `ollama` to switch providers, for both builds.

## Layout

```
src/jarvis/   download, download_quarterly, ingest, ingest_pdf, index, onnx_models, retrieve, llm, rag, agent,
              lc (LangChain), server (web app API), step3, testset, evaluate, calibrate, retrieval_eval, extra_docs
notebooks/    01 to 06, one per step of the brief; 07 the LangChain build
reports/      executive_summary.md, system_documentation.md, evaluation_report.md, evaluation data
web/          the Jarvis web app (index.html, style.css, app.js; no external libraries), served by jarvis.server
app.py        the Streamlit demo
data/, models/, mlruns/, logs/   generated, not committed
```
