use crate::core::constants::*;
use crate::core::errors::{AppError, AppResult};
use crate::domain::entities::Station;
use crate::domain::repositories::StationRepository;
use crate::domain::services::StationService;
use async_trait::async_trait;
use std::sync::Arc;

pub struct StationServiceImpl {
    station_repo: Arc<dyn StationRepository>,
}

impl StationServiceImpl {
    pub fn new(station_repo: Arc<dyn StationRepository>) -> Self {
        Self { station_repo }
    }
}

#[async_trait]
impl StationService for StationServiceImpl {
    async fn find_nearby_stations(
        &self,
        latitude: f64,
        longitude: f64,
        radius_meters: Option<i32>,
        limit: Option<i32>,
    ) -> AppResult<Vec<Station>> {
        // Validate coordinates
        if latitude < -90.0 || latitude > 90.0 {
            return Err(AppError::ValidationError(
                "Latitude must be between -90 and 90".to_string(),
            ));
        }
        if longitude < -180.0 || longitude > 180.0 {
            return Err(AppError::ValidationError(
                "Longitude must be between -180 and 180".to_string(),
            ));
        }

        let radius = radius_meters.unwrap_or(DEFAULT_RADIUS_METERS);
        if radius <= 0 || radius > MAX_RADIUS_METERS {
            return Err(AppError::ValidationError(format!(
                "Radius must be between 1 and {} meters",
                MAX_RADIUS_METERS
            )));
        }

        let limit_val = limit.unwrap_or(DEFAULT_LIMIT);
        if limit_val <= 0 || limit_val > MAX_LIMIT {
            return Err(AppError::ValidationError(format!(
                "Limit must be between 1 and {}",
                MAX_LIMIT
            )));
        }

        self.station_repo
            .find_nearby(latitude, longitude, radius, limit_val)
            .await
    }
}
