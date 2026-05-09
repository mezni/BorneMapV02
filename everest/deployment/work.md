export DATABASE_URL=postgresql://postgres:password@localhost:5700/evcs_db
export JWT_ISSUER=http://keycloak:8080/realms/myrealm
export JWKS_URL=http://keycloak:8080/realms/myrealm/protocol/openid-connect/certs
RUST_BACKTRACE=1 cargo run


docker exec -it evcs-db psql -U postgres -d evcs_db


SELECT * 
FROM find_nearby_stations2(36.806253, 10.181719);


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