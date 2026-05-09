-- ============================
-- Find nearby stations
-- ============================
CREATE OR REPLACE FUNCTION find_nearby_stations(
    p_latitude FLOAT,
    p_longitude FLOAT,
    p_radius_meters INTEGER DEFAULT 5000,
    p_limit INTEGER DEFAULT 50
) RETURNS TABLE(
    station_id VARCHAR(32),
    name VARCHAR,
    address TEXT,
    distance_meters FLOAT,
    has_available_connectors BOOLEAN,
    total_available_connectors BIGINT,
    max_power_kw FLOAT,
    power_tier TEXT,
    operator TEXT,
    latitude FLOAT,
    longitude FLOAT
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        gs.station_id,
        gs.name,
        gs.address,
        ST_Distance(gs.location, ST_Point(p_longitude, p_latitude)::GEOGRAPHY) AS distance_meters,
        gs.has_available_connectors,
        gs.total_available_connectors,
        gs.max_power_kw::FLOAT,
        gs.power_tier,
        gs.operator,
        ST_Y(gs.location::GEOMETRY)::FLOAT AS latitude,
        ST_X(gs.location::GEOMETRY)::FLOAT AS longitude
    FROM mv_stations_geo gs
    WHERE ST_DWithin(gs.location, ST_Point(p_longitude, p_latitude)::GEOGRAPHY, p_radius_meters)
    ORDER BY ST_Distance(gs.location, ST_Point(p_longitude, p_latitude)::GEOGRAPHY)
    LIMIT p_limit;
END;
$$ LANGUAGE plpgsql;



-- ============================
-- Export stations as GeoJSON
-- ============================
CREATE OR REPLACE FUNCTION export_stations_geojson()
RETURNS JSON AS $$
DECLARE
    result JSON;
BEGIN
    SELECT json_build_object(
        'type', 'FeatureCollection',
        'features', json_agg(
            json_build_object(
                'type', 'Feature',
                'geometry', ST_AsGeoJSON(location::geometry)::json,
                'properties', json_build_object(
                    'station_id', station_id,
                    'osm_id', osm_id,
                    'name', name,
                    'address', address,
                    'max_power_kw', max_power_kw,
                    'total_available_connectors', total_available_connectors,
                    'total_connectors', total_connectors,
                    'operator', operator,
                    'opening_hours', opening_hours,
                    'capacity', capacity,
                    'fee', fee,
                    'parking_fee', parking_fee,
                    'access', access,
                    'power_tier', power_tier,
                    'has_available_connectors', has_available_connectors,
                    'available_connector_names', available_connector_names
                )
            )
        )
    ) INTO result
    FROM mv_stations_geo;

    RETURN COALESCE(result, '{"type":"FeatureCollection","features":[]}'::json);
END;
$$ LANGUAGE plpgsql;


-- ============================
-- Station statistics
-- ============================
CREATE OR REPLACE FUNCTION get_station_statistics()
RETURNS TABLE(
    total_stations BIGINT,
    total_connectors BIGINT,
    available_connectors BIGINT,
    avg_power_kw NUMERIC,
    stations_with_available BIGINT,
    connector_type_breakdown JSON
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        COUNT(DISTINCT s.station_id) AS total_stations,
        COALESCE(SUM(c.count_total), 0) AS total_connectors,
        COALESCE(SUM(c.count_available), 0) AS available_connectors,
        AVG(c.power_kw) AS avg_power_kw,
        COUNT(DISTINCT CASE WHEN EXISTS (
            SELECT 1 FROM connectors c2 
            WHERE c2.station_id = s.station_id AND c2.count_available > 0
        ) THEN s.station_id END) AS stations_with_available,
        (
            SELECT json_agg(row_to_json(t))
            FROM (
                SELECT 
                    ct.name AS connector_type,
                    COUNT(c.id) AS count,
                    SUM(c.count_available) AS available,
                    AVG(c.power_kw) AS avg_power
                FROM connectors c
                JOIN connector_types ct ON c.connector_type_id = ct.id
                GROUP BY ct.name
                ORDER BY count DESC
            ) t
        ) AS connector_type_breakdown
    FROM stations s
    LEFT JOIN connectors c ON s.station_id = c.station_id;
END;
$$ LANGUAGE plpgsql;
