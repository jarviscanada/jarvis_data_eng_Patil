# Introduction

London Gift Shop (LGS) is a UK-based online retailer specializing in unique all-occasion giftware. Despite having a large transaction history dating back to 2009, LGS lacks internal data analytics capability to extract meaningful business insights from their data. They are unable to identify trends, understand customer behavior, or make data-driven decisions to grow revenue.

This project addresses that gap by building a data analytics pipeline that ingests LGS transactional data, stores it in a PostgreSQL data warehouse, and performs exploratory and behavioral analysis using Python. The results help LGS understand sales trends, customer activity, and customer value — enabling their marketing team to design targeted campaigns and improve retention.

LGS can use the analytic results to:
- Identify high-value customers using RFM segmentation and target them with loyalty programs
- Re-engage at-risk or hibernating customers with win-back promotions
- Understand monthly sales trends to plan inventory and marketing spend
- Track new vs existing user growth to evaluate acquisition campaign effectiveness
- Monitor canceled orders to identify fulfillment or product quality issues

**Technologies used:** Python, Jupyter Notebook, Pandas, Matplotlib, NumPy, PostgreSQL, SQLAlchemy, psycopg2, Docker

# Implementation

## Project Architecture

The architecture consists of the following components:

- **LGS Web App (Microsoft SQL Server):** The source OLTP system capturing all retail transactions in real time
- **Data Export:** The LGS IT team exports transactional data into a PostgreSQL dump file and an Excel file
- **Jarvis Data Warehouse (PostgreSQL):** A PostgreSQL instance provisioned via Docker that serves as the OLAP data warehouse storing the full retail dataset for analytical queries
- **Jupyter Notebook (Python):** The analytics environment where data is loaded, cleaned, transformed, and analyzed using Pandas and Matplotlib
- **Docker Bridge Network (jarvis-net):** Connects the Jupyter and PostgreSQL containers so the notebook can query the warehouse directly using the container hostname

```
+-------------------------+
|  LGS Web App            |
|  (MSSQL OLTP)           |
+-------------------------+
           |
           | Data Export (SQL dump / XLSX)
           v
+-------------------------+
|  PostgreSQL             |
|  Data Warehouse         |
|  (Docker: jarvis-psql)  |
+-------------------------+
           |
           | pandas.read_sql / read_excel
           v
+-------------------------+
|  Jupyter Notebook       |
|  (Docker: jupyter)      |
|  Python, Pandas,        |
|  Matplotlib             |
+-------------------------+
           |
           | Analytics Output
           v
+-------------------------+
|  Charts, RFM Table,     |
|  Business Insights      |
+-------------------------+
```

## Data Analytics and Wrangling

The full analytics notebook can be found here: [retail_data_analytics_wrangling.ipynb](./retail_data_analytics_wrangling.ipynb)

The notebook covers the following analyses:

- **Data Preparation:** Loading data from PostgreSQL and Excel, renaming columns to snake_case, casting data types
- **Invoice Amount Distribution:** Visualizing the full distribution and filtered 85th percentile distribution with min, max, mean, median, and mode stats
- **Monthly Placed and Canceled Orders:** Tracking order volumes and cancellation trends over time
- **Monthly Sales:** Visualizing total revenue per month to identify seasonal trends
- **Monthly Sales Growth:** Computing month-over-month percentage growth to identify acceleration and decline periods
- **Monthly Active Users:** Tracking unique customer counts per month
- **New vs Existing Users:** Identifying customer acquisition vs retention trends monthly
- **RFM Analysis:** Scoring every customer on Recency, Frequency, and Monetary value
- **RFM Segmentation:** Categorizing customers into 10 segments (Champions, Loyal Customers, At Risk, Hibernating, etc.)

### How the data helps LGS increase revenue

**1. RFM Segmentation — Targeted Marketing**
By scoring every customer on RFM dimensions, LGS can segment their customer base and take targeted action:
- Reward Champions and Loyal Customers with VIP offers and early access
- Send win-back campaigns to At Risk and Hibernating customers
- Nurture Potential Loyalists with personalized product recommendations

**2. Seasonal Sales Planning**
Monthly sales and growth charts reveal seasonal peaks such as the Q4 holiday surge. LGS can use this to time inventory procurement and promotional campaigns ahead of high-demand periods to maximize revenue.

**3. Customer Acquisition vs Retention**
New vs existing user trends show whether growth is driven by acquisition or retention. A consistent drop in new users signals a need for acquisition campaigns, while a drop in existing users signals a retention problem requiring loyalty incentives.

**4. Reducing Cancellations**
Tracking monthly canceled orders helps LGS identify months with unusually high cancellation rates, prompting investigation into fulfillment delays or product quality issues that may be hurting revenue.

# Improvements

1. **Automate the data pipeline:** Currently data is loaded manually via SQL dump or Excel file. Given more time, I would build an automated ETL pipeline using Apache Airflow or a cron job that pulls data directly from the LGS MSSQL server into the PostgreSQL warehouse on a schedule, keeping analytics always up to date without manual intervention.

2. **Build an interactive dashboard:** The current analysis produces static Matplotlib charts inside a Jupyter notebook. I would replace these with an interactive dashboard using Plotly Dash or Streamlit, allowing LGS business users to filter by date range, country, or customer segment without needing to run Python code themselves.

3. **Enhance RFM segmentation with machine learning:** The current RFM segmentation uses fixed quantile-based scoring rules. Given more time, I would apply unsupervised clustering such as K-Means on the RFM features to discover natural customer groupings in the data, which may produce more meaningful and actionable segments than the manual scoring approach.
