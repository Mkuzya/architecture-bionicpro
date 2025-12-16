-- ClickHouse initialization script
-- Creates database and reports data mart table

CREATE DATABASE IF NOT EXISTS reports_db;

USE reports_db;

-- Reports Data Mart table
-- Pre-aggregated data for fast report generation
CREATE TABLE IF NOT EXISTS reports_data_mart
(
    user_id String,
    date Date,
    customer_name String,
    customer_email String,
    prothesis_id String,
    total_movements UInt64,
    avg_response_time_ms Float32,
    battery_usage_percent Float32,
    battery_cycles UInt32,
    error_count UInt32,
    usage_hours Float32,
    last_activity DateTime,
    -- Aggregated metrics
    movements_by_type Map(String, UInt64),
    daily_usage_hours Map(Date, Float32),
    -- Metadata
    created_at DateTime DEFAULT now(),
    updated_at DateTime DEFAULT now()
)
ENGINE = MergeTree()
PARTITION BY toYYYYMM(date)
ORDER BY (user_id, date, prothesis_id)
SETTINGS index_granularity = 8192;

