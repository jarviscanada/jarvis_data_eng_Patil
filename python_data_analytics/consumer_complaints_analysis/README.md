# Consumer Complaint Intelligence

<p align="center">
  <img src="https://img.shields.io/badge/Python-Analytics-3776AB?style=for-the-badge&logo=python" alt="Python" />
  <img src="https://img.shields.io/badge/Pandas-Data%20Wrangling-150458?style=for-the-badge&logo=pandas" alt="Pandas" />
  <img src="https://img.shields.io/badge/Plotly-Visualization-3F4F75?style=for-the-badge&logo=plotly" alt="Plotly" />
  <img src="https://img.shields.io/badge/CFPB-Consumer%20Finance-16A34A?style=for-the-badge" alt="CFPB" />
</p>

A story-driven data analysis of the U.S. Consumer Financial Protection Bureau complaint database — a massive public dataset that captures how consumers experience financial products and institutions across time.

This project turns raw complaint records into a readable map of risk, market concentration, product pain points, and institutional behavior.

## Why this project matters

Every complaint tells a story. When you combine millions of them, those stories reveal patterns that matter to regulators, financial institutions, and the public:

- Which financial products trigger the most complaints?
- Which companies dominate complaint volume?
- Are complaint trends shifting over time?
- Where do consumers feel the most friction in the system?

This notebook uses data as a lens to understand customer experience at scale.

## The dataset

Source: CFPB Consumer Complaint Database

- approximately 1.28M complaint records
- around 5,275 companies involved
- time range: December 2011 to May 2019

Data source: https://www.kaggle.com/datasets/selener/consumer-complaint-database

> The raw file is not included in the repository. Download the dataset from Kaggle and place it in a local `data/` folder before running the notebook.

## Project objective

This project is designed to do more than summarize numbers. It aims to:

- profile the complaint landscape
- identify dominant financial products and company behaviors
- visualize complaint patterns over time
- surface business and regulatory signals hidden in large-scale text and categorical data

## What the notebook does

The analysis explores the dataset through an end-to-end Python workflow:

- load and inspect the complaint data
- clean and standardize fields for analysis
- profile complaint distribution by product, company, and timeframe
- derive trend and concentration insights
- build static and interactive visual narratives using Matplotlib and Plotly

## Tech stack

- Python
- Pandas
- NumPy
- Matplotlib
- Plotly
- Jupyter Notebook

## Expected outputs

The analysis is intended to generate:

- product-level complaint trends
- company concentration insights
- time-based complaint behavior
- visual summaries for stakeholder understanding
- a narrative view of consumer financial pain points

## Repository structure

```text
consumer_complaints_analysis/
├── Consumer-Complaints_DA.ipynb
├── README.md
├── .gitignore
└── data/
```

## Why this is interesting

This project sits at the intersection of:

- public policy
- financial services
- behavioral analytics
- communication of risk through data storytelling

It is not just a data exercise — it is a way to translate massive consumer data into meaningful insight.

## Final thought

The real value of this project is not only the charts; it is the ability to look at an entire financial ecosystem and ask: where is the system breaking down, and which patterns deserve attention?

This notebook is a compact but powerful answer to that question.

---

Built to analyze complaint volume, discover product risk, and turn raw financial dissatisfaction into evidence-backed insight.
