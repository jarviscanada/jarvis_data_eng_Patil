-- Linux Cluster Monitoring Agent - analytical queries
--
-- The three questions the LCA team asks of the collected data. Run against the
-- host_agent database once host_usage.sh has been collecting for a few minutes:
--
--   psql -h localhost -U postgres -d host_agent -f sql/queries.sql

-- ---------------------------------------------------------------------------
-- 1. Which servers are running low on memory?
--
-- total_mem is recorded in KB by /proc/meminfo, memory_free in MB by vmstat,
-- so total_mem is converted before the two are compared. Anything under 20%
-- free on its most recent reading is a candidate for rebalancing.
-- ---------------------------------------------------------------------------
SELECT
    i.hostname,
    u."timestamp"                                             AS measured_at,
    ROUND(i.total_mem / 1024.0)                               AS total_mem_mb,
    u.memory_free                                             AS free_mem_mb,
    ROUND(100.0 * u.memory_free / (i.total_mem / 1024.0), 1)  AS pct_free
FROM PUBLIC.host_usage u
JOIN PUBLIC.host_info  i ON i.id = u.host_id
-- keep only each host's latest reading
WHERE u."timestamp" = (
        SELECT MAX(u2."timestamp")
        FROM PUBLIC.host_usage u2
        WHERE u2.host_id = u.host_id
      )
  AND 100.0 * u.memory_free / (i.total_mem / 1024.0) < 20.0
ORDER BY pct_free ASC;

-- ---------------------------------------------------------------------------
-- 2. Did any server stop reporting?
--
-- host_usage.sh runs once a minute, so a healthy host contributes 5 rows per
-- 5-minute bucket. Fewer than 5 means the agent, the host or the network
-- dropped out during that window.
-- ---------------------------------------------------------------------------
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

-- ---------------------------------------------------------------------------
-- 3. How is CPU usage trending across the cluster?
--
-- cpu_idle is the percentage of time the CPU was idle, so utilisation is its
-- complement. Averaged per host per 5-minute bucket, with the previous bucket
-- alongside it so a rising trend is visible without leaving SQL.
-- ---------------------------------------------------------------------------
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
