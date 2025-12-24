-- Telemetry Database initialization
CREATE TABLE IF NOT EXISTS telemetry_data (
    id SERIAL PRIMARY KEY,
    prothesis_id VARCHAR(255) NOT NULL,
    user_id VARCHAR(255) NOT NULL,
    timestamp TIMESTAMP NOT NULL,
    movement_type VARCHAR(50),
    response_time_ms INTEGER,
    battery_level_percent INTEGER,
    battery_cycle_count INTEGER,
    error_code VARCHAR(50),
    sensor_data JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_telemetry_prothesis ON telemetry_data(prothesis_id);
CREATE INDEX IF NOT EXISTS idx_telemetry_user ON telemetry_data(user_id);
CREATE INDEX IF NOT EXISTS idx_telemetry_timestamp ON telemetry_data(timestamp);

-- Insert mock telemetry data for the last 30 days
DO $$
DECLARE
    i INTEGER;
    prothesis_ids VARCHAR[] := ARRAY['PROT-001', 'PROT-002', 'PROT-003'];
    user_ids VARCHAR[] := ARRAY['prothetic1', 'prothetic2', 'prothetic3'];
    movement_types VARCHAR[] := ARRAY['grasp', 'release', 'rotate', 'flex', 'extend'];
    current_date DATE;
BEGIN
    FOR i IN 1..30 LOOP
        current_date := CURRENT_DATE - (30 - i);
        
        FOR j IN 1..3 LOOP
            FOR k IN 1..(50 + (random() * 50)::INTEGER) LOOP
                INSERT INTO telemetry_data (
                    prothesis_id,
                    user_id,
                    timestamp,
                    movement_type,
                    response_time_ms,
                    battery_level_percent,
                    battery_cycle_count,
                    error_code,
                    sensor_data
                ) VALUES (
                    prothesis_ids[j],
                    user_ids[j],
                    current_date + (random() * interval '1 day'),
                    movement_types[1 + (random() * (array_length(movement_types, 1) - 1))::INTEGER],
                    (80 + random() * 20)::INTEGER,
                    (60 + random() * 40)::INTEGER,
                    (100 + i * 2)::INTEGER,
                    CASE WHEN random() > 0.95 THEN 'ERR-001' ELSE NULL END,
                    jsonb_build_object(
                        'sensor1', (random() * 100)::INTEGER,
                        'sensor2', (random() * 100)::INTEGER,
                        'sensor3', (random() * 100)::INTEGER
                    )
                );
            END LOOP;
        END LOOP;
    END LOOP;
END $$;

