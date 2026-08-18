# Stock Market Analytics Pipeline

A production-grade data pipeline for ingesting, processing, and analyzing real-time stock market data from Twelve Data API using Databricks Lakeflow and the Medallion Architecture.

## Overview

This pipeline implements a multi-layered ETL architecture (Bronze ? Silver ? Gold) to transform raw financial market data into analytics-ready datasets for investment analysis, trend monitoring, and dashboard visualizations.

**Key Features:**
* Real-time stock quote ingestion
* Historical daily price data (OHLCV) processing
* Company fundamentals and financial statistics
* Multi-timeframe trend analysis (7/30/90-day windows)
* Dashboard-optimized data models
* Fully automated data quality and transformation workflows

## Architecture

```
???????????????????????????????????????????????????????????????
?                      Twelve Data API                        ?
?              (Stock Prices, Quotes, Company Info)           ?
???????????????????????????????????????????????????????????????
                            ?
                            ?
???????????????????????????????????????????????????????????????
?                     BRONZE LAYER                            ?
?                  (Raw Data Ingestion)                       ?
???????????????????????????????????????????????????????????????
?  ? bronze_stock_prices      (400 rows - Daily OHLCV)       ?
?  ? bronze_stock_quotes      (4 symbols - Latest Quotes)    ?
?  ? bronze_company_info      (Company Profiles)             ?
???????????????????????????????????????????????????????????????
                            ?
                            ?
???????????????????????????????????????????????????????????????
?                     SILVER LAYER                            ?
?              (Cleaned & Standardized)                       ?
???????????????????????????????????????????????????????????????
?  ? silver_stock_prices      (Typed, with daily metrics)    ?
?  ? silver_stock_quotes      (Numeric transformations)      ?
?  ? silver_company_info      (Cleaned fundamentals)         ?
???????????????????????????????????????????????????????????????
                            ?
                            ?
???????????????????????????????????????????????????????????????
?                      GOLD LAYER                             ?
?                 (Analytics-Ready)                           ?
???????????????????????????????????????????????????????????????
?  ? gold_price_trends        (7/30/90-day price changes)    ?
?  ? gold_volume_trends       (7/30/90-day avg volumes)      ?
?  ? gold_latest_snapshot     (Dashboard-ready combined)     ?
???????????????????????????????????????????????????????????????
                            ?
                            ?
                  ???????????????????????
                  ?  BI Dashboards &    ?
                  ?  Analytics Tools    ?
                  ???????????????????????
```

## Medallion Architecture

### Bronze Layer (Raw Data)

Ingests raw data from Twelve Data API with minimal transformation.

| Dataset | Description | Row Count |
| --- | --- | --- |
| `bronze_stock_prices` | Raw daily OHLCV price data from time_series endpoint | 400 |
| `bronze_stock_quotes` | Latest quote snapshot per symbol from quote endpoint | 4 |
| `bronze_company_info` | Company profile + financial statistics per symbol | 1 |

**Characteristics:**
* Preserves source data structure
* String-based data types from API
* No data quality enforcement
* Foundation for downstream processing

### Silver Layer (Cleaned & Validated)

Transforms raw data into clean, typed, and validated datasets.

| Dataset | Description | Transformations |
| --- | --- | --- |
| `silver_stock_prices` | Cleaned daily price data | ? Type casting (decimal, date)<br>? Daily change calculations<br>? Data validation |
| `silver_stock_quotes` | Cleaned latest quotes | ? Numeric conversion<br>? Percent formatting<br>? NULL handling |
| `silver_company_info` | Cleaned fundamentals | ? String to numeric casting<br>? Field standardization |

**Characteristics:**
* Strongly-typed columns
* Derived metrics (daily changes, percentages)
* Data quality rules applied
* Ready for analytical joins

### Gold Layer (Business Logic)

Aggregates and enriches data for specific analytical use cases.

| Dataset | Description | Use Case |
| --- | --- | --- |
| `gold_price_trends` | Daily closing price changes over multiple windows | Trend analysis, momentum indicators |
| `gold_volume_trends` | Average daily volumes over 7/30/90 days | Liquidity assessment, volume patterns |
| `gold_latest_snapshot` | Combined quotes, trends, and company fundamentals | Real-time dashboards, KPI monitoring |

**Characteristics:**
* Business-level aggregations
* Multi-timeframe analysis (7/30/90 days)
* Dashboard-optimized schemas
* Denormalized for query performance

## Technology Stack

* **Platform**: Databricks Lakehouse
* **Compute**: Serverless with Photon engine
* **ETL Framework**: Spark Declarative Pipelines (Lakeflow)
* **Storage**: Delta Lake (Unity Catalog)
* **Processing Engine**: Apache Spark / PySpark
* **Data Catalog**: Unity Catalog (workspace.default)
* **Data Source**: Twelve Data Financial API

## Project Structure

```
/Workspace/Users/mailtokaustubhpatil@gmail.com/New Pipeline 2026-07-20 13:35/
??? README.md                          # This file
??? transformations/
    ??? my_transformation.py           # Main pipeline logic (Bronze ? Silver ? Gold)
```

## Pipeline Configuration

* **Pipeline Name**: `stock_dlt_pipeline`
* **Pipeline ID**: `9b106f56-4ad5-4b46-a9c2-86912524eac7`
* **Target Catalog**: `workspace`
* **Target Schema**: `default`
* **Compute Type**: Serverless (Photon enabled)
* **Mode**: Batch (triggered)
* **Publishing Mode**: Default

## Datasets

### Output Tables

All datasets are published to **Unity Catalog** under `workspace.default.*`:

**Bronze:**
* `workspace.default.bronze_stock_prices`
* `workspace.default.bronze_stock_quotes`
* `workspace.default.bronze_company_info`

**Silver:**
* `workspace.default.silver_stock_prices`
* `workspace.default.silver_stock_quotes`
* `workspace.default.silver_company_info`

**Gold:**
* `workspace.default.gold_price_trends`
* `workspace.default.gold_volume_trends`
* `workspace.default.gold_latest_snapshot`

### Sample Queries

**Get latest stock snapshot with trends:**
```sql
SELECT * FROM workspace.default.gold_latest_snapshot;
```

**Analyze price trends over 30 days:**
```sql
SELECT 
  symbol,
  datetime,
  close_price,
  price_change_30d,
  price_change_pct_30d
FROM workspace.default.gold_price_trends
WHERE price_change_pct_30d > 10
ORDER BY price_change_pct_30d DESC;
```

**Monitor volume patterns:**
```sql
SELECT 
  symbol,
  datetime,
  volume,
  avg_volume_7d,
  avg_volume_30d
FROM workspace.default.gold_volume_trends
WHERE volume > avg_volume_30d * 1.5  -- Volume spike detection
ORDER BY datetime DESC;
```

## Getting Started

### Prerequisites

* Databricks workspace access
* Unity Catalog enabled
* Twelve Data API credentials
* Appropriate permissions on `workspace.default` schema

### Running the Pipeline

1. **Dry Run (Validation):**
   * Validates syntax and dependencies without materializing data
   * Recommended before full runs

2. **Full Update:**
   * Processes all datasets from Bronze ? Gold
   * Run frequency: As needed based on data freshness requirements

3. **Selective Refresh:**
   * Update specific datasets only
   * Example: Refresh only Gold layer for dashboard updates

### Monitoring

* Check pipeline status in Databricks UI
* Review event logs for errors or warnings
* Monitor dataset lineage and data quality metrics
* Track row counts and update timestamps

## Data Freshness

* **Bronze Layer**: Ingests on-demand from Twelve Data API
* **Silver Layer**: Transforms immediately after Bronze ingestion
* **Gold Layer**: Aggregates from Silver with multi-day lookback windows
* **Recommended Cadence**: Daily or on-demand based on trading schedule

## Future Enhancements

### Immediate Improvements
* [ ] Add data quality expectations (expectations for NULL checks, range validations)
* [ ] Implement streaming ingestion for real-time quote updates
* [ ] Add more stock symbols beyond current 4
* [ ] Create technical indicators (RSI, MACD, Bollinger Bands)
* [ ] Add partition optimization by date for large datasets

### Advanced Features
* [ ] Machine learning features for price prediction
* [ ] Anomaly detection for unusual price/volume movements
* [ ] Sentiment analysis integration from news APIs
* [ ] Portfolio performance tracking and attribution
* [ ] Risk metrics (volatility, beta, Sharpe ratio)
* [ ] Automated alerts for significant price movements
* [ ] Integration with trading platforms

### Operational Improvements
* [ ] Schedule pipeline runs during market hours
* [ ] Add CDC (Change Data Capture) for incremental processing
* [ ] Implement retry logic for API failures
* [ ] Create dashboard visualizations for Gold layer data
* [ ] Add pipeline documentation and data dictionary
* [ ] Set up monitoring and alerting for pipeline failures

## Data Quality & Governance

* All datasets stored in Unity Catalog for governance
* Delta Lake provides ACID transactions and time travel
* Pipeline maintains full data lineage across all layers
* Serverless compute ensures cost-effective, auto-scaling execution

## Performance Optimization

* **Photon Engine**: Accelerated query execution
* **Serverless Compute**: Auto-scaling based on workload
* **Delta Lake**: Optimized storage with columnar format
* **Materialized Views**: Pre-computed aggregations for fast queries

## Support & Contribution

For questions or issues with the pipeline:
* Review pipeline event logs in Databricks UI
* Check Twelve Data API status and rate limits
* Verify Unity Catalog permissions
* Contact: mailtokaustubhpatil@gmail.com

## License

Internal use - proprietary.

---

**Last Updated**: 2026-07-20  
**Pipeline Version**: 1.0  
**Databricks Runtime**: Serverless with Photon
