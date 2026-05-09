use crate::core::errors::AppResult;
use crate::domain::entities::Station;
use crate::domain::repositories::StationRepository;
use async_trait::async_trait;
use sqlx::PgPool;

pub struct PgStationRepository {
    pool: PgPool,
}

impl PgStationRepository {
    pub fn new(pool: PgPool) -> Self {
        Self { pool }
    }
}

#[async_trait]
impl StationRepository for PgStationRepository {
    async fn find_nearby(
        &self,
        latitude: f64,
        longitude: f64,
        radius_meters: i32,
        limit: i32,
    ) -> AppResult<Vec<Station>> {
        let stations = sqlx::query_as::<_, Station>(
            r#"
            SELECT 
                station_id,
                name,
                address,
                distance_meters,
                has_available_connectors,
                total_available_connectors,
                max_power_kw,
                power_tier,
                operator,
                latitude,
                longitude
            FROM find_nearby_stations($1, $2, $3, $4)
            "#,
        )
        .bind(latitude)
        .bind(longitude)
        .bind(radius_meters)
        .bind(limit)
        .fetch_all(&self.pool)
        .await?;

        Ok(stations)
    }
}