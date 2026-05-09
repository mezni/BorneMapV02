use super::entities::{Connector, Network, Station};
use crate::core::errors::AppResult;
use crate::domain::value_objects::{
    CreateConnectorData, CreateNetworkData, CreateStationData, UpdateConnectorData,
    UpdateNetworkData, UpdateStationData,
};
use async_trait::async_trait;

#[async_trait]
pub trait NetworkService: Send + Sync {
    async fn create_network(&self, data: CreateNetworkData) -> AppResult<Network>;
    async fn get_network(&self, network_id: &str) -> AppResult<Network>;
    async fn list_networks(&self, limit: i64, offset: i64) -> AppResult<(Vec<Network>, i64)>;
    async fn update_network(&self, network_id: &str, data: UpdateNetworkData)
    -> AppResult<Network>;
    async fn delete_network(&self, network_id: &str) -> AppResult<()>;
}

#[async_trait]
pub trait StationService: Send + Sync {
    async fn create_station(&self, data: CreateStationData) -> AppResult<Station>;
    async fn get_station(&self, station_id: &str) -> AppResult<Station>;
    async fn list_stations(
        &self,
        network_id: Option<String>,
        limit: i64,
        offset: i64,
    ) -> AppResult<(Vec<Station>, i64)>;
    async fn update_station(&self, station_id: &str, data: UpdateStationData)
    -> AppResult<Station>;
    async fn delete_station(&self, station_id: &str) -> AppResult<()>;
}

#[async_trait]
pub trait ConnectorService: Send + Sync {
    async fn create_connector(&self, data: CreateConnectorData) -> AppResult<Connector>;
    async fn get_connector(&self, connector_id: &str) -> AppResult<Connector>;
    async fn list_connectors(
        &self,
        station_id: Option<String>,
        limit: i64,
        offset: i64,
    ) -> AppResult<(Vec<Connector>, i64)>;
    async fn update_connector(
        &self,
        connector_id: &str,
        data: UpdateConnectorData,
    ) -> AppResult<Connector>;
    async fn delete_connector(&self, connector_id: &str) -> AppResult<()>;
}
