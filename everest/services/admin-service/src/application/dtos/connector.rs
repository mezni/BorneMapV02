use crate::domain::entities::Connector;
use serde::{Deserialize, Serialize};
use utoipa::ToSchema;
use validator::Validate;

#[derive(Debug, Deserialize, Validate, ToSchema)]
pub struct CreateConnectorRequest {
    pub station_id: String,
    pub connector_type_id: i64,
    pub status_id: i64,
    pub current_type_id: i64,
    pub power_kw: Option<f64>, // Changed from String to f64
    pub voltage: Option<i32>,
    pub amperage: Option<i32>,
    #[validate(range(min = 0))]
    pub count_available: i32,
    #[validate(range(min = 1))]
    pub count_total: i32,
}

#[derive(Debug, Deserialize, ToSchema)]
pub struct UpdateConnectorRequest {
    pub connector_type_id: Option<i64>,
    pub status_id: Option<i64>,
    pub current_type_id: Option<i64>,
    pub power_kw: Option<f64>, // Changed from String to f64
    pub voltage: Option<i32>,
    pub amperage: Option<i32>,
    pub count_available: Option<i32>,
    pub count_total: Option<i32>,
}

#[derive(Debug, Serialize, ToSchema)]
pub struct ConnectorResponse {
    pub connector_id: String,
    pub station_id: String,
    pub connector_type_id: i64,
    pub status_id: i64,
    pub current_type_id: i64,
    pub power_kw: Option<f64>, // Changed from String to f64
    pub voltage: Option<i32>,
    pub amperage: Option<i32>,
    pub count_available: i32,
    pub count_total: i32,
    pub created_at: String,
    pub updated_at: Option<String>,
}

impl From<Connector> for ConnectorResponse {
    fn from(connector: Connector) -> Self {
        Self {
            connector_id: connector.connector_id,
            station_id: connector.station_id,
            connector_type_id: connector.connector_type_id,
            status_id: connector.status_id,
            current_type_id: connector.current_type_id,
            power_kw: connector.power_kw, // Direct assignment, no conversion needed
            voltage: connector.voltage,
            amperage: connector.amperage,
            count_available: connector.count_available,
            count_total: connector.count_total,
            created_at: connector.created_at.to_rfc3339(),
            updated_at: connector.updated_at.map(|dt| dt.to_rfc3339()),
        }
    }
}
