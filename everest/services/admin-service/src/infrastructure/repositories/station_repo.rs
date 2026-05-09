use crate::core::errors::AppResult;
use crate::domain::entities::Station;
use crate::domain::repositories::StationRepository;
use async_trait::async_trait;
use chrono::{DateTime, Utc};
use serde_json::Value;
use sqlx::PgPool;

pub struct PgStationRepository {
    pool: PgPool,
}

impl PgStationRepository {
    pub fn new(pool: PgPool) -> Self {
        Self { pool }
    }
}

type StationRow = (
    String,
    i64,
    String,
    Option<String>,
    f64,
    f64,
    Option<Value>,
    Option<String>,
    Option<String>,
    DateTime<Utc>,
    Option<String>,
    Option<DateTime<Utc>>,
);

#[async_trait]
impl StationRepository for PgStationRepository {
    async fn create(&self, station: &Station) -> AppResult<Station> {
        sqlx::query(
            r#"INSERT INTO stations (station_id, osm_id, name, address, location, tags, network_id, created_by, created_at) 
               VALUES ($1, $2, $3, $4, ST_SetSRID(ST_MakePoint($5, $6), 4326)::geography, $7::jsonb::hstore, $8, $9, $10)"#
        )
        .bind(&station.station_id).bind(station.osm_id).bind(&station.name).bind(&station.address)
        .bind(station.longitude).bind(station.latitude).bind(&station.tags).bind(&station.network_id)
        .bind(&station.created_by).bind(station.created_at)
        .execute(&self.pool).await?;
        Ok(station.clone())
    }

    async fn find_by_id(&self, id: &str) -> AppResult<Option<Station>> {
        let row = sqlx::query_as::<_, StationRow>(
            r#"SELECT station_id, osm_id, name, address, ST_Y(location::geometry), ST_X(location::geometry), 
               tags::jsonb, network_id, created_by, created_at, updated_by, updated_at FROM stations WHERE station_id = $1"#
        ).bind(id).fetch_optional(&self.pool).await?;
        Ok(row.map(map_row))
    }

    async fn update(&self, s: &Station) -> AppResult<Station> {
        sqlx::query(r#"UPDATE stations SET name=$2, address=$3, location=ST_SetSRID(ST_MakePoint($4, $5), 4326)::geography, 
                       tags=$6::jsonb::hstore, network_id=$7, updated_at=$8 WHERE station_id=$1"#)
        .bind(&s.station_id).bind(&s.name).bind(&s.address).bind(s.longitude).bind(s.latitude)
        .bind(&s.tags).bind(&s.network_id).bind(Utc::now())
        .execute(&self.pool).await?;
        Ok(s.clone())
    }

    async fn find_all(&self, limit: i64, offset: i64) -> AppResult<Vec<Station>> {
        let rows = sqlx::query_as::<_, StationRow>(
            r#"SELECT station_id, osm_id, name, address, ST_Y(location::geometry), ST_X(location::geometry), 
               tags::jsonb, network_id, created_by, created_at, updated_by, updated_at FROM stations LIMIT $1 OFFSET $2"#
        ).bind(limit).bind(offset).fetch_all(&self.pool).await?;
        Ok(rows.into_iter().map(map_row).collect())
    }

    async fn find_by_network(&self, id: &str, limit: i64, offset: i64) -> AppResult<Vec<Station>> {
        let rows = sqlx::query_as::<_, StationRow>(
            r#"SELECT station_id, osm_id, name, address, ST_Y(location::geometry), ST_X(location::geometry), 
               tags::jsonb, network_id, created_by, created_at, updated_by, updated_at FROM stations WHERE network_id = $1 LIMIT $2 OFFSET $3"#
        ).bind(id).bind(limit).bind(offset).fetch_all(&self.pool).await?;
        Ok(rows.into_iter().map(map_row).collect())
    }

    async fn delete(&self, id: &str) -> AppResult<()> {
        sqlx::query("DELETE FROM stations WHERE station_id = $1")
            .bind(id)
            .execute(&self.pool)
            .await?;
        Ok(())
    }

    async fn count(&self) -> AppResult<i64> {
        let res: (i64,) = sqlx::query_as("SELECT COUNT(*) FROM stations")
            .fetch_one(&self.pool)
            .await?;
        Ok(res.0)
    }
}

fn map_row(r: StationRow) -> Station {
    Station {
        station_id: r.0,
        osm_id: r.1,
        name: r.2,
        address: r.3,
        latitude: r.4,
        longitude: r.5,
        tags: r.6,
        network_id: r.7,
        created_by: r.8,
        created_at: r.9,
        updated_by: r.10,
        updated_at: r.11,
    }
}
