-- host_agent schema
-- usage: psql -h localhost -U postgres -d host_agent -f sql/ddl.sql

-- hardware specs, one row per host (host_info.sh)
CREATE TABLE IF NOT EXISTS PUBLIC.host_info (
    id               SERIAL       PRIMARY KEY,
    hostname         VARCHAR      NOT NULL UNIQUE,
    cpu_number       INT2         NOT NULL,
    cpu_architecture VARCHAR      NOT NULL,
    cpu_model        VARCHAR      NOT NULL,
    cpu_mhz          FLOAT8       NOT NULL,
    l2_cache         INT4         NOT NULL,
    "timestamp"      TIMESTAMP    NOT NULL,
    total_mem        INT4         NOT NULL
);

-- usage every minute per host (host_usage.sh via cron)
CREATE TABLE IF NOT EXISTS PUBLIC.host_usage (
    "timestamp"    TIMESTAMP NOT NULL,
    host_id        SERIAL    NOT NULL,
    memory_free    INT4      NOT NULL,
    cpu_idle       INT2      NOT NULL,
    cpu_kernel     INT2      NOT NULL,
    disk_io        INT4      NOT NULL,
    disk_available INT4      NOT NULL,
    FOREIGN KEY (host_id) REFERENCES PUBLIC.host_info (id)
);

CREATE INDEX IF NOT EXISTS idx_host_usage_host_time
    ON PUBLIC.host_usage (host_id, "timestamp" DESC);
