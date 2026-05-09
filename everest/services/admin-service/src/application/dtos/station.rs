use crate::domain::entities::Station;
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use utoipa::ToSchema;
use validator::Validate;

#[derive(Debug, Deserialize, Validate, ToSchema)]
pub struct CreateStationRequest {
    pub osm_id: i64,
    #[validate(length(min = 1, max = 255))]
    pub name: String,
    pub address: Option<String>,
    #[validate(range(min = -90.0, max = 90.0))]
    pub latitude: f64,
    #[validate(range(min = -180.0, max = 180.0))]
    pub longitude: f64,
    // Keep HashMap here so the API user sends a simple JSON object
    pub tags: Option<HashMap<String, String>>,
    pub network_id: Option<String>,
}

#[derive(Debug, Deserialize, ToSchema)]
pub struct UpdateStationRequest {
    pub name: Option<String>,
    pub address: Option<String>,
    pub latitude: Option<f64>,
    pub longitude: Option<f64>,
    pub tags: Option<HashMap<String, String>>,
    pub network_id: Option<String>,
}

#[derive(Debug, Serialize, ToSchema)]
pub struct StationResponse {
    pub station_id: String,
    pub osm_id: i64,
    pub name: String,
    pub address: Option<String>,
    pub latitude: f64,
    pub longitude: f64,
    pub tags: Option<serde_json::Value>, // Correctly matches Entity
    pub network_id: Option<String>,
    pub created_at: String,
    pub updated_at: Option<String>,
}

impl From<Station> for StationResponse {
    fn from(station: Station) -> Self {
        Self {
            station_id: station.station_id,
            osm_id: station.osm_id,
            name: station.name,
            address: station.address,
            latitude: station.latitude,
            longitude: station.longitude,
            tags: station.tags, // This now works because both are Option<serde_json::Value>
            network_id: station.network_id,
            created_at: station.created_at.to_rfc3339(),
            updated_at: station.updated_at.map(|dt| dt.to_rfc3339()),
        }
    }
}
