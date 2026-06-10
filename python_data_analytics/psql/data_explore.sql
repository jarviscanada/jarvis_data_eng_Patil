-- Show table schema
\d+ retail;

-- Q1: Show first 10 rows
SELECT * FROM retail LIMIT 10;

-- Q2: Check # of records
SELECT COUNT(*) FROM retail;

-- Q3: Number of unique clients
SELECT COUNT(DISTINCT customer_id) FROM retail;

-- Q4: Invoice date range
SELECT MAX(invoice_date), MIN(invoice_date) FROM retail;

-- Q5: Number of unique SKUs
SELECT COUNT(DISTINCT stock_code) FROM retail;

-- Q6: Average invoice amount (excluding negative/canceled)
SELECT AVG(invoice_total) AS avg
FROM (
  SELECT invoice_no, SUM(unit_price * quantity) AS invoice_total
  FROM retail
  GROUP BY invoice_no
  HAVING SUM(unit_price * quantity) > 0
) AS invoice_totals;

-- Q7: Total revenue
SELECT SUM(unit_price * quantity) FROM retail;

-- Q8: Total revenue by YYYYMM
SELECT
  CAST(EXTRACT(YEAR FROM invoice_date) * 100 + EXTRACT(MONTH FROM invoice_date) AS INTEGER) AS yyyymm,
  SUM(unit_price * quantity) AS sum
FROM retail
GROUP BY yyyymm
ORDER BY yyyymm;
