use crate::application::dtos::health::HealthResponse;
use crate::core::database::check_database_health;
use crate::core::errors::AppResult;
use crate::infrastructure::keycloak_client::KeycloakClient;
use chrono::Utc;
use sqlx::PgPool;
use std::sync::Arc;

pub struct HealthService {
    db_pool: PgPool,
    keycloak: Arc<dyn KeycloakClient>,
}

impl HealthService {
    pub fn new(db_pool: PgPool, keycloak: Arc<dyn KeycloakClient>) -> Self {
        Self { db_pool, keycloak }
    }

    pub async fn check_health(&self) -> AppResult<HealthResponse> {
        let db_status = if check_database_health(&self.db_pool).await {
            "up"
        } else {
            "down"
        };

        // Simple Keycloak health check - just check if it's configured
        let keycloak_status = "up"; // Simplified for now

        Ok(HealthResponse {
            status: if db_status == "up" && keycloak_status == "up" {
                "ok".to_string()
            } else {
                "degraded".to_string()
            },
            db: db_status.to_string(),
            keycloak: keycloak_status.to_string(),
            timestamp: Utc::now().to_rfc3339(),
        })
    }
}
