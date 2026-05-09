use crate::core::constants::*;
use crate::core::errors::{AppError, AppResult};
use crate::core::utils::generate_id;
use crate::domain::entities::Station;
use crate::domain::repositories::StationRepository;
use crate::domain::services::StationService;
use crate::domain::value_objects::{CreateStationData, UpdateStationData};
use async_trait::async_trait;
use chrono::Utc;
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
    async fn create_station(&self, data: CreateStationData) -> AppResult<Station> {
        // Validate coordinates
        if data.latitude < -90.0 || data.latitude > 90.0 {
            return Err(AppError::ValidationError(
                "Latitude must be between -90 and 90".to_string(),
            ));
        }
        if data.longitude < -180.0 || data.longitude > 180.0 {
            return Err(AppError::ValidationError(
                "Longitude must be between -180 and 180".to_string(),
            ));
        }

        let station = Station {
            station_id: generate_id(STATION_ID_PREFIX),
            osm_id: data.osm_id,
            name: data.name,
            address: data.address,
            latitude: data.latitude,
            longitude: data.longitude,
            tags: data.tags,
            network_id: data.network_id,
            created_by: None,
            created_at: Utc::now(),
            updated_by: None,
            updated_at: None,
        };

        self.station_repo.create(&station).await
    }

    async fn get_station(&self, station_id: &str) -> AppResult<Station> {
        self.station_repo
            .find_by_id(station_id)
            .await?
            .ok_or(AppError::NotFound("Station not found".to_string()))
    }

    async fn list_stations(
        &self,
        network_id: Option<String>,
        limit: i64,
        offset: i64,
    ) -> AppResult<(Vec<Station>, i64)> {
        let stations = if let Some(net_id) = network_id {
            self.station_repo
                .find_by_network(&net_id, limit, offset)
                .await?
        } else {
            self.station_repo.find_all(limit, offset).await?
        };
        let total = self.station_repo.count().await?;
        Ok((stations, total))
    }

    async fn update_station(
        &self,
        station_id: &str,
        data: UpdateStationData,
    ) -> AppResult<Station> {
        let mut station = self.get_station(station_id).await?;

        if let Some(name) = data.name {
            station.name = name;
        }
        if let Some(address) = data.address {
            station.address = Some(address);
        }
        if let Some(lat) = data.latitude {
            if lat < -90.0 || lat > 90.0 {
                return Err(AppError::ValidationError(
                    "Latitude must be between -90 and 90".to_string(),
                ));
            }
            station.latitude = lat;
        }
        if let Some(lon) = data.longitude {
            if lon < -180.0 || lon > 180.0 {
                return Err(AppError::ValidationError(
                    "Longitude must be between -180 and 180".to_string(),
                ));
            }
            station.longitude = lon;
        }
        if let Some(tags) = data.tags {
            station.tags = Some(tags);
        }
        if let Some(network_id) = data.network_id {
            station.network_id = Some(network_id);
        }

        station.updated_at = Some(Utc::now());
        self.station_repo.update(&station).await
    }

    async fn delete_station(&self, station_id: &str) -> AppResult<()> {
        let _ = self.get_station(station_id).await?;
        self.station_repo.delete(station_id).await
    }
}
