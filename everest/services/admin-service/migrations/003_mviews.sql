-- ============================
-- Drop existing views
-- ============================
DROP MATERIALIZED VIEW IF EXISTS mv_stations_geo;
DROP MATERIALIZED VIEW IF EXISTS mv_stations_summary;
DROP MATERIALIZED VIEW IF EXISTS mv_connector_type_stats;

-- ============================
-- Main geographic optimized view
-- ============================
CREATE MATERIALIZED VIEW mv_stations_geo AS
SELECT 
    cs.station_id,
    cs.osm_id,
    cs.name,
    cs.address,
    cs.location,
    
    -- Extract coordinates for easy access
    ST_X(cs.location::geometry) AS longitude,
    ST_Y(cs.location::geometry) AS latitude,
    
    -- Quick availability summary
    EXISTS (
        SELECT 1 FROM connectors sc 
        WHERE sc.station_id = cs.station_id AND sc.count_available > 0
    ) AS has_available_connectors,
    
    -- Connector summary as JSON
    (
        SELECT jsonb_agg(
            jsonb_build_object(
                'connector_id', sc.connector_id,
                'type_id', sc.connector_type_id,
                'type_name', ct.name,
                'status_id', sc.status_id,
                'status_name', cs2.name,
                'current_type_id', sc.current_type_id,
                'current_type_name', cur.name,
                'power_kw', sc.power_kw,
                'voltage', sc.voltage,
                'amperage', sc.amperage,
                'available', sc.count_available,
                'total', sc.count_total
            ) ORDER BY sc.power_kw DESC NULLS LAST
        )
        FROM connectors sc
        LEFT JOIN connector_types ct ON sc.connector_type_id = ct.id
        LEFT JOIN connector_statuses cs2 ON sc.status_id = cs2.id
        LEFT JOIN current_types cur ON sc.current_type_id = cur.id
        WHERE sc.station_id = cs.station_id
    ) AS connectors,
    
    -- Power statistics
    (
        SELECT MAX(power_kw) 
        FROM connectors sc 
        WHERE sc.station_id = cs.station_id
    ) AS max_power_kw,
    
    (
        SELECT MIN(power_kw) 
        FROM connectors sc 
        WHERE sc.station_id = cs.station_id AND sc.power_kw > 0
    ) AS min_power_kw,
    
    -- Connector counts
    (
        SELECT COALESCE(SUM(count_available), 0)
        FROM connectors sc 
        WHERE sc.station_id = cs.station_id
    ) AS total_available_connectors,
    
    (
        SELECT COUNT(*)
        FROM connectors sc 
        WHERE sc.station_id = cs.station_id
    ) AS total_connectors,
    
    -- Array of available connector type IDs and names
    (
        SELECT ARRAY_AGG(DISTINCT sc.connector_type_id)
        FROM connectors sc
        WHERE sc.station_id = cs.station_id AND sc.count_available > 0
    ) AS available_connector_type_ids,

    (
        SELECT ARRAY_AGG(DISTINCT ct.name)
        FROM connectors sc
        LEFT JOIN connector_types ct ON sc.connector_type_id = ct.id
        WHERE sc.station_id = cs.station_id AND sc.count_available > 0
    ) AS available_connector_names,

    -- Power tier classification
    CASE 
        WHEN (SELECT MAX(power_kw) FROM connectors WHERE station_id = cs.station_id) >= 150 THEN 'ultra_fast'
        WHEN (SELECT MAX(power_kw) FROM connectors WHERE station_id = cs.station_id) >= 50 THEN 'fast'
        WHEN (SELECT MAX(power_kw) FROM connectors WHERE station_id = cs.station_id) >= 22 THEN 'medium'
        ELSE 'slow'
    END AS power_tier,

    -- Station metadata from tags
    cs.tags->'operator' AS operator,
    cs.tags->'opening_hours' AS opening_hours,
    cs.tags->'capacity' AS capacity,
    cs.tags->'fee' AS fee,
    cs.tags->'parking_fee' AS parking_fee,
    cs.tags->'access' AS access,

    -- Timestamps
    cs.created_at,
    cs.updated_at

FROM stations cs
WHERE cs.location IS NOT NULL
WITH DATA;

-- ============================
-- Summary view for analytics
-- ============================
CREATE MATERIALIZED VIEW mv_stations_summary AS
SELECT 
    cs.station_id,
    cs.osm_id,
    cs.name,
    cs.address,
    cs.location,
    cs.tags,
    cs.created_at,
    cs.updated_at,
    
    -- Connector statistics
    COUNT(sc.connector_id) AS total_connectors,
    SUM(sc.count_available) AS available_connectors,
    SUM(sc.count_total) AS total_connector_slots,
    MAX(sc.power_kw) AS max_power_kw,
    MIN(sc.power_kw) AS min_power_kw,
    AVG(sc.power_kw) AS avg_power_kw,
    
    -- Connector type breakdown
    COUNT(DISTINCT sc.connector_type_id) AS unique_connector_types,
    
    -- Array of available connector types
    ARRAY_AGG(DISTINCT ct.name) FILTER (WHERE ct.name IS NOT NULL) AS connector_type_names,
    
    -- Current status summary
    EXISTS (
        SELECT 1 FROM connectors sc2 
        WHERE sc2.station_id = cs.station_id AND sc2.count_available > 0
    ) AS has_available_connectors,
    
    -- Power capacity tiers
    CASE 
        WHEN MAX(sc.power_kw) >= 150 THEN 'ultra_fast'
        WHEN MAX(sc.power_kw) >= 50 THEN 'fast'
        WHEN MAX(sc.power_kw) >= 22 THEN 'medium'
        ELSE 'slow'
    END AS power_tier

FROM stations cs
LEFT JOIN connectors sc ON cs.station_id = sc.station_id
LEFT JOIN connector_types ct ON sc.connector_type_id = ct.id
GROUP BY cs.station_id, cs.osm_id, cs.name, cs.address, cs.location, cs.tags, cs.created_at, cs.updated_at
WITH DATA;

-- ============================
-- Connector type statistics view
-- ============================
CREATE MATERIALIZED VIEW mv_connector_type_stats AS
SELECT 
    cs.station_id,
    cs.name AS station_name,
    ct.name AS connector_type,
    COUNT(sc.connector_id) AS connector_count,
    SUM(sc.count_available) AS available_count,
    SUM(sc.count_total) AS total_slots,
    AVG(sc.power_kw) AS avg_power,
    MIN(sc.power_kw) AS min_power,
    MAX(sc.power_kw) AS max_power,
    cs.location

FROM stations cs
JOIN connectors sc ON cs.station_id = sc.station_id
JOIN connector_types ct ON sc.connector_type_id = ct.id
GROUP BY cs.station_id, cs.name, ct.name, cs.location
WITH DATA;


-- ============================
-- Drop existing user review view
-- ============================
DROP MATERIALIZED VIEW IF EXISTS mv_stations_reviews;

-- ============================
-- Stations + Reviews View
-- ============================
CREATE MATERIALIZED VIEW mv_stations_reviews AS
SELECT
    s.station_id,
    s.name AS station_name,
    s.address,
    s.location,
    ST_X(s.location::geometry) AS longitude,
    ST_Y(s.location::geometry) AS latitude,
    
    -- Connector summary
    EXISTS (
        SELECT 1
        FROM connectors c
        WHERE c.station_id = s.station_id AND c.count_available > 0
    ) AS has_available_connectors,
    
    (
        SELECT jsonb_agg(
            jsonb_build_object(
                'connector_id', c.connector_id,
                'type_id', c.connector_type_id,
                'type_name', ct.name,
                'status_id', c.status_id,
                'status_name', cs.name,
                'current_type_id', c.current_type_id,
                'current_type_name', cur.name,
                'power_kw', c.power_kw,
                'voltage', c.voltage,
                'amperage', c.amperage,
                'available', c.count_available,
                'total', c.count_total
            ) ORDER BY c.power_kw DESC NULLS LAST
        )
        FROM connectors c
        LEFT JOIN connector_types ct ON c.connector_type_id = ct.id
        LEFT JOIN connector_statuses cs ON c.status_id = cs.id
        LEFT JOIN current_types cur ON c.current_type_id = cur.id
        WHERE c.station_id = s.station_id
    ) AS connectors,
    
    -- Reviews summary
    (
        SELECT AVG(r.rating) 
        FROM user_reviews r
        WHERE r.station_id = s.station_id
    ) AS avg_rating,
    
    (
        SELECT COUNT(*)
        FROM user_reviews r
        WHERE r.station_id = s.station_id
    ) AS total_reviews,
    
    -- Detailed reviews as JSON
    (
        SELECT jsonb_agg(
            jsonb_build_object(
                'review_id', r.review_id,
                'user_id', r.user_id,
                'rating', r.rating,
                'review_text', r.review_text,
                'created_at', r.created_at,
                'updated_at', r.updated_at
            ) ORDER BY r.created_at DESC
        )
        FROM user_reviews r
        WHERE r.station_id = s.station_id
    ) AS reviews,
    
    s.tags,
    s.created_at,
    s.updated_at

FROM stations s
WHERE s.location IS NOT NULL
WITH DATA;


-- ============================
-- Indexes for performance
-- ============================
CREATE UNIQUE INDEX idx_mv_geo_station_id ON mv_stations_geo (station_id);
CREATE INDEX idx_mv_geo_location_gist ON mv_stations_geo USING GIST (location);
CREATE INDEX idx_mv_geo_coords ON mv_stations_geo (longitude, latitude);
CREATE INDEX idx_mv_geo_available ON mv_stations_geo (has_available_connectors);
CREATE INDEX idx_mv_geo_max_power ON mv_stations_geo (max_power_kw);
CREATE INDEX idx_mv_geo_power_tier ON mv_stations_geo (power_tier);
CREATE INDEX idx_mv_geo_operator ON mv_stations_geo (operator);
CREATE INDEX idx_mv_geo_connector_types ON mv_stations_geo USING GIN (available_connector_type_ids);

CREATE UNIQUE INDEX idx_mv_summary_station_id ON mv_stations_summary (station_id);
CREATE INDEX idx_mv_summary_location ON mv_stations_summary USING GIST (location);
CREATE INDEX idx_mv_summary_power_tier ON mv_stations_summary (power_tier);

CREATE INDEX idx_mv_connector_stats_station ON mv_connector_type_stats (station_id);
CREATE INDEX idx_mv_connector_stats_type ON mv_connector_type_stats (connector_type);


CREATE UNIQUE INDEX idx_mv_stations_reviews_id ON mv_stations_reviews (station_id);
CREATE INDEX idx_mv_stations_reviews_location_gist ON mv_stations_reviews USING GIST (location);
CREATE INDEX idx_mv_stations_reviews_rating ON mv_stations_reviews (avg_rating);
CREATE INDEX idx_mv_stations_reviews_available ON mv_stations_reviews (has_available_connectors);
