-- ============================
-- Create OSM staging table
-- ============================
CREATE TABLE IF NOT EXISTS osm_charging_stations_temp (
    osm_id BIGINT PRIMARY KEY,
    name VARCHAR(255),
    address TEXT,
    longitude FLOAT,
    latitude FLOAT,
    operator VARCHAR(255),
    opening_hours TEXT,
    capacity INTEGER,
    fee TEXT,
    parking_fee TEXT,
    access TEXT,
    socket_type2 INTEGER,
    socket_ccs INTEGER,
    socket_chademo INTEGER,
    socket_type2_output DECIMAL(5,2),
    socket_ccs_output DECIMAL(5,2),
    socket_chademo_output DECIMAL(5,2),
    tags HSTORE,
    geom GEOMETRY(Point, 4326),
    imported_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_osm_temp_geom ON osm_charging_stations_temp USING GIST (geom);
CREATE INDEX IF NOT EXISTS idx_osm_temp_osm_id ON osm_charging_stations_temp (osm_id);

-- ============================
-- Function to extract connectors from OSM tags
-- ============================
CREATE OR REPLACE FUNCTION extract_connectors_from_osm_tags(
    p_station_id VARCHAR(32),
    p_tags HSTORE,
    p_user_id VARCHAR(32)
) RETURNS INTEGER AS $$
DECLARE
    v_connector_count INTEGER := 0;
    v_count_total INTEGER;
    v_power_kw DECIMAL(5,2);
BEGIN
    -- Clear existing connectors for this station
    DELETE FROM connectors WHERE station_id = p_station_id;

    -- Type2 AC
    IF p_tags ? 'socket:type2' AND p_tags->'socket:type2' ~ '^\d+$' THEN
        v_count_total := (p_tags->'socket:type2')::INTEGER;
        v_power_kw := NULLIF(p_tags->'socket:type2:output', '')::DECIMAL;
        INSERT INTO connectors (
            connector_id, station_id, connector_type_id, status_id, current_type_id,
            power_kw, count_total, count_available, created_by, created_at
        ) VALUES (
            'CHR' || gen_random_uuid()::TEXT,
            p_station_id,
            (SELECT id FROM connector_types WHERE name = 'type2'),
            1,  -- Available
            (SELECT id FROM current_types WHERE name = 'AC'),
            COALESCE(v_power_kw, 22.0),
            v_count_total,
            v_count_total,
            p_user_id,
            NOW()
        );
        v_connector_count := v_connector_count + 1;
    END IF;

    -- CCS DC
    IF p_tags ? 'socket:ccs' AND p_tags->'socket:ccs' ~ '^\d+$' THEN
        v_count_total := (p_tags->'socket:ccs')::INTEGER;
        v_power_kw := NULLIF(p_tags->'socket:ccs:output', '')::DECIMAL;
        INSERT INTO connectors (
            connector_id, station_id, connector_type_id, status_id, current_type_id,
            power_kw, count_total, count_available, created_by, created_at
        ) VALUES (
            'CHR' || gen_random_uuid()::TEXT,
            p_station_id,
            (SELECT id FROM connector_types WHERE name = 'ccs'),
            1,
            (SELECT id FROM current_types WHERE name = 'DC'),
            COALESCE(v_power_kw, 50.0),
            v_count_total,
            v_count_total,
            p_user_id,
            NOW()
        );
        v_connector_count := v_connector_count + 1;
    END IF;

    -- CHAdeMO DC
    IF p_tags ? 'socket:chademo' AND p_tags->'socket:chademo' ~ '^\d+$' THEN
        v_count_total := (p_tags->'socket:chademo')::INTEGER;
        v_power_kw := NULLIF(p_tags->'socket:chademo:output', '')::DECIMAL;
        INSERT INTO connectors (
            connector_id, station_id, connector_type_id, status_id, current_type_id,
            power_kw, count_total, count_available, created_by, created_at
        ) VALUES (
            'CHR' || gen_random_uuid()::TEXT,
            p_station_id,
            (SELECT id FROM connector_types WHERE name = 'chademo'),
            1,
            (SELECT id FROM current_types WHERE name = 'DC'),
            COALESCE(v_power_kw, 50.0),
            v_count_total,
            v_count_total,
            p_user_id,
            NOW()
        );
        v_connector_count := v_connector_count + 1;
    END IF;

    RETURN v_connector_count;
END;
$$ LANGUAGE plpgsql;

-- ============================
-- Main OSM sync function
-- ============================
CREATE OR REPLACE FUNCTION sync_osm_charging_stations(
    p_user_id VARCHAR(32) DEFAULT 'USR000000000000000000000000000000'
) RETURNS TABLE(
    updated_count INTEGER,
    inserted_count INTEGER,
    deactivated_count INTEGER
) AS $$
DECLARE
    v_updated_count INTEGER := 0;
    v_inserted_count INTEGER := 0;
    v_deactivated_count INTEGER := 0;
    v_station_id VARCHAR(32);
    v_tags HSTORE;
BEGIN
    -- Update existing stations
    WITH updated AS (
        UPDATE stations s
        SET
            name = COALESCE(osm.name, s.name),
            address = COALESCE(osm.address, s.address),
            tags = s.tags || hstore(array[
                ['operator', osm.operator],
                ['opening_hours', osm.opening_hours],
                ['capacity', osm.capacity::text],
                ['fee', osm.fee],
                ['parking_fee', osm.parking_fee],
                ['access', osm.access],
                ['socket:type2', osm.socket_type2::text],
                ['socket:ccs', osm.socket_ccs::text],
                ['socket:chademo', osm.socket_chademo::text],
                ['socket:type2:output', osm.socket_type2_output::text],
                ['socket:ccs:output', osm.socket_ccs_output::text],
                ['socket:chademo:output', osm.socket_chademo_output::text]
            ]) || osm.tags,
            updated_by = p_user_id,
            updated_at = NOW()
        FROM osm_charging_stations_temp osm
        WHERE s.osm_id = osm.osm_id
        AND (
            s.name IS DISTINCT FROM osm.name OR
            s.address IS DISTINCT FROM osm.address OR
            s.tags IS DISTINCT FROM (
                hstore(array[
                    ['operator', osm.operator],
                    ['opening_hours', osm.opening_hours],
                    ['capacity', osm.capacity::text],
                    ['fee', osm.fee],
                    ['parking_fee', osm.parking_fee],
                    ['access', osm.access],
                    ['socket:type2', osm.socket_type2::text],
                    ['socket:ccs', osm.socket_ccs::text],
                    ['socket:chademo', osm.socket_chademo::text],
                    ['socket:type2:output', osm.socket_type2_output::text],
                    ['socket:ccs:output', osm.socket_ccs_output::text],
                    ['socket:chademo:output', osm.socket_chademo_output::text]
                ]) || osm.tags
            )
        )
        RETURNING s.station_id, s.tags
    )
    SELECT COUNT(*) INTO v_updated_count FROM updated;

    -- Process connectors for updated stations
    FOR v_station_id, v_tags IN 
        SELECT s.station_id, s.tags
        FROM stations s
        INNER JOIN osm_charging_stations_temp osm ON s.osm_id = osm.osm_id
        WHERE s.updated_at >= NOW() - INTERVAL '5 minutes'
    LOOP
        PERFORM extract_connectors_from_osm_tags(v_station_id, v_tags, p_user_id);
    END LOOP;

    -- Insert new stations
    WITH inserted AS (
        INSERT INTO stations (
            station_id, osm_id, name, address, location, tags, created_by, created_at
        )
        SELECT 
            'STA' || gen_random_uuid()::TEXT,
            osm.osm_id,
            osm.name,
            osm.address,
            osm.geom::GEOGRAPHY,
            hstore(array[
                ['operator', osm.operator],
                ['opening_hours', osm.opening_hours],
                ['capacity', osm.capacity::text],
                ['fee', osm.fee],
                ['parking_fee', osm.parking_fee],
                ['access', osm.access],
                ['socket:type2', osm.socket_type2::text],
                ['socket:ccs', osm.socket_ccs::text],
                ['socket:chademo', osm.socket_chademo::text],
                ['socket:type2:output', osm.socket_type2_output::text],
                ['socket:ccs:output', osm.socket_ccs_output::text],
                ['socket:chademo:output', osm.socket_chademo_output::text]
            ]) || osm.tags,
            p_user_id,
            NOW()
        FROM osm_charging_stations_temp osm
        WHERE NOT EXISTS (
            SELECT 1 FROM stations WHERE osm_id = osm.osm_id
        )
        RETURNING station_id, osm_id, tags
    )
    SELECT COUNT(*) INTO v_inserted_count FROM inserted;

    -- Process connectors for new stations
    FOR v_station_id, v_tags IN 
        SELECT s.station_id, s.tags
        FROM stations s
        INNER JOIN osm_charging_stations_temp osm ON s.osm_id = osm.osm_id
        WHERE s.created_at >= NOW() - INTERVAL '5 minutes'
    LOOP
        PERFORM extract_connectors_from_osm_tags(v_station_id, v_tags, p_user_id);
    END LOOP;

    -- Refresh materialized views if there were changes
    IF (v_updated_count + v_inserted_count) > 0 THEN
        PERFORM refresh_charging_station_views();
    END IF;

    RETURN QUERY SELECT v_updated_count, v_inserted_count, v_deactivated_count;

EXCEPTION WHEN OTHERS THEN
    RAISE EXCEPTION 'OSM sync failed: %', SQLERRM;
END;
$$ LANGUAGE plpgsql;
