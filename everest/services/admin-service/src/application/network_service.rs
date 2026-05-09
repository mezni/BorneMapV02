use crate::core::constants::*;
use crate::core::errors::{AppError, AppResult};
use crate::core::utils::generate_id;
use crate::domain::entities::Network;
use crate::domain::repositories::NetworkRepository;
use crate::domain::services::NetworkService;
use crate::domain::value_objects::{CreateNetworkData, UpdateNetworkData};
use async_trait::async_trait;
use chrono::Utc;
use std::sync::Arc;

pub struct NetworkServiceImpl {
    network_repo: Arc<dyn NetworkRepository>,
}

impl NetworkServiceImpl {
    pub fn new(network_repo: Arc<dyn NetworkRepository>) -> Self {
        Self { network_repo }
    }
}

#[async_trait]
impl NetworkService for NetworkServiceImpl {
    async fn create_network(&self, data: CreateNetworkData) -> AppResult<Network> {
        // Validate network type
        if data.network_type != "INDIVIDUAL" && data.network_type != "COMPANY" {
            return Err(AppError::ValidationError(
                "Network type must be INDIVIDUAL or COMPANY".to_string(),
            ));
        }

        let network = Network {
            network_id: generate_id(NETWORK_ID_PREFIX),
            name: data.name,
            network_type: data.network_type,
            support_phone: data.support_phone,
            support_email: data.support_email,
            is_verified: false,
            created_at: Utc::now(),
            updated_at: Utc::now(),
            created_by: None,
            updated_by: None,
        };

        self.network_repo.create(&network).await
    }

    async fn get_network(&self, network_id: &str) -> AppResult<Network> {
        self.network_repo
            .find_by_id(network_id)
            .await?
            .ok_or(AppError::NotFound("Network not found".to_string()))
    }

    async fn list_networks(&self, limit: i64, offset: i64) -> AppResult<(Vec<Network>, i64)> {
        let networks = self.network_repo.find_all(limit, offset).await?;
        let total = self.network_repo.count().await?;
        Ok((networks, total))
    }

    async fn update_network(
        &self,
        network_id: &str,
        data: UpdateNetworkData,
    ) -> AppResult<Network> {
        let mut network = self.get_network(network_id).await?;

        if let Some(name) = data.name {
            network.name = name;
        }
        if let Some(network_type) = data.network_type {
            if network_type != "INDIVIDUAL" && network_type != "COMPANY" {
                return Err(AppError::ValidationError(
                    "Network type must be INDIVIDUAL or COMPANY".to_string(),
                ));
            }
            network.network_type = network_type;
        }
        if let Some(phone) = data.support_phone {
            network.support_phone = Some(phone);
        }
        if let Some(email) = data.support_email {
            network.support_email = Some(email);
        }
        if let Some(verified) = data.is_verified {
            network.is_verified = verified;
        }

        network.updated_at = Utc::now();
        self.network_repo.update(&network).await
    }

    async fn delete_network(&self, network_id: &str) -> AppResult<()> {
        let _ = self.get_network(network_id).await?;
        self.network_repo.delete(network_id).await
    }
}
