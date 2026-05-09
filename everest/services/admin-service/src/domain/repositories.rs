use super::entities::{Connector, Network, Station};
use crate::core::errors::AppResult;
use async_trait::async_trait;

#[async_trait]
pub trait NetworkRepository: Send + Sync {
    async fn create(&self, network: &Network) -> AppResult<Network>;
    async fn find_by_id(&self, network_id: &str) -> AppResult<Option<Network>>;
    async fn find_all(&self, limit: i64, offset: i64) -> AppResult<Vec<Network>>;
    async fn update(&self, network: &Network) -> AppResult<Network>;
    async fn delete(&self, network_id: &str) -> AppResult<()>;
    async fn count(&self) -> AppResult<i64>;
}

#[async_trait]
pub trait StationRepository: Send + Sync {
    async fn create(&self, station: &Station) -> AppResult<Station>;
    async fn find_by_id(&self, station_id: &str) -> AppResult<Option<Station>>;
    async fn find_by_network(
        &self,
        network_id: &str,
        limit: i64,
        offset: i64,
    ) -> AppResult<Vec<Station>>;
    async fn find_all(&self, limit: i64, offset: i64) -> AppResult<Vec<Station>>;
    async fn update(&self, station: &Station) -> AppResult<Station>;
    async fn delete(&self, station_id: &str) -> AppResult<()>;
    async fn count(&self) -> AppResult<i64>;
}

#[async_trait]
pub trait ConnectorRepository: Send + Sync {
    async fn create(&self, connector: &Connector) -> AppResult<Connector>;
    async fn find_by_id(&self, connector_id: &str) -> AppResult<Option<Connector>>;
    async fn find_by_station(&self, station_id: &str) -> AppResult<Vec<Connector>>;
    async fn find_all(&self, limit: i64, offset: i64) -> AppResult<Vec<Connector>>;
    async fn update(&self, connector: &Connector) -> AppResult<Connector>;
    async fn delete(&self, connector_id: &str) -> AppResult<()>;
    async fn count(&self) -> AppResult<i64>;
}
