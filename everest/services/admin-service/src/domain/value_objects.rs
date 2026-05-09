use serde::{Deserialize, Serialize};
use serde_json::Value;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CreateNetworkData {
    pub name: String,
    pub network_type: String,
    pub support_phone: Option<String>,
    pub support_email: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct UpdateNetworkData {
    pub name: Option<String>,
    pub network_type: Option<String>,
    pub support_phone: Option<String>,
    pub support_email: Option<String>,
    pub is_verified: Option<bool>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CreateStationData {
    pub osm_id: i64,
    pub name: String,
    pub address: Option<String>,
    pub latitude: f64,
    pub longitude: f64,
    pub tags: Option<Value>, // Use Value here
    pub network_id: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct UpdateStationData {
    pub name: Option<String>,
    pub address: Option<String>,
    pub latitude: Option<f64>,
    pub longitude: Option<f64>,
    pub tags: Option<Value>, // Use Value here
    pub network_id: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CreateConnectorData {
    pub station_id: String,
    pub connector_type_id: i64,
    pub status_id: i64,
    pub current_type_id: i64,
    pub power_kw: Option<f64>, // Changed from BigDecimal to f64
    pub voltage: Option<i32>,
    pub amperage: Option<i32>,
    pub count_available: i32,
    pub count_total: i32,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct UpdateConnectorData {
    pub connector_type_id: Option<i64>,
    pub status_id: Option<i64>,
    pub current_type_id: Option<i64>,
    pub power_kw: Option<f64>, // Changed from BigDecimal to f64
    pub voltage: Option<i32>,
    pub amperage: Option<i32>,
    pub count_available: Option<i32>,
    pub count_total: Option<i32>,
}
