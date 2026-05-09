use crate::domain::entities::Network;
use serde::{Deserialize, Serialize};
use utoipa::ToSchema;
use validator::Validate;

#[derive(Debug, Deserialize, Validate, ToSchema)]
pub struct CreateNetworkRequest {
    #[validate(length(min = 1, max = 255))]
    pub name: String,
    pub network_type: String,
    pub support_phone: Option<String>,
    #[validate(email)]
    pub support_email: Option<String>,
}

#[derive(Debug, Deserialize, ToSchema)]
pub struct UpdateNetworkRequest {
    pub name: Option<String>,
    pub network_type: Option<String>,
    pub support_phone: Option<String>,
    pub support_email: Option<String>,
    pub is_verified: Option<bool>,
}

#[derive(Debug, Serialize, ToSchema)]
pub struct NetworkResponse {
    pub network_id: String,
    pub name: String,
    pub network_type: String,
    pub support_phone: Option<String>,
    pub support_email: Option<String>,
    pub is_verified: bool,
    pub created_at: String,
    pub updated_at: String,
}

impl From<Network> for NetworkResponse {
    fn from(network: Network) -> Self {
        Self {
            network_id: network.network_id,
            name: network.name,
            network_type: network.network_type,
            support_phone: network.support_phone,
            support_email: network.support_email,
            is_verified: network.is_verified,
            created_at: network.created_at.to_rfc3339(),
            updated_at: network.updated_at.to_rfc3339(),
        }
    }
}
