-- ===========================
-- Sample Users
-- ===========================
INSERT INTO users (user_id, username, email, password, role) VALUES
('USR-F4T8Y3K2J5L9N1P', 'admin', 'admin@charging.com', '$2b$12$LQv3c1yqBWVHxkd0L6k0uO9S6VY6Qk8JvY8cZc6vY6X2rV8c6vY6X', 'admin'),
('USR-J8D5P2K1M7L4A3B', 'operator1', 'operator@charging.com', '$2b$12$LQv3c1yqBWVHxkd0L6k0uO9S6VY6Qk8JvY8cZc6vY6X2rV8c6vY6X', 'operator'),
('USR-N2Q1R6S8T4U9V0X', 'user1', 'user1@charging.com', '$2b$12$LQv3c1yqBWVHxkd0L6k0uO9S6VY6Qk8JvY8cZc6vY6X2rV8c6vY6X', 'user'),
('USR-K3L5M7N2P8Q4R6S', 'partner1', 'partner1@charging.com', '$2b$12$LQv3c1yqBWVHxkd0L6k0uO9S6VY6Qk8JvY8cZc6vY6X2rV8c6vY6X', 'partner');

-- ===========================
-- Sample Networks
-- ===========================
INSERT INTO networks (network_id, name, network_type, created_by) VALUES
('NET-B6C8D0E2F4G6H8I', 'STEG', 'COMPANY', 'USR-F4T8Y3K2J5L9N1P'),
('NET-T3U5V7W9X1Y3Z5A', 'Golden Tulip', 'COMPANY', 'USR-F4T8Y3K2J5L9N1P'),
('NET-C2D4E6F8G0H2I4J', 'Tunisia Mall', 'COMPANY', 'USR-F4T8Y3K2J5L9N1P'),
('NET-L0M2N4O6P8Q0R2S', 'Energym', 'COMPANY', 'USR-F4T8Y3K2J5L9N1P'),
('NET-B2C4D6E8F0G2H4I', 'The Residence', 'COMPANY', 'USR-F4T8Y3K2J5L9N1P'),
('NET-R2S4T6U8V0W2X4Y', 'Carrefour', 'COMPANY', 'USR-F4T8Y3K2J5L9N1P'),
('NET-H2I4J6K8L0M2N4O', 'Tunis Airport', 'COMPANY', 'USR-F4T8Y3K2J5L9N1P'),
('NET-Y2Z4A6B8C0D2E4F', 'ENNOUR', 'COMPANY', 'USR-F4T8Y3K2J5L9N1P');

-- ===========================
-- Sample Stations
-- ===========================
INSERT INTO stations (station_id, osm_id, name, address, location, tags, network_id, created_by) VALUES
('STA-F4T8Y3K2J5L9N1P6', 202500000001, 'STEG Charging Station - Lac', 'Lac de Tunis, near Tunis City Center', ST_GeogFromText('POINT(10.2417 36.8380)'),
 hstore(ARRAY[['amenity','charging_station'],['operator','STEG'],['capacity','4'],['fee','no'],['parking_fee','no'],['access','public']]), 'NET-B6C8D0E2F4G6H8I', 'USR-F4T8Y3K2J5L9N1P'),
('STA-J8D5P2K1M7L4A3B9', 202500000002, 'Hotel Golden Tulip El Mechtel', 'Avenue Ouled Haffouz, Tunis', ST_GeogFromText('POINT(10.2087 36.8374)'),
 hstore(ARRAY[['amenity','charging_station'],['operator','Golden Tulip'],['capacity','2'],['fee','yes'],['parking_fee','yes'],['access','customers']]), 'NET-T3U5V7W9X1Y3Z5A', 'USR-F4T8Y3K2J5L9N1P'),
('STA-N2Q1R6S8T4U9V0X5', 202500000003, 'Tunisia Mall Charging Point', 'Les Berges du Lac, Tunis', ST_GeogFromText('POINT(10.2376 36.8510)'),
 hstore(ARRAY[['amenity','charging_station'],['operator','Tunisia Mall'],['capacity','6'],['fee','no'],['parking_fee','yes'],['access','public']]), 'NET-C2D4E6F8G0H2I4J', 'USR-F4T8Y3K2J5L9N1P'),
('STA-K3L5M7N2P8Q4R6S1', 202500000004, 'Energym Charging Station', 'La Goulette, Tunis', ST_GeogFromText('POINT(10.3050 36.8185)'),
 hstore(ARRAY[['amenity','charging_station'],['operator','Energym'],['capacity','8'],['fee','yes'],['parking_fee','no'],['access','public']]), 'NET-L0M2N4O6P8Q0R2S', 'USR-F4T8Y3K2J5L9N1P'),
('STA-B6C8D0E2F4G6H8I1', 202500000005, 'The Residence Tunis', 'Gammarth, Tunis', ST_GeogFromText('POINT(10.3234 36.9542)'),
 hstore(ARRAY[['amenity','charging_station'],['operator','The Residence'],['capacity','2'],['fee','no'],['parking_fee','no'],['access','customers']]), 'NET-B2C4D6E8F0G2H4I', 'USR-F4T8Y3K2J5L9N1P'),
('STA-L0M2N4O6P8Q0R2S5', 202500000006, 'Carrefour Charging Point', 'Marsa, Tunis', ST_GeogFromText('POINT(10.3247 36.8782)'),
 hstore(ARRAY[['amenity','charging_station'],['operator','Carrefour'],['capacity','4'],['fee','no'],['parking_fee','no'],['access','public']]), 'NET-R2S4T6U8V0W2X4Y', 'USR-F4T8Y3K2J5L9N1P'),
('STA-T3U5V7W9X1Y3Z5A8', 202500000007, 'Aeroport Tunis-Carthage', 'Aéroport International de Tunis-Carthage', ST_GeogFromText('POINT(10.2272 36.8510)'),
 hstore(ARRAY[['amenity','charging_station'],['operator','Tunis Air'],['capacity','4'],['fee','yes'],['parking_fee','yes'],['access','public']]), 'NET-H2I4J6K8L0M2N4O', 'USR-F4T8Y3K2J5L9N1P'),
('STA-C2D4E6F8G0H2I4J7', 202500000008, 'Station ENNOUR', 'Route de La Marsa, Carthage', ST_GeogFromText('POINT(10.3215 36.8612)'),
 hstore(ARRAY[['amenity','charging_station'],['operator','ENNOUR'],['capacity','2'],['fee','yes'],['parking_fee','no'],['access','public']]), 'NET-Y2Z4A6B8C0D2E4F', 'USR-F4T8Y3K2J5L9N1P');

-- ===========================
-- Sample Connectors
-- ===========================
INSERT INTO connectors (
    connector_id, station_id, connector_type_id, status_id, current_type_id,
    power_kw, voltage, amperage, count_available, count_total, created_by
) VALUES
-- STA001
('CHR-F4T8Y3K2J5L9N1P', 'STA-F4T8Y3K2J5L9N1P6', 1, 1, 1, 22.0, 400, 32, 2, 2, 'USR-F4T8Y3K2J5L9N1P'),
('CHR-J8D5P2K1M7L4A3B', 'STA-F4T8Y3K2J5L9N1P6', 2, 1, 2, 50.0, 500, 125, 1, 2, 'USR-F4T8Y3K2J5L9N1P'),

-- STA002
('CHR-N2Q1R6S8T4U9V0X', 'STA-J8D5P2K1M7L4A3B9', 2, 1, 2, 150.0, 500, 300, 1, 1, 'USR-F4T8Y3K2J5L9N1P'),
('CHR-K3L5M7N2P8Q4R6S', 'STA-J8D5P2K1M7L4A3B9', 3, 2, 2, 50.0, 500, 125, 0, 1, 'USR-F4T8Y3K2J5L9N1P'),
('CHR-B6C8D0E2F4G6H8I', 'STA-J8D5P2K1M7L4A3B9', 1, 1, 1, 22.0, 400, 32, 1, 1, 'USR-F4T8Y3K2J5L9N1P'),

-- STA003
('CHR-L0M2N4O6P8Q0R2S', 'STA-N2Q1R6S8T4U9V0X5', 1, 1, 1, 11.0, 230, 16, 3, 4, 'USR-F4T8Y3K2J5L9N1P'),
('CHR-T3U5V7W9X1Y3Z5A', 'STA-N2Q1R6S8T4U9V0X5', 2, 1, 2, 100.0, 500, 200, 1, 1, 'USR-F4T8Y3K2J5L9N1P'),
('CHR-C2D4E6F8G0H2I4J', 'STA-N2Q1R6S8T4U9V0X5', 3, 1, 2, 50.0, 500, 125, 1, 1, 'USR-F4T8Y3K2J5L9N1P'),

-- STA004
('CHR-F1G3H5I7J9K1L3M', 'STA-K3L5M7N2P8Q4R6S1', 2, 1, 2, 350.0, 1000, 350, 2, 2, 'USR-F4T8Y3K2J5L9N1P'),
('CHR-N5O7P9Q1R3S5T7U', 'STA-K3L5M7N2P8Q4R6S1', 4, 1, 2, 250.0, 480, 520, 2, 2, 'USR-F4T8Y3K2J5L9N1P'),

-- STA005
('CHR-B2C4D6E8F0G2H4I', 'STA-B6C8D0E2F4G6H8I1', 1, 1, 1, 22.0, 400, 32, 2, 2, 'USR-F4T8Y3K2J5L9N1P'),
('CHR-J2K4L6M8N0O2P4Q', 'STA-B6C8D0E2F4G6H8I1', 2, 1, 2, 50.0, 500, 125, 1, 2, 'USR-F4T8Y3K2J5L9N1P'),

-- STA006
('CHR-R2S4T6U8V0W2X4Y', 'STA-L0M2N4O6P8Q0R2S5', 1, 1, 1, 11.0, 230, 16, 2, 2, 'USR-F4T8Y3K2J5L9N1P'),
('CHR-Z2A4B6C8D0E2F4G', 'STA-L0M2N4O6P8Q0R2S5', 5, 3, 1, 3.7, 230, 16, 0, 2, 'USR-F4T8Y3K2J5L9N1P'),

-- STA007
('CHR-H2I4J6K8L0M2N4O', 'STA-T3U5V7W9X1Y3Z5A8', 2, 1, 2, 150.0, 500, 300, 2, 2, 'USR-F4T8Y3K2J5L9N1P'),
('CHR-P2Q4R6S8T0U2V4W', 'STA-T3U5V7W9X1Y3Z5A8', 3, 1, 2, 50.0, 500, 125, 1, 2, 'USR-F4T8Y3K2J5L9N1P'),

-- STA008
('CHR-Y2Z4A6B8C0D2E4F', 'STA-C2D4E6F8G0H2I4J7', 1, 1, 1, 22.0, 400, 32, 2, 2, 'USR-F4T8Y3K2J5L9N1P'),
('CHR-G2H4I6J8K0L2M4N', 'STA-C2D4E6F8G0H2I4J7', 2, 1, 2, 50.0, 500, 125, 1, 2, 'USR-F4T8Y3K2J5L9N1P');

-- ===========================
-- Refresh Materialized Views
-- ===========================
REFRESH MATERIALIZED VIEW mv_stations_geo;
REFRESH MATERIALIZED VIEW mv_stations_summary;
REFRESH MATERIALIZED VIEW mv_connector_type_stats;
REFRESH MATERIALIZED VIEW mv_stations_reviews;
