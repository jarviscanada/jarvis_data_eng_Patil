# Retail Intelligence Engine

<p align="center">
  <img src="https://img.shields.io/badge/Python-Analytics-3776AB?style=for-the-badge&logo=python" alt="Python" />
  <img src="https://img.shields.io/badge/PostgreSQL-Warehouse-4169E1?style=for-the-badge&logo=postgresql" alt="PostgreSQL" />
  <img src="https://img.shields.io/badge/Jupyter-Notebook-F37726?style=for-the-badge&logo=jupyter" alt="Jupyter" />
  <img src="https://img.shields.io/badge/RFM-Customer%20Segmentation-8B5CF6?style=for-the-badge" alt="RFM" />
</p>

London Gift Shop (LGS) had the kind of retail problem that looks healthy on the surface but hides its true story in the data: a long transaction history, an active customer base, and a business that needed sharper insight into who its customers are, what they buy, and when they drift away.

This project turns raw retail transactions into business intelligence. It builds a lightweight data warehouse, loads transactional history into a structured analytical layer, and uses Python to uncover the patterns behind sales, customer retention, and revenue opportunity.

## Why this project matters

Retail success is rarely about one big campaign. It is usually about a thousand small decisions made with confidence:

- Which customers are worth investing in?
- When is demand peaking?
- Which customers are slipping quietly into inactivity?
- Are cancellations pointing to a deeper service issue?
- Is growth coming from new customers or repeat buyers?

This analysis gives LGS a way to answer those questions with data instead of intuition.

## What the project does

The project ingests UK retail transaction data from LGS, stores it in a PostgreSQL warehouse, and performs customer and sales analysis using Python. The notebook focuses on:

- data cleaning and transformation
- monthly sales and cancellation trends
- active customer and acquisition analysis
- customer lifecycle behavior
- RFM segmentation for targeted marketing actions

## Business value

The output is designed to help the business make better decisions in the real world:

- identify high-value customers and reward them
- detect inactive or at-risk customers before they churn
- optimize inventory and marketing around seasonal sales cycles
- measure new versus returning customer performance
- investigate cancellation spikes that may indicate operational friction

## Technical stack

- Python
- Jupyter Notebook
- Pandas
- NumPy
- Matplotlib
- PostgreSQL
- SQLAlchemy
- psycopg2
- Docker

## Project architecture

The system combines transactional data, a warehouse, and analytics notebook into a simple but effective data story pipeline:

```text
LGS Web App (MSSQL OLTP)
        |
        | Data export
        v
PostgreSQL Data Warehouse (Docker)
        |
        | SQL + Excel ingestion
        v
Jupyter Notebook (Python)
        |
        | Data cleaning, analysis, RFM scoring
        v
Business insights and customer segmentation
```

## Notebook focus

The main analysis notebook is here: [retail_data_analytics_wrangling.ipynb](./retail_data_analytics_wrangling.ipynb)

It covers the following analytical layers:

- Data preparation and standardization
- invoice amount distribution analysis
- monthly placed and canceled orders
- monthly sales trend analysis
- month-over-month sales growth
- monthly active users
- new vs existing customer behavior
- RFM segmentation across 10 customer groups

## RFM segmentation: the heart of the analysis

The most valuable part of this project is the customer segmentation model built from Recency, Frequency, and Monetary value.

This breaks the customer base into actionable groups such as:

- Champions
- Loyal Customers
- At Risk
- Hibernating
- Potential Loyalists

That matters because it turns raw transactions into a practical marketing playbook.

## Why it is compelling

This project sits at the intersection of:

- retail analytics
- customer lifetime value
- behavioral segmentation
- business storytelling through data

It is not only a notebook — it is a decision-making tool for a business that wants to grow smarter, not just bigger.

## Final thought

The strongest insight in this project is simple: in retail, the real opportunity is not just selling more — it is understanding who keeps buying, who is fading, and which actions will move the right customers back into growth.

This project provides that lens.

---

Built to transform transactional data into customer value, sales clarity, and smarter revenue decisions.