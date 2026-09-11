-- Linux Cluster Monitoring Agent - schema
--
-- Creates the two tables the collection scripts write to. Run once, after the
-- PostgreSQL container is up and the host_agent database exists:
--
--   ./scripts/psql_docker.sh create postgres <password>
--   createdb -h localhost -U postgres host_agent      # or: CREATE DATABASE host_agent;
--   psql -h localhost -U postgres -d host_agent -f sql/ddl.sql
--
-- Safe to re-run: both tables are created only if absent.

-- Static hardware specification, one row per server in the cluster.
-- Written once per host by host_info.sh.
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

-- hostname is UNIQUE because host_usage.sh resolves host_id with
--   (SELECT id FROM host_info WHERE hostname = '<fqdn>')
-- which must return exactly one row.

-- Time series of resource usage, one row per host per collection interval.
-- Written every minute by host_usage.sh via crontab.
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

-- Usage rows are always read by host and ordered by time, so index that pair.
CREATE INDEX IF NOT EXISTS idx_host_usage_host_time
    ON PUBLIC.host_usage (host_id, "timestamp" DESC);
