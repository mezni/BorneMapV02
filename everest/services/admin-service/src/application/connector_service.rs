use crate::core::constants::*;
use crate::core::errors::{AppError, AppResult};
use crate::core::utils::generate_id;
use crate::domain::entities::Connector;
use crate::domain::repositories::ConnectorRepository;
use crate::domain::services::ConnectorService;
use crate::domain::value_objects::{CreateConnectorData, UpdateConnectorData};
use async_trait::async_trait;
use chrono::Utc;
use std::sync::Arc;

pub struct ConnectorServiceImpl {
    connector_repo: Arc<dyn ConnectorRepository>,
}

impl ConnectorServiceImpl {
    pub fn new(connector_repo: Arc<dyn ConnectorRepository>) -> Self {
        Self { connector_repo }
    }
}

#[async_trait]
impl ConnectorService for ConnectorServiceImpl {
    async fn create_connector(&self, data: CreateConnectorData) -> AppResult<Connector> {
        // Validate counts
        if data.count_total < 1 {
            return Err(AppError::ValidationError(
                "count_total must be at least 1".to_string(),
            ));
        }
        if data.count_available > data.count_total {
            return Err(AppError::ValidationError(
                "count_available cannot exceed count_total".to_string(),
            ));
        }

        let connector = Connector {
            connector_id: generate_id(CONNECTOR_ID_PREFIX),
            station_id: data.station_id,
            connector_type_id: data.connector_type_id,
            status_id: data.status_id,
            current_type_id: data.current_type_id,
            power_kw: data.power_kw,
            voltage: data.voltage,
            amperage: data.amperage,
            count_available: data.count_available,
            count_total: data.count_total,
            created_by: None,
            created_at: Utc::now(),
            updated_by: None,
            updated_at: None,
        };

        self.connector_repo.create(&connector).await
    }

    async fn get_connector(&self, connector_id: &str) -> AppResult<Connector> {
        self.connector_repo
            .find_by_id(connector_id)
            .await?
            .ok_or(AppError::NotFound("Connector not found".to_string()))
    }

    async fn list_connectors(
        &self,
        station_id: Option<String>,
        limit: i64,
        offset: i64,
    ) -> AppResult<(Vec<Connector>, i64)> {
        let connectors = if let Some(sta_id) = station_id {
            self.connector_repo.find_by_station(&sta_id).await?
        } else {
            self.connector_repo.find_all(limit, offset).await?
        };
        let total = self.connector_repo.count().await?;
        Ok((connectors, total))
    }

    async fn update_connector(
        &self,
        connector_id: &str,
        data: UpdateConnectorData,
    ) -> AppResult<Connector> {
        let mut connector = self.get_connector(connector_id).await?;

        if let Some(type_id) = data.connector_type_id {
            connector.connector_type_id = type_id;
        }
        if let Some(status_id) = data.status_id {
            connector.status_id = status_id;
        }
        if let Some(current_id) = data.current_type_id {
            connector.current_type_id = current_id;
        }
        if let Some(power) = data.power_kw {
            connector.power_kw = Some(power);
        }
        if let Some(voltage) = data.voltage {
            connector.voltage = Some(voltage);
        }
        if let Some(amperage) = data.amperage {
            connector.amperage = Some(amperage);
        }
        if let Some(available) = data.count_available {
            connector.count_available = available;
        }
        if let Some(total) = data.count_total {
            connector.count_total = total;
        }

        // Validate counts after update
        if connector.count_available > connector.count_total {
            return Err(AppError::ValidationError(
                "count_available cannot exceed count_total".to_string(),
            ));
        }

        connector.updated_at = Some(Utc::now());
        self.connector_repo.update(&connector).await
    }

    async fn delete_connector(&self, connector_id: &str) -> AppResult<()> {
        let _ = self.get_connector(connector_id).await?;
        self.connector_repo.delete(connector_id).await
    }
}
