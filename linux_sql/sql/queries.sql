-- usage: psql -h localhost -U postgres -d host_agent -f sql/queries.sql

-- 1. hosts under 20% free memory (total_mem is KB, memory_free is MB)
SELECT
    i.hostname,
    u."timestamp"                                             AS measured_at,
    ROUND(i.total_mem / 1024.0)                               AS total_mem_mb,
    u.memory_free                                             AS free_mem_mb,
    ROUND(100.0 * u.memory_free / (i.total_mem / 1024.0), 1)  AS pct_free
FROM PUBLIC.host_usage u
JOIN PUBLIC.host_info  i ON i.id = u.host_id
-- latest reading only
WHERE u."timestamp" = (
        SELECT MAX(u2."timestamp")
        FROM PUBLIC.host_usage u2
        WHERE u2.host_id = u.host_id
      )
  AND 100.0 * u.memory_free / (i.total_mem / 1024.0) < 20.0
ORDER BY pct_free ASC;

-- 2. missing data points (expect 5 rows per 5 min bucket)
SELECT
    i.hostname,
    to_timestamp(
        floor(extract(EPOCH FROM u."timestamp") / 300) * 300
    ) AT TIME ZONE 'UTC'        AS bucket_start,
    COUNT(*)                    AS rows_collected,
    5 - COUNT(*)                AS rows_missing
FROM PUBLIC.host_usage u
JOIN PUBLIC.host_info  i ON i.id = u.host_id
GROUP BY i.hostname, bucket_start
HAVING COUNT(*) < 5
ORDER BY bucket_start DESC, i.hostname;

-- 3. avg CPU usage per 5 min bucket, with change vs previous bucket
SELECT
    i.hostname,
    to_timestamp(
        floor(extract(EPOCH FROM u."timestamp") / 300) * 300
    ) AT TIME ZONE 'UTC'                            AS bucket_start,
    ROUND(AVG(100 - u.cpu_idle), 1)                 AS avg_cpu_used_pct,
    ROUND(AVG(u.cpu_kernel), 1)                     AS avg_cpu_kernel_pct,
    ROUND(
        AVG(100 - u.cpu_idle) - LAG(AVG(100 - u.cpu_idle)) OVER (
            PARTITION BY i.hostname ORDER BY MIN(u."timestamp")
        ), 1
    )                                               AS change_vs_prev_bucket
FROM PUBLIC.host_usage u
JOIN PUBLIC.host_info  i ON i.id = u.host_id
GROUP BY i.hostname, bucket_start
ORDER BY i.hostname, bucket_start DESC;
