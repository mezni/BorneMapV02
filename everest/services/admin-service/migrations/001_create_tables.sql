-- ===================================
-- Enable extensions
-- ===================================
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS hstore;

------------------------------------------------------------
-- Lookup Tables (Enum-like)
------------------------------------------------------------

CREATE TABLE access_types (
    id SERIAL PRIMARY KEY,
    name VARCHAR(50) NOT NULL UNIQUE,
    description TEXT
);

CREATE TABLE data_sources (
    id SERIAL PRIMARY KEY,
    name VARCHAR(50) NOT NULL UNIQUE,
    description TEXT
);

CREATE TABLE connector_types (
    id SERIAL PRIMARY KEY,
    name VARCHAR(50) NOT NULL UNIQUE,
    description TEXT
);

CREATE TABLE current_types (
    id SERIAL PRIMARY KEY,
    name VARCHAR(20) NOT NULL UNIQUE,
    description TEXT
);

CREATE TABLE connector_statuses (
    id SERIAL PRIMARY KEY,
    name VARCHAR(20) NOT NULL UNIQUE,
    description TEXT
);

------------------------------------------------------------
-- Networks
------------------------------------------------------------

CREATE TABLE networks (
    network_id VARCHAR(32) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    network_type VARCHAR(20) NOT NULL CHECK (network_type IN ('INDIVIDUAL', 'COMPANY')),
    support_phone VARCHAR(50),
    support_email VARCHAR(255),
    is_verified BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    created_by VARCHAR(36),
    updated_by VARCHAR(36)
);

------------------------------------------------------------
-- Stations
------------------------------------------------------------

CREATE TABLE stations (
    station_id VARCHAR(32) PRIMARY KEY,
    osm_id BIGINT UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    address TEXT,
    location GEOGRAPHY(Point, 4326) NOT NULL,
    tags HSTORE,
    network_id VARCHAR(32) REFERENCES networks(network_id),
    created_by VARCHAR(36),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_by VARCHAR(36),
    updated_at TIMESTAMPTZ
);

------------------------------------------------------------
-- Users
------------------------------------------------------------

CREATE TABLE users (
    user_id VARCHAR(36) PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    email VARCHAR(100) NOT NULL UNIQUE,
    password VARCHAR(255) NOT NULL,
    role VARCHAR(20) NOT NULL CHECK (role IN ('admin', 'partner', 'operator', 'user')),
    network_id VARCHAR(32) REFERENCES networks(network_id),
    station_id VARCHAR(32) REFERENCES stations(station_id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ,
    created_by VARCHAR(36),
    updated_by VARCHAR(36)
);

------------------------------------------------------------
-- Connectors
------------------------------------------------------------

CREATE TABLE connectors (
    connector_id VARCHAR(32) PRIMARY KEY,
    station_id VARCHAR(32) NOT NULL REFERENCES stations(station_id) ON DELETE CASCADE,
    connector_type_id BIGINT NOT NULL REFERENCES connector_types(id) ON DELETE CASCADE,
    status_id BIGINT NOT NULL REFERENCES connector_statuses(id) ON DELETE CASCADE,
    current_type_id BIGINT NOT NULL REFERENCES current_types(id) ON DELETE CASCADE,
    power_kw DECIMAL(5,2),
    voltage INT,
    amperage INT,
    count_available INT DEFAULT 1 CHECK (count_available >= 0),
    count_total INT DEFAULT 1 CHECK (count_total >= 1 AND count_total >= count_available),
    created_by VARCHAR(36),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_by VARCHAR(36),
    updated_at TIMESTAMPTZ,
    CONSTRAINT unique_connector UNIQUE (station_id, connector_type_id, current_type_id)
);

------------------------------------------------------------
-- User Reviews
------------------------------------------------------------

CREATE TABLE user_reviews (
    review_id VARCHAR(32) PRIMARY KEY,
    user_id VARCHAR(36),
    station_id VARCHAR(32) NOT NULL REFERENCES stations(station_id),
    rating INTEGER CHECK (rating BETWEEN 1 AND 5),
    review_text TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    created_by VARCHAR(36),
    updated_by VARCHAR(36)
);

------------------------------------------------------------
-- Indexes
------------------------------------------------------------

CREATE INDEX idx_stations_location ON stations USING GIST (location);
CREATE INDEX idx_stations_osm_id ON stations (osm_id);
CREATE INDEX idx_connectors_station_id ON connectors (station_id);
CREATE INDEX idx_connectors_status_id ON connectors (status_id);
CREATE INDEX idx_connectors_connector_type ON connectors (connector_type_id);
