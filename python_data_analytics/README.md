# Python Data Analytics

Two analytics projects that start from a raw file nobody has looked at properly and end
with something a business person can act on. One works at regulatory scale, the other at
small-business scale, and between them they cover the whole Python analytics toolchain:
profiling, cleaning, feature engineering, a SQL warehouse, segmentation, and reporting.

| | [Consumer Complaint Intelligence](consumer_complaints_analysis/) | [Retail Intelligence Engine](retail_data_wrangling/) |
|---|---|---|
| **Question** | Which financial institutions generate the most consumer pain, and is it getting better? | Who are this shop's best customers, and which ones are quietly leaving? |
| **Data** | U.S. CFPB Consumer Complaint Database — 1.28M complaints, 5,275 companies, Dec 2011 – May 2019 | London Gift Shop UK transactions (Online Retail II) |
| **Stack** | Pandas, NumPy, Plotly, Jupyter | Pandas, PostgreSQL, Jupyter, HTML reporting |
| **Output** | Market concentration, product mix shift, and a multi-dimension accountability scorecard | Monthly sales and cancellation trends, customer lifecycle, RFM segments |

## 1. Consumer Complaint Intelligence

Profiles a regulator's public complaint database to see which institutions and products
generate the most consumer harm, and how that has moved over eight years.

The interesting part is not the volume ranking — it is that raw counts are misleading,
because a bank with more customers will naturally attract more complaints. The analysis
engineers time-series, lag, and company-tier features so firms are compared fairly, then
scores them on a seven-dimension accountability scorecard rather than a single number.
Results were validated against the CFPB's own published statistics, and the notebook
documents what a Spark/Databricks migration would look like once the dataset outgrows a
single machine.

**Note:** the raw Kaggle CSV is deliberately not committed. See
[`consumer_complaints_analysis/data/README.md`](consumer_complaints_analysis/data/README.md)
for the download step and the `DATA_PATH` variable to set.

## 2. Retail Intelligence Engine

Turns a long, messy transaction history into the handful of decisions a small retailer
actually has to make: who to reward, who to win back, and when to stock up.

Transactions are loaded into a PostgreSQL warehouse, cleaned, then analysed for monthly
sales and cancellation trends, new-versus-returning revenue, and customer lifecycle.
The centrepiece is **RFM segmentation** — scoring every customer on how recently they
bought, how often, and how much — which converts an undifferentiated customer list into
groups worth treating differently. Cancellation spikes are investigated as an operational
signal rather than written off as noise. Output is an HTML dashboard that opens in a
browser with no environment to set up.

## Layout

```text
python_data_analytics/
├── consumer_complaints_analysis/
│   ├── notebooks/          ← CFPB_V2.ipynb (current), Consumer-Complaints_DA.ipynb (first pass)
│   ├── reports/            ← Complaint_Signal_Equifax.pdf
│   ├── data/               ← download instructions; the raw CSV is not committed
│   ├── src/                ← reusable helpers as notebook code is refactored out
│   └── requirements.txt
└── retail_data_wrangling/
    ├── retail_data_analytics_wrangling.ipynb
    ├── psql/               ← retail.sql (schema + load), data_explore.sql
    ├── data/               ← online_retail_II.xlsx
    ├── retail_dashboard_report.py
    └── retail_dashboard_report.html
```

## Running them

```bash
# Consumer complaints
cd consumer_complaints_analysis
pip install -r requirements.txt
# download the Kaggle CSV into data/, set DATA_PATH in the notebook, then:
jupyter notebook notebooks/CFPB_V2.ipynb

# Retail
cd retail_data_wrangling
psql -h localhost -U postgres -d retail -f psql/retail.sql
jupyter notebook retail_data_analytics_wrangling.ipynb
python retail_dashboard_report.py        # regenerates the HTML dashboard
```

Each sub-project has its own README with the full write-up.
